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
    res = simulation.run_simulation(net)
    assert res is not None, "Simulation diverged on healthy grid!"
    assert res['vm_pu'].min() > 0.9, "Voltage too low on healthy grid"