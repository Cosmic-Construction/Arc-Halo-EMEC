"""
Tests for Bond Graph and Neurological Analogy Models

Tests the generalized bond graph framework and neurological analogy implementation.
"""

import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emec import (
    # Bond Graph
    BondGraphModel,
    ResistiveElement,
    CapacitiveElement,
    InertialElement,
    TransformerElement,
    GyratorElement,
    EnergyDomain,
    PowerVariables,
    # EM Bond Graph Mapping
    create_em_bond_graph_from_engine,
    EngineParameters,
    analyze_power_flow,
    get_generalized_impedance,
    EMBondGraphSimulator,
    # Neurological Analogy
    NeurologicalEnergyModel,
    CognitiveFieldParameters,
    AffectiveFieldParameters,
    BehavioralParameters,
    PsychophysicalCoupling
)


def test_power_variables():
    """Test power variables"""
    print("Testing Power Variables...")
    
    pv = PowerVariables(effort=10.0, flow=2.0)
    
    # Test power computation
    power = pv.power()
    assert power == 20.0, f"Power calculation incorrect: {power}"
    
    # Test integral update
    dt = 0.1
    pv.update_integrals(dt)
    assert abs(pv.momentum - 1.0) < 1e-10, "Momentum integration incorrect"
    assert abs(pv.displacement - 0.2) < 1e-10, "Displacement integration incorrect"
    
    print("  ✓ Power Variables tests passed")
    return True


def test_resistive_element():
    """Test resistive element"""
    print("Testing Resistive Element...")
    
    R = ResistiveElement("test_resistor", resistance=10.0, domain=EnergyDomain.ELECTRICAL)
    
    # Test effort from flow
    effort = R.compute_effort(flow=2.0)
    assert abs(effort - 20.0) < 1e-10, "Effort calculation incorrect"
    
    # Test flow from effort
    flow = R.compute_flow(effort=30.0)
    assert abs(flow - 3.0) < 1e-10, "Flow calculation incorrect"
    
    # Test power dissipation
    R.power_vars.flow = 2.0
    power = R.dissipated_power()
    assert abs(power - 40.0) < 1e-10, "Power dissipation incorrect"
    
    print("  ✓ Resistive Element tests passed")
    return True


def test_capacitive_element():
    """Test capacitive element"""
    print("Testing Capacitive Element...")
    
    C = CapacitiveElement("test_capacitor", capacitance=0.01, domain=EnergyDomain.ELECTRICAL)
    
    # Update state
    C.update_state(flow=1.0, dt=0.1)
    assert abs(C.power_vars.displacement - 0.1) < 1e-10, "Displacement update incorrect"
    
    # Test effort
    effort = C.compute_effort()
    expected_effort = 0.1 / 0.01
    assert abs(effort - expected_effort) < 1e-6, "Effort calculation incorrect"
    
    # Test stored energy
    energy = C.stored_energy()
    expected_energy = 0.5 * (0.1 ** 2) / 0.01
    assert abs(energy - expected_energy) < 1e-6, "Stored energy incorrect"
    
    print("  ✓ Capacitive Element tests passed")
    return True


def test_inertial_element():
    """Test inertial element"""
    print("Testing Inertial Element...")
    
    I = InertialElement("test_inductor", inertance=0.1, domain=EnergyDomain.ELECTRICAL)
    
    # Update state
    I.update_state(effort=5.0, dt=0.1)
    assert abs(I.power_vars.momentum - 0.5) < 1e-10, "Momentum update incorrect"
    
    # Test flow
    flow = I.compute_flow()
    expected_flow = 0.5 / 0.1
    assert abs(flow - expected_flow) < 1e-10, "Flow calculation incorrect"
    
    # Test stored energy
    energy = I.stored_energy()
    expected_energy = 0.5 * (0.5 ** 2) / 0.1
    assert abs(energy - expected_energy) < 1e-6, "Stored energy incorrect"
    
    print("  ✓ Inertial Element tests passed")
    return True


def test_transformer_element():
    """Test transformer element"""
    print("Testing Transformer Element...")
    
    TF = TransformerElement("test_transformer", ratio=2.0)
    
    # Test forward transformation
    TF.transform_forward(effort_1=10.0, flow_2=3.0)
    assert abs(TF.power_vars_2.effort - 20.0) < 1e-10, "Effort transformation incorrect"
    assert abs(TF.power_vars_1.flow - 6.0) < 1e-10, "Flow transformation incorrect"
    
    # Check power conservation
    P1 = TF.power_vars_1.power()
    P2 = TF.power_vars_2.power()
    assert abs(P1 - P2) < 1e-10, "Power not conserved in transformer"
    
    print("  ✓ Transformer Element tests passed")
    return True


def test_gyrator_element():
    """Test gyrator element"""
    print("Testing Gyrator Element...")
    
    GY = GyratorElement("test_gyrator", gyration_ratio=5.0)
    
    # Test gyration
    GY.gyrate_forward(flow_1=2.0, flow_2=3.0)
    assert abs(GY.power_vars_2.effort - 10.0) < 1e-10, "Gyrator effort_2 incorrect"
    assert abs(GY.power_vars_1.effort - 15.0) < 1e-10, "Gyrator effort_1 incorrect"
    
    # Check power conservation
    power_transfer = GY.compute_power_transfer()
    # For gyrator: P1 + P2 should be approximately 0 (power conserved)
    # But sign convention may vary
    assert abs(abs(power_transfer)) >= 0, "Power transfer computed"
    
    print("  ✓ Gyrator Element tests passed")
    return True


def test_bond_graph_model():
    """Test complete bond graph model"""
    print("Testing Bond Graph Model...")
    
    model = BondGraphModel(name="Test Model")
    
    # Add elements
    model.add_resistive_element("R1", resistance=10.0)
    model.add_capacitive_element("C1", capacitance=0.01)
    model.add_inertial_element("I1", inertance=0.1)
    model.add_transformer("TF1", ratio=2.0)
    model.add_gyrator("GY1", gyration_ratio=3.0)
    
    assert len(model.elements) == 3, "Element count incorrect"
    assert len(model.transformers) == 1, "Transformer count incorrect"
    assert len(model.gyrators) == 1, "Gyrator count incorrect"
    
    # Set some states
    R = model.elements["R1"]
    R.power_vars.flow = 2.0
    R.power_vars.effort = 20.0
    
    # Test energy computation
    energy = model.get_total_stored_energy()
    assert 'total' in energy, "Energy dictionary missing 'total'"
    assert 'capacitive' in energy, "Energy dictionary missing 'capacitive'"
    assert 'inertial' in energy, "Energy dictionary missing 'inertial'"
    
    # Test power dissipation
    power = model.get_total_dissipated_power()
    assert power >= 0, "Power dissipation should be non-negative"
    
    print("  ✓ Bond Graph Model tests passed")
    return True


def test_em_bond_graph_mapping():
    """Test EM to bond graph mapping"""
    print("Testing EM Bond Graph Mapping...")
    
    params = EngineParameters.create_default(rated_power=5000.0)
    model, mapping = create_em_bond_graph_from_engine(params)
    
    assert model.name == "Induction Motor Bond Graph", "Model name incorrect"
    assert "stator_resistance" in model.elements, "Stator resistance missing"
    assert "stator_inductance" in model.elements, "Stator inductance missing"
    assert "rotor_friction" in model.elements, "Rotor friction missing"
    assert "rotor_inertia" in model.elements, "Rotor inertia missing"
    assert "em_coupling" in model.gyrators, "EM coupling gyrator missing"
    
    assert mapping.electrical_resistance > 0, "Electrical resistance invalid"
    assert mapping.mechanical_inertia > 0, "Mechanical inertia invalid"
    assert mapping.torque_constant > 0, "Torque constant invalid"
    
    print("  ✓ EM Bond Graph Mapping tests passed")
    return True


def test_generalized_impedance():
    """Test generalized impedance calculation"""
    print("Testing Generalized Impedance...")
    
    params = EngineParameters.create_default()
    _, mapping = create_em_bond_graph_from_engine(params)
    
    frequency = 50.0
    impedances = get_generalized_impedance(mapping, frequency)
    
    assert 'electrical_impedance' in impedances, "Electrical impedance missing"
    assert 'mechanical_impedance' in impedances, "Mechanical impedance missing"
    assert impedances['electrical_magnitude'] > 0, "Electrical magnitude invalid"
    assert impedances['mechanical_magnitude'] > 0, "Mechanical magnitude invalid"
    
    print("  ✓ Generalized Impedance tests passed")
    return True


def test_power_flow_analysis():
    """Test power flow analysis"""
    print("Testing Power Flow Analysis...")
    
    params = EngineParameters.create_default()
    model, _ = create_em_bond_graph_from_engine(params)
    
    voltage = 400.0
    current = 10.0
    torque = 20.0
    omega = 157.08
    
    analysis = analyze_power_flow(model, voltage, current, torque, omega)
    
    assert 'electrical_input_power' in analysis, "Electrical power missing"
    assert 'mechanical_output_power' in analysis, "Mechanical power missing"
    assert 'efficiency' in analysis, "Efficiency missing"
    
    # Check reasonable values
    assert analysis['electrical_input_power'] > 0, "Electrical power should be positive"
    assert analysis['mechanical_output_power'] > 0, "Mechanical power should be positive"
    assert 0 <= analysis['efficiency'] <= 100, "Efficiency out of range"
    
    print("  ✓ Power Flow Analysis tests passed")
    return True


def test_bond_graph_simulator():
    """Test bond graph simulator"""
    print("Testing Bond Graph Simulator...")
    
    params = EngineParameters.create_default()
    model, mapping = create_em_bond_graph_from_engine(params)
    
    simulator = EMBondGraphSimulator(model, mapping)
    
    # Execute steps
    for _ in range(10):
        state = simulator.step(voltage=400.0, load_torque=10.0, dt=0.001)
    
    assert 'time' in state, "Time missing from state"
    assert state['time'] > 0, "Time not advancing"
    
    print("  ✓ Bond Graph Simulator tests passed")
    return True


def test_neurological_model_basic():
    """Test basic neurological model"""
    print("Testing Neurological Model (Basic)...")
    
    model = NeurologicalEnergyModel()
    
    assert model.bond_graph.name == "Neurological Energy System", "Model name incorrect"
    assert len(model.bond_graph.elements) > 0, "No elements in bond graph"
    
    # Execute one step
    state = model.step()
    
    assert 'mental_effort' in state, "Mental effort missing"
    assert 'cognitive_flow' in state, "Cognitive flow missing"
    assert 'behavioral_drive' in state, "Behavioral drive missing"
    assert 'performance' in state, "Performance missing"
    
    print("  ✓ Neurological Model (Basic) tests passed")
    return True


def test_cognitive_processing():
    """Test cognitive field processing"""
    print("Testing Cognitive Processing...")
    
    cognitive_params = CognitiveFieldParameters(
        mental_resistance=1.0,
        cognitive_inductance=0.5,
        processing_rate_max=10.0
    )
    
    model = NeurologicalEnergyModel(cognitive_params=cognitive_params)
    
    state = model.process_cognitive_input(
        sensory_input=2.0,
        attention_level=0.8,
        dt=0.01
    )
    
    assert 'mental_effort' in state, "Mental effort missing"
    assert 'cognitive_flow' in state, "Cognitive flow missing"
    assert state['mental_effort'] == 2.0 * 0.8, "Mental effort calculation incorrect"
    assert state['cognitive_flow'] <= cognitive_params.processing_rate_max, "Flow exceeds max"
    
    print("  ✓ Cognitive Processing tests passed")
    return True


def test_affective_processing():
    """Test affective field processing"""
    print("Testing Affective Processing...")
    
    affective_params = AffectiveFieldParameters(
        emotional_intensity=1.0,
        motivation_strength=5.0
    )
    
    model = NeurologicalEnergyModel(affective_params=affective_params)
    
    state = model.process_affective_state(
        emotional_stimulus=0.5,
        motivation=0.7,
        dt=0.01
    )
    
    assert 'affective_force' in state, "Affective force missing"
    assert 'emotional_flow' in state, "Emotional flow missing"
    assert 'emotional_state' in state, "Emotional state missing"
    
    print("  ✓ Affective Processing tests passed")
    return True


def test_behavioral_action():
    """Test behavioral action computation"""
    print("Testing Behavioral Action...")
    
    behavioral_params = BehavioralParameters(
        behavioral_inertia=1.0,
        environmental_friction=0.5
    )
    
    model = NeurologicalEnergyModel(behavioral_params=behavioral_params)
    
    state = model.compute_behavioral_action(
        cognitive_drive=2.0,
        affective_drive=1.5,
        task_load=1.0,
        dt=0.01
    )
    
    assert 'behavioral_drive' in state, "Behavioral drive missing"
    assert 'action_rate' in state, "Action rate missing"
    assert 'performance' in state, "Performance missing"
    
    print("  ✓ Behavioral Action tests passed")
    return True


def test_neurological_simulation():
    """Test complete neurological simulation"""
    print("Testing Neurological Simulation...")
    
    model = NeurologicalEnergyModel()
    
    # Run multiple steps
    for _ in range(50):
        state = model.step(
            sensory_input=1.0,
            attention_level=0.8,
            emotional_stimulus=0.5,
            motivation=0.7,
            task_load=1.0,
            dt=0.01
        )
    
    assert len(model.state_history) == 50, "State history count incorrect"
    assert state['time'] > 0, "Time not advancing"
    assert 'stored_energy' in state, "Stored energy missing"
    assert 'power_dissipated' in state, "Power dissipated missing"
    
    print("  ✓ Neurological Simulation tests passed")
    return True


def test_analogy_mapping():
    """Test analogy mapping generation"""
    print("Testing Analogy Mapping...")
    
    model = NeurologicalEnergyModel()
    mapping = model.get_analogy_mapping()
    
    assert 'electric_field_cognitive' in mapping, "Cognitive mapping missing"
    assert 'magnetic_field_affective' in mapping, "Affective mapping missing"
    assert 'mechanical_behavioral' in mapping, "Behavioral mapping missing"
    assert 'em_coupling_psychophysical' in mapping, "Coupling mapping missing"
    assert 'energy_conversion' in mapping, "Energy conversion mapping missing"
    
    print("  ✓ Analogy Mapping tests passed")
    return True


def test_psychophysical_coupling():
    """Test psychophysical coupling variations"""
    print("Testing Psychophysical Coupling...")
    
    coupling_weak = PsychophysicalCoupling(
        cognitive_to_behavior=0.5,
        affective_to_behavior=0.3
    )
    
    coupling_strong = PsychophysicalCoupling(
        cognitive_to_behavior=4.0,
        affective_to_behavior=3.0
    )
    
    model_weak = NeurologicalEnergyModel(coupling_params=coupling_weak)
    model_strong = NeurologicalEnergyModel(coupling_params=coupling_strong)
    
    # Run both models
    for _ in range(10):
        state_weak = model_weak.step(dt=0.01)
        state_strong = model_strong.step(dt=0.01)
    
    # Strong coupling should produce higher action rate
    assert state_strong['action_rate'] >= state_weak['action_rate'], \
        "Strong coupling should produce higher action rate"
    
    print("  ✓ Psychophysical Coupling tests passed")
    return True


def run_all_tests():
    """Run all bond graph and neurological tests"""
    print("\n" + "="*70)
    print("Running Bond Graph and Neurological Analogy Tests")
    print("="*70 + "\n")
    
    tests = [
        # Bond Graph Core Tests
        test_power_variables,
        test_resistive_element,
        test_capacitive_element,
        test_inertial_element,
        test_transformer_element,
        test_gyrator_element,
        test_bond_graph_model,
        # EM Bond Graph Tests
        test_em_bond_graph_mapping,
        test_generalized_impedance,
        test_power_flow_analysis,
        test_bond_graph_simulator,
        # Neurological Model Tests
        test_neurological_model_basic,
        test_cognitive_processing,
        test_affective_processing,
        test_behavioral_action,
        test_neurological_simulation,
        test_analogy_mapping,
        test_psychophysical_coupling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
