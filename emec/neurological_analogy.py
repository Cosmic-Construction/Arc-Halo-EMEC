"""
Neurological Analogy Model for Electromagnetic Energy Conversion

This module implements a novel neurological analogy to electromagnetic energy conversion,
mapping cognitive and affective processes to electrical and magnetic phenomena using
bond graph theory as a unifying framework.

Conceptual Framework:
====================

ELECTRICAL DOMAIN → COGNITIVE FIELD
- Voltage (Effort) → Mental Effort / Cognitive Potential
- Current (Flow) → Thought Flow / Cognitive Processing Rate
- Resistance → Cognitive Load / Mental Resistance
- Inductance → Cognitive Inertia / Mental Momentum
- Flux Linkage → Accumulated Cognitive State
- Charge → Integrated Thought

MAGNETIC DOMAIN → AFFECTIVE FIELD
- Magnetic Field Intensity → Emotional Field Intensity
- Magnetic Flux → Affective State Flux
- Magnetic Flux Density → Emotional Density
- MMF (Magnetomotive Force) → Affective Motivational Force

MECHANICAL DOMAIN → BEHAVIORAL ACTION
- Torque (Effort) → Behavioral Drive / Action Impulse
- Angular Velocity (Flow) → Action Rate / Behavioral Velocity
- Inertia → Behavioral Inertia / Habit Strength
- Friction → Behavioral Resistance / Environmental Constraints
- Angular Momentum → Sustained Action Momentum

COUPLING:
- Electromagnetic Coupling → Psychophysical Integration
- Electric Field ↔ Magnetic Field → Cognitive ↔ Affective Interaction
- EM ↔ Mechanical → Mental/Emotional ↔ Behavioral Action

ENERGY CONVERSION:
- Electrical Input → Cognitive Input (attention, sensory processing)
- Magnetic Field → Affective Modulation (emotional processing)
- Mechanical Output → Behavioral Output (action, performance)
- Efficiency → Psychomotor Efficiency / Behavioral Effectiveness

The model provides insights into:
1. How cognitive effort translates to behavioral action
2. How affective states modulate cognitive-behavioral coupling
3. Energy dissipation as mental fatigue and behavioral friction
4. Storage elements as memory, habits, and emotional states
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .bond_graph import (
    BondGraphModel,
    EnergyDomain,
    PowerVariables,
    DomainMapping,
    ResistiveElement,
    CapacitiveElement,
    InertialElement,
    GyratorElement
)


# Define neurological energy domain
NEUROLOGICAL_DOMAINS = {
    EnergyDomain.NEUROLOGICAL: DomainMapping(
        domain=EnergyDomain.NEUROLOGICAL,
        effort_name="mental_effort",
        flow_name="cognitive_flow",
        momentum_name="cognitive_state",
        displacement_name="integrated_thought",
        effort_unit="cognitive_units",
        flow_unit="thoughts/s",
        momentum_unit="cognitive_state_units",
        displacement_unit="thought_units",
        description="Neurological domain: mental effort - cognitive flow conjugate pair"
    )
}


class NeurologicalDomain(Enum):
    """Neurological energy sub-domains"""
    COGNITIVE = "cognitive"          # Cognitive field (analogous to electric field)
    AFFECTIVE = "affective"          # Affective/emotional field (analogous to magnetic field)
    BEHAVIORAL = "behavioral"        # Behavioral action (analogous to mechanical)
    SENSORY = "sensory"             # Sensory input
    MEMORY = "memory"               # Memory storage
    ATTENTION = "attention"         # Attention control


@dataclass
class CognitiveFieldParameters:
    """
    Parameters for cognitive field (analogous to electric field).
    
    Cognitive field represents:
    - Mental potential differences
    - Information processing capacity
    - Attention allocation
    - Working memory dynamics
    """
    mental_resistance: float = 1.0        # Cognitive load/resistance to processing
    cognitive_inductance: float = 0.5     # Cognitive inertia/mental momentum
    attention_capacitance: float = 2.0    # Attention buffer capacity
    processing_rate_max: float = 10.0     # Maximum cognitive processing rate
    mental_fatigue_rate: float = 0.1      # Rate of mental fatigue accumulation


@dataclass
class AffectiveFieldParameters:
    """
    Parameters for affective field (analogous to magnetic field).
    
    Affective field represents:
    - Emotional states and intensities
    - Motivational forces
    - Mood dynamics
    - Emotional regulation capacity
    """
    emotional_intensity: float = 1.0      # Base emotional field intensity
    affective_inertia: float = 0.8        # Emotional inertia (slow mood changes)
    emotional_capacitance: float = 3.0    # Emotional buffer/regulation capacity
    motivation_strength: float = 5.0      # Motivational drive strength
    emotional_damping: float = 0.2        # Emotional regulation/damping


@dataclass
class BehavioralParameters:
    """
    Parameters for behavioral action domain (analogous to mechanical).
    
    Behavioral domain represents:
    - Observable actions and behaviors
    - Motor responses
    - Task performance
    - Habit formation and execution
    """
    behavioral_inertia: float = 1.0       # Habit strength/behavioral inertia
    environmental_friction: float = 0.5   # Environmental constraints/friction
    action_threshold: float = 0.1         # Minimum drive for action initiation
    habit_strength: float = 0.3           # Strength of habitual responses
    fatigue_coefficient: float = 0.05     # Physical fatigue rate


@dataclass
class PsychophysicalCoupling:
    """
    Coupling parameters between cognitive/affective and behavioral domains.
    
    Represents the psychophysical transformation:
    - How mental/emotional states drive behavior
    - How behavior feeds back to mental/emotional states
    """
    cognitive_to_behavior: float = 2.0    # Cognitive → behavioral coupling strength
    affective_to_behavior: float = 1.5    # Affective → behavioral coupling strength
    behavior_to_cognitive: float = 0.5    # Behavioral → cognitive feedback
    behavior_to_affective: float = 0.3    # Behavioral → affective feedback
    integration_time: float = 1.0         # Integration time constant


class NeurologicalEnergyModel:
    """
    Complete neurological energy conversion model using bond graph theory.
    
    Models the flow of "mental energy" from:
    1. Cognitive input (sensory/attention) → 
    2. Affective modulation (emotional processing) →
    3. Behavioral output (action/performance)
    
    With energy storage in:
    - Working memory (cognitive capacitance)
    - Emotional states (affective capacitance)
    - Habits (behavioral inertia)
    
    And energy dissipation as:
    - Mental fatigue (cognitive resistance)
    - Emotional regulation (affective damping)
    - Physical/environmental constraints (behavioral friction)
    """
    
    def __init__(self,
                 cognitive_params: Optional[CognitiveFieldParameters] = None,
                 affective_params: Optional[AffectiveFieldParameters] = None,
                 behavioral_params: Optional[BehavioralParameters] = None,
                 coupling_params: Optional[PsychophysicalCoupling] = None):
        """
        Initialize neurological energy model.
        
        Args:
            cognitive_params: Cognitive field parameters
            affective_params: Affective field parameters
            behavioral_params: Behavioral parameters
            coupling_params: Psychophysical coupling parameters
        """
        self.cognitive = cognitive_params or CognitiveFieldParameters()
        self.affective = affective_params or AffectiveFieldParameters()
        self.behavioral = behavioral_params or BehavioralParameters()
        self.coupling = coupling_params or PsychophysicalCoupling()
        
        # Build bond graph model
        self.bond_graph = self._build_bond_graph()
        
        # State variables
        self.time = 0.0
        self.state_history: List[Dict] = []
        
    def _build_bond_graph(self) -> BondGraphModel:
        """Build bond graph representation of neurological system"""
        model = BondGraphModel(name="Neurological Energy System")
        
        # Cognitive domain elements
        model.add_resistive_element(
            "cognitive_load",
            resistance=self.cognitive.mental_resistance,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_inertial_element(
            "cognitive_momentum",
            inertance=self.cognitive.cognitive_inductance,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_capacitive_element(
            "attention_buffer",
            capacitance=self.cognitive.attention_capacitance,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        # Affective domain elements
        model.add_resistive_element(
            "emotional_regulation",
            resistance=self.affective.emotional_damping,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_inertial_element(
            "emotional_inertia",
            inertance=self.affective.affective_inertia,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_capacitive_element(
            "emotional_buffer",
            capacitance=self.affective.emotional_capacitance,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        # Behavioral domain elements
        model.add_resistive_element(
            "behavioral_friction",
            resistance=self.behavioral.environmental_friction,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_inertial_element(
            "behavioral_inertia",
            inertance=self.behavioral.behavioral_inertia,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        model.add_capacitive_element(
            "habit_formation",
            capacitance=self.behavioral.habit_strength,
            domain=EnergyDomain.NEUROLOGICAL
        )
        
        # Coupling elements (gyrators for psychophysical transformation)
        model.add_gyrator(
            "cognitive_behavioral_coupling",
            gyration_ratio=self.coupling.cognitive_to_behavior
        )
        
        model.add_gyrator(
            "affective_behavioral_coupling",
            gyration_ratio=self.coupling.affective_to_behavior
        )
        
        return model
    
    def process_cognitive_input(self, 
                               sensory_input: float,
                               attention_level: float,
                               dt: float) -> Dict[str, float]:
        """
        Process cognitive input (analogous to applying voltage).
        
        Args:
            sensory_input: Sensory information input
            attention_level: Attention allocation (0 to 1)
            dt: Time step
            
        Returns:
            Cognitive processing state
        """
        # Mental effort = sensory input × attention level
        mental_effort = sensory_input * attention_level
        
        # Get cognitive elements
        cognitive_load = self.bond_graph.elements.get("cognitive_load")
        cognitive_momentum = self.bond_graph.elements.get("cognitive_momentum")
        attention_buffer = self.bond_graph.elements.get("attention_buffer")
        
        # Compute cognitive flow (thought processing rate)
        if cognitive_load and isinstance(cognitive_load, ResistiveElement):
            cognitive_flow = cognitive_load.compute_flow(mental_effort)
        else:
            cognitive_flow = mental_effort / (self.cognitive.mental_resistance + 1e-6)
        
        # Limit by maximum processing rate
        cognitive_flow = np.clip(cognitive_flow, 0, self.cognitive.processing_rate_max)
        
        # Update cognitive momentum (mental state accumulation)
        if cognitive_momentum and isinstance(cognitive_momentum, InertialElement):
            cognitive_momentum.update_state(mental_effort, dt)
        
        # Update attention buffer
        if attention_buffer and isinstance(attention_buffer, CapacitiveElement):
            attention_buffer.update_state(cognitive_flow, dt)
        
        return {
            'mental_effort': mental_effort,
            'cognitive_flow': cognitive_flow,
            'cognitive_state': cognitive_momentum.power_vars.momentum if cognitive_momentum else 0.0,
            'attention_load': attention_buffer.power_vars.displacement if attention_buffer else 0.0
        }
    
    def process_affective_state(self,
                               emotional_stimulus: float,
                               motivation: float,
                               dt: float) -> Dict[str, float]:
        """
        Process affective/emotional state (analogous to magnetic field).
        
        Args:
            emotional_stimulus: Emotional input stimulus
            motivation: Motivational drive
            dt: Time step
            
        Returns:
            Affective processing state
        """
        # Affective force = emotional stimulus + motivation
        affective_force = emotional_stimulus + motivation * self.affective.motivation_strength
        
        # Get affective elements
        emotional_regulation = self.bond_graph.elements.get("emotional_regulation")
        emotional_inertia = self.bond_graph.elements.get("emotional_inertia")
        emotional_buffer = self.bond_graph.elements.get("emotional_buffer")
        
        # Compute emotional flow (affective processing rate)
        if emotional_regulation and isinstance(emotional_regulation, ResistiveElement):
            emotional_flow = emotional_regulation.compute_flow(affective_force)
        else:
            emotional_flow = affective_force / (self.affective.emotional_damping + 1e-6)
        
        # Update emotional inertia (slow mood changes)
        if emotional_inertia and isinstance(emotional_inertia, InertialElement):
            emotional_inertia.update_state(affective_force, dt)
        
        # Update emotional buffer
        if emotional_buffer and isinstance(emotional_buffer, CapacitiveElement):
            emotional_buffer.update_state(emotional_flow, dt)
        
        return {
            'affective_force': affective_force,
            'emotional_flow': emotional_flow,
            'emotional_state': emotional_inertia.power_vars.momentum if emotional_inertia else 0.0,
            'mood_level': emotional_buffer.power_vars.displacement if emotional_buffer else 0.0
        }
    
    def compute_behavioral_action(self,
                                 cognitive_drive: float,
                                 affective_drive: float,
                                 task_load: float,
                                 dt: float) -> Dict[str, float]:
        """
        Compute behavioral action output (analogous to mechanical output/torque).
        
        Args:
            cognitive_drive: Drive from cognitive processing
            affective_drive: Drive from affective state
            task_load: External task demands/load
            dt: Time step
            
        Returns:
            Behavioral action state
        """
        # Total behavioral drive (via psychophysical coupling)
        behavioral_drive = (
            self.coupling.cognitive_to_behavior * cognitive_drive +
            self.coupling.affective_to_behavior * affective_drive
        )
        
        # Get behavioral elements
        behavioral_friction = self.bond_graph.elements.get("behavioral_friction")
        behavioral_inertia = self.bond_graph.elements.get("behavioral_inertia")
        habit_formation = self.bond_graph.elements.get("habit_formation")
        
        # Net behavioral force (drive - task load - friction)
        current_action_rate = behavioral_inertia.power_vars.flow if behavioral_inertia else 0.0
        friction_force = self.behavioral.environmental_friction * current_action_rate
        net_force = behavioral_drive - task_load - friction_force
        
        # Update behavioral inertia (habits, momentum)
        if behavioral_inertia and isinstance(behavioral_inertia, InertialElement):
            behavioral_inertia.update_state(net_force, dt)
            action_rate = behavioral_inertia.power_vars.flow
        else:
            action_rate = 0.0
        
        # Update habit formation
        if habit_formation and isinstance(habit_formation, CapacitiveElement):
            habit_formation.update_state(action_rate, dt)
        
        # Compute performance (work done)
        performance = action_rate * task_load
        
        return {
            'behavioral_drive': behavioral_drive,
            'action_rate': action_rate,
            'performance': performance,
            'habit_strength': habit_formation.power_vars.displacement if habit_formation else 0.0,
            'behavioral_momentum': behavioral_inertia.power_vars.momentum if behavioral_inertia else 0.0
        }
    
    def step(self,
             sensory_input: float = 1.0,
             attention_level: float = 0.8,
             emotional_stimulus: float = 0.5,
             motivation: float = 0.7,
             task_load: float = 1.0,
             dt: float = 0.01) -> Dict[str, float]:
        """
        Execute one time step of neurological energy conversion.
        
        Args:
            sensory_input: Sensory input level
            attention_level: Attention allocation (0-1)
            emotional_stimulus: Emotional stimulus intensity
            motivation: Motivational drive (0-1)
            task_load: Task demand/load
            dt: Time step
            
        Returns:
            Complete system state
        """
        # Process cognitive field
        cognitive_state = self.process_cognitive_input(sensory_input, attention_level, dt)
        
        # Process affective field
        affective_state = self.process_affective_state(emotional_stimulus, motivation, dt)
        
        # Compute behavioral action
        behavioral_state = self.compute_behavioral_action(
            cognitive_state['cognitive_flow'],
            affective_state['emotional_flow'],
            task_load,
            dt
        )
        
        # Compute energy analysis
        energy = self.bond_graph.get_total_stored_energy()
        power_dissipated = self.bond_graph.get_total_dissipated_power()
        
        # Update time
        self.time += dt
        
        # Combine state
        state = {
            'time': self.time,
            **cognitive_state,
            **affective_state,
            **behavioral_state,
            'stored_energy': energy['total'],
            'power_dissipated': power_dissipated
        }
        
        self.state_history.append(state)
        
        return state
    
    def get_analogy_mapping(self) -> Dict[str, str]:
        """
        Get complete mapping between EM and neurological domains.
        
        Returns:
            Dictionary describing the analogy
        """
        return {
            'electric_field_cognitive': (
                "ELECTRIC FIELD ↔ COGNITIVE FIELD\n"
                "├─ Voltage → Mental Effort / Cognitive Potential\n"
                "├─ Current → Thought Flow / Processing Rate\n"
                "├─ Resistance → Cognitive Load / Mental Resistance\n"
                "├─ Inductance → Cognitive Inertia / Mental Momentum\n"
                "├─ Flux Linkage → Accumulated Cognitive State\n"
                "└─ Charge → Integrated Thought"
            ),
            'magnetic_field_affective': (
                "MAGNETIC FIELD ↔ AFFECTIVE FIELD\n"
                "├─ Magnetic Field → Emotional Field Intensity\n"
                "├─ Magnetic Flux → Affective State Flux\n"
                "├─ MMF → Motivational Force\n"
                "├─ Magnetic Energy → Emotional Potential Energy\n"
                "└─ Permeability → Emotional Susceptibility"
            ),
            'mechanical_behavioral': (
                "MECHANICAL DOMAIN ↔ BEHAVIORAL ACTION\n"
                "├─ Torque → Behavioral Drive / Action Impulse\n"
                "├─ Angular Velocity → Action Rate / Performance Velocity\n"
                "├─ Inertia → Behavioral Inertia / Habit Strength\n"
                "├─ Friction → Environmental Constraints\n"
                "├─ Angular Momentum → Sustained Action Momentum\n"
                "└─ Angle → Cumulative Behavior"
            ),
            'em_coupling_psychophysical': (
                "ELECTROMAGNETIC COUPLING ↔ PSYCHOPHYSICAL INTEGRATION\n"
                "├─ E-field ↔ M-field → Cognitive ↔ Affective Interaction\n"
                "├─ EM → Mechanical → Mental/Emotional → Behavioral\n"
                "├─ Torque Constant → Cognitive-Behavioral Coupling\n"
                "└─ Back-EMF → Behavioral Feedback to Cognition"
            ),
            'energy_conversion': (
                "ENERGY CONVERSION PROCESS\n"
                "├─ Electrical Input → Cognitive Input (Attention, Sensory)\n"
                "├─ Magnetic Field → Affective Modulation (Emotion, Motivation)\n"
                "├─ Mechanical Output → Behavioral Output (Action, Performance)\n"
                "├─ Efficiency → Psychomotor Efficiency\n"
                "├─ Losses → Mental Fatigue + Emotional Regulation + Physical Constraints\n"
                "└─ Stored Energy → Working Memory + Mood State + Habits"
            )
        }
    
    def export_comparison(self) -> Dict[str, any]:
        """
        Export comparison between EM and neurological models.
        
        Returns:
            Complete comparison data
        """
        return {
            'domain_mappings': self.get_analogy_mapping(),
            'bond_graph_elements': {
                'cognitive': ['cognitive_load', 'cognitive_momentum', 'attention_buffer'],
                'affective': ['emotional_regulation', 'emotional_inertia', 'emotional_buffer'],
                'behavioral': ['behavioral_friction', 'behavioral_inertia', 'habit_formation']
            },
            'energy_storage': {
                'cognitive': 'Working memory, mental state',
                'affective': 'Emotional state, mood',
                'behavioral': 'Habits, learned behaviors'
            },
            'energy_dissipation': {
                'cognitive': 'Mental fatigue, cognitive load',
                'affective': 'Emotional regulation effort',
                'behavioral': 'Physical fatigue, environmental friction'
            },
            'coupling': {
                'cognitive_behavioral': f'{self.coupling.cognitive_to_behavior}',
                'affective_behavioral': f'{self.coupling.affective_to_behavior}'
            }
        }
