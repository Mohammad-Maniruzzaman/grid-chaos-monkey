from dataclasses import dataclass
from typing import Callable, Dict

import pandapower as pp  # kept for future extension / validation


@dataclass(frozen=True)
class ScenarioSpec:
    key: str
    display_name: str
    target: str          # BROWNOUT | BLACKOUT
    reversible: bool
    fn: Callable


def _ensure_single_apply(net, scenario_key: str) -> None:
    """
    Prevent repeated application of scenarios that compound multipliers.
    Stores state on the pandapower net object.
    """
    if not hasattr(net, "user_pf_options") or net.user_pf_options is None:
        net.user_pf_options = {}

    applied = net.user_pf_options.get("chaos_applied", {})
    if applied.get(scenario_key):
        raise RuntimeError(f"Scenario '{scenario_key}' already applied to this grid instance.")

    applied[scenario_key] = True
    net.user_pf_options["chaos_applied"] = applied


# --- CON EDISON "WAR STORIES" SCENARIO LIBRARY ---

def event_hurricane_ida_flash_flood(net) -> None:
    """
    Scenario: Hurricane Ida.
    Target: BLACKOUT
    Strategy: Disconnect external grid (slack) + increase load.
    """
    _ensure_single_apply(net, "hurricane_ida")
    net.ext_grid["in_service"] = False
    net.load["p_mw"] *= 3.0


def event_heatwave_2023_voltage_collapse(net) -> None:
    """
    Scenario: Heatwave.
    Target: BROWNOUT
    Strategy: sag external voltage + spike load + reduce reactive headroom.
    """
    _ensure_single_apply(net, "heatwave_2023")
    if not net.ext_grid.empty:
        net.ext_grid.at[0, "vm_pu"] = 0.92
    net.load["p_mw"] *= 2.1
    if not net.gen.empty and "max_q_mvar" in net.gen.columns:
        net.gen["max_q_mvar"] *= 0.5


def event_staten_island_ev_fleet_spike(net) -> None:
    """
    Scenario: EV Fleet Spike.
    Target: BROWNOUT
    Strategy: mild sag + larger load spike.
    """
    _ensure_single_apply(net, "ev_fleet_spike")
    if not net.ext_grid.empty:
        net.ext_grid.at[0, "vm_pu"] = 0.94
    net.load["p_mw"] *= 3.5


def event_sandy_protection_miscoord(net) -> None:
    """
    Scenario: Superstorm Sandy.
    Target: BLACKOUT
    Strategy: trip generators + spike load.
    """
    _ensure_single_apply(net, "sandy_2012")
    if not net.gen.empty:
        net.gen["in_service"] = False
    net.load["p_mw"] *= 5.0


def event_2003_blackout_cascade(net) -> None:
    """
    Scenario: Northeast Blackout.
    Target: BLACKOUT
    Strategy: trip multiple lines + spike load.
    """
    _ensure_single_apply(net, "blackout_2003")
    if 3 in net.line.index:
        net.line.at[3, "in_service"] = False
    if 4 in net.line.index:
        net.line.at[4, "in_service"] = False
    net.load["p_mw"] *= 10.0


SCENARIOS: Dict[str, ScenarioSpec] = {
    "hurricane_ida": ScenarioSpec(
        key="hurricane_ida",
        display_name="Hurricane Ida (2021)",
        target="BLACKOUT",
        reversible=False,
        fn=event_hurricane_ida_flash_flood,
    ),
    "heatwave_2023": ScenarioSpec(
        key="heatwave_2023",
        display_name="Heatwave (2023)",
        target="BROWNOUT",
        reversible=False,
        fn=event_heatwave_2023_voltage_collapse,
    ),
    "ev_fleet_spike": ScenarioSpec(
        key="ev_fleet_spike",
        display_name="EV Fleet Spike (2024)",
        target="BROWNOUT",
        reversible=False,
        fn=event_staten_island_ev_fleet_spike,
    ),
    "sandy_2012": ScenarioSpec(
        key="sandy_2012",
        display_name="Superstorm Sandy (2012)",
        target="BLACKOUT",
        reversible=False,
        fn=event_sandy_protection_miscoord,
    ),
    "blackout_2003": ScenarioSpec(
        key="blackout_2003",
        display_name="Northeast Blackout (2003)",
        target="BLACKOUT",
        reversible=False,
        fn=event_2003_blackout_cascade,
    ),
}


# --- LEGACY TOOLS (manual injection) ---
def trip_line(net, line_id: int) -> None:
    if line_id in net.line.index:
        net.line.at[line_id, "in_service"] = False


def cyber_attack_load_spike(net, multiplier: float) -> None:
    net.load["p_mw"] *= multiplier
