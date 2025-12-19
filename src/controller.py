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

    def begin_experiment(self, scenario: str, notes: str = "") -> Experiment:
        with self._lock:
            if self.active_experiment and self.active_experiment.status == "ACTIVE":
                raise RuntimeError("An experiment is already active. End it before starting a new one.")

            exp = Experiment(
                experiment_id=str(uuid.uuid4()),
                scenario=scenario,
                phase="baseline",
                started_at_ns=time.time_ns(),
                notes=notes,
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
