import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from . import chaos
from .controller import GridController
from .telemetry import db

"""
GridChaos Control Plane Design Notes

- Single-writer control plane via GridController to avoid concurrent mutations.
- Scenarios are discovered via a registry (chaos.SCENARIOS), not hard-coded if/elif.
- Status computes simulation health and emits telemetry correlated to experiment context.
- Read-only mode can disable all state mutations for safe demos.
"""

READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "false").lower() == "true"

app = FastAPI(title="GridChaos Control Plane", version="2.0.0")
controller = GridController()


def _require_writable():
    if READ_ONLY_MODE:
        raise HTTPException(
            status_code=403,
            detail="READ_ONLY_MODE is enabled. Mutations are disabled.",
        )


def _health_from_voltage(min_voltage: float) -> str:
    # thresholds can be configured; defaults align with prior behavior
    v_critical = float(os.getenv("V_CRITICAL", "0.90"))
    v_unstable = float(os.getenv("V_UNSTABLE", "0.95"))

    if min_voltage < v_critical:
        return "CRITICAL"
    if min_voltage < v_unstable:
        return "UNSTABLE"
    return "HEALTHY"


class StartExperimentRequest(BaseModel):
    # Netflix-aligned modes:
    # - "sandbox"     = uncontained chaos (blackout allowed)
    # - "guardrailed" = safe chaos (blast radius containment + later auto-recovery)
    execution_mode: str = "sandbox"  # "sandbox" | "guardrailed"
    max_load_loss_pct: float = 0.20
    notes: str = ""


@app.get("/")
def home():
    return {
        "message": "GridChaos API is Online",
        "docs": "Go to /docs to see the interactive dashboard",
        "read_only_mode": READ_ONLY_MODE,
    }


@app.get("/scenarios")
def list_scenarios():
    """
    Lists available war-room scenarios (registry-backed).
    """
    return {
        "scenarios": [
            {
                "key": spec.key,
                "display_name": spec.display_name,
                "target": spec.target,
                "reversible": spec.reversible,
            }
            for spec in chaos.SCENARIOS.values()
        ]
    }


@app.post("/experiments/start/{scenario_key}")
def start_experiment(scenario_key: str, req: StartExperimentRequest):
    """
    Starts an experiment lifecycle and sets phase=baseline.
    This does NOT apply chaos yet. (Operator triggers chaos next.)
    """
    _require_writable()
    if scenario_key not in chaos.SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    try:
        exp = controller.begin_experiment(
            scenario=scenario_key,
            notes=req.notes,
            execution_mode=req.execution_mode,
            max_load_loss_pct=req.max_load_loss_pct,
        )
        controller.set_phase("baseline")
        return {
            "message": "Experiment started",
            "experiment_id": exp.experiment_id,
            "scenario": exp.scenario,
            "phase": exp.phase,
            "execution_mode": getattr(exp, "execution_mode", "sandbox"),
            "max_load_loss_pct": getattr(exp, "max_load_loss_pct", 0.20),
        }
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/experiments/end")
def end_experiment():
    """
    Ends the current experiment. Phase becomes recovery.
    """
    _require_writable()
    controller.end_experiment()
    return {"message": "Experiment ended", "context": controller.experiment_context()}


@app.get("/status")
def get_grid_status():
    """
    Runs a Power Flow snapshot via the controller (lock-safe), returns health,
    AND logs to InfluxDB correlated to experiment context.
    """
    snap = controller.snapshot()
    ctx = snap.get("context", {})

    # Handle Blackouts (Physics Failed)
    if not snap.get("converged", False):
        db.log_grid_state(
            ctx=ctx,
            voltage_pu=0.0,
            total_load=0.0,
            total_gen=0.0,
            status="BLACKOUT",
            converged=False,
            solve_time_ms=0.0,
        )
        return {
            "status": "BLACKOUT",
            "min_voltage_pu": 0.0,
            "total_load_mw": 0.0,
            "generation_mw": 0.0,
            "message": snap.get(
                "error",
                "Power flow diverged or results unavailable. Grid has collapsed.",
            ),
            "context": ctx,
            "execution_mode": snap.get("execution_mode", "sandbox"),
            "estimated_load_loss_pct": snap.get("estimated_load_loss_pct"),
            "blast_radius_triggered": snap.get("blast_radius_triggered", False),
            "blast_radius_reason": snap.get("blast_radius_reason"),
            "containment_action": snap.get("containment_action"),
        }

    # Pull metrics from snapshot dict
    min_voltage = float(snap["min_voltage_pu"])
    total_load = float(snap.get("total_load_mw", 0.0))
    total_generation = float(snap.get("generation_mw", 0.0))

    # Determine health status
    health = _health_from_voltage(min_voltage)

    db.log_grid_state(
        ctx=ctx,
        voltage_pu=min_voltage,
        total_load=total_load,
        total_gen=total_generation,
        status=health,
        converged=True,
        solve_time_ms=float(snap.get("solve_time_ms") or 0.0),
    )

    return {
        "status": health,
        "min_voltage_pu": round(min_voltage, 4),
        "total_load_mw": round(total_load, 3),
        "generation_mw": round(total_generation, 3),
        "solve_time_ms": snap.get("solve_time_ms"),
        "context": ctx,
        "execution_mode": snap.get("execution_mode", "sandbox"),
        "estimated_load_loss_pct": snap.get("estimated_load_loss_pct"),
        "blast_radius_triggered": snap.get("blast_radius_triggered", False),
        "blast_radius_reason": snap.get("blast_radius_reason"),
    }
@app.post("/inject/scenario/{scenario_key}")
def run_scenario(scenario_key: str):
    """
    Applies a named scenario mutation.
    Also moves experiment phase to 'chaos' if an experiment is active.
    """
    _require_writable()

    spec = chaos.SCENARIOS.get(scenario_key)
    if not spec:
        raise HTTPException(status_code=404, detail="Scenario not found")

    try:
        controller.set_phase("chaos")
        controller.mutate(spec.fn, mutation_source="scenario")
        return {"message": f"Scenario applied: {spec.display_name}", "scenario": scenario_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- LEGACY MANUAL CONTROL (kept for UI compatibility) ---

@app.post("/inject/line_trip/{line_id}")
def trip_line(line_id: int):
    _require_writable()
    try:
        controller.mutate(chaos.trip_line, line_id, mutation_source="manual")
        return {"message": f"Line {line_id} has been tripped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inject/load_spike/{multiplier}")
def load_spike(multiplier: float):
    _require_writable()
    try:
        controller.mutate(chaos.cyber_attack_load_spike, multiplier, mutation_source="manual")
        return {"message": f"Load spiked by factor of {multiplier}x"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
def reset_grid():
    _require_writable()
    controller.reset()
    return {
        "message": "Grid state has been reset to baseline.",
        "context": controller.experiment_context(),
    }
