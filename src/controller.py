from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Optional
import time
import uuid

from . import simulation


@dataclass
class Experiment:
    experiment_id: str
    scenario: str
    phase: str               # baseline | chaos | recovery
    started_at_ns: int
    status: str = "ACTIVE"   # ACTIVE | ENDED
    notes: str = ""

    # NEW: Netflix-aligned execution mode
    execution_mode: str = "sandbox"  # "sandbox" | "guardrailed"

    # NEW: guardrail config
    max_load_loss_pct: float = 0.20

    # NEW: guardrail state
    blast_radius_triggered: bool = False
    blast_radius_reason: Optional[str] = None


class GridController:
    """
    Single-writer control plane for deterministic chaos experiments.

    Why:
    - FastAPI can process concurrent requests.
    - Pandapower network objects are mutable.
    - We serialize mutations to avoid race conditions and nondeterminism.
    """
    def __init__(self):
        self._lock = Lock()
        self.net = simulation.create_grid()
        self.active_experiment: Optional[Experiment] = None
        self.simulation_id = str(uuid.uuid4())
        self.last_mutation_source = "init"  # scenario|manual|reset|status

    def reset(self) -> None:
        with self._lock:
            self.net = simulation.create_grid()
            self.simulation_id = str(uuid.uuid4())
            self.active_experiment = None
            self.last_mutation_source = "reset"

    def begin_experiment(self, scenario: str, notes: str = "", execution_mode: str = "sandbox", max_load_loss_pct: float = 0.20) -> Experiment:
        with self._lock:
            if self.active_experiment and self.active_experiment.status == "ACTIVE":
                raise RuntimeError("An experiment is already active. End it before starting a new one.")

            exp = Experiment(
                experiment_id=str(uuid.uuid4()),
                scenario=scenario,
                phase="baseline",
                started_at_ns=time.time_ns(),
                notes=notes,
                execution_mode=execution_mode,
                max_load_loss_pct=max_load_loss_pct,
            )
            self.active_experiment = exp
            self.last_mutation_source = "scenario"
            return exp

    def set_phase(self, phase: str) -> None:
        with self._lock:
            if self.active_experiment and self.active_experiment.status == "ACTIVE":
                self.active_experiment.phase = phase

    def end_experiment(self) -> None:
        with self._lock:
            if self.active_experiment:
                self.active_experiment.status = "ENDED"
                self.active_experiment.phase = "recovery"
            self.last_mutation_source = "end_experiment"

    def mutate(self, fn: Callable[..., Any], *args: Any, mutation_source: str = "manual", **kwargs: Any) -> Any:
        with self._lock:
            self.last_mutation_source = mutation_source
            return fn(self.net, *args, **kwargs)

    def read(self):
        with self._lock:
            return self.net
    def snapshot(self) -> Dict[str, Any]:
 
    #Runs simulation snapshot and applies blast radius guardrail if in guardrailed mode.
        with self._lock:
            exp = self.active_experiment

        # Build context without calling experiment_context() (avoids lock re-entry)
            if not exp:
                ctx = {
                    "experiment_id": "none",
                    "scenario": "none",
                    "phase": "baseline",
                    "simulation_id": self.simulation_id,
                    "mutation_source": self.last_mutation_source,
                }
                execution_mode = "sandbox"
                max_loss = 0.20
            else:
                ctx = {
                    "experiment_id": exp.experiment_id,
                    "scenario": exp.scenario,
                    "phase": exp.phase,
                    "simulation_id": self.simulation_id,
                    "mutation_source": self.last_mutation_source,
            }
            execution_mode = getattr(exp, "execution_mode", "sandbox")
            max_loss = float(getattr(exp, "max_load_loss_pct", 0.20))

        snap = simulation.run_simulation(self.net)
        if snap is None:
            return {
                "converged": False,
                "error": "Powerflow failed",
                "context": ctx,
                "execution_mode": execution_mode,
            }

        # Attach context
        snap["context"] = ctx
        snap["execution_mode"] = execution_mode

        # Apply guardrails only for guardrailed mode
        if exp and exp.status == "ACTIVE" and execution_mode == "guardrailed":
            total_load = float(snap.get("total_load_mw", 0.0))
            gen = float(snap.get("generation_mw", 0.0))

            if total_load > 0:
                est_loss_pct = max(0.0, (total_load - gen) / total_load)
            else:
                est_loss_pct = 0.0

            snap["estimated_load_loss_pct"] = round(est_loss_pct, 4)

            if est_loss_pct >= max_loss:
                exp.blast_radius_triggered = True
                exp.blast_radius_reason = (
                    f"Blast radius exceeded: estimated {est_loss_pct:.1%} load lost "
                    f"(limit {max_loss:.0%})"
                )

        # Always include guardrail state if experiment exists
        if exp:
            snap["blast_radius_triggered"] = getattr(exp, "blast_radius_triggered", False)
            snap["blast_radius_reason"] = getattr(exp, "blast_radius_reason", None)

        return snap

    def experiment_context(self) -> Dict[str, str]:
        with self._lock:
            if not self.active_experiment:
                return {
                    "experiment_id": "none",
                    "scenario": "none",
                    "phase": "baseline",
                    "simulation_id": self.simulation_id,
                    "mutation_source": self.last_mutation_source,
                }

            return {
                "experiment_id": self.active_experiment.experiment_id,
                "scenario": self.active_experiment.scenario,
                "phase": self.active_experiment.phase,
                "simulation_id": self.simulation_id,
                "mutation_source": self.last_mutation_source,
            }
