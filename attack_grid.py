import src.simulation as simulation
import src.chaos as chaos

# 1. Initialize
print("--- 1. Initializing Healthy Grid ---")
net = simulation.create_grid()
baseline = simulation.run_simulation(net)

# 2. THE NUCLEAR OPTION
print("\n--- 2. Injecting CATASTROPHIC LOAD ---")
# 3.5x is impossible for this grid to handle.
chaos.cyber_attack_load_spike(net, multiplier=3.5)

# 3. Measure Impact
print("\n--- 3. Measuring Impact ---")
results_after = simulation.run_simulation(net)

if results_after is not None:
    # If we get here, the grid is magical.
    min_voltage = results_after['vm_pu'].min()
    print(f"New Min Voltage: {min_voltage:.4f} p.u.")
    if min_voltage < 0.90:
        print("🚨 ALERT: Grid Stability Compromised!")
else:
    # This is what we want.
    print("💀 CATASTROPHIC FAILURE: Grid Collapse.")
    print("   Reason: Power Flow Divergence (Demand > Supply).")
    print("   Status: TOTAL BLACKOUT.")