import time
import pandapower as pp
import pandapower.networks as pn


def create_grid():
    """
    Loads the IEEE 14-bus test system.
    """
    return pn.case14()


def run_simulation(net):
    """
    Runs a power-flow simulation and returns a stable snapshot dict.

    Returns None if the solver fails or results are unavailable.
    """
    start = time.time()

    try:
        pp.runpp(net)
    except Exception:
        return None

    solve_time_ms = round((time.time() - start) * 1000, 2)

    # Defensive checks — CI-safe
    if not hasattr(net, "res_bus"):
        return None
    if net.res_bus is None or net.res_bus.empty:
        return None
    if "vm_pu" not in net.res_bus.columns:
        return None

    min_voltage_pu = float(net.res_bus["vm_pu"].min())

    # Load
    total_load_mw = 0.0
    if hasattr(net, "load") and not net.load.empty and "p_mw" in net.load.columns:
        total_load_mw = float(net.load["p_mw"].sum())

    # Generation
    local_gen_mw = 0.0
    if hasattr(net, "res_gen") and not net.res_gen.empty and "p_mw" in net.res_gen.columns:
        local_gen_mw = float(net.res_gen["p_mw"].sum())

    ext_grid_mw = 0.0
    if (
        hasattr(net, "res_ext_grid")
        and not net.res_ext_grid.empty
        and "p_mw" in net.res_ext_grid.columns
    ):
        ext_grid_mw = float(net.res_ext_grid["p_mw"].sum())

    total_generation_mw = local_gen_mw + ext_grid_mw

    return {
        "converged": True,
        "solve_time_ms": solve_time_ms,
        "min_voltage_pu": min_voltage_pu,
        "total_load_mw": total_load_mw,
        "generation_mw": total_generation_mw,
    }
