# Arc-Halo EMEC - Electromagnetic Energy Conversion Simulator

**Virtual Engine Model with Rotor & Stator Dynamics + Bond Graph Generalization**

A comprehensive electro-mechanical energy conversion simulator implementing electromagnetic field equations for polyphase induction machines, with generalized bond graph framework and neurological analogy modeling.

## Overview

The EMEC (Electromagnetic Energy Conversion) module provides a complete virtual engine simulation framework that models:

- **Electromagnetic Field Equations**: Maxwell's equations solver for rotating electrical machines
- **Polyphase Induction Winding Model**: Three-phase (and general polyphase) winding configurations with inductance calculations
- **Rotor Mechanical Dynamics**: Newton's laws of motion with inertia, friction, and load torque
- **Stator Electrical Dynamics**: Voltage/current equations and power supply interface
- **Electro-Mechanical Coupling**: Complete energy conversion process simulation
- **Bond Graph Generalization**: Unified framework for multi-domain energy modeling
- **Neurological Analogy**: Novel mapping of EM energy conversion to cognitive-affective-behavioral processes

## Features

### ✨ Core Capabilities

**Electromagnetic Simulation:**
- **Maxwell's Equations**: Faraday's Law, Ampere's Law, Gauss's Laws
- **dq0 Transformation**: Park and inverse Park transformations for reference frame conversion
- **Flux Linkage Calculation**: Stator-rotor mutual inductances with position dependence
- **Torque Computation**: Electromagnetic torque from field interactions
- **Mechanical Dynamics**: Rotor acceleration, friction, and load torque effects
- **Three-Phase Supply**: Balanced voltage generation and power calculations
- **Performance Metrics**: Efficiency, power, speed, torque analysis

**Bond Graph Framework (NEW):**
- **Generalized Energy Domains**: Unified modeling across electrical, mechanical, hydraulic, thermal domains
- **Power Variables**: Effort-flow conjugate pairs with momentum and displacement
- **Bond Graph Elements**: R (resistor), C (capacitor), I (inertia), TF (transformer), GY (gyrator)
- **Domain Mapping**: Systematic mapping between physical domains
- **Generalized Impedance**: Unified impedance analysis across domains

**Neurological Analogy (NEW):**
- **Cognitive Field**: Mental effort, thought flow, cognitive inertia (↔ Electric field)
- **Affective Field**: Emotional intensity, motivational force (↔ Magnetic field)
- **Behavioral Action**: Action rate, habit formation (↔ Mechanical output)
- **Psychophysical Integration**: Mind-body coupling, behavioral feedback
- **Energy Analysis**: Mental fatigue, emotional regulation, performance efficiency

### 🎯 Applications

**Electromagnetic Systems:**
- Motor design and performance analysis
- Control system development and testing
- Educational demonstrations of EM principles
- Energy conversion optimization
- Transient analysis (startup, load changes)
- Multi-physics simulation

**Bond Graph Modeling:**
- Cross-domain energy system analysis
- Unified modeling of multi-physics systems
- Impedance matching and optimization
- Power flow analysis and visualization
- Domain-agnostic control design

**Neurological Analogy:**
- Cognitive workload modeling
- Psychomotor performance analysis
- Habit formation and behavioral dynamics
- Emotional-cognitive interaction studies
- Human-machine interface design
- Mental energy flow optimization

## Quick Start

### Installation

```bash
# Install dependencies
pip install numpy

# The module is ready to use - no compilation needed
```

### Basic Usage - Electromagnetic Simulation

```python
from emec import VirtualEngine

# Create a virtual induction motor
engine = VirtualEngine()

# Set load torque (constant 10 N⋅m)
engine.set_load_torque(lambda t, omega: 10.0)

# Run simulation
engine.simulate(duration=1.0, dt=1e-4)

# Get performance metrics
metrics = engine.get_performance_metrics()
print(f"Speed: {metrics['final_speed_rpm']:.1f} RPM")
print(f"Efficiency: {metrics['avg_efficiency']:.1f}%")
```

### Bond Graph Usage (NEW)

```python
from emec import (
    create_em_bond_graph_from_engine,
    EngineParameters,
    analyze_power_flow
)

# Create engine parameters
params = EngineParameters.create_default(rated_power=10000.0)

# Generate bond graph representation
model, mapping = create_em_bond_graph_from_engine(params)

# Analyze power flow
analysis = analyze_power_flow(
    model,
    voltage=400.0,
    current=15.0,
    torque=30.0,
    omega=157.08
)

print(f"Efficiency: {analysis['efficiency']:.2f}%")
print(f"Electrical Input: {analysis['electrical_input_power']:.2f} W")
print(f"Mechanical Output: {analysis['mechanical_output_power']:.2f} W")
```

### Neurological Analogy Usage (NEW)

```python
from emec import NeurologicalEnergyModel

# Create neurological energy model
model = NeurologicalEnergyModel()

# Simulate cognitive-affective-behavioral dynamics
state = model.step(
    sensory_input=1.0,        # Sensory information
    attention_level=0.8,      # Attention allocation
    emotional_stimulus=0.5,   # Emotional input
    motivation=0.7,           # Motivational drive
    task_load=1.0,            # Task demands
    dt=0.01
)

print(f"Cognitive Flow: {state['cognitive_flow']:.2f} thoughts/s")
print(f"Action Rate: {state['action_rate']:.2f}")
print(f"Performance: {state['performance']:.2f}")

# Get complete analogy mapping
mapping = model.get_analogy_mapping()
for key, desc in mapping.items():
    print(f"\n{desc}")
```

### Custom Parameters

```python
from emec import VirtualEngine, EngineParameters

# Create custom engine parameters
params = EngineParameters.create_default(rated_power=10000.0)
params.stator_electrical.rated_voltage = 690.0
params.rotor_mechanical.inertia = 0.05

# Create engine with custom parameters
engine = VirtualEngine(params)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Virtual Engine (EMEC)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  EM Field Solver │      │ Polyphase Winding│        │
│  │  (Maxwell Eqs)   │◄────►│     Model        │        │
│  └──────────────────┘      └──────────────────┘        │
│           │                          │                  │
│           │                          │                  │
│           ▼                          ▼                  │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │ Rotor Dynamics   │      │ Stator Dynamics  │        │
│  │ (Mechanics)      │◄────►│  (Electrical)    │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                          │
│                  Torque ◄──► Current                    │
│                  Speed  ◄──► Voltage                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Module Components

### 1. EMFieldSolver (`em_field_solver.py`)

Solves Maxwell's equations for electromagnetic fields in rotating machines:

- **Magnetic flux density**: B = μH
- **Induced EMF**: EMF = -dλ/dt (Faraday's Law)
- **Torque calculation**: T = (3/2)p(λ_d·i_q - λ_q·i_d)
- **Park transformation**: abc ↔ dq0 reference frames

```python
from emec import EMFieldSolver

solver = EMFieldSolver()
B = solver.compute_magnetic_flux_density(current, geometry_factor=1.0)
torque = solver.compute_torque(stator_flux, rotor_current, pole_pairs=2)
```

### 2. PolyphaseWindingModel (`polyphase_winding.py`)

Models multiphase induction windings:

- **Inductance matrices**: Self and mutual inductances
- **Flux linkages**: λ_s = L_ss·i_s + L_sr(θ)·i_r
- **Winding factors**: Distribution and pitch factors
- **Power calculations**: Active, reactive, apparent power

```python
from emec import PolyphaseWindingModel, WindingParameters

stator_params = WindingParameters(num_phases=3, turns_per_phase=100)
rotor_params = WindingParameters(num_phases=3, turns_per_phase=80)
winding = PolyphaseWindingModel(stator_params, rotor_params)

flux = winding.compute_flux_linkage(i_stator, i_rotor, theta_rotor)
```

### 3. RotorDynamics (`rotor_dynamics.py`)

Simulates rotor mechanical behavior:

- **Equation of motion**: J·dω/dt = T_em - T_load - T_friction
- **Friction models**: Viscous, Coulomb, windage
- **Slip calculation**: s = (ω_s - ω_r)/ω_s
- **Kinetic energy**: E = (1/2)Jω²

```python
from emec import RotorDynamics, RotorParameters

params = RotorParameters(inertia=0.01, friction_coefficient=0.001)
rotor = RotorDynamics(params)

state = rotor.solve_dynamics(T_em=15.0, dt=1e-4)
print(f"Speed: {state.speed_rpm} RPM")
```

### 4. StatorDynamics (`stator_dynamics.py`)

Models stator electrical system:

- **Voltage equations**: v = R·i + dλ/dt
- **Three-phase supply**: Balanced voltage generation
- **Power calculations**: P, Q, S, power factor
- **Losses**: Copper (I²R) and core losses

```python
from emec import StatorDynamics, StatorParameters

params = StatorParameters(rated_voltage=400.0, rated_frequency=50.0)
stator = StatorDynamics(params)

voltage = stator.compute_supply_voltage(time)
current = stator.solve_current_dynamics(voltage, flux, d_flux_dt, dt)
```

### 5. VirtualEngine (`virtual_engine.py`)

Integrates all components into complete simulator:

- **Coupled simulation**: Electrical + mechanical + electromagnetic
- **Time-stepping**: Euler integration with configurable dt
- **Performance metrics**: Efficiency, torque, power, speed
- **Data export**: Time-series data for analysis

```python
from emec import VirtualEngine

engine = VirtualEngine()
engine.simulate(duration=1.0)
data = engine.export_data()
```

## Examples

See example files for complete usage demonstrations:

```bash
# Basic electromagnetic simulation
python -m emec.examples

# Bond graph framework examples
python -m emec.examples_bond_graph

# Neurological analogy examples
python -m emec.examples_neurological
```

**Example Topics:**

**`examples.py`:**
1. Basic simulation with constant load
2. Variable load simulation
3. Custom engine parameters
4. Data export and analysis
5. Motor startup transient

**`examples_bond_graph.py` (NEW):**
1. Basic bond graph model with R, C, I elements
2. EM to bond graph mapping
3. Generalized impedance analysis
4. Energy domain equivalences
5. Bond graph simulation
6. Multi-domain comparison

**`examples_neurological.py` (NEW):**
1. Basic neurological energy model
2. Cognitive field processing
3. Affective field modulation
4. Behavioral action and habit formation
5. Complete EM ↔ Neurological analogy
6. Psychophysical efficiency analysis

## Testing

Run the test suite:

```bash
# Original EMEC tests
python -m emec.test_emec

# Bond graph and neurological tests
python -m emec.test_bond_graph

# All tests
python -m emec.test_emec && python -m emec.test_bond_graph
```

**Test Coverage:**
- 8 original EMEC tests (EM field, winding, rotor, stator, engine)
- 18 bond graph and neurological tests
- **26 total tests, all passing**

Tests cover:
- EM field solver accuracy
- Winding model calculations
- Rotor dynamics integration
- Stator voltage/current equations
- Complete engine simulation
- Bond graph elements (R, C, I, TF, GY)
- EM-to-bond-graph mapping
- Generalized impedance
- Neurological model components
- Cognitive, affective, behavioral processing
- Psychophysical coupling
- Data export functionality

## Physical Model

### Electromagnetic Equations

**Maxwell's Equations:**
- ∇×E = -∂B/∂t (Faraday's Law)
- ∇×H = J + ∂D/∂t (Ampere's Law)
- ∇·D = ρ (Gauss's Law)
- ∇·B = 0 (No magnetic monopoles)

**Voltage Equations (dq frame):**
- v_d = R·i_d + dλ_d/dt - ω·λ_q
- v_q = R·i_q + dλ_q/dt + ω·λ_d

**Torque Equation:**
- T_em = (3/2)p(λ_d·i_q - λ_q·i_d)

### Mechanical Equations

**Newton's Second Law (Rotation):**
- J·dω/dt = T_em - T_load - B·ω - T_coulomb - K_w·ω²

**Kinematics:**
- dθ/dt = ω

### Electrical Equations

**Stator Voltage:**
- v_s = R_s·i_s + dλ_s/dt

**Rotor Voltage (squirrel cage):**
- 0 = R_r·i_r + dλ_r/dt

**Flux Linkages:**
- λ_s = L_ss·i_s + L_sr(θ)·i_r
- λ_r = L_rr·i_r + L_rs(θ)·i_s

## Performance

- **Time step**: Configurable (default 1e-4 s for stability)
- **Simulation speed**: ~10,000 steps/second (typical hardware)
- **Accuracy**: Second-order effects included (friction, leakage, etc.)
- **Numerical stability**: Euler integration with small dt

## Future Enhancements

**Electromagnetic Simulation:**
- [ ] Runge-Kutta integration for better accuracy
- [ ] Space harmonic modeling
- [ ] Saturation effects
- [ ] Temperature-dependent parameters
- [ ] Advanced control strategies (FOC, DTC)
- [ ] Finite element coupling
- [ ] Real-time capability

**Bond Graph Framework:**
- [ ] Graphical bond graph visualization
- [ ] Automatic equation generation from bond graph
- [ ] Higher-order causality assignment
- [ ] Multi-port elements (3-port junctions)
- [ ] Modulated transformers and gyrators
- [ ] Bond graph reduction algorithms
- [ ] Integration with other modeling tools

**Neurological Analogy:**
- [ ] Neural network integration
- [ ] Reinforcement learning framework
- [ ] Attention mechanism modeling
- [ ] Memory consolidation dynamics
- [ ] Sleep-wake cycle modeling
- [ ] Multi-agent cognitive systems
- [ ] Clinical applications (depression, anxiety models)

## References

**Electromagnetic Theory:**
1. **Electric Machinery Fundamentals** - Stephen Chapman
2. **Analysis of Electric Machinery and Drive Systems** - Paul Krause
3. **Vector Control of AC Drives** - Peter Vas
4. **Theory of Electromechanical Energy Conversion** - Ralph Smith

**Bond Graph Theory:**
1. **System Dynamics: Modeling, Simulation, and Control of Mechatronic Systems** - Karnopp, Margolis, Rosenberg
2. **Bond Graph Methodology** - Wolfgang Borutzky
3. **Metamodelling: Bond Graphs and Dynamic Systems** - Gawthrop & Smith

**Neurological Modeling:**
1. **Neurodynamics: An Exploration in Mesoscopic Brain Dynamics** - Walter Freeman
2. "Emerging concepts for the dynamical organization of resting-state activity in the brain" - Deco, Jirsa, McIntosh
3. "The free-energy principle: a unified brain theory?" - Karl Friston

## Documentation

- [Main EMEC README](README.md) - This file
- [Bond Graph Guide](BOND_GRAPH_GUIDE.md) - Comprehensive guide to bond graph framework and neurological analogy
- [Project Overview](../README.md) - Overall Arc-Halo EMEC project
- [Examples](examples.py, examples_bond_graph.py, examples_neurological.py) - Usage examples

## Integration with Arc-Halo

The EMEC module complements the Arc-Halo Cognitive Fusion Reactor by providing:

- Physical system modeling capability
- Energy conversion simulation
- Multi-physics integration potential
- Control system validation
- **Bond graph framework for unified multi-domain modeling**
- **Neurological analogy enabling cognitive-physical system integration**

## Summary

**Arc-Halo EMEC v2.0** provides a comprehensive framework for:

1. **Electromagnetic Energy Conversion**: Complete induction motor simulation with Maxwell's equations
2. **Bond Graph Generalization**: Unified energy domain modeling across electrical, mechanical, and other physical systems
3. **Neurological Analogy**: Novel mapping of cognitive-affective-behavioral processes to electromagnetic principles

This creates a unique platform for:
- Cross-domain energy system analysis
- Interdisciplinary research bridging engineering and cognitive science
- Educational demonstrations of energy conversion principles
- Development of bio-inspired control systems
- Quantitative modeling of psychophysical processes

**Key Innovation**: Using bond graph theory as a unifying framework, EMEC demonstrates that the same mathematical structure governs:
- Electrical systems (voltage-current)
- Mechanical systems (torque-velocity)
- Neurological systems (mental effort-cognitive flow)

This enables insights from electromagnetic engineering to inform our understanding of cognitive and behavioral processes, and vice versa.

## License

Part of the Arc-Halo ecosystem.

---

**Arc-Halo EMEC** - Bridging electromagnetic theory and practical simulation 🔌⚡🔄
