import pandapower as pp

# --- CON EDISON "WAR STORIES" SCENARIO LIBRARY ---
# Tuned with "Nuclear Option" parameters to defeat IEEE 14 Robustness.

def event_hurricane_ida_flash_flood(net):
    """
    Scenario: Hurricane Ida.
    Target: BLACKOUT (Red).
    Strategy: Disconnect the External Grid (Slack Bus). 
    """
    print("🌊 ALERT: Substation Flooding. Slack Bus Disconnected.")
    # This is the "Kill Switch". Removing the external grid guarantees collapse
    # if local gen isn't enough (and in IEEE 14, it isn't).
    net.ext_grid['in_service'] = False
    
    # Just to be sure, triple the load
    net.load['p_mw'] *= 3.0

def event_heatwave_2023_voltage_collapse(net):
    """
    Scenario: Heatwave 2023.
    Target: BROWNOUT (Yellow).
    Strategy: Sag External Voltage + Load Spike.
    """
    print("🔥 ALERT: Heatwave. Sagging Grid.")
    # This worked before, keeping it exactly as is.
    if not net.ext_grid.empty:
        net.ext_grid.at[0, 'vm_pu'] = 0.92
    net.load['p_mw'] *= 2.1
    net.gen['max_q_mvar'] *= 0.5

def event_staten_island_ev_fleet_spike(net):
    """
    Scenario: EV Fleet Spike.
    Target: BROWNOUT (Yellow).
    Strategy: Sag External Voltage slightly + Massive Load Spike.
    """
    print("⚡ ALERT: EV Fleet. Grid Sag + Spike.")
    # 1. Sag the grid, but not as bad as heatwave
    if not net.ext_grid.empty:
        net.ext_grid.at[0, 'vm_pu'] = 0.94
        
    # 2. Massive global spike (not just local) to drag average down
    net.load['p_mw'] *= 3.5

def event_sandy_protection_miscoord(net):
    """
    Scenario: Superstorm Sandy.
    Target: BLACKOUT (Red).
    Strategy: Trip Slack Gen + Massive Load.
    """
    print("🌪️ ALERT: Relay Mis-operation. Generator Trip.")
    # Trip the biggest generators
    net.gen['in_service'] = False 
    # Spike load to force non-convergence
    net.load['p_mw'] *= 5.0

def event_2003_blackout_cascade(net):
    """
    Scenario: Blackout 2003.
    Target: BLACKOUT (Red).
    Strategy: Trip multiple lines + 10x Load.
    """
    print("🌲 ALERT: Cascade Sequence.")
    # Trip a critical path
    if 3 in net.line.index: net.line.at[3, 'in_service'] = False
    if 4 in net.line.index: net.line.at[4, 'in_service'] = False
    
    # The "Hammer": 10x Load. Physics cannot solve this.
    net.load['p_mw'] *= 10.0

# --- LEGACY TOOLS ---
def trip_line(net, line_id):
    if line_id in net.line.index:
        net.line.at[line_id, 'in_service'] = False

def cyber_attack_load_spike(net, multiplier):
    net.load['p_mw'] *= multiplier