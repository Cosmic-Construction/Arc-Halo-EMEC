"""
Electromagnetic to Bond Graph Domain Mapping

Maps electromagnetic energy conversion (EMEC) components to bond graph elements,
enabling unified analysis of electrical and mechanical energy domains.

This module provides:
- Mapping of EM field components to bond graph power variables
- Translation between EMEC parameters and bond graph elements
- Integrated bond graph representation of induction motors
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .bond_graph import (
    BondGraphModel,
    EnergyDomain,
    PowerVariables,
    DOMAIN_MAPPINGS,
    ResistiveElement,
    CapacitiveElement,
    InertialElement,
    GyratorElement
)
from .virtual_engine import EngineParameters


@dataclass
class EMBondGraphMapping:
    """
    Complete mapping between electromagnetic system and bond graph representation.
    
    Electrical Domain:
    - Effort: Voltage (V)
    - Flow: Current (I)
    - Momentum: Flux linkage (λ = ∫V dt)
    - Displacement: Charge (Q = ∫I dt)
    - R-element: Stator resistance
    - I-element: Stator inductance (stores magnetic energy)
    
    Mechanical Domain:
    - Effort: Torque (τ)
    - Flow: Angular velocity (ω)
    - Momentum: Angular momentum (L = ∫τ dt)
    - Displacement: Angle (θ = ∫ω dt)
    - R-element: Friction
    - I-element: Rotor inertia (stores kinetic energy)
    
    Coupling:
    - GY-element: Electromagnetic torque-current gyrator
    """
    
    # Electrical domain
    electrical_resistance: float  # Stator resistance [Ω]
    electrical_inductance: float  # Stator inductance [H]
    
    # Mechanical domain
    mechanical_friction: float    # Friction coefficient [N·m·s/rad]
    mechanical_inertia: float     # Moment of inertia [kg·m²]
    
    # Coupling
    torque_constant: float        # Electromagnetic coupling [N·m/A]
    voltage_constant: float       # Back-EMF constant [V·s/rad]
    
    # Operating point
    supply_voltage: float         # Supply voltage [V]
    supply_frequency: float       # Supply frequency [Hz]


def create_em_bond_graph_from_engine(params: EngineParameters) -> Tuple[BondGraphModel, EMBondGraphMapping]:
    """
    Create bond graph model from engine parameters.
    
    Args:
        params: Engine parameters
        
    Returns:
        Tuple of (BondGraphModel, EMBondGraphMapping)
    """
    # Extract parameters
    R_s = params.stator_winding.resistance_per_phase
    L_s = params.stator_winding.self_inductance
    J = params.rotor_mechanical.inertia
    B = params.rotor_mechanical.friction_coefficient
    p = params.rotor_mechanical.pole_pairs
    
    # Compute electromagnetic constants
    # For induction motor: k_t ≈ (3/2) * p * L_m
    L_m = params.stator_winding.mutual_inductance
    k_t = 1.5 * p * L_m  # Torque constant
    k_e = k_t  # Back-EMF constant (for reciprocal systems)
    
    # Create mapping
    mapping = EMBondGraphMapping(
        electrical_resistance=R_s,
        electrical_inductance=L_s,
        mechanical_friction=B,
        mechanical_inertia=J,
        torque_constant=k_t,
        voltage_constant=k_e,
        supply_voltage=params.stator_electrical.rated_voltage,
        supply_frequency=params.stator_electrical.rated_frequency
    )
    
    # Create bond graph model
    model = BondGraphModel(name="Induction Motor Bond Graph")
    
    # Electrical domain elements
    model.add_resistive_element(
        "stator_resistance",
        resistance=R_s,
        domain=EnergyDomain.ELECTRICAL
    )
    
    model.add_inertial_element(
        "stator_inductance",
        inertance=L_s,
        domain=EnergyDomain.ELECTRICAL
    )
    
    # Mechanical domain elements
    model.add_resistive_element(
        "rotor_friction",
        resistance=B,
        domain=EnergyDomain.MECHANICAL_ROTATION
    )
    
    model.add_inertial_element(
        "rotor_inertia",
        inertance=J,
        domain=EnergyDomain.MECHANICAL_ROTATION
    )
    
    # Electromechanical coupling
    model.add_gyrator(
        "em_coupling",
        gyration_ratio=k_t
    )
    
    return model, mapping


def analyze_power_flow(model: BondGraphModel, 
                       voltage: float,
                       current: float,
                       torque: float,
                       omega: float) -> Dict[str, float]:
    """
    Analyze power flow through bond graph model.
    
    Args:
        model: Bond graph model
        voltage: Applied voltage [V]
        current: Stator current [A]
        torque: Electromagnetic torque [N·m]
        omega: Angular velocity [rad/s]
        
    Returns:
        Dictionary of power flow analysis
    """
    # Update element states
    if "stator_resistance" in model.elements:
        R_elem = model.elements["stator_resistance"]
        if isinstance(R_elem, ResistiveElement):
            R_elem.power_vars.effort = voltage
            R_elem.power_vars.flow = current
    
    if "rotor_friction" in model.elements:
        B_elem = model.elements["rotor_friction"]
        if isinstance(B_elem, ResistiveElement):
            B_elem.power_vars.effort = torque
            B_elem.power_vars.flow = omega
    
    if "rotor_inertia" in model.elements:
        J_elem = model.elements["rotor_inertia"]
        if isinstance(J_elem, InertialElement):
            J_elem.power_vars.effort = torque
            J_elem.power_vars.flow = omega
    
    # Compute power flow
    P_electrical = voltage * current
    P_mechanical = torque * omega
    P_resistive_loss = model.get_total_dissipated_power()
    
    energy = model.get_total_stored_energy()
    
    return {
        'electrical_input_power': P_electrical,
        'mechanical_output_power': P_mechanical,
        'resistive_losses': P_resistive_loss,
        'stored_energy_capacitive': energy['capacitive'],
        'stored_energy_inertial': energy['inertial'],
        'stored_energy_total': energy['total'],
        'efficiency': (P_mechanical / P_electrical * 100.0) if abs(P_electrical) > 1e-6 else 0.0
    }


def get_generalized_impedance(mapping: EMBondGraphMapping, frequency: float) -> Dict[str, complex]:
    """
    Compute generalized impedances in bond graph representation.
    
    For electrical domain:
    Z_electrical = R + jωL
    
    For mechanical domain:
    Z_mechanical = B + jωJ
    
    Args:
        mapping: EM bond graph mapping
        frequency: Frequency [Hz]
        
    Returns:
        Dictionary of impedances
    """
    omega = 2 * np.pi * frequency
    
    Z_electrical = complex(
        mapping.electrical_resistance,
        omega * mapping.electrical_inductance
    )
    
    Z_mechanical = complex(
        mapping.mechanical_friction,
        omega * mapping.mechanical_inertia
    )
    
    return {
        'electrical_impedance': Z_electrical,
        'electrical_magnitude': abs(Z_electrical),
        'electrical_phase': np.angle(Z_electrical),
        'mechanical_impedance': Z_mechanical,
        'mechanical_magnitude': abs(Z_mechanical),
        'mechanical_phase': np.angle(Z_mechanical)
    }


def compute_energy_domain_equivalences(mapping: EMBondGraphMapping) -> Dict[str, str]:
    """
    Compute equivalences between energy domains.
    
    Returns human-readable descriptions of domain equivalences.
    
    Args:
        mapping: EM bond graph mapping
        
    Returns:
        Dictionary of equivalence descriptions
    """
    return {
        'electrical_mechanical_analogy': (
            "Voltage (V) ↔ Torque (τ)\n"
            "Current (I) ↔ Angular Velocity (ω)\n"
            "Resistance (R) ↔ Friction (B)\n"
            "Inductance (L) ↔ Inertia (J)\n"
            "Flux Linkage (λ) ↔ Angular Momentum (L)\n"
            "Charge (Q) ↔ Angle (θ)"
        ),
        'power_conservation': (
            f"Electrical Power (P_e = V·I) ↔ Mechanical Power (P_m = τ·ω)\n"
            f"Coupled through gyrator with ratio k = {mapping.torque_constant:.4f}"
        ),
        'energy_storage': (
            "Magnetic Energy (E_mag = ½LI²) ↔ Kinetic Energy (E_kin = ½Jω²)\n"
            "Both stored in I-elements (inertial elements)"
        ),
        'energy_dissipation': (
            "Electrical Losses (P_R = RI²) ↔ Friction Losses (P_B = Bω²)\n"
            "Both dissipated in R-elements (resistive elements)"
        )
    }


class EMBondGraphSimulator:
    """
    Simulator that uses bond graph representation for EM energy conversion.
    Provides alternative formulation using generalized power variables.
    """
    
    def __init__(self, model: BondGraphModel, mapping: EMBondGraphMapping):
        """
        Initialize bond graph simulator.
        
        Args:
            model: Bond graph model
            mapping: EM bond graph mapping
        """
        self.model = model
        self.mapping = mapping
        self.time = 0.0
        
    def step(self, voltage: float, load_torque: float, dt: float) -> Dict[str, float]:
        """
        Execute one time step using bond graph formulation.
        
        Args:
            voltage: Applied voltage [V]
            load_torque: Load torque [N·m]
            dt: Time step [s]
            
        Returns:
            Dictionary of state variables
        """
        # Get elements
        R_s = self.model.elements.get("stator_resistance")
        L_s = self.model.elements.get("stator_inductance")
        B = self.model.elements.get("rotor_friction")
        J = self.model.elements.get("rotor_inertia")
        GY = self.model.gyrators.get("em_coupling")
        
        # Simplified dynamics for demonstration
        # In full implementation, would solve coupled differential equations
        
        # Update inertial element (rotor)
        if J and isinstance(J, InertialElement):
            # T_em - T_load - B*omega = J * d(omega)/dt
            omega = J.power_vars.flow
            T_friction = self.mapping.mechanical_friction * omega
            T_net = -load_torque - T_friction  # Net torque (excluding electromagnetic)
            
            # Electromagnetic torque from current (via gyrator)
            if L_s and isinstance(L_s, InertialElement):
                current = L_s.power_vars.flow
                T_em = self.mapping.torque_constant * current
                T_net += T_em
            
            J.update_state(T_net, dt)
        
        # Update electrical inertial element (inductance)
        if L_s and isinstance(L_s, InertialElement):
            # V - R*I = L * d(I)/dt
            current = L_s.power_vars.flow
            V_resistive = self.mapping.electrical_resistance * current
            
            # Back-EMF from angular velocity (via gyrator)
            if J and isinstance(J, InertialElement):
                omega = J.power_vars.flow
                V_back_emf = self.mapping.voltage_constant * omega
            else:
                V_back_emf = 0.0
            
            V_net = voltage - V_resistive - V_back_emf
            L_s.update_state(V_net, dt)
        
        # Update time
        self.time += dt
        
        # Return state
        state = {}
        if J and isinstance(J, InertialElement):
            state['angular_velocity'] = J.power_vars.flow
            state['angle'] = J.power_vars.displacement
            state['angular_momentum'] = J.power_vars.momentum
        
        if L_s and isinstance(L_s, InertialElement):
            state['current'] = L_s.power_vars.flow
            state['flux_linkage'] = L_s.power_vars.momentum
            state['charge'] = L_s.power_vars.displacement
        
        state['time'] = self.time
        
        return state
