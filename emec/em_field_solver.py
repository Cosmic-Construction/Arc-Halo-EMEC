"""
Electromagnetic Field Equations Solver

Implements Maxwell's equations for electromagnetic field analysis in
rotating electrical machines, specifically for induction motors.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class EMFieldState:
    """State of electromagnetic field at a given instant"""
    magnetic_flux_density: np.ndarray  # B field [T]
    electric_field: np.ndarray         # E field [V/m]
    current_density: np.ndarray        # J [A/m²]
    magnetic_field: np.ndarray         # H field [A/m]
    time: float                        # Current time [s]


class EMFieldSolver:
    """
    Electromagnetic Field Equations Solver for induction machines.
    
    Solves Maxwell's equations:
    - Faraday's Law: ∇×E = -∂B/∂t
    - Ampere's Law: ∇×H = J + ∂D/∂t
    - Gauss's Law: ∇·D = ρ
    - Gauss's Law for Magnetism: ∇·B = 0
    
    For rotating machines, we use the dq0 reference frame transformation.
    """
    
    def __init__(self, 
                 permeability: float = 4 * np.pi * 1e-7,
                 permittivity: float = 8.854e-12,
                 conductivity: float = 5.96e7):
        """
        Initialize EM field solver.
        
        Args:
            permeability: Magnetic permeability μ [H/m] (default: μ₀ for air)
            permittivity: Electric permittivity ε [F/m] (default: ε₀ for air)
            conductivity: Electrical conductivity σ [S/m] (default: copper)
        """
        self.mu = permeability
        self.epsilon = permittivity
        self.sigma = conductivity
        
        # State variables
        self.current_state: Optional[EMFieldState] = None
    
    def compute_magnetic_flux_density(self,
                                     current: np.ndarray,
                                     geometry_factor: float = 1.0) -> np.ndarray:
        """
        Compute magnetic flux density B from current distribution.
        
        Uses Biot-Savart law for magnetic field from current:
        B = (μ/4π) ∫ (I dl × r̂) / r²
        
        For simplified rotating machine: B ≈ μ * H = μ * (N * I) / l_gap
        
        Args:
            current: Current distribution [A]
            geometry_factor: Machine geometry factor (accounts for winding, gap)
            
        Returns:
            Magnetic flux density [T]
        """
        # Simplified model for rotating machine
        # In actual machine: B = f(current, position, geometry)
        magnetic_field = current * geometry_factor
        B = self.mu * magnetic_field
        return B
    
    def compute_induced_emf(self,
                           flux_linkage: np.ndarray,
                           dt: float) -> np.ndarray:
        """
        Compute induced EMF from changing magnetic flux (Faraday's Law).
        
        EMF = -dλ/dt where λ is flux linkage
        
        Args:
            flux_linkage: Magnetic flux linkage [Wb]
            dt: Time step [s]
            
        Returns:
            Induced EMF [V]
        """
        if dt <= 0:
            return np.zeros_like(flux_linkage)
        
        # Numerical derivative
        if self.current_state is not None:
            d_flux = flux_linkage - self.current_state.magnetic_flux_density
            emf = -d_flux / dt
        else:
            emf = np.zeros_like(flux_linkage)
        
        return emf
    
    def solve_field_step(self,
                        current: np.ndarray,
                        angular_velocity: float,
                        dt: float,
                        geometry_factor: float = 1.0) -> EMFieldState:
        """
        Solve electromagnetic field for one time step.
        
        Args:
            current: Current vector [A]
            angular_velocity: Rotor angular velocity [rad/s]
            dt: Time step [s]
            geometry_factor: Geometry factor for the machine
            
        Returns:
            EMFieldState with computed fields
        """
        # Compute magnetic flux density
        B = self.compute_magnetic_flux_density(current, geometry_factor)
        
        # Compute magnetic field H
        H = B / self.mu
        
        # Compute current density (simplified)
        # For conductors: J = σE, but we use supplied current
        J = current * geometry_factor
        
        # Compute electric field from Ohm's law: E = J/σ
        E = J / self.sigma if self.sigma > 0 else np.zeros_like(J)
        
        # Update time
        new_time = 0.0 if self.current_state is None else self.current_state.time + dt
        
        # Create new state
        new_state = EMFieldState(
            magnetic_flux_density=B,
            electric_field=E,
            current_density=J,
            magnetic_field=H,
            time=new_time
        )
        
        self.current_state = new_state
        return new_state
    
    def compute_torque(self,
                      stator_flux: np.ndarray,
                      rotor_current: np.ndarray,
                      pole_pairs: int = 2) -> float:
        """
        Compute electromagnetic torque.
        
        For induction machine in dq frame:
        T = (3/2) * p * (λ_d * i_q - λ_q * i_d)
        
        where p is pole pairs, λ is flux linkage, i is current
        
        Args:
            stator_flux: Stator flux linkage in dq frame [Wb]
            rotor_current: Rotor current in dq frame [A]
            pole_pairs: Number of pole pairs
            
        Returns:
            Electromagnetic torque [Nm]
        """
        if len(stator_flux) < 2 or len(rotor_current) < 2:
            return 0.0
        
        # dq frame torque equation
        lambda_d = stator_flux[0]
        lambda_q = stator_flux[1] if len(stator_flux) > 1 else 0.0
        i_d = rotor_current[0]
        i_q = rotor_current[1] if len(rotor_current) > 1 else 0.0
        
        torque = (3.0 / 2.0) * pole_pairs * (lambda_d * i_q - lambda_q * i_d)
        
        return torque
    
    def park_transform(self,
                      abc_vector: np.ndarray,
                      theta: float) -> np.ndarray:
        """
        Park (abc to dq0) transformation.
        
        Transforms three-phase quantities to synchronous reference frame.
        
        Args:
            abc_vector: Three-phase vector [a, b, c]
            theta: Electrical angle [rad]
            
        Returns:
            dq0 vector [d, q, 0]
        """
        if len(abc_vector) < 3:
            return np.zeros(3)
        
        a, b, c = abc_vector[0], abc_vector[1], abc_vector[2]
        
        # Park transformation matrix
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        cos_theta_120 = np.cos(theta - 2*np.pi/3)
        sin_theta_120 = np.sin(theta - 2*np.pi/3)
        cos_theta_240 = np.cos(theta + 2*np.pi/3)
        sin_theta_240 = np.sin(theta + 2*np.pi/3)
        
        # dq0 components
        d = (2.0/3.0) * (a * cos_theta + b * cos_theta_120 + c * cos_theta_240)
        q = (2.0/3.0) * (-a * sin_theta - b * sin_theta_120 - c * sin_theta_240)
        zero = (1.0/3.0) * (a + b + c)
        
        return np.array([d, q, zero])
    
    def inverse_park_transform(self,
                              dq0_vector: np.ndarray,
                              theta: float) -> np.ndarray:
        """
        Inverse Park (dq0 to abc) transformation.
        
        Args:
            dq0_vector: dq0 vector [d, q, 0]
            theta: Electrical angle [rad]
            
        Returns:
            Three-phase vector [a, b, c]
        """
        if len(dq0_vector) < 2:
            return np.zeros(3)
        
        d = dq0_vector[0]
        q = dq0_vector[1]
        zero = dq0_vector[2] if len(dq0_vector) > 2 else 0.0
        
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        
        # Inverse transformation
        a = d * cos_theta - q * sin_theta + zero
        b = d * np.cos(theta - 2*np.pi/3) - q * np.sin(theta - 2*np.pi/3) + zero
        c = d * np.cos(theta + 2*np.pi/3) - q * np.sin(theta + 2*np.pi/3) + zero
        
        return np.array([a, b, c])
    
    def reset(self):
        """Reset solver state"""
        self.current_state = None
