"""
Bond Graph Examples

Demonstrates the bond graph generalization framework for energy domain analysis.
Shows how to use bond graph theory to model electromagnetic systems and
draw analogies with other energy domains.
"""

import numpy as np
import sys

from emec import (
    BondGraphModel,
    EnergyDomain,
    create_em_bond_graph_from_engine,
    EngineParameters,
    analyze_power_flow,
    get_generalized_impedance,
    compute_energy_domain_equivalences,
    EMBondGraphSimulator
)


def example_basic_bond_graph():
    """Example 1: Basic bond graph with R, C, I elements"""
    print("\n" + "="*70)
    print("Example 1: Basic Bond Graph Model")
    print("="*70)
    
    # Create bond graph model
    model = BondGraphModel(name="Simple RLC System")
    
    # Add elements
    model.add_resistive_element("resistor", resistance=10.0, domain=EnergyDomain.ELECTRICAL)
    model.add_inertial_element("inductor", inertance=0.1, domain=EnergyDomain.ELECTRICAL)
    model.add_capacitive_element("capacitor", capacitance=0.001, domain=EnergyDomain.ELECTRICAL)
    
    print(f"\nModel: {model.name}")
    print(f"Elements: {list(model.elements.keys())}")
    
    # Set some state values
    R = model.elements["resistor"]
    R.power_vars.effort = 10.0  # 10V
    R.power_vars.flow = 1.0      # 1A
    
    L = model.elements["inductor"]
    L.power_vars.effort = 5.0
    L.power_vars.flow = 0.5
    
    # Get system state
    state = model.get_system_state()
    energy = state['energy']
    
    print("\nSystem State:")
    print(f"  Stored Energy (Inertial/Kinetic): {energy['inertial']:.6f} J")
    print(f"  Stored Energy (Capacitive/Potential): {energy['capacitive']:.6f} J")
    print(f"  Total Stored Energy: {energy['total']:.6f} J")
    print(f"  Power Dissipated: {state['power_dissipated']:.6f} W")
    
    print("\n✓ Basic bond graph example completed")


def example_em_bond_graph_mapping():
    """Example 2: Electromagnetic system bond graph mapping"""
    print("\n" + "="*70)
    print("Example 2: EM to Bond Graph Mapping")
    print("="*70)
    
    # Create engine parameters
    params = EngineParameters.create_default(rated_power=5000.0)
    
    # Create bond graph from engine
    model, mapping = create_em_bond_graph_from_engine(params)
    
    print(f"\nModel: {model.name}")
    print(f"\nEM Bond Graph Mapping:")
    print(f"  Electrical Resistance: {mapping.electrical_resistance:.4f} Ω")
    print(f"  Electrical Inductance: {mapping.electrical_inductance:.6f} H")
    print(f"  Mechanical Friction: {mapping.mechanical_friction:.6f} N·m·s/rad")
    print(f"  Mechanical Inertia: {mapping.mechanical_inertia:.6f} kg·m²")
    print(f"  Torque Constant: {mapping.torque_constant:.4f} N·m/A")
    print(f"  Voltage Constant: {mapping.voltage_constant:.4f} V·s/rad")
    
    # Analyze power flow
    voltage = 400.0  # V
    current = 10.0   # A
    torque = 20.0    # N·m
    omega = 157.08   # rad/s (1500 rpm)
    
    power_analysis = analyze_power_flow(model, voltage, current, torque, omega)
    
    print(f"\nPower Flow Analysis:")
    print(f"  Electrical Input Power: {power_analysis['electrical_input_power']:.2f} W")
    print(f"  Mechanical Output Power: {power_analysis['mechanical_output_power']:.2f} W")
    print(f"  Resistive Losses: {power_analysis['resistive_losses']:.2f} W")
    print(f"  Efficiency: {power_analysis['efficiency']:.2f}%")
    
    print("\n✓ EM bond graph mapping example completed")


def example_generalized_impedance():
    """Example 3: Generalized impedance across domains"""
    print("\n" + "="*70)
    print("Example 3: Generalized Impedance Analysis")
    print("="*70)
    
    # Create engine parameters
    params = EngineParameters.create_default(rated_power=10000.0)
    
    # Create bond graph mapping
    _, mapping = create_em_bond_graph_from_engine(params)
    
    # Compute generalized impedances
    frequency = 50.0  # Hz
    impedances = get_generalized_impedance(mapping, frequency)
    
    print(f"\nGeneralized Impedance at {frequency} Hz:")
    print(f"\nElectrical Domain:")
    print(f"  Impedance: {impedances['electrical_impedance']}")
    print(f"  Magnitude: {impedances['electrical_magnitude']:.4f} Ω")
    print(f"  Phase: {np.degrees(impedances['electrical_phase']):.2f}°")
    
    print(f"\nMechanical Domain:")
    print(f"  Impedance: {impedances['mechanical_impedance']}")
    print(f"  Magnitude: {impedances['mechanical_magnitude']:.6f} N·m·s/rad")
    print(f"  Phase: {np.degrees(impedances['mechanical_phase']):.2f}°")
    
    print("\nInterpretation:")
    print("  - Both domains show similar impedance structure: Z = R + jωL")
    print("  - Electrical: resistive and inductive components")
    print("  - Mechanical: friction and inertial components")
    print("  - Phase angle indicates energy storage vs dissipation ratio")
    
    print("\n✓ Generalized impedance example completed")


def example_domain_equivalences():
    """Example 4: Energy domain equivalences"""
    print("\n" + "="*70)
    print("Example 4: Energy Domain Equivalences")
    print("="*70)
    
    # Create engine parameters
    params = EngineParameters.create_default()
    _, mapping = create_em_bond_graph_from_engine(params)
    
    # Get equivalences
    equivalences = compute_energy_domain_equivalences(mapping)
    
    print("\nBond Graph Energy Domain Equivalences:\n")
    for key, description in equivalences.items():
        print(f"{key.replace('_', ' ').title()}:")
        print(description)
        print()
    
    print("✓ Domain equivalences example completed")


def example_bond_graph_simulation():
    """Example 5: Bond graph-based simulation"""
    print("\n" + "="*70)
    print("Example 5: Bond Graph Simulation")
    print("="*70)
    
    # Create engine and bond graph
    params = EngineParameters.create_default(rated_power=5000.0)
    model, mapping = create_em_bond_graph_from_engine(params)
    
    # Create simulator
    simulator = EMBondGraphSimulator(model, mapping)
    
    print("\nRunning bond graph simulation...")
    
    # Simulate
    voltage = 400.0    # Applied voltage
    load_torque = 15.0  # Load torque
    dt = 0.001         # Time step
    duration = 0.1     # Simulation duration
    
    states = []
    for i in range(int(duration / dt)):
        state = simulator.step(voltage, load_torque, dt)
        if i % 10 == 0:  # Store every 10th step
            states.append(state)
    
    # Show final state
    final_state = states[-1]
    print(f"\nFinal State (t = {final_state['time']:.3f} s):")
    if 'angular_velocity' in final_state:
        omega = final_state['angular_velocity']
        print(f"  Angular Velocity: {omega:.4f} rad/s ({omega * 60 / (2*np.pi):.1f} rpm)")
    if 'current' in final_state:
        print(f"  Current: {final_state['current']:.4f} A")
    if 'flux_linkage' in final_state:
        print(f"  Flux Linkage: {final_state['flux_linkage']:.6f} Wb")
    
    print("\nBond Graph Representation Benefits:")
    print("  ✓ Unified framework for electrical and mechanical domains")
    print("  ✓ Clear identification of energy storage and dissipation")
    print("  ✓ Systematic analysis of power flow and conversion")
    print("  ✓ Domain-agnostic modeling enabling cross-domain analogies")
    
    print("\n✓ Bond graph simulation example completed")


def example_multi_domain_comparison():
    """Example 6: Multi-domain comparison"""
    print("\n" + "="*70)
    print("Example 6: Multi-Domain Comparison")
    print("="*70)
    
    print("\nBond Graph Power Variables Across Domains:\n")
    
    domains = [
        ("Electrical", "Voltage (V)", "Current (I)", "Flux Linkage (λ)", "Charge (Q)"),
        ("Mechanical (Rot)", "Torque (τ)", "Ang. Velocity (ω)", "Ang. Momentum (L)", "Angle (θ)"),
        ("Mechanical (Trans)", "Force (F)", "Velocity (v)", "Momentum (p)", "Position (x)"),
        ("Hydraulic", "Pressure (P)", "Flow Rate (Q)", "Pressure Mom.", "Volume (V)"),
        ("Thermal", "Temperature (T)", "Heat Flow (q)", "Heat", "Entropy (S)")
    ]
    
    print(f"{'Domain':<20} {'Effort':<20} {'Flow':<20} {'Momentum':<20} {'Displacement':<15}")
    print("-" * 100)
    for domain, effort, flow, momentum, displacement in domains:
        print(f"{domain:<20} {effort:<20} {flow:<20} {momentum:<20} {displacement:<15}")
    
    print("\nCommon Bond Graph Elements:")
    print("  R (Resistive): Dissipates energy as heat")
    print("  C (Capacitive): Stores potential energy (effort-dependent)")
    print("  I (Inertial): Stores kinetic energy (flow-dependent)")
    print("  TF (Transformer): Power-conserving effort/flow scaling")
    print("  GY (Gyrator): Power-conserving effort-flow coupling")
    
    print("\n✓ Multi-domain comparison example completed")


def run_all_examples():
    """Run all bond graph examples"""
    print("\n" + "="*70)
    print("BOND GRAPH GENERALIZATION EXAMPLES")
    print("="*70)
    print("\nDemonstrating bond graph theory for generalized energy modeling")
    print("and electromagnetic-to-mechanical energy conversion analysis.")
    
    try:
        example_basic_bond_graph()
        example_em_bond_graph_mapping()
        example_generalized_impedance()
        example_domain_equivalences()
        example_bond_graph_simulation()
        example_multi_domain_comparison()
        
        print("\n" + "="*70)
        print("ALL BOND GRAPH EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error in examples: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_examples()
    sys.exit(0 if success else 1)
