"""
Example usage of the Virtual Engine EMEC simulator.

Demonstrates how to:
1. Create a virtual induction motor
2. Run simulations with different load conditions
3. Analyze performance metrics
4. Export data for visualization
"""

import numpy as np
from emec import VirtualEngine, EngineParameters


def example_basic_simulation():
    """Basic simulation with constant load"""
    print("="*70)
    print("Example 1: Basic Virtual Engine Simulation")
    print("="*70)
    
    # Create engine with default parameters
    engine = VirtualEngine()
    
    # Set a constant load torque (10 N⋅m)
    engine.set_load_torque(lambda t, omega: 10.0)
    
    # Run simulation for 1 second
    print("\nRunning simulation for 1.0 second...")
    engine.simulate(duration=1.0, dt=1e-4)
    
    # Get performance metrics
    metrics = engine.get_performance_metrics()
    
    print("\nPerformance Metrics:")
    print(f"  Final Speed:           {metrics['final_speed_rpm']:.1f} RPM")
    print(f"  Steady-State Speed:    {metrics['steady_state_speed']:.1f} RPM")
    print(f"  Average Torque:        {metrics['avg_torque']:.2f} N⋅m")
    print(f"  Max Torque:            {metrics['max_torque']:.2f} N⋅m")
    print(f"  Mechanical Power:      {metrics['avg_power_mechanical']:.1f} W")
    print(f"  Electrical Power:      {metrics['avg_power_electrical']:.1f} W")
    print(f"  Efficiency:            {metrics['avg_efficiency']:.1f} %")
    
    return engine, metrics


def example_variable_load():
    """Simulation with time-varying load"""
    print("\n" + "="*70)
    print("Example 2: Variable Load Simulation")
    print("="*70)
    
    # Create engine
    engine = VirtualEngine()
    
    # Set a time-varying load (ramp from 5 to 15 N⋅m)
    def variable_load(t, omega):
        return 5.0 + 10.0 * min(t / 0.5, 1.0)
    
    engine.set_load_torque(variable_load)
    
    # Run simulation
    print("\nRunning simulation with variable load...")
    engine.simulate(duration=1.0, dt=1e-4)
    
    # Get metrics
    metrics = engine.get_performance_metrics()
    
    print("\nPerformance Metrics:")
    print(f"  Final Speed:           {metrics['final_speed_rpm']:.1f} RPM")
    print(f"  Average Torque:        {metrics['avg_torque']:.2f} N⋅m")
    print(f"  Efficiency:            {metrics['avg_efficiency']:.1f} %")
    
    return engine, metrics


def example_custom_parameters():
    """Simulation with custom engine parameters"""
    print("\n" + "="*70)
    print("Example 3: Custom Engine Parameters")
    print("="*70)
    
    # Create custom parameters (higher power motor)
    params = EngineParameters.create_default(rated_power=10000.0)
    
    # Modify some parameters
    params.stator_electrical.rated_voltage = 690.0  # Higher voltage
    params.rotor_mechanical.inertia = 0.05          # Higher inertia
    
    # Create engine
    engine = VirtualEngine(params)
    
    # Set load
    engine.set_load_torque(lambda t, omega: 20.0)
    
    # Run simulation
    print("\nRunning simulation with custom parameters...")
    print(f"  Rated Voltage: {params.stator_electrical.rated_voltage} V")
    print(f"  Rotor Inertia: {params.rotor_mechanical.inertia} kg⋅m²")
    
    engine.simulate(duration=1.5, dt=1e-4)
    
    # Get metrics
    metrics = engine.get_performance_metrics()
    
    print("\nPerformance Metrics:")
    print(f"  Final Speed:           {metrics['final_speed_rpm']:.1f} RPM")
    print(f"  Mechanical Power:      {metrics['avg_power_mechanical']:.1f} W")
    print(f"  Efficiency:            {metrics['avg_efficiency']:.1f} %")
    
    return engine, metrics


def example_data_export():
    """Export simulation data for analysis"""
    print("\n" + "="*70)
    print("Example 4: Data Export")
    print("="*70)
    
    # Create and run simulation
    engine = VirtualEngine()
    engine.set_load_torque(lambda t, omega: 8.0)
    engine.simulate(duration=0.5, dt=1e-4)
    
    # Export data
    data = engine.export_data()
    
    print("\nExported data arrays:")
    for key, array in data.items():
        print(f"  {key:20s}: shape {array.shape}, "
              f"range [{array.min():.2f}, {array.max():.2f}]")
    
    # Show some statistics
    print("\nSpeed Statistics:")
    print(f"  Initial: {data['speed_rpm'][0]:.2f} RPM")
    print(f"  Final:   {data['speed_rpm'][-1]:.2f} RPM")
    print(f"  Mean:    {np.mean(data['speed_rpm']):.2f} RPM")
    
    print("\nTorque Statistics:")
    print(f"  Mean:    {np.mean(data['torque']):.2f} N⋅m")
    print(f"  Max:     {np.max(data['torque']):.2f} N⋅m")
    print(f"  Min:     {np.min(data['torque']):.2f} N⋅m")
    
    return data


def example_motor_startup():
    """Simulate motor startup transient"""
    print("\n" + "="*70)
    print("Example 5: Motor Startup Transient")
    print("="*70)
    
    # Create engine
    engine = VirtualEngine()
    
    # Light load for startup
    engine.set_load_torque(lambda t, omega: 5.0)
    
    # Run longer simulation to see full startup
    print("\nSimulating motor startup...")
    engine.simulate(duration=2.0, dt=1e-4)
    
    # Analyze startup
    data = engine.export_data()
    
    # Find time to reach 95% of final speed
    final_speed = data['speed_rpm'][-1]
    target_speed = 0.95 * final_speed
    
    time_to_95 = None
    for i, speed in enumerate(data['speed_rpm']):
        if speed >= target_speed:
            time_to_95 = data['time'][i]
            break
    
    print("\nStartup Analysis:")
    print(f"  Final Speed:           {final_speed:.1f} RPM")
    print(f"  Time to 95% speed:     {time_to_95:.3f} s" if time_to_95 else "  Not reached")
    print(f"  Peak Starting Torque:  {np.max(data['torque'][:1000]):.2f} N⋅m")
    print(f"  Steady-State Torque:   {np.mean(data['torque'][-1000:]):.2f} N⋅m")
    
    return engine, data


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "Virtual Engine EMEC Simulator" + " "*24 + "║")
    print("║" + " "*10 + "Electro-Mechanical Energy Conversion" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        # Run examples
        engine1, metrics1 = example_basic_simulation()
        engine2, metrics2 = example_variable_load()
        engine3, metrics3 = example_custom_parameters()
        data = example_data_export()
        engine5, data5 = example_motor_startup()
        
        # Summary
        print("\n" + "="*70)
        print("All examples completed successfully!")
        print("="*70)
        print("\nThe Virtual Engine simulator can model:")
        print("  ✓ Electromagnetic field dynamics (Maxwell's equations)")
        print("  ✓ Polyphase induction winding behavior")
        print("  ✓ Rotor mechanical dynamics")
        print("  ✓ Stator electrical dynamics")
        print("  ✓ Electro-mechanical energy conversion")
        print("\nUse cases:")
        print("  • Motor design and analysis")
        print("  • Performance prediction")
        print("  • Control system development")
        print("  • Educational demonstrations")
        
    except Exception as e:
        print(f"\n❌ Error during examples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
