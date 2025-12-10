import pandapower as pp

def trip_line(net, line_idx):
    """
    Simulates a physical line break (e.g., tree falling on a wire).
    disconnects the line from the grid logic.
    """
    # Check if line exists
    if line_idx in net.line.index:
        print(f"🔥 CHAOS: Tripping Line ID {line_idx}...")
        net.line.at[line_idx, 'in_service'] = False
    else:
        print(f"⚠️ Error: Line ID {line_idx} not found.")

def generator_fail(net, gen_idx):
    """
    Simulates a generator failure (e.g., turbine overheat).
    """
    if gen_idx in net.gen.index:
        print(f"🔥 CHAOS: Killing Generator ID {gen_idx}...")
        net.gen.at[gen_idx, 'in_service'] = False
    else:
        print(f"⚠️ Error: Generator ID {gen_idx} not found.")

def cyber_attack_load_spike(net, multiplier=1.5):
    """
    Simulates an IoT botnet attack (e.g., hackers turning on all AC units).
    Multiplies the demand (load) across the entire grid.
    """
    print(f"👾 CHAOS: Cyber Attack! Increasing Load by {multiplier}x...")
    net.load['p_mw'] *= multiplier