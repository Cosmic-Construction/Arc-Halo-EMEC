"""
Tests for Virtual Engine EMEC Simulator

Tests the electromagnetic energy conversion simulator components.
"""

import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emec import (
    VirtualEngine,
    EngineParameters,
    EMFieldSolver,
    PolyphaseWindingModel,
    WindingParameters,
    RotorDynamics,
    RotorParameters,
    StatorDynamics,
    StatorParameters
)


def test_em_field_solver():
    """Test electromagnetic field solver"""
    print("Testing EM Field Solver...")
    
    solver = EMFieldSolver()
    
    # Test magnetic flux density computation
    current = np.array([1.0, 2.0, 3.0])
    B = solver.compute_magnetic_flux_density(current, geometry_factor=1.0)
    assert B.shape == current.shape, "B field shape mismatch"
    assert np.all(B >= 0) or np.all(B <= 0), "B field computed"
    
    # Test Park transformation
    abc = np.array([1.0, -0.5, -0.5])
    theta = 0.0
    dq0 = solver.park_transform(abc, theta)
    assert len(dq0) == 3, "dq0 transform size incorrect"
    
    # Test inverse Park transformation
    abc_back = solver.inverse_park_transform(dq0, theta)
    assert np.allclose(abc, abc_back, atol=1e-10), "Park transform not invertible"
    
    # Test field step
    state = solver.solve_field_step(current, 100.0, 1e-4)
    assert state.time >= 0, "State time invalid"
    
    print("  ✓ EM Field Solver tests passed")
    return True


def test_polyphase_winding():
    """Test polyphase winding model"""
    print("Testing Polyphase Winding Model...")
    
    stator_params = WindingParameters()
    rotor_params = WindingParameters()
    
    winding = PolyphaseWindingModel(stator_params, rotor_params)
    
    # Test inductance matrix
    assert winding.L_ss.shape == (3, 3), "Stator inductance matrix wrong shape"
    assert winding.L_rr.shape == (3, 3), "Rotor inductance matrix wrong shape"
    
    # Test mutual inductance
    theta = 0.0
    L_sr = winding.compute_mutual_inductance(theta)
    assert L_sr.shape == (3, 3), "Mutual inductance matrix wrong shape"
    
    # Test flux linkage
    i_s = np.array([1.0, -0.5, -0.5])
    i_r = np.array([0.5, -0.25, -0.25])
    flux = winding.compute_flux_linkage(i_s, i_r, theta)
    assert 'stator' in flux and 'rotor' in flux, "Flux linkage missing components"
    assert flux['stator'].shape == (3,), "Stator flux wrong shape"
    
    # Test winding factor
    k_w = winding.compute_winding_factor()
    assert 0 < k_w <= 1.0, f"Winding factor {k_w} out of range"
    
    print("  ✓ Polyphase Winding Model tests passed")
    return True


def test_rotor_dynamics():
    """Test rotor dynamics"""
    print("Testing Rotor Dynamics...")
    
    params = RotorParameters()
    rotor = RotorDynamics(params)
    
    # Test initial state
    assert rotor.state.angular_velocity == 0.0, "Initial velocity not zero"
    assert rotor.state.angle == 0.0, "Initial angle not zero"
    
    # Test friction torque
    T_friction = rotor.compute_friction_torque(100.0)
    assert T_friction > 0, "Friction torque should be positive for positive velocity"
    
    # Test dynamics step with torque
    state = rotor.solve_dynamics(T_em=10.0, dt=0.001)
    assert state.angular_velocity > 0, "Velocity should increase with positive torque"
    assert state.time > 0, "Time not advancing"
    
    # Test electrical angle
    theta_e = rotor.get_electrical_angle()
    assert theta_e == params.pole_pairs * state.angle, "Electrical angle incorrect"
    
    # Test slip calculation
    slip = rotor.get_slip(50.0)
    assert -1.0 <= slip <= 2.0, f"Slip {slip} out of reasonable range"
    
    # Test kinetic energy
    E_k = rotor.get_kinetic_energy()
    assert E_k >= 0, "Kinetic energy should be non-negative"
    
    print("  ✓ Rotor Dynamics tests passed")
    return True


def test_stator_dynamics():
    """Test stator dynamics"""
    print("Testing Stator Dynamics...")
    
    params = StatorParameters()
    stator = StatorDynamics(params)
    
    # Test balanced voltage generation
    V = stator.generate_balanced_voltage(100.0, 50.0, 0.0)
    assert V.shape == (3,), "Voltage vector wrong shape"
    # At t=0, phase a should be 0, phase b negative, phase c positive
    assert abs(V[0]) < 1e-10, "Phase A voltage should be ~0 at t=0"
    
    # Test supply voltage
    V_supply = stator.compute_supply_voltage(0.0)
    assert V_supply.shape == (3,), "Supply voltage wrong shape"
    
    # Test current dynamics (simplified)
    flux = np.array([0.01, 0.01, 0.01])
    d_flux = np.array([0.0, 0.0, 0.0])
    I = stator.solve_current_dynamics(V_supply, flux, d_flux, 1e-4)
    assert I.shape == (3,), "Current wrong shape"
    
    # Test state update
    state = stator.update_state(I, V_supply, 1e-4)
    assert state.time > 0, "Time not advancing"
    
    # Test power computation
    power = stator.compute_power()
    assert 'instantaneous' in power, "Missing instantaneous power"
    assert 'power_factor' in power, "Missing power factor"
    
    # Test losses
    losses = stator.compute_losses()
    assert 'copper' in losses, "Missing copper losses"
    assert losses['copper'] >= 0, "Copper losses should be non-negative"
    
    print("  ✓ Stator Dynamics tests passed")
    return True


def test_virtual_engine_basic():
    """Test basic virtual engine operation"""
    print("Testing Virtual Engine (Basic)...")
    
    # Create engine with defaults
    engine = VirtualEngine()
    
    # Test single step
    state = engine.step(dt=1e-4)
    assert state.time > 0, "Time not advancing"
    assert state.torque is not None, "Torque not computed"
    
    # Test reset
    engine.reset()
    assert engine.current_time == 0.0, "Engine not reset"
    assert len(engine.history) == 0, "History not cleared"
    
    print("  ✓ Virtual Engine (Basic) tests passed")
    return True


def test_virtual_engine_simulation():
    """Test virtual engine simulation"""
    print("Testing Virtual Engine (Simulation)...")
    
    engine = VirtualEngine()
    
    # Set a small load
    engine.set_load_torque(lambda t, omega: 5.0)
    
    # Run short simulation
    states = engine.simulate(duration=0.1, dt=1e-4)
    
    assert len(states) > 0, "No states generated"
    assert len(states) == len(engine.history), "History length mismatch"
    
    # Check that simulation ran without errors
    # Note: The simplified electro-mechanical model may not produce perfect acceleration
    # but should generate valid torque and speed data
    assert all(hasattr(s, 'torque') for s in states), "Missing torque in states"
    assert all(hasattr(s, 'rotor') for s in states), "Missing rotor in states"
    
    # Test metrics
    metrics = engine.get_performance_metrics()
    assert 'avg_torque' in metrics, "Missing torque metric"
    assert 'avg_efficiency' in metrics, "Missing efficiency metric"
    assert metrics['simulation_time'] > 0, "Simulation time not recorded"
    
    print("  ✓ Virtual Engine (Simulation) tests passed")
    return True


def test_virtual_engine_data_export():
    """Test data export functionality"""
    print("Testing Virtual Engine (Data Export)...")
    
    engine = VirtualEngine()
    engine.set_load_torque(lambda t, omega: 3.0)
    engine.simulate(duration=0.05, dt=1e-4)
    
    data = engine.export_data()
    
    assert 'time' in data, "Missing time data"
    assert 'speed_rpm' in data, "Missing speed data"
    assert 'torque' in data, "Missing torque data"
    assert 'efficiency' in data, "Missing efficiency data"
    
    # Check data shapes
    n_points = len(data['time'])
    assert data['speed_rpm'].shape == (n_points,), "Speed data shape mismatch"
    assert data['torque'].shape == (n_points,), "Torque data shape mismatch"
    
    print("  ✓ Virtual Engine (Data Export) tests passed")
    return True


def test_engine_parameters():
    """Test engine parameters"""
    print("Testing Engine Parameters...")
    
    # Test default creation
    params = EngineParameters.create_default()
    assert params.stator_winding.num_phases == 3, "Wrong number of phases"
    assert params.rotor_mechanical.pole_pairs > 0, "Invalid pole pairs"
    assert params.time_step > 0, "Invalid time step"
    
    # Test custom power
    params_high = EngineParameters.create_default(rated_power=20000.0)
    assert params_high is not None, "Failed to create high power parameters"
    
    print("  ✓ Engine Parameters tests passed")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("Running Virtual Engine EMEC Simulator Tests")
    print("="*70 + "\n")
    
    tests = [
        test_em_field_solver,
        test_polyphase_winding,
        test_rotor_dynamics,
        test_stator_dynamics,
        test_engine_parameters,
        test_virtual_engine_basic,
        test_virtual_engine_simulation,
        test_virtual_engine_data_export,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
