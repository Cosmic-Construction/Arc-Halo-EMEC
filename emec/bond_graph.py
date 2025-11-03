"""
Bond Graph Generalization Framework

Implements bond graph theory for generalized energy domain modeling.
Bond graphs provide a unified framework for modeling energy conversion across
different physical domains (electrical, mechanical, hydraulic, thermal, etc.)
using effort-flow conjugate power variables.

Core Concepts:
- Effort (e): Generalized force-like quantity (voltage, force, pressure, temperature)
- Flow (f): Generalized velocity-like quantity (current, velocity, flow rate, heat flow)
- Power = Effort × Flow
- Momentum (p): Generalized momentum (flux linkage, linear momentum, pressure momentum)
- Displacement (q): Generalized displacement (charge, position, volume, entropy)

Bond Graph Elements:
- R (Resistor): Dissipative element (e = R·f)
- C (Capacitor): Storage of potential energy (e = q/C, q̇ = f)
- I (Inertia): Storage of kinetic energy (f = p/I, ṗ = e)
- TF (Transformer): Power-conserving conversion (e₂ = n·e₁, f₁ = n·f₂)
- GY (Gyrator): Power-conserving gyration (e₂ = r·f₁, e₁ = r·f₂)
- 0-junction: Common effort (series)
- 1-junction: Common flow (parallel)
"""

import numpy as np
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class EnergyDomain(Enum):
    """Energy domain types"""
    ELECTRICAL = "electrical"
    MECHANICAL_TRANSLATION = "mechanical_translation"
    MECHANICAL_ROTATION = "mechanical_rotation"
    HYDRAULIC = "hydraulic"
    THERMAL = "thermal"
    MAGNETIC = "magnetic"
    NEUROLOGICAL = "neurological"
    GENERIC = "generic"


@dataclass
class PowerVariables:
    """
    Conjugate power variables for bond graph analysis.
    Power = effort × flow
    """
    effort: float  # Generalized force-like quantity
    flow: float    # Generalized velocity-like quantity
    momentum: float = 0.0  # Generalized momentum (integral of effort)
    displacement: float = 0.0  # Generalized displacement (integral of flow)
    
    def power(self) -> float:
        """Compute instantaneous power"""
        return self.effort * self.flow
    
    def update_integrals(self, dt: float):
        """Update momentum and displacement using time integration"""
        self.momentum += self.effort * dt
        self.displacement += self.flow * dt


@dataclass
class DomainMapping:
    """
    Mapping of physical quantities to bond graph power variables.
    Defines the effort-flow conjugate pair for a specific energy domain.
    """
    domain: EnergyDomain
    effort_name: str
    flow_name: str
    momentum_name: str
    displacement_name: str
    effort_unit: str
    flow_unit: str
    momentum_unit: str
    displacement_unit: str
    
    # Physical interpretation
    description: str = ""
    
    # Typical values for scaling
    effort_scale: float = 1.0
    flow_scale: float = 1.0


# Predefined domain mappings
DOMAIN_MAPPINGS = {
    EnergyDomain.ELECTRICAL: DomainMapping(
        domain=EnergyDomain.ELECTRICAL,
        effort_name="voltage",
        flow_name="current",
        momentum_name="flux_linkage",
        displacement_name="charge",
        effort_unit="V",
        flow_unit="A",
        momentum_unit="Wb",
        displacement_unit="C",
        description="Electrical domain: voltage-current conjugate pair"
    ),
    
    EnergyDomain.MECHANICAL_TRANSLATION: DomainMapping(
        domain=EnergyDomain.MECHANICAL_TRANSLATION,
        effort_name="force",
        flow_name="velocity",
        momentum_name="momentum",
        displacement_name="position",
        effort_unit="N",
        flow_unit="m/s",
        momentum_unit="N·s",
        displacement_unit="m",
        description="Mechanical translation: force-velocity conjugate pair"
    ),
    
    EnergyDomain.MECHANICAL_ROTATION: DomainMapping(
        domain=EnergyDomain.MECHANICAL_ROTATION,
        effort_name="torque",
        flow_name="angular_velocity",
        momentum_name="angular_momentum",
        displacement_name="angle",
        effort_unit="N·m",
        flow_unit="rad/s",
        momentum_unit="N·m·s",
        displacement_unit="rad",
        description="Mechanical rotation: torque-angular velocity conjugate pair"
    ),
    
    EnergyDomain.MAGNETIC: DomainMapping(
        domain=EnergyDomain.MAGNETIC,
        effort_name="magnetomotive_force",
        flow_name="flux_rate",
        momentum_name="flux",
        displacement_name="flux_linkage",
        effort_unit="A·turns",
        flow_unit="Wb/s",
        momentum_unit="Wb",
        displacement_unit="Wb·turns",
        description="Magnetic domain: MMF-flux rate conjugate pair"
    ),
}


class BondGraphElement:
    """
    Base class for bond graph elements.
    All elements exchange power through effort-flow conjugate pairs.
    """
    
    def __init__(self, name: str, domain: EnergyDomain = EnergyDomain.GENERIC):
        """
        Initialize bond graph element.
        
        Args:
            name: Element identifier
            domain: Energy domain
        """
        self.name = name
        self.domain = domain
        self.power_vars = PowerVariables(effort=0.0, flow=0.0)
        
    def compute_power(self) -> float:
        """Compute power through element"""
        return self.power_vars.power()
    
    def get_state(self) -> Dict[str, float]:
        """Get element state"""
        return {
            'effort': self.power_vars.effort,
            'flow': self.power_vars.flow,
            'momentum': self.power_vars.momentum,
            'displacement': self.power_vars.displacement,
            'power': self.compute_power()
        }


class ResistiveElement(BondGraphElement):
    """
    R-element: Dissipative (resistive) element.
    Represents energy dissipation as heat.
    Constitutive relation: e = R·f or f = (1/R)·e
    
    Examples:
    - Electrical: resistor (V = R·I)
    - Mechanical: damper (F = B·v)
    - Hydraulic: flow restriction
    - Thermal: thermal resistance
    """
    
    def __init__(self, name: str, resistance: float, domain: EnergyDomain = EnergyDomain.GENERIC):
        """
        Initialize resistive element.
        
        Args:
            name: Element identifier
            resistance: Resistance parameter (generalized)
            domain: Energy domain
        """
        super().__init__(name, domain)
        self.resistance = resistance
    
    def compute_effort(self, flow: float) -> float:
        """Compute effort from flow: e = R·f"""
        self.power_vars.flow = flow
        self.power_vars.effort = self.resistance * flow
        return self.power_vars.effort
    
    def compute_flow(self, effort: float) -> float:
        """Compute flow from effort: f = e/R"""
        self.power_vars.effort = effort
        self.power_vars.flow = effort / (self.resistance + 1e-12)
        return self.power_vars.flow
    
    def dissipated_power(self) -> float:
        """Compute power dissipated"""
        return self.resistance * (self.power_vars.flow ** 2)


class CapacitiveElement(BondGraphElement):
    """
    C-element: Capacitive element (stores potential energy).
    Represents storage of energy in a potential (effort-dependent) form.
    Constitutive relation: e = q/C where q̇ = f
    
    Examples:
    - Electrical: capacitor (V = Q/C)
    - Mechanical translation: spring (F = x/C, where C = 1/k)
    - Mechanical rotation: torsional spring (τ = θ/C)
    - Hydraulic: accumulator
    """
    
    def __init__(self, name: str, capacitance: float, domain: EnergyDomain = EnergyDomain.GENERIC):
        """
        Initialize capacitive element.
        
        Args:
            name: Element identifier
            capacitance: Capacitance parameter (generalized)
            domain: Energy domain
        """
        super().__init__(name, domain)
        self.capacitance = capacitance
    
    def compute_effort(self) -> float:
        """Compute effort from displacement: e = q/C"""
        self.power_vars.effort = self.power_vars.displacement / (self.capacitance + 1e-12)
        return self.power_vars.effort
    
    def update_state(self, flow: float, dt: float):
        """Update state from flow"""
        self.power_vars.flow = flow
        self.power_vars.displacement += flow * dt
        self.compute_effort()
    
    def stored_energy(self) -> float:
        """Compute stored potential energy: E = (1/2)·q²/C"""
        return 0.5 * (self.power_vars.displacement ** 2) / (self.capacitance + 1e-12)


class InertialElement(BondGraphElement):
    """
    I-element: Inertial element (stores kinetic energy).
    Represents storage of energy in a kinetic (flow-dependent) form.
    Constitutive relation: f = p/I where ṗ = e
    
    Examples:
    - Electrical: inductor (I = Φ/L, where Φ̇ = V)
    - Mechanical translation: mass (v = p/m, where ṗ = F)
    - Mechanical rotation: moment of inertia (ω = L/J, where L̇ = τ)
    - Hydraulic: fluid inertia
    """
    
    def __init__(self, name: str, inertance: float, domain: EnergyDomain = EnergyDomain.GENERIC):
        """
        Initialize inertial element.
        
        Args:
            name: Element identifier
            inertance: Inertance parameter (generalized)
            domain: Energy domain
        """
        super().__init__(name, domain)
        self.inertance = inertance
    
    def compute_flow(self) -> float:
        """Compute flow from momentum: f = p/I"""
        self.power_vars.flow = self.power_vars.momentum / (self.inertance + 1e-12)
        return self.power_vars.flow
    
    def update_state(self, effort: float, dt: float):
        """Update state from effort"""
        self.power_vars.effort = effort
        self.power_vars.momentum += effort * dt
        self.compute_flow()
    
    def stored_energy(self) -> float:
        """Compute stored kinetic energy: E = (1/2)·p²/I"""
        return 0.5 * (self.power_vars.momentum ** 2) / (self.inertance + 1e-12)


class TransformerElement:
    """
    TF-element: Transformer (power-conserving conversion).
    Transforms effort and flow with constant ratio.
    Constitutive relations: e₂ = n·e₁, f₁ = n·f₂ (power conserved)
    
    Examples:
    - Electrical: ideal transformer
    - Mechanical: lever, gear ratio
    - Electromechanical: motor constant
    """
    
    def __init__(self, name: str, ratio: float):
        """
        Initialize transformer.
        
        Args:
            name: Element identifier
            ratio: Transformation ratio n
        """
        self.name = name
        self.ratio = ratio
        self.power_vars_1 = PowerVariables(effort=0.0, flow=0.0)
        self.power_vars_2 = PowerVariables(effort=0.0, flow=0.0)
    
    def transform_forward(self, effort_1: float, flow_2: float):
        """Transform from side 1 to side 2"""
        self.power_vars_1.effort = effort_1
        self.power_vars_2.flow = flow_2
        self.power_vars_2.effort = self.ratio * effort_1
        self.power_vars_1.flow = self.ratio * flow_2
    
    def transform_backward(self, effort_2: float, flow_1: float):
        """Transform from side 2 to side 1"""
        self.power_vars_2.effort = effort_2
        self.power_vars_1.flow = flow_1
        self.power_vars_1.effort = effort_2 / (self.ratio + 1e-12)
        self.power_vars_2.flow = flow_1 / (self.ratio + 1e-12)


class GyratorElement:
    """
    GY-element: Gyrator (power-conserving gyration).
    Couples effort on one side to flow on the other.
    Constitutive relations: e₂ = r·f₁, e₁ = r·f₂ (power conserved)
    
    Examples:
    - Electromechanical: DC motor (τ = k·i, V = k·ω)
    - AC motor: electromagnetic coupling
    - Gyroscope
    """
    
    def __init__(self, name: str, gyration_ratio: float):
        """
        Initialize gyrator.
        
        Args:
            name: Element identifier
            gyration_ratio: Gyration ratio r
        """
        self.name = name
        self.gyration_ratio = gyration_ratio
        self.power_vars_1 = PowerVariables(effort=0.0, flow=0.0)
        self.power_vars_2 = PowerVariables(effort=0.0, flow=0.0)
    
    def gyrate_forward(self, flow_1: float, flow_2: float):
        """Gyrate from side 1 to side 2"""
        self.power_vars_1.flow = flow_1
        self.power_vars_2.flow = flow_2
        self.power_vars_2.effort = self.gyration_ratio * flow_1
        self.power_vars_1.effort = self.gyration_ratio * flow_2
    
    def compute_power_transfer(self) -> float:
        """Compute power transferred through gyrator"""
        return self.power_vars_1.power() + self.power_vars_2.power()


class BondGraphModel:
    """
    Complete bond graph model for energy system analysis.
    Manages elements and their interconnections.
    """
    
    def __init__(self, name: str = "Bond Graph Model"):
        """
        Initialize bond graph model.
        
        Args:
            name: Model name
        """
        self.name = name
        self.elements: Dict[str, BondGraphElement] = {}
        self.transformers: Dict[str, TransformerElement] = {}
        self.gyrators: Dict[str, GyratorElement] = {}
        
    def add_resistive_element(self, name: str, resistance: float, 
                             domain: EnergyDomain = EnergyDomain.GENERIC):
        """Add resistive element to model"""
        self.elements[name] = ResistiveElement(name, resistance, domain)
        
    def add_capacitive_element(self, name: str, capacitance: float,
                               domain: EnergyDomain = EnergyDomain.GENERIC):
        """Add capacitive element to model"""
        self.elements[name] = CapacitiveElement(name, capacitance, domain)
        
    def add_inertial_element(self, name: str, inertance: float,
                            domain: EnergyDomain = EnergyDomain.GENERIC):
        """Add inertial element to model"""
        self.elements[name] = InertialElement(name, inertance, domain)
        
    def add_transformer(self, name: str, ratio: float):
        """Add transformer element to model"""
        self.transformers[name] = TransformerElement(name, ratio)
        
    def add_gyrator(self, name: str, gyration_ratio: float):
        """Add gyrator element to model"""
        self.gyrators[name] = GyratorElement(name, gyration_ratio)
    
    def get_total_stored_energy(self) -> Dict[str, float]:
        """Compute total stored energy in all storage elements"""
        energy = {
            'capacitive': 0.0,
            'inertial': 0.0,
            'total': 0.0
        }
        
        for element in self.elements.values():
            if isinstance(element, CapacitiveElement):
                energy['capacitive'] += element.stored_energy()
            elif isinstance(element, InertialElement):
                energy['inertial'] += element.stored_energy()
        
        energy['total'] = energy['capacitive'] + energy['inertial']
        return energy
    
    def get_total_dissipated_power(self) -> float:
        """Compute total power dissipation in all resistive elements"""
        power = 0.0
        for element in self.elements.values():
            if isinstance(element, ResistiveElement):
                power += element.dissipated_power()
        return power
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get complete system state"""
        return {
            'elements': {name: elem.get_state() for name, elem in self.elements.items()},
            'energy': self.get_total_stored_energy(),
            'power_dissipated': self.get_total_dissipated_power()
        }
