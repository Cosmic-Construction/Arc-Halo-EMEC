"""
Rotor Dynamics Model

Implements mechanical dynamics of the rotor including inertia,
friction, and load torque effects.
"""

import numpy as np
from typing import Optional, Callable
from dataclasses import dataclass


# Numerical constants
VELOCITY_DEADBAND = 0.01  # Deadband [rad/s] for Coulomb friction near zero to avoid numerical issues


@dataclass
class RotorParameters:
    """Physical parameters of rotor"""
    inertia: float = 0.01           # Moment of inertia [kg⋅m²]
    friction_coefficient: float = 0.001  # Viscous friction [N⋅m⋅s/rad]
    pole_pairs: int = 2              # Number of pole pairs
    rated_speed: float = 1500.0      # Rated speed [rpm]
    
    # Optional parameters
    coulomb_friction: float = 0.0    # Coulomb friction torque [N⋅m]
    windage_coefficient: float = 0.0 # Windage loss coefficient


@dataclass
class RotorState:
    """State of rotor at a given instant"""
    angle: float                     # Mechanical angle [rad]
    angular_velocity: float          # Mechanical angular velocity [rad/s]
    angular_acceleration: float      # Angular acceleration [rad/s²]
    speed_rpm: float                 # Speed in RPM
    time: float                      # Current time [s]


class RotorDynamics:
    """
    Rotor dynamics model for induction machine.
    
    Solves the equation of motion:
    J * dω/dt = T_em - T_load - T_friction
    
    where:
    - J is moment of inertia
    - ω is angular velocity
    - T_em is electromagnetic torque
    - T_load is load torque
    - T_friction includes viscous, coulomb, and windage losses
    """
    
    def __init__(self, params: RotorParameters):
        """
        Initialize rotor dynamics model.
        
        Args:
            params: Rotor physical parameters
        """
        self.params = params
        
        # Initial state
        self.state = RotorState(
            angle=0.0,
            angular_velocity=0.0,
            angular_acceleration=0.0,
            speed_rpm=0.0,
            time=0.0
        )
        
        # Load torque function (can be set externally)
        self.load_torque_fn: Optional[Callable[[float, float], float]] = None
    
    def set_load_torque(self, torque_fn: Callable[[float, float], float]):
        """
        Set load torque function.
        
        Args:
            torque_fn: Function that takes (time, speed) and returns torque [N⋅m]
        """
        self.load_torque_fn = torque_fn
    
    def compute_friction_torque(self, omega: float) -> float:
        """
        Compute friction torque.
        
        T_friction = B*ω + T_c*sign(ω) + K_w*ω²
        
        where:
        - B is viscous friction coefficient
        - T_c is coulomb friction
        - K_w is windage coefficient
        
        Args:
            omega: Angular velocity [rad/s]
            
        Returns:
            Friction torque [N⋅m]
        """
        # Viscous friction
        T_viscous = self.params.friction_coefficient * omega
        
        # Coulomb friction (sign function with deadband near zero)
        if abs(omega) > VELOCITY_DEADBAND:
            T_coulomb = self.params.coulomb_friction * np.sign(omega)
        else:
            T_coulomb = 0.0
        
        # Windage (proportional to ω²)
        T_windage = self.params.windage_coefficient * omega * abs(omega)
        
        return T_viscous + T_coulomb + T_windage
    
    def compute_load_torque(self, time: float, omega: float) -> float:
        """
        Compute load torque at current state.
        
        Args:
            time: Current time [s]
            omega: Angular velocity [rad/s]
            
        Returns:
            Load torque [N⋅m]
        """
        if self.load_torque_fn is not None:
            return self.load_torque_fn(time, omega)
        return 0.0
    
    def solve_dynamics(self,
                      T_em: float,
                      dt: float) -> RotorState:
        """
        Solve rotor dynamics for one time step.
        
        Uses Euler integration:
        ω(t+dt) = ω(t) + α*dt
        θ(t+dt) = θ(t) + ω*dt
        
        where α = (T_em - T_load - T_friction) / J
        
        Args:
            T_em: Electromagnetic torque [N⋅m]
            dt: Time step [s]
            
        Returns:
            New rotor state
        """
        # Get current state
        omega = self.state.angular_velocity
        theta = self.state.angle
        time = self.state.time
        
        # Compute torques
        T_friction = self.compute_friction_torque(omega)
        T_load = self.compute_load_torque(time, omega)
        
        # Net torque
        T_net = T_em - T_load - T_friction
        
        # Angular acceleration (Newton's second law for rotation)
        alpha = T_net / self.params.inertia
        
        # Update velocity (Euler integration)
        omega_new = omega + alpha * dt
        
        # Update angle
        theta_new = theta + omega_new * dt
        
        # Normalize angle to [0, 2π)
        theta_new = theta_new % (2 * np.pi)
        
        # Convert to RPM
        speed_rpm = omega_new * 60.0 / (2 * np.pi)
        
        # Update state
        self.state = RotorState(
            angle=theta_new,
            angular_velocity=omega_new,
            angular_acceleration=alpha,
            speed_rpm=speed_rpm,
            time=time + dt
        )
        
        return self.state
    
    def get_electrical_angle(self) -> float:
        """
        Get electrical angle (accounts for pole pairs).
        
        θ_electrical = p * θ_mechanical
        
        Returns:
            Electrical angle [rad]
        """
        return self.params.pole_pairs * self.state.angle
    
    def get_slip(self, synchronous_frequency: float) -> float:
        """
        Compute slip.
        
        Slip s = (ω_s - ω_r) / ω_s
        
        where ω_s is synchronous speed
        
        Args:
            synchronous_frequency: Synchronous frequency [Hz]
            
        Returns:
            Slip (dimensionless)
        """
        # Synchronous speed [rad/s]
        omega_sync = 2 * np.pi * synchronous_frequency / self.params.pole_pairs
        
        # Slip
        if omega_sync > 0:
            slip = (omega_sync - self.state.angular_velocity) / omega_sync
        else:
            slip = 1.0
        
        return slip
    
    def get_kinetic_energy(self) -> float:
        """
        Compute kinetic energy of rotor.
        
        E_k = (1/2) * J * ω²
        
        Returns:
            Kinetic energy [J]
        """
        return 0.5 * self.params.inertia * self.state.angular_velocity**2
    
    def set_state(self, angle: float, angular_velocity: float):
        """
        Set rotor state directly (for initialization).
        
        Args:
            angle: Mechanical angle [rad]
            angular_velocity: Angular velocity [rad/s]
        """
        self.state.angle = angle % (2 * np.pi)
        self.state.angular_velocity = angular_velocity
        self.state.speed_rpm = angular_velocity * 60.0 / (2 * np.pi)
        self.state.angular_acceleration = 0.0
    
    def reset(self):
        """Reset rotor to initial state"""
        self.state = RotorState(
            angle=0.0,
            angular_velocity=0.0,
            angular_acceleration=0.0,
            speed_rpm=0.0,
            time=0.0
        )
