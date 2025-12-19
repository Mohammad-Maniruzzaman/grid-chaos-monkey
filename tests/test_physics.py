import sys
import os
import pytest

# Add src to path so we can import the engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import simulation

def test_grid_initialization():
    """Smoke Test: Does the grid load?"""
    net = simulation.create_grid()
    assert len(net.bus) == 14, "Grid should have 14 buses"

def test_convergence():
    """Physics Test: Does the math work on a healthy grid?"""
    net = simulation.create_grid()
    snap = simulation.run_simulation(net)

    assert snap is not None
    assert snap["converged"] is True
    assert "min_voltage_pu" in snap
    assert 0.0 < snap["min_voltage_pu"] < 1.2