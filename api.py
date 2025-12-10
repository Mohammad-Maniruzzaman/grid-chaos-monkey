from fastapi import FastAPI, HTTPException
import simulation
import chaos

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
    Runs a Power Flow simulation and returns the current health of the grid.
    """
    results = simulation.run_simulation(grid_state["net"])
    
    # Check for Blackout (None result)
    if results is None:
        return {
            "status": "BLACKOUT", 
            "voltage_pu": 0.0, 
            "message": "Power flow diverged. Grid has collapsed."
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