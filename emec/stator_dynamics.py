"""
Stator Dynamics Model

Implements electrical dynamics of the stator including voltage equations,
current dynamics, and power supply interface.
"""

import numpy as np
from typing import Dict, Optional, Callable
from dataclasses import dataclass


@dataclass
class StatorParameters:
    """Physical parameters of stator"""
    num_phases: int = 3              # Number of phases
    rated_voltage: float = 400.0     # Rated line voltage [V]
    rated_frequency: float = 50.0    # Rated frequency [Hz]
    resistance_per_phase: float = 0.5  # Phase resistance [Ω]
    
    # Connection type
    connection_type: str = "wye"     # "wye" or "delta"


@dataclass
class StatorState:
    """State of stator at a given instant"""
    voltage: np.ndarray              # Phase voltages [V]
    current: np.ndarray              # Phase currents [A]
    frequency: float                 # Supply frequency [Hz]
    phase_angle: float               # Electrical angle [rad]
    time: float                      # Current time [s]


class StatorDynamics:
    """
    Stator dynamics model for induction machine.
    
    Manages stator voltage supply, current dynamics, and
    electrical equations of the stator windings.
    """
    
    def __init__(self, params: StatorParameters):
        """
        Initialize stator dynamics model.
        
        Args:
            params: Stator parameters
        """
        self.params = params
        
        # Initial state
        self.state = StatorState(
            voltage=np.zeros(params.num_phases),
            current=np.zeros(params.num_phases),
            frequency=params.rated_frequency,
            phase_angle=0.0,
            time=0.0
        )
        
        # Voltage supply function (can be set externally)
        self.voltage_supply_fn: Optional[Callable[[float], np.ndarray]] = None
    
    def set_voltage_supply(self, voltage_fn: Callable[[float], np.ndarray]):
        """
        Set voltage supply function.
        
        Args:
            voltage_fn: Function that takes time and returns phase voltages [V]
        """
        self.voltage_supply_fn = voltage_fn
    
    def generate_balanced_voltage(self,
                                 amplitude: float,
                                 frequency: float,
                                 time: float) -> np.ndarray:
        """
        Generate balanced three-phase voltage.
        
        For three-phase:
        v_a = V * sin(ωt)
        v_b = V * sin(ωt - 2π/3)
        v_c = V * sin(ωt + 2π/3)
        
        Args:
            amplitude: Voltage amplitude (peak) [V]
            frequency: Supply frequency [Hz]
            time: Current time [s]
            
        Returns:
            Phase voltages [V]
        """
        omega = 2 * np.pi * frequency
        theta = omega * time
        
        voltages = np.zeros(self.params.num_phases)
        
        for i in range(self.params.num_phases):
            phase_shift = 2 * np.pi * i / self.params.num_phases
            voltages[i] = amplitude * np.sin(theta - phase_shift)
        
        return voltages
    
    def compute_supply_voltage(self, time: float) -> np.ndarray:
        """
        Compute supply voltage at given time.
        
        Args:
            time: Current time [s]
            
        Returns:
            Phase voltages [V]
        """
        if self.voltage_supply_fn is not None:
            return self.voltage_supply_fn(time)
        else:
            # Default: balanced three-phase voltage
            # Convert line voltage to phase voltage
            if self.params.connection_type == "wye":
                V_phase = self.params.rated_voltage / np.sqrt(3)
            else:  # delta
                V_phase = self.params.rated_voltage
            
            # Peak voltage
            V_peak = V_phase * np.sqrt(2)
            
            return self.generate_balanced_voltage(
                V_peak,
                self.params.rated_frequency,
                time
            )
    
    def solve_current_dynamics(self,
                              voltage: np.ndarray,
                              flux_linkage: np.ndarray,
                              d_flux_dt: np.ndarray,
                              dt: float) -> np.ndarray:
        """
        Solve stator current dynamics.
        
        From voltage equation:
        v = R*i + dλ/dt
        
        Therefore:
        i = (v - dλ/dt) / R
        
        In practice, this is solved iteratively with the EM field equations.
        
        Args:
            voltage: Applied voltage [V]
            flux_linkage: Flux linkage [Wb]
            d_flux_dt: Time derivative of flux linkage [Wb/s]
            dt: Time step [s]
            
        Returns:
            Stator current [A]
        """
        # Simplified current calculation
        # (In full model, this couples with EM field solver)
        
        R = self.params.resistance_per_phase
        
        # From v = R*i + dλ/dt, solve for i
        current = (voltage - d_flux_dt) / R if R > 0 else np.zeros_like(voltage)
        
        return current
    
    def update_state(self,
                    current: np.ndarray,
                    voltage: Optional[np.ndarray],
                    dt: float) -> StatorState:
        """
        Update stator state for one time step.
        
        Args:
            current: Computed stator current [A]
            voltage: Applied voltage (if None, uses supply function) [V]
            dt: Time step [s]
            
        Returns:
            Updated stator state
        """
        time = self.state.time + dt
        
        # Get voltage
        if voltage is None:
            voltage = self.compute_supply_voltage(time)
        
        # Update phase angle
        omega = 2 * np.pi * self.state.frequency
        phase_angle = (self.state.phase_angle + omega * dt) % (2 * np.pi)
        
        # Update state
        self.state = StatorState(
            voltage=voltage.copy(),
            current=current.copy(),
            frequency=self.state.frequency,
            phase_angle=phase_angle,
            time=time
        )
        
        return self.state
    
    def compute_power(self) -> Dict[str, float]:
        """
        Compute instantaneous electrical power.
        
        For three-phase:
        P = v_a*i_a + v_b*i_b + v_c*i_c
        
        Returns:
            Dictionary with power values
        """
        # Instantaneous power
        P_inst = np.sum(self.state.voltage * self.state.current)
        
        # RMS values (approximation from instantaneous)
        V_rms = np.sqrt(np.mean(self.state.voltage**2))
        I_rms = np.sqrt(np.mean(self.state.current**2))
        
        # Apparent power
        S = self.params.num_phases * V_rms * I_rms
        
        # Power factor (simplified)
        pf = abs(P_inst / S) if S > 0 else 0.0
        pf = min(pf, 1.0)  # Clamp to [0, 1]
        
        return {
            'instantaneous': P_inst,
            'apparent': S,
            'power_factor': pf,
            'reactive': np.sqrt(max(0, S**2 - P_inst**2))
        }
    
    def compute_losses(self) -> Dict[str, float]:
        """
        Compute stator losses.
        
        Returns:
            Dictionary with loss components [W]
        """
        # Copper losses (I²R)
        I_squared = np.sum(self.state.current**2)
        P_copper = I_squared * self.params.resistance_per_phase
        
        # Core losses would require flux density information
        # Simplified model: assume constant core loss
        P_core = 0.0  # Would be computed from flux density
        
        return {
            'copper': P_copper,
            'core': P_core,
            'total': P_copper + P_core
        }
    
    def get_line_voltage(self) -> float:
        """
        Compute line voltage magnitude.
        
        Returns:
            RMS line voltage [V]
        """
        if self.params.connection_type == "wye":
            # V_line = √3 * V_phase
            V_phase_rms = np.sqrt(np.mean(self.state.voltage**2))
            return np.sqrt(3) * V_phase_rms
        else:  # delta
            # V_line = V_phase
            return np.sqrt(np.mean(self.state.voltage**2))
    
    def get_line_current(self) -> float:
        """
        Compute line current magnitude.
        
        Returns:
            RMS line current [A]
        """
        if self.params.connection_type == "wye":
            # I_line = I_phase
            return np.sqrt(np.mean(self.state.current**2))
        else:  # delta
            # I_line = √3 * I_phase
            I_phase_rms = np.sqrt(np.mean(self.state.current**2))
            return np.sqrt(3) * I_phase_rms
    
    def set_frequency(self, frequency: float):
        """
        Set supply frequency (for variable frequency drives).
        
        Args:
            frequency: New frequency [Hz]
        """
        self.state.frequency = frequency
    
    def reset(self):
        """Reset stator to initial state"""
        self.state = StatorState(
            voltage=np.zeros(self.params.num_phases),
            current=np.zeros(self.params.num_phases),
            frequency=self.params.rated_frequency,
            phase_angle=0.0,
            time=0.0
        )
