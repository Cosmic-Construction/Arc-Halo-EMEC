"""
Neurological Analogy Examples

Demonstrates the neurological analogy to electromagnetic energy conversion.
Shows how cognitive, affective, and behavioral processes can be modeled
using the same bond graph framework as electromagnetic systems.
"""

import numpy as np
import sys

from emec import (
    NeurologicalEnergyModel,
    CognitiveFieldParameters,
    AffectiveFieldParameters,
    BehavioralParameters,
    PsychophysicalCoupling
)


def example_basic_neurological_model():
    """Example 1: Basic neurological energy model"""
    print("\n" + "="*70)
    print("Example 1: Basic Neurological Energy Model")
    print("="*70)
    
    # Create model with default parameters
    model = NeurologicalEnergyModel()
    
    print("\nNeurological Energy Model Initialized")
    print(f"Bond Graph Model: {model.bond_graph.name}")
    print(f"Elements: {len(model.bond_graph.elements)}")
    
    # Execute one step
    state = model.step(
        sensory_input=1.0,
        attention_level=0.8,
        emotional_stimulus=0.5,
        motivation=0.7,
        task_load=1.0,
        dt=0.01
    )
    
    print("\nSystem State:")
    print(f"  Mental Effort: {state['mental_effort']:.4f}")
    print(f"  Cognitive Flow: {state['cognitive_flow']:.4f} thoughts/s")
    print(f"  Affective Force: {state['affective_force']:.4f}")
    print(f"  Emotional Flow: {state['emotional_flow']:.4f}")
    print(f"  Behavioral Drive: {state['behavioral_drive']:.4f}")
    print(f"  Action Rate: {state['action_rate']:.4f}")
    print(f"  Performance: {state['performance']:.4f}")
    
    print("\n✓ Basic neurological model example completed")


def example_cognitive_processing():
    """Example 2: Cognitive field processing"""
    print("\n" + "="*70)
    print("Example 2: Cognitive Field Processing")
    print("="*70)
    
    # Create model with custom cognitive parameters
    cognitive_params = CognitiveFieldParameters(
        mental_resistance=0.5,        # Lower resistance = easier processing
        cognitive_inductance=0.3,     # Lower inertia = faster adaptation
        attention_capacitance=3.0,    # Higher capacity = more working memory
        processing_rate_max=15.0,     # Higher max = better cognitive ability
        mental_fatigue_rate=0.05      # Lower fatigue rate = more stamina
    )
    
    model = NeurologicalEnergyModel(cognitive_params=cognitive_params)
    
    print("\nCognitive Parameters:")
    print(f"  Mental Resistance: {cognitive_params.mental_resistance}")
    print(f"  Cognitive Inductance: {cognitive_params.cognitive_inductance}")
    print(f"  Attention Capacitance: {cognitive_params.attention_capacitance}")
    print(f"  Max Processing Rate: {cognitive_params.processing_rate_max}")
    
    print("\nSimulating cognitive processing over time...")
    
    # Simulate varying attention and sensory load
    duration = 1.0
    dt = 0.01
    steps = int(duration / dt)
    
    for i in range(steps):
        t = i * dt
        # Varying sensory input (simulating task difficulty)
        sensory_input = 1.0 + 0.5 * np.sin(2 * np.pi * t)
        # Decreasing attention (simulating fatigue)
        attention_level = max(0.5, 1.0 - 0.3 * t)
        
        state = model.step(
            sensory_input=sensory_input,
            attention_level=attention_level,
            emotional_stimulus=0.3,
            motivation=0.6,
            task_load=1.0,
            dt=dt
        )
    
    final_state = state
    print(f"\nFinal State (t = {final_state['time']:.2f} s):")
    print(f"  Cognitive Flow: {final_state['cognitive_flow']:.4f} thoughts/s")
    print(f"  Cognitive State: {final_state['cognitive_state']:.4f}")
    print(f"  Attention Load: {final_state['attention_load']:.4f}")
    print(f"  Performance: {final_state['performance']:.4f}")
    
    print("\nInterpretation:")
    print("  - Cognitive flow represents rate of information processing")
    print("  - Cognitive state accumulates mental effort over time")
    print("  - Attention load fills the working memory buffer")
    print("  - Performance depends on sustained cognitive processing")
    
    print("\n✓ Cognitive processing example completed")


def example_affective_modulation():
    """Example 3: Affective field modulation"""
    print("\n" + "="*70)
    print("Example 3: Affective Field Modulation")
    print("="*70)
    
    # Create model with custom affective parameters
    affective_params = AffectiveFieldParameters(
        emotional_intensity=1.5,      # Higher baseline emotional intensity
        affective_inertia=1.2,        # Slower emotional changes
        emotional_capacitance=4.0,    # Larger emotional buffer
        motivation_strength=7.0,      # Stronger motivational drive
        emotional_damping=0.15        # Less regulation (more emotional)
    )
    
    model = NeurologicalEnergyModel(affective_params=affective_params)
    
    print("\nAffective Parameters:")
    print(f"  Emotional Intensity: {affective_params.emotional_intensity}")
    print(f"  Affective Inertia: {affective_params.affective_inertia}")
    print(f"  Emotional Capacitance: {affective_params.emotional_capacitance}")
    print(f"  Motivation Strength: {affective_params.motivation_strength}")
    
    print("\nSimulating emotional state changes...")
    
    # Simulate emotional stimulus variation
    duration = 2.0
    dt = 0.01
    states = []
    
    for i in range(int(duration / dt)):
        t = i * dt
        # Emotional stimulus spike (e.g., stressful event)
        if 0.5 < t < 1.0:
            emotional_stimulus = 2.0
        else:
            emotional_stimulus = 0.3
        
        # Motivation varies
        motivation = 0.5 + 0.3 * np.sin(np.pi * t)
        
        state = model.step(
            sensory_input=1.0,
            attention_level=0.7,
            emotional_stimulus=emotional_stimulus,
            motivation=motivation,
            task_load=1.0,
            dt=dt
        )
        
        if i % 20 == 0:
            states.append(state)
    
    print(f"\nEmotional State Evolution:")
    for i, st in enumerate(states[::5]):  # Show every 5th stored state
        print(f"  t={st['time']:.2f}s: Emotional State={st['emotional_state']:.4f}, "
              f"Mood={st['mood_level']:.4f}, Performance={st['performance']:.4f}")
    
    print("\nInterpretation:")
    print("  - Emotional state shows inertia (slow changes)")
    print("  - Mood level integrates emotional experiences")
    print("  - High emotional stimulus affects performance")
    print("  - Motivation provides sustained affective drive")
    
    print("\n✓ Affective modulation example completed")


def example_behavioral_action():
    """Example 4: Behavioral action and habits"""
    print("\n" + "="*70)
    print("Example 4: Behavioral Action and Habit Formation")
    print("="*70)
    
    # Create model with custom behavioral parameters
    behavioral_params = BehavioralParameters(
        behavioral_inertia=2.0,       # Strong habits
        environmental_friction=0.3,   # Moderate environmental constraints
        action_threshold=0.05,        # Low threshold for action
        habit_strength=1.5,           # Strong habit formation
        fatigue_coefficient=0.03      # Low physical fatigue
    )
    
    model = NeurologicalEnergyModel(behavioral_params=behavioral_params)
    
    print("\nBehavioral Parameters:")
    print(f"  Behavioral Inertia: {behavioral_params.behavioral_inertia}")
    print(f"  Environmental Friction: {behavioral_params.environmental_friction}")
    print(f"  Habit Strength: {behavioral_params.habit_strength}")
    
    print("\nSimulating repeated task performance (habit formation)...")
    
    # Simulate repeated task with varying difficulty
    duration = 3.0
    dt = 0.01
    
    for i in range(int(duration / dt)):
        t = i * dt
        
        # Task load varies (easier over time as skill develops)
        task_load = 2.0 * np.exp(-t / 2.0) + 0.5
        
        # Consistent cognitive and affective input
        state = model.step(
            sensory_input=1.2,
            attention_level=0.85,
            emotional_stimulus=0.4,
            motivation=0.8,
            task_load=task_load,
            dt=dt
        )
    
    final_state = state
    print(f"\nFinal State (t = {final_state['time']:.2f} s):")
    print(f"  Behavioral Drive: {final_state['behavioral_drive']:.4f}")
    print(f"  Action Rate: {final_state['action_rate']:.4f}")
    print(f"  Behavioral Momentum: {final_state['behavioral_momentum']:.4f}")
    print(f"  Habit Strength: {final_state['habit_strength']:.4f}")
    print(f"  Performance: {final_state['performance']:.4f}")
    
    print("\nInterpretation:")
    print("  - Behavioral inertia creates momentum in repeated actions")
    print("  - Habit strength accumulates with repeated performance")
    print("  - Performance improves as task load decreases and habits form")
    print("  - Environmental friction limits maximum action rate")
    
    print("\n✓ Behavioral action example completed")


def example_complete_analogy_mapping():
    """Example 5: Complete EM-Neurological analogy mapping"""
    print("\n" + "="*70)
    print("Example 5: Complete EM ↔ Neurological Analogy")
    print("="*70)
    
    model = NeurologicalEnergyModel()
    
    # Get analogy mapping
    mapping = model.get_analogy_mapping()
    
    print("\nComplete Domain Mapping:\n")
    for key, description in mapping.items():
        print(description)
        print()
    
    print("="*70)
    print("\nKey Insights:")
    print("="*70)
    print("""
1. ELECTRIC FIELD ↔ COGNITIVE FIELD
   - Both involve potential differences driving flow
   - Voltage → Mental effort needed for processing
   - Current → Rate of information/thought processing
   - Resistance → Cognitive load that impedes processing

2. MAGNETIC FIELD ↔ AFFECTIVE FIELD
   - Both create fields that influence behavior
   - Magnetic flux → Emotional state flux through system
   - MMF → Motivational force driving affective changes
   - Stored magnetic energy → Emotional potential energy

3. MECHANICAL OUTPUT ↔ BEHAVIORAL ACTION
   - Both represent observable, measurable output
   - Torque → Behavioral drive/impulse to act
   - Angular velocity → Rate of action/performance
   - Inertia → Habit strength and behavioral momentum

4. ELECTROMAGNETIC COUPLING ↔ PSYCHOPHYSICAL INTEGRATION
   - Both couple different energy domains
   - E-M coupling → Cognitive-affective interaction
   - EM-mechanical → Mental/emotional to behavioral conversion
   - Back-EMF → Behavioral feedback to mental state

5. ENERGY FLOW
   - Electrical input → Cognitive input (attention, perception)
   - Magnetic modulation → Affective modulation (emotion, motivation)
   - Mechanical output → Behavioral output (action, performance)
   - Losses → Mental fatigue, emotional regulation, physical constraints
   - Storage → Working memory, emotional states, learned habits
    """)
    
    print("✓ Complete analogy mapping example completed")


def example_psychophysical_efficiency():
    """Example 6: Psychophysical efficiency analysis"""
    print("\n" + "="*70)
    print("Example 6: Psychophysical Efficiency")
    print("="*70)
    
    # Compare different coupling strengths
    coupling_scenarios = [
        ("Weak Coupling", PsychophysicalCoupling(
            cognitive_to_behavior=0.5,
            affective_to_behavior=0.3,
            behavior_to_cognitive=0.1,
            behavior_to_affective=0.1
        )),
        ("Moderate Coupling", PsychophysicalCoupling(
            cognitive_to_behavior=2.0,
            affective_to_behavior=1.5,
            behavior_to_cognitive=0.5,
            behavior_to_affective=0.3
        )),
        ("Strong Coupling", PsychophysicalCoupling(
            cognitive_to_behavior=4.0,
            affective_to_behavior=3.0,
            behavior_to_cognitive=1.0,
            behavior_to_affective=0.8
        ))
    ]
    
    print("\nComparing psychophysical coupling strengths:\n")
    
    for scenario_name, coupling in coupling_scenarios:
        model = NeurologicalEnergyModel(coupling_params=coupling)
        
        # Run simulation
        duration = 0.5
        dt = 0.01
        
        for _ in range(int(duration / dt)):
            state = model.step(
                sensory_input=1.0,
                attention_level=0.8,
                emotional_stimulus=0.6,
                motivation=0.7,
                task_load=1.0,
                dt=dt
            )
        
        print(f"{scenario_name}:")
        print(f"  Cognitive→Behavior: {coupling.cognitive_to_behavior:.2f}")
        print(f"  Affective→Behavior: {coupling.affective_to_behavior:.2f}")
        print(f"  Final Action Rate: {state['action_rate']:.4f}")
        print(f"  Final Performance: {state['performance']:.4f}")
        print(f"  Stored Energy: {state['stored_energy']:.4f}")
        print(f"  Power Dissipated: {state['power_dissipated']:.4f}")
        
        # Compute efficiency-like metric
        if state['stored_energy'] + state['power_dissipated'] > 0:
            efficiency = state['performance'] / (state['stored_energy'] + state['power_dissipated'])
            print(f"  Psychomotor Efficiency: {efficiency:.4f}")
        print()
    
    print("Interpretation:")
    print("  - Stronger coupling → Higher action rate and performance")
    print("  - Similar to motor torque constant in EM systems")
    print("  - Efficiency reflects how well mental/emotional energy")
    print("    converts to behavioral output")
    
    print("\n✓ Psychophysical efficiency example completed")


def run_all_examples():
    """Run all neurological analogy examples"""
    print("\n" + "="*70)
    print("NEUROLOGICAL ANALOGY EXAMPLES")
    print("="*70)
    print("\nDemonstrating neurological analogy to electromagnetic energy conversion")
    print("using bond graph theory as a unifying framework.")
    
    try:
        example_basic_neurological_model()
        example_cognitive_processing()
        example_affective_modulation()
        example_behavioral_action()
        example_complete_analogy_mapping()
        example_psychophysical_efficiency()
        
        print("\n" + "="*70)
        print("ALL NEUROLOGICAL ANALOGY EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70)
        
        print("\n" + "="*70)
        print("SUMMARY: Bond Graph Unified Framework")
        print("="*70)
        print("""
The bond graph framework provides a powerful, domain-agnostic approach
to modeling energy conversion systems. By mapping:

  ELECTROMAGNETIC SYSTEM ↔ NEUROLOGICAL SYSTEM
  
  Voltage       ↔  Mental Effort
  Current       ↔  Cognitive Flow
  Magnetic Flux ↔  Affective State
  Torque        ↔  Behavioral Drive
  Speed         ↔  Action Rate
  
We gain insights into:
  1. How cognitive effort translates to action
  2. How emotions modulate behavior
  3. Energy storage in memory and habits
  4. Dissipation as mental and physical fatigue
  5. Efficiency of psychomotor performance

This analogy enables:
  - Quantitative modeling of cognitive-affective-behavioral processes
  - Design of interventions to improve "psychomotor efficiency"
  - Understanding of mental energy flow and conversion
  - Cross-domain insights from electromagnetic engineering
        """)
        
    except Exception as e:
        print(f"\n❌ Error in examples: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_examples()
    sys.exit(0 if success else 1)
