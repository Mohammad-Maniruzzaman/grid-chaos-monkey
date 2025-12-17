from fastapi import FastAPI, HTTPException
from . import simulation
from . import chaos
from .telemetry import db

# --- 1. INITIALIZE APP (MUST BE AT THE TOP) ---
app = FastAPI(title="GridChaos Control Plane", version="1.0.0")

# --- 2. GLOBAL STATE ---
grid_state = {
    "net": simulation.create_grid()
}

# --- 3. CORE ENDPOINTS ---

@app.get("/")
def home():
    return {
        "message": "GridChaos API is Online",
        "docs": "Go to /docs to see the interactive dashboard"
    }

@app.get("/status")
def get_grid_status():
    """
    Runs a Power Flow simulation, returns health, AND logs to InfluxDB.
    """
    results = simulation.run_simulation(grid_state["net"])
    
    # Handle Blackouts (Physics Failed)
    if results is None:
        db.log_grid_state(voltage_pu=0.0, total_load=0, total_gen=0, status="BLACKOUT")
        return {
            "status": "BLACKOUT", 
            "min_voltage_pu": 0.0,
            "total_load_mw": 0.0,
            "generation_mw": 0.0,
            "message": "Power flow diverged. Grid has collapsed."
        }
    
    # Calculate Metrics
    min_voltage = results['vm_pu'].min()
    local_gen = grid_state["net"].res_gen.p_mw.sum()
    external_grid = grid_state["net"].res_ext_grid.p_mw.sum()
    total_generation = local_gen + external_grid
    total_load = grid_state["net"].load.p_mw.sum()

    # Determine Health Status
    if min_voltage < 0.90:
        health = "CRITICAL"
    elif min_voltage < 0.95:
        health = "UNSTABLE"
    else:
        health = "HEALTHY"
    
    # Log to Database
    db.log_grid_state(min_voltage, total_load, total_generation, health)

    return {
        "status": health,
        "min_voltage_pu": round(min_voltage, 4),
        "total_load_mw": total_load,
        "generation_mw": total_generation
    }

# --- 4. WAR ROOM SCENARIOS (NEW) ---

@app.post("/inject/scenario/{scenario_name}")
def run_scenario(scenario_name: str):
    """
    Executes a named Con Ed War Story scenario.
    """
    net = grid_state["net"]
    try:
        if scenario_name == "hurricane_ida":
            chaos.event_hurricane_ida_flash_flood(net)
            return {"message": "🌊 Hurricane Ida: Flood protection tripped Lines 0 & 1."}
        elif scenario_name == "heatwave_2023":
            chaos.event_heatwave_2023_voltage_collapse(net)
            return {"message": "🔥 Heatwave 2023: Loads peaked, Reactive reserves depleted."}
        elif scenario_name == "ev_fleet_spike":
            chaos.event_staten_island_ev_fleet_spike(net)
            return {"message": "⚡ EV Fleet: 40MW step-change on Bus 14."}
        elif scenario_name == "sandy_2012":
            chaos.event_sandy_protection_miscoord(net)
            return {"message": "🌪️ Superstorm Sandy: Generator Relay Mis-operation."}
        elif scenario_name == "blackout_2003":
            chaos.event_2003_blackout_cascade(net)
            return {"message": "🌲 2003 Cascade: Vegetation contact on Line 3."}
        else:
            raise HTTPException(status_code=404, detail="Scenario not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. LEGACY MANUAL CONTROL ---

@app.post("/inject/line_trip/{line_id}")
def trip_line(line_id: int):
    try:
        chaos.trip_line(grid_state["net"], line_id)
        return {"message": f"Line {line_id} has been tripped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inject/load_spike/{multiplier}")
def load_spike(multiplier: float):
    try:
        chaos.cyber_attack_load_spike(grid_state["net"], multiplier)
        return {"message": f"Load spiked by factor of {multiplier}x"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
def reset_grid():
    grid_state["net"] = simulation.create_grid()
    return {"message": "Grid state has been reset to baseline."}