# Bond Graph Generalization and Neurological Analogy

## Overview

This document describes the bond graph generalization framework and neurological analogy model added to the Arc-Halo EMEC system. These additions provide a unified, domain-agnostic approach to modeling energy conversion systems and enable novel insights through cross-domain analogies.

## Table of Contents

1. [Bond Graph Theory](#bond-graph-theory)
2. [Bond Graph Framework](#bond-graph-framework)
3. [EM to Bond Graph Mapping](#em-to-bond-graph-mapping)
4. [Neurological Analogy](#neurological-analogy)
5. [Usage Examples](#usage-examples)
6. [API Reference](#api-reference)

---

## Bond Graph Theory

### What are Bond Graphs?

Bond graphs are a graphical modeling technique for energy systems that uses a unified framework across different physical domains (electrical, mechanical, hydraulic, thermal, etc.). They represent energy flow through systems using conjugate power variables.

### Core Concepts

**Power Variables (Conjugate Pairs)**
- **Effort (e)**: Generalized force-like quantity
- **Flow (f)**: Generalized velocity-like quantity
- **Power**: P = e × f

**Energy Variables**
- **Momentum (p)**: ∫e dt (generalized momentum)
- **Displacement (q)**: ∫f dt (generalized displacement)

**Bond Graph Elements**
- **R (Resistor)**: Dissipative element (e = R·f)
- **C (Capacitor)**: Potential energy storage (e = q/C)
- **I (Inertia)**: Kinetic energy storage (f = p/I)
- **TF (Transformer)**: Power-conserving scaling (e₂ = n·e₁, f₁ = n·f₂)
- **GY (Gyrator)**: Power-conserving coupling (e₂ = r·f₁, e₁ = r·f₂)

### Energy Domain Mappings

| Domain | Effort | Flow | Momentum | Displacement |
|--------|--------|------|----------|--------------|
| **Electrical** | Voltage (V) | Current (I) | Flux Linkage (λ) | Charge (Q) |
| **Mechanical (Rot)** | Torque (τ) | Angular Velocity (ω) | Angular Momentum (L) | Angle (θ) |
| **Mechanical (Trans)** | Force (F) | Velocity (v) | Momentum (p) | Position (x) |
| **Hydraulic** | Pressure (P) | Flow Rate (Q) | Pressure Momentum | Volume (V) |
| **Thermal** | Temperature (T) | Heat Flow (q) | Heat | Entropy (S) |
| **Magnetic** | MMF (A·turns) | Flux Rate (Wb/s) | Flux (Wb) | Flux Linkage |

---

## Bond Graph Framework

### Implementation

The bond graph framework is implemented in `emec/bond_graph.py` and provides:

1. **Power Variables** (`PowerVariables` class)
   - Stores effort, flow, momentum, displacement
   - Computes instantaneous power
   - Integrates over time

2. **Domain Mappings** (`DomainMapping` dataclass)
   - Maps physical quantities to bond graph variables
   - Includes units and scaling factors
   - Provides physical interpretation

3. **Bond Graph Elements**
   - `ResistiveElement`: Energy dissipation (e = R·f)
   - `CapacitiveElement`: Potential energy storage (e = q/C)
   - `InertialElement`: Kinetic energy storage (f = p/I)
   - `TransformerElement`: Power-conserving scaling
   - `GyratorElement`: Power-conserving coupling

4. **Bond Graph Model** (`BondGraphModel` class)
   - Container for elements and connections
   - Computes total stored energy
   - Computes total dissipated power
   - Manages system state

### Example: Simple RLC System

```python
from emec import BondGraphModel, EnergyDomain

# Create model
model = BondGraphModel(name="RLC Circuit")

# Add elements
model.add_resistive_element("R", resistance=10.0, domain=EnergyDomain.ELECTRICAL)
model.add_inertial_element("L", inertance=0.1, domain=EnergyDomain.ELECTRICAL)
model.add_capacitive_element("C", capacitance=0.001, domain=EnergyDomain.ELECTRICAL)

# Analyze system
energy = model.get_total_stored_energy()
power_loss = model.get_total_dissipated_power()
```

---

## EM to Bond Graph Mapping

### Electromagnetic System Bond Graph Representation

The electromagnetic energy conversion system (induction motor) maps to bond graph elements as follows:

**Electrical Domain**
- Stator Resistance → R-element (electrical resistance)
- Stator Inductance → I-element (magnetic energy storage)
- Voltage → Effort
- Current → Flow
- Flux Linkage → Momentum

**Mechanical Domain**
- Rotor Friction → R-element (mechanical damping)
- Rotor Inertia → I-element (kinetic energy storage)
- Torque → Effort
- Angular Velocity → Flow
- Angular Momentum → Momentum

**Electromechanical Coupling**
- EM Torque-Current Relationship → GY-element (gyrator)
- Torque Constant → Gyration ratio
- Back-EMF → Reverse coupling through gyrator

### Implementation

The EM-to-bond-graph mapping is in `emec/em_bond_graph_mapping.py`:

```python
from emec import create_em_bond_graph_from_engine, EngineParameters

# Create engine parameters
params = EngineParameters.create_default(rated_power=5000.0)

# Generate bond graph representation
model, mapping = create_em_bond_graph_from_engine(params)

# Mapping contains:
# - electrical_resistance, electrical_inductance
# - mechanical_friction, mechanical_inertia
# - torque_constant, voltage_constant
```

### Generalized Impedance

Bond graph formulation enables generalized impedance analysis:

**Electrical Impedance**: Z_e = R_s + jωL_s

**Mechanical Impedance**: Z_m = B + jωJ

Both have same structure (resistive + reactive components), enabling direct comparison and analysis.

```python
from emec import get_generalized_impedance

impedances = get_generalized_impedance(mapping, frequency=50.0)
# Returns: electrical_impedance, mechanical_impedance, magnitudes, phases
```

### Power Flow Analysis

```python
from emec import analyze_power_flow

analysis = analyze_power_flow(
    model,
    voltage=400.0,
    current=10.0,
    torque=20.0,
    omega=157.08
)

# Returns:
# - electrical_input_power
# - mechanical_output_power
# - resistive_losses
# - stored_energy
# - efficiency
```

---

## Neurological Analogy

### Conceptual Framework

The neurological analogy maps psychological processes to electromagnetic phenomena using bond graph theory as the unifying framework.

### Domain Mappings

**Electric Field ↔ Cognitive Field**
- Voltage → Mental Effort / Cognitive Potential
- Current → Thought Flow / Cognitive Processing Rate
- Resistance → Cognitive Load / Mental Resistance
- Inductance → Cognitive Inertia / Mental Momentum
- Flux Linkage → Accumulated Cognitive State
- Charge → Integrated Thought

**Magnetic Field ↔ Affective Field**
- Magnetic Field → Emotional Field Intensity
- Magnetic Flux → Affective State Flux
- MMF → Motivational Force
- Magnetic Energy → Emotional Potential Energy
- Permeability → Emotional Susceptibility

**Mechanical Domain ↔ Behavioral Action**
- Torque → Behavioral Drive / Action Impulse
- Angular Velocity → Action Rate / Performance Velocity
- Inertia → Behavioral Inertia / Habit Strength
- Friction → Environmental Constraints
- Angular Momentum → Sustained Action Momentum
- Angle → Cumulative Behavior

**Electromagnetic Coupling ↔ Psychophysical Integration**
- E-field ↔ M-field → Cognitive ↔ Affective Interaction
- EM → Mechanical → Mental/Emotional → Behavioral
- Torque Constant → Cognitive-Behavioral Coupling
- Back-EMF → Behavioral Feedback to Cognition

### Energy Conversion Process

```
Cognitive Input (Attention, Sensory)
    ↓
Affective Modulation (Emotion, Motivation)
    ↓
Behavioral Output (Action, Performance)
```

**Energy Storage**
- Cognitive: Working memory, mental state
- Affective: Emotional state, mood
- Behavioral: Habits, learned behaviors

**Energy Dissipation**
- Cognitive: Mental fatigue, cognitive load
- Affective: Emotional regulation effort
- Behavioral: Physical fatigue, environmental friction

### Implementation

The neurological analogy is implemented in `emec/neurological_analogy.py`:

```python
from emec import (
    NeurologicalEnergyModel,
    CognitiveFieldParameters,
    AffectiveFieldParameters,
    BehavioralParameters,
    PsychophysicalCoupling
)

# Create model with custom parameters
cognitive = CognitiveFieldParameters(
    mental_resistance=1.0,
    cognitive_inductance=0.5,
    processing_rate_max=10.0
)

affective = AffectiveFieldParameters(
    emotional_intensity=1.5,
    motivation_strength=7.0
)

behavioral = BehavioralParameters(
    behavioral_inertia=2.0,
    habit_strength=1.5
)

coupling = PsychophysicalCoupling(
    cognitive_to_behavior=2.0,
    affective_to_behavior=1.5
)

model = NeurologicalEnergyModel(
    cognitive_params=cognitive,
    affective_params=affective,
    behavioral_params=behavioral,
    coupling_params=coupling
)
```

### Simulation

```python
# Run simulation step
state = model.step(
    sensory_input=1.0,        # Sensory information input
    attention_level=0.8,      # Attention allocation (0-1)
    emotional_stimulus=0.5,   # Emotional stimulus intensity
    motivation=0.7,           # Motivational drive (0-1)
    task_load=1.0,            # Task demand/load
    dt=0.01                   # Time step
)

# State contains:
# - mental_effort, cognitive_flow, cognitive_state
# - affective_force, emotional_flow, emotional_state
# - behavioral_drive, action_rate, performance
# - stored_energy, power_dissipated
```

### Insights and Applications

**Cognitive Psychology**
- Model mental workload and cognitive capacity
- Analyze information processing dynamics
- Study attention and working memory
- Predict mental fatigue

**Affective Science**
- Model emotional dynamics and mood
- Analyze motivational processes
- Study emotion regulation
- Understand affective-cognitive interaction

**Behavioral Science**
- Model habit formation and behavioral inertia
- Analyze psychomotor performance
- Study environmental influences on behavior
- Optimize behavioral interventions

**Psychophysical Integration**
- Understand mind-body interaction
- Model cognitive-behavioral therapy processes
- Analyze stress and performance
- Design human-machine interfaces

---

## Usage Examples

### Example 1: Bond Graph Analysis of Induction Motor

```python
from emec import (
    create_em_bond_graph_from_engine,
    EngineParameters,
    analyze_power_flow,
    compute_energy_domain_equivalences
)

# Create engine
params = EngineParameters.create_default(rated_power=10000.0)
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
print(f"Losses: {analysis['resistive_losses']:.2f} W")

# Get domain equivalences
equivalences = compute_energy_domain_equivalences(mapping)
for key, desc in equivalences.items():
    print(f"\n{key}:\n{desc}")
```

### Example 2: Neurological Model of Task Performance

```python
from emec import NeurologicalEnergyModel

# Create model
model = NeurologicalEnergyModel()

# Simulate task with varying difficulty
duration = 2.0
dt = 0.01

for i in range(int(duration / dt)):
    t = i * dt
    
    # Varying task load (learning curve)
    task_load = 2.0 * np.exp(-t / 1.0) + 0.5
    
    # Consistent input
    state = model.step(
        sensory_input=1.2,
        attention_level=0.85,
        emotional_stimulus=0.4,
        motivation=0.8,
        task_load=task_load,
        dt=dt
    )

print(f"Final Performance: {state['performance']:.2f}")
print(f"Habit Strength: {state['habit_strength']:.2f}")
print(f"Efficiency: {state['performance'] / state['stored_energy']:.2f}")
```

### Example 3: Comparative Analysis

```python
from emec import (
    NeurologicalEnergyModel,
    create_em_bond_graph_from_engine,
    EngineParameters
)

# Create both models
em_params = EngineParameters.create_default()
em_model, em_mapping = create_em_bond_graph_from_engine(em_params)

neuro_model = NeurologicalEnergyModel()

# Compare structures
print("EM Model Elements:", list(em_model.elements.keys()))
print("Neuro Model Elements:", list(neuro_model.bond_graph.elements.keys()))

# Show analogies
analogies = neuro_model.get_analogy_mapping()
print("\nAnalogies:")
for key, desc in analogies.items():
    print(f"\n{desc}")
```

### Running Examples

```bash
# Bond graph examples
python -m emec.examples_bond_graph

# Neurological analogy examples
python -m emec.examples_neurological

# Original EMEC examples
python -m emec.examples
```

---

## API Reference

### Bond Graph Core (`bond_graph.py`)

**Classes:**
- `PowerVariables`: Conjugate power variables (effort, flow, momentum, displacement)
- `DomainMapping`: Maps physical domain to bond graph variables
- `BondGraphElement`: Base class for all bond graph elements
- `ResistiveElement`: R-element (dissipation)
- `CapacitiveElement`: C-element (potential energy storage)
- `InertialElement`: I-element (kinetic energy storage)
- `TransformerElement`: TF-element (power-conserving scaling)
- `GyratorElement`: GY-element (power-conserving coupling)
- `BondGraphModel`: Complete bond graph system model

**Enums:**
- `EnergyDomain`: ELECTRICAL, MECHANICAL_ROTATION, MECHANICAL_TRANSLATION, HYDRAULIC, THERMAL, MAGNETIC, NEUROLOGICAL

**Constants:**
- `DOMAIN_MAPPINGS`: Dictionary of predefined domain mappings

### EM Bond Graph Mapping (`em_bond_graph_mapping.py`)

**Classes:**
- `EMBondGraphMapping`: Complete EM-to-bond-graph mapping
- `EMBondGraphSimulator`: Bond graph-based EM simulator

**Functions:**
- `create_em_bond_graph_from_engine(params)`: Create bond graph from engine parameters
- `analyze_power_flow(model, voltage, current, torque, omega)`: Analyze power flow
- `get_generalized_impedance(mapping, frequency)`: Compute generalized impedances
- `compute_energy_domain_equivalences(mapping)`: Get domain equivalence descriptions

### Neurological Analogy (`neurological_analogy.py`)

**Classes:**
- `CognitiveFieldParameters`: Cognitive field parameters
- `AffectiveFieldParameters`: Affective field parameters
- `BehavioralParameters`: Behavioral domain parameters
- `PsychophysicalCoupling`: Coupling between domains
- `NeurologicalEnergyModel`: Complete neurological energy model

**Enums:**
- `NeurologicalDomain`: COGNITIVE, AFFECTIVE, BEHAVIORAL, SENSORY, MEMORY, ATTENTION

**Methods:**
- `NeurologicalEnergyModel.step()`: Execute simulation step
- `NeurologicalEnergyModel.process_cognitive_input()`: Process cognitive field
- `NeurologicalEnergyModel.process_affective_state()`: Process affective field
- `NeurologicalEnergyModel.compute_behavioral_action()`: Compute behavioral output
- `NeurologicalEnergyModel.get_analogy_mapping()`: Get complete analogy mapping
- `NeurologicalEnergyModel.export_comparison()`: Export EM-neurological comparison

---

## Testing

Run tests:

```bash
# Bond graph and neurological tests
python -m emec.test_bond_graph

# Original EMEC tests
python -m emec.test_emec

# All tests
python -m emec.test_emec && python -m emec.test_bond_graph
```

Test coverage:
- 18 bond graph and neurological tests
- 8 original EMEC tests
- **26 total tests, all passing**

---

## References

### Bond Graph Theory
1. Karnopp, D., Margolis, D., & Rosenberg, R. (2012). *System Dynamics: Modeling, Simulation, and Control of Mechatronic Systems*. Wiley.
2. Borutzky, W. (2010). *Bond Graph Methodology*. Springer.
3. Gawthrop, P. J., & Smith, L. P. (1996). *Metamodelling: Bond Graphs and Dynamic Systems*. Prentice Hall.

### Electromagnetic Theory
1. Chapman, S. J. (2005). *Electric Machinery Fundamentals*. McGraw-Hill.
2. Krause, P. C., Wasynczuk, O., & Sudhoff, S. D. (2013). *Analysis of Electric Machinery and Drive Systems*. Wiley-IEEE Press.

### Neurological Modeling
1. Freeman, W. J. (2000). *Neurodynamics: An Exploration in Mesoscopic Brain Dynamics*. Springer.
2. Deco, G., Jirsa, V. K., & McIntosh, A. R. (2011). "Emerging concepts for the dynamical organization of resting-state activity in the brain." *Nature Reviews Neuroscience*, 12(1), 43-56.
3. Friston, K. (2010). "The free-energy principle: a unified brain theory?" *Nature Reviews Neuroscience*, 11(2), 127-138.

---

## Conclusion

The bond graph generalization framework provides a powerful, unified approach to modeling energy conversion across domains. The neurological analogy demonstrates the framework's flexibility and provides novel insights into cognitive-affective-behavioral processes by drawing parallels with electromagnetic energy conversion.

This implementation enables:
1. **Unified Modeling**: Same framework for electrical, mechanical, and neurological systems
2. **Cross-Domain Insights**: Lessons from electromagnetic engineering applied to neurological processes
3. **Quantitative Analysis**: Mathematical modeling of mental energy flow and conversion
4. **Educational Value**: Understanding complex systems through familiar analogies
5. **Research Platform**: Foundation for interdisciplinary research in psychophysics

The framework is extensible and can be applied to other domains (hydraulic, thermal, chemical, etc.) following the same bond graph principles.
