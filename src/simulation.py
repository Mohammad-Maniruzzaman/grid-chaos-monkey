import pandapower as pp
import pandapower.networks as pn
import pandas as pd

def create_grid():
    """
    Loads the IEEE 14-Bus Standard System.
    This represents a realistic chunk of the US power grid (Midwest).
    """
    # Load the standard network model
    net = pn.case14()
    return net

def run_simulation(net):
    """
    Runs a Power Flow (Newton-Raphson method) to calculate
    voltages and line flows based on current physics.
    """
    try:
        # Run the power flow solver
        pp.runpp(net)
        print("✅ Power Flow Converged!")
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")
        return None

    # extract key metrics
    # res_bus contains voltage levels (vm_pu = Voltage Magnitude Per Unit)
    # 1.0 pu = ideal. < 0.90 = Brownout. < 0.80 = Blackout.
    results = net.res_bus[['vm_pu', 'p_mw', 'q_mvar']]
    
    return results

if __name__ == "__main__":
    print("--- Initializing GridChaos Engine ---")
    grid = create_grid()
    
    print("--- Running Baseline Simulation ---")
    metrics = run_simulation(grid)
    
    if metrics is not None:
        print("\n--- Grid State (First 5 Buses) ---")
        print(metrics.head())
        
        # Simple Logic: Check if grid is healthy
        min_voltage = metrics['vm_pu'].min()
        print(f"\nMinimum Voltage: {min_voltage:.4f} p.u.")
        
        if min_voltage < 0.90:
            print("⚠️ ALERT: Grid Instability Detected!")
        else:
            print("✅ Grid is Stable.")