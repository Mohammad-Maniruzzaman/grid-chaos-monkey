from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Optional

from . import simulation


@dataclass
class Experiment:
    experiment_id: str
    scenario: str
    phase: str  # baseline | chaos | recovery
    started_at_ns: int
    status: str = "ACTIVE"  # ACTIVE | ENDED
    notes: str = ""

    # Netflix-aligned execution modes
    execution_mode: str = "sandbox"  # "sandbox" | "guardrailed"

    # Blast radius guardrail threshold
    max_load_loss_pct: float = 0.20

    # Guardrail state (incident metadata; should persist through recovery)
    blast_radius_triggered: bool = False
    blast_radius_reason: Optional[str] = None

    # NEW: persistent containment marker (so UI doesn't lose it after recovery)
    containment_action: Optional[str] = None


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
        self.last_mutation_source = "init"  # scenario|manual|reset|rollback|status|end_experiment

    # ---------------------------
    # Lifecycle / control
    # ---------------------------

    def reset(self) -> None:
        """
        Hard reset: restore baseline AND clear active experiment.
        """
        with self._lock:
            self.net = simulation.create_grid()
            self.simulation_id = str(uuid.uuid4())
            self.active_experiment = None
            self.last_mutation_source = "reset"

    def begin_experiment(
        self,
        scenario: str,
        notes: str = "",
        execution_mode: str = "sandbox",
        max_load_loss_pct: float = 0.20,
    ) -> Experiment:
        with self._lock:
            if self.active_experiment and self.active_experiment.status == "ACTIVE":
                raise RuntimeError(
                    "An experiment is already active. End it before starting a new one."
                )

            if execution_mode not in ("sandbox", "guardrailed"):
                raise ValueError("execution_mode must be 'sandbox' or 'guardrailed'")

            exp = Experiment(
                experiment_id=str(uuid.uuid4()),
                scenario=scenario,
                phase="baseline",
                started_at_ns=time.time_ns(),
                notes=notes,
                execution_mode=execution_mode,
                max_load_loss_pct=float(max_load_loss_pct),
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

    def mutate(
        self,
        fn: Callable[..., Any],
        *args: Any,
        mutation_source: str = "manual",
        **kwargs: Any,
    ) -> Any:
        with self._lock:
            self.last_mutation_source = mutation_source
            return fn(self.net, *args, **kwargs)

    def read(self):
        with self._lock:
            return self.net

    # ---------------------------
    # Internals
    # ---------------------------

    def _build_context(self, exp: Optional[Experiment]) -> Dict[str, str]:
        if not exp:
            return {
                "experiment_id": "none",
                "scenario": "none",
                "phase": "baseline",
                "simulation_id": self.simulation_id,
                "mutation_source": self.last_mutation_source,
            }

        return {
            "experiment_id": exp.experiment_id,
            "scenario": exp.scenario,
            "phase": exp.phase,
            "simulation_id": self.simulation_id,
            "mutation_source": self.last_mutation_source,
        }

    def _rollback(self) -> None:
        """
        Restore baseline without deleting the experiment record.
        NOTE: caller must hold self._lock
        """
        self.net = simulation.create_grid()
        self.simulation_id = str(uuid.uuid4())
        self.last_mutation_source = "rollback"

    def _trigger_containment(self, exp: Experiment, action: str = "AUTO_ABORT_ROLLBACK") -> None:
        """
        Option A containment: mark containment + end experiment + rollback grid to baseline.
        NOTE: caller must hold self._lock
        """
        # Persist containment so it remains visible after recovery
        exp.containment_action = action

        exp.status = "ENDED"
        exp.phase = "recovery"
        self._rollback()

    def _build_response(
        self,
        *,
        converged: bool,
        error: Optional[str],
        ctx: Dict[str, str],
        exp: Optional[Experiment],
        estimated_load_loss_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes snapshot responses (used for failure paths).
        """
        payload: Dict[str, Any] = {
            "converged": bool(converged),
            "error": error,
            "context": ctx,
            "execution_mode": exp.execution_mode if exp else "sandbox",
            "containment_action": exp.containment_action if exp else None,
            "estimated_load_loss_pct": estimated_load_loss_pct,
        }

        if exp:
            payload.update(
                {
                    "blast_radius_triggered": exp.blast_radius_triggered,
                    "blast_radius_reason": exp.blast_radius_reason,
                    "experiment_status": exp.status,
                    "experiment_phase": exp.phase,
                }
            )
        else:
            payload.update(
                {
                    "blast_radius_triggered": False,
                    "blast_radius_reason": None,
                    "experiment_status": None,
                    "experiment_phase": None,
                }
            )

        return payload

    # ---------------------------
    # Snapshot (core)
    # ---------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Runs simulation snapshot.

        If execution_mode='guardrailed', it enforces Blast Radius containment
        (Option A): auto-abort + rollback on either:
          - solver divergence / blackout, or
          - estimated load-loss exceeding max_load_loss_pct
        """
        with self._lock:
            exp = self.active_experiment

            ctx = self._build_context(exp)
            execution_mode = exp.execution_mode if exp else "sandbox"
            max_loss = float(exp.max_load_loss_pct) if exp else 0.20

            snap = simulation.run_simulation(self.net)

            # -------------------------------
            # CASE A: PHYSICS FAILURE
            # -------------------------------
            physics_failed = (
                snap is None
                or not isinstance(snap, dict)
                or snap.get("converged") is False
            )

            if physics_failed:
                err_msg = "Powerflow failed (Blackout)"
                if isinstance(snap, dict) and snap.get("error"):
                    err_msg = str(snap.get("error"))

                if exp and exp.status == "ACTIVE" and execution_mode == "guardrailed":
                    exp.blast_radius_triggered = True
                    exp.blast_radius_reason = (
                        "Power flow did not converge (simulator blackout). "
                        "Auto-containment triggered."
                    )

                    # Contain + rollback (persist containment_action)
                    self._trigger_containment(exp, action="AUTO_ABORT_ROLLBACK")

                    # Refresh context after rollback (simulation_id/mutation_source changed)
                    ctx_after = self._build_context(exp)

                    # OPTIONAL (recommended): probe baseline immediately so UI sees recovery fast
                    probe = simulation.run_simulation(self.net)
                    if isinstance(probe, dict) and probe.get("converged", False):
                        probe["context"] = ctx_after
                        probe["execution_mode"] = execution_mode
                        probe["estimated_load_loss_pct"] = None
                        probe["containment_action"] = exp.containment_action
                        probe["blast_radius_triggered"] = exp.blast_radius_triggered
                        probe["blast_radius_reason"] = exp.blast_radius_reason
                        probe["experiment_status"] = exp.status
                        probe["experiment_phase"] = exp.phase
                        return probe

                    # If probe still fails (rare), return normalized blackout response
                    return self._build_response(
                        converged=False,
                        error=err_msg,
                        ctx=ctx_after,
                        exp=exp,
                        estimated_load_loss_pct=None,
                    )

                # Sandbox mode: report blackout only
                return self._build_response(
                    converged=False,
                    error=err_msg,
                    ctx=ctx,
                    exp=exp,
                    estimated_load_loss_pct=None,
                )

            # -------------------------------
            # CASE B: PHYSICS SUCCESS
            # -------------------------------
            snap["context"] = ctx
            snap["execution_mode"] = execution_mode

            # Only compute loss% for ACTIVE + guardrailed
            snap["estimated_load_loss_pct"] = None

            # IMPORTANT: do NOT overwrite containment_action to None.
            # Persist it from experiment so UI sees containment even after recovery.
            snap["containment_action"] = exp.containment_action if exp else None

            if exp and exp.status == "ACTIVE" and execution_mode == "guardrailed":
                total_load = float(snap.get("total_load_mw", 0.0))
                generation = float(snap.get("generation_mw", 0.0))

                if total_load > 0:
                    est_loss_pct = max(0.0, (total_load - generation) / total_load)
                else:
                    est_loss_pct = 0.0

                snap["estimated_load_loss_pct"] = round(est_loss_pct, 4)

                if est_loss_pct >= max_loss:
                    exp.blast_radius_triggered = True
                    exp.blast_radius_reason = (
                        f"Blast radius exceeded: estimated {est_loss_pct:.1%} load lost "
                        f"(limit {max_loss:.0%})"
                    )

                    self._trigger_containment(exp, action="AUTO_ABORT_ROLLBACK")

                    snap["containment_action"] = exp.containment_action
                    snap["context"] = self._build_context(exp)

            # Always include experiment metadata
            if exp:
                snap["blast_radius_triggered"] = exp.blast_radius_triggered
                snap["blast_radius_reason"] = exp.blast_radius_reason
                snap["experiment_status"] = exp.status
                snap["experiment_phase"] = exp.phase
            else:
                snap["blast_radius_triggered"] = False
                snap["blast_radius_reason"] = None
                snap["experiment_status"] = None
                snap["experiment_phase"] = None

            return snap

    # ---------------------------
    # Existing API helper
    # ---------------------------

    def experiment_context(self) -> Dict[str, str]:
        with self._lock:
            return self._build_context(self.active_experiment)
