from fastapi import FastAPI, HTTPException
from .telemetry import db
import src.simulation as simulation
import src.chaos as chaos

# 1. Initialize the App
app = FastAPI(title="GridChaos Control Plane", version="1.0.0")

# 2. Global State
grid_state = {
    "net": simulation.create_grid()
}

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
    
    # 1. Handle Blackouts (Physics Failed)
    if results is None:
        db.log_grid_state(voltage_pu=0.0, total_load=0, total_gen=0, status="BLACKOUT")
        return {
            "status": "BLACKOUT", 
            "voltage_pu": 0.0, 
            "message": "Power flow diverged. Grid has collapsed."
        }
    
    # 2. Calculate Metrics
    min_voltage = results['vm_pu'].min()
    local_gen = grid_state["net"].res_gen.p_mw.sum()
    external_grid = grid_state["net"].res_ext_grid.p_mw.sum()
    total_generation = local_gen + external_grid
    total_load = grid_state["net"].load.p_mw.sum()

    # 3. Determine Health Status
    if min_voltage < 0.90:
        health = "CRITICAL"
    elif min_voltage < 0.95:
        health = "UNSTABLE"
    else:
        health = "HEALTHY"
    
    # 4. LOG TO DATABASE (The Magic Line)
    db.log_grid_state(min_voltage, total_load, total_generation, health)

    return {
        "status": health,
        "min_voltage_pu": round(min_voltage, 4),
        "total_load_mw": total_load,
        "generation_mw": total_generation
    }
    
    # Check for Brownout (Low Voltage)
    min_voltage = results['vm_pu'].min()
    
    if min_voltage < 0.90:
        health = "CRITICAL"
    elif min_voltage < 0.95:
        health = "UNSTABLE"
    else:
        health = "HEALTHY"
    
    # TELEMETRY CALCULATION
    # Fix: Total Gen = Local Gen (res_gen) + External Grid Import (res_ext_grid)
    local_gen = grid_state["net"].res_gen.p_mw.sum()
    external_grid = grid_state["net"].res_ext_grid.p_mw.sum()
    total_generation = local_gen + external_grid

    return {
        "status": health,
        "min_voltage_pu": round(min_voltage, 4),
        "total_load_mw": grid_state["net"].load.p_mw.sum(),
        "generation_mw": total_generation
    }

@app.post("/inject/line_trip/{line_id}")
def trip_line(line_id: int):
    """
    Simulates a physical line failure (Chaos Monkey).
    """
    try:
        chaos.trip_line(grid_state["net"], line_id)
        return {"message": f"Line {line_id} has been tripped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inject/load_spike/{multiplier}")
def load_spike(multiplier: float):
    """
    Simulates a Cyber Attack (Load Surge).
    """
    try:
        chaos.cyber_attack_load_spike(grid_state["net"], multiplier)
        return {"message": f"Load spiked by factor of {multiplier}x"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
def reset_grid():
    """
    Restores the grid to its original healthy state.
    """
    grid_state["net"] = simulation.create_grid()
    return {"message": "Grid state has been reset to baseline."}