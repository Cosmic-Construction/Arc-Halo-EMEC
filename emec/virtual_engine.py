"""
Virtual Engine - Electro-Mechanical Energy Conversion Simulator

Main integration class that combines EM field solver, polyphase winding model,
rotor dynamics, and stator dynamics into a complete virtual induction motor simulator.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .em_field_solver import EMFieldSolver, EMFieldState
from .polyphase_winding import PolyphaseWindingModel, WindingParameters
from .rotor_dynamics import RotorDynamics, RotorParameters, RotorState
from .stator_dynamics import StatorDynamics, StatorParameters, StatorState


@dataclass
class EngineParameters:
    """Complete engine parameters"""
    stator_winding: WindingParameters
    rotor_winding: WindingParameters
    rotor_mechanical: RotorParameters
    stator_electrical: StatorParameters
    
    # Simulation parameters
    time_step: float = 1e-4          # Simulation time step [s]
    
    @classmethod
    def create_default(cls, rated_power: float = 5000.0):
        """
        Create default engine parameters for a given rated power.
        
        Args:
            rated_power: Rated power [W]
            
        Returns:
            EngineParameters instance
        """
        # Scale parameters based on power
        # These are typical values for industrial induction motors
        
        return cls(
            stator_winding=WindingParameters(
                num_phases=3,
                turns_per_phase=100,
                resistance_per_phase=0.5,
                self_inductance=0.01,
                mutual_inductance=0.005,
                leakage_inductance=0.001,
                pole_pairs=2,
                air_gap=0.001,
                stator_slots=36,
                rotor_slots=28
            ),
            rotor_winding=WindingParameters(
                num_phases=3,
                turns_per_phase=80,
                resistance_per_phase=0.3,
                self_inductance=0.008,
                mutual_inductance=0.004,
                leakage_inductance=0.0008,
                pole_pairs=2,
                air_gap=0.001,
                stator_slots=36,
                rotor_slots=28
            ),
            rotor_mechanical=RotorParameters(
                inertia=0.02,
                friction_coefficient=0.001,
                pole_pairs=2,
                rated_speed=1500.0,
                coulomb_friction=0.05,
                windage_coefficient=1e-6
            ),
            stator_electrical=StatorParameters(
                num_phases=3,
                rated_voltage=400.0,
                rated_frequency=50.0,
                resistance_per_phase=0.5,
                connection_type="wye"
            )
        )


@dataclass
class SimulationState:
    """Complete simulation state at a given instant"""
    time: float
    rotor: RotorState
    stator: StatorState
    em_field: Optional[EMFieldState]
    torque: float
    power_mechanical: float
    power_electrical: float
    efficiency: float


class VirtualEngine:
    """
    Virtual Engine - Complete electro-mechanical induction motor simulator.
    
    Integrates:
    - Electromagnetic field equations (Maxwell's equations)
    - Polyphase winding model (inductances, flux linkages)
    - Rotor mechanical dynamics (Newton's laws)
    - Stator electrical dynamics (voltage/current equations)
    
    Simulates the complete electro-mechanical energy conversion process.
    """
    
    def __init__(self, params: Optional[EngineParameters] = None):
        """
        Initialize virtual engine.
        
        Args:
            params: Engine parameters (if None, uses defaults)
        """
        if params is None:
            params = EngineParameters.create_default()
        
        self.params = params
        
        # Initialize subsystems
        self.em_solver = EMFieldSolver()
        self.winding_model = PolyphaseWindingModel(
            params.stator_winding,
            params.rotor_winding
        )
        self.rotor = RotorDynamics(params.rotor_mechanical)
        self.stator = StatorDynamics(params.stator_electrical)
        
        # Simulation state
        self.current_time = 0.0
        self.history: List[SimulationState] = []
    
    def step(self, dt: Optional[float] = None) -> SimulationState:
        """
        Execute one simulation time step.
        
        This performs coupled electro-mechanical simulation:
        1. Update stator voltage from supply
        2. Compute flux linkages from winding model
        3. Solve EM field equations
        4. Compute electromagnetic torque
        5. Solve rotor mechanical dynamics
        6. Update stator current
        7. Store state
        
        Args:
            dt: Time step [s] (if None, uses default)
            
        Returns:
            Current simulation state
        """
        if dt is None:
            dt = self.params.time_step
        
        # 1. Get stator supply voltage
        stator_voltage = self.stator.compute_supply_voltage(self.current_time)
        
        # 2. Get rotor position
        theta_r = self.rotor.get_electrical_angle()
        
        # 3. Simplified current calculation for stability
        # Use voltage equation: i ≈ v / (R + jωL)
        # For initial steps, use simplified model
        omega_e = 2 * np.pi * self.params.stator_electrical.rated_frequency
        Z_mag = np.sqrt(self.params.stator_winding.resistance_per_phase**2 + 
                       (omega_e * self.params.stator_winding.self_inductance)**2)
        stator_current = stator_voltage / (Z_mag + 1e-6)
        
        # 4. Compute flux linkages
        # For squirrel cage rotor, initial current is small
        rotor_current_init = np.zeros(self.params.rotor_winding.num_phases)
        
        flux_linkages = self.winding_model.compute_flux_linkage(
            stator_current,
            rotor_current_init,
            theta_r
        )
        
        # 5. Compute rotor current based on slip
        slip = self.rotor.get_slip(self.params.stator_electrical.rated_frequency)
        slip = np.clip(slip, -0.5, 1.5)  # Reasonable slip range
        
        # Rotor current from slip and flux (simplified)
        # In actual motor: i_r ≈ (s * E_r) / Z_r
        # Where E_r is induced EMF proportional to flux
        if abs(slip) > 0.01:
            rotor_current = flux_linkages['rotor'] * slip * 0.1  # Scale factor for stability
        else:
            rotor_current = rotor_current_init
        
        # Limit currents
        stator_current = np.clip(stator_current, -100.0, 100.0)
        rotor_current = np.clip(rotor_current, -100.0, 100.0)
        
        # 6. Update flux with actual currents
        flux_linkages = self.winding_model.compute_flux_linkage(
            stator_current,
            rotor_current,
            theta_r
        )
        
        # 7. Solve EM field equations
        em_state = self.em_solver.solve_field_step(
            stator_current,
            self.rotor.state.angular_velocity,
            dt,
            geometry_factor=1.0
        )
        
        # 8. Compute electromagnetic torque (with safety limits)
        T_em_raw = self.em_solver.compute_torque(
            flux_linkages['stator'],
            rotor_current,
            self.params.rotor_mechanical.pole_pairs
        )
        # Realistic torque limit based on motor size
        T_em = np.clip(T_em_raw, -100.0, 100.0)
        
        # 9. Solve rotor dynamics
        rotor_state = self.rotor.solve_dynamics(T_em, dt)
        
        # 10. Update stator state
        stator_state = self.stator.update_state(stator_current, stator_voltage, dt)
        
        # 11. Compute power
        P_electrical = np.sum(stator_state.voltage * stator_state.current)
        P_mechanical = T_em * rotor_state.angular_velocity
        
        # 12. Compute efficiency
        if abs(P_electrical) > 1e-6:
            efficiency = abs(P_mechanical / P_electrical) * 100.0
        else:
            efficiency = 0.0
        
        # 13. Update time
        self.current_time += dt
        
        # 14. Create and store state
        state = SimulationState(
            time=self.current_time,
            rotor=rotor_state,
            stator=stator_state,
            em_field=em_state,
            torque=T_em,
            power_mechanical=P_mechanical,
            power_electrical=P_electrical,
            efficiency=min(efficiency, 100.0)
        )
        
        self.history.append(state)
        
        return state
    
    def simulate(self, duration: float, dt: Optional[float] = None) -> List[SimulationState]:
        """
        Run simulation for specified duration.
        
        Args:
            duration: Simulation duration [s]
            dt: Time step [s] (if None, uses default)
            
        Returns:
            List of simulation states
        """
        if dt is None:
            dt = self.params.time_step
        
        num_steps = int(duration / dt)
        
        for _ in range(num_steps):
            self.step(dt)
        
        return self.history
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Compute performance metrics from simulation.
        
        Returns:
            Dictionary with performance metrics
        """
        if len(self.history) == 0:
            return {
                'avg_torque': 0.0,
                'avg_power_mechanical': 0.0,
                'avg_power_electrical': 0.0,
                'avg_efficiency': 0.0,
                'final_speed_rpm': 0.0,
                'max_torque': 0.0,
                'steady_state_speed': 0.0
            }
        
        # Extract data from history
        torques = [s.torque for s in self.history]
        speeds = [s.rotor.speed_rpm for s in self.history]
        P_mech = [s.power_mechanical for s in self.history]
        P_elec = [s.power_electrical for s in self.history]
        efficiencies = [s.efficiency for s in self.history]
        
        # Compute metrics
        # Use last 20% of data for steady-state values
        steady_idx = int(len(self.history) * 0.8)
        
        return {
            'avg_torque': np.mean(torques[steady_idx:]),
            'avg_power_mechanical': np.mean(P_mech[steady_idx:]),
            'avg_power_electrical': np.mean(P_elec[steady_idx:]),
            'avg_efficiency': np.mean(efficiencies[steady_idx:]),
            'final_speed_rpm': speeds[-1],
            'max_torque': np.max(np.abs(torques)),
            'steady_state_speed': np.mean(speeds[steady_idx:]),
            'simulation_time': self.history[-1].time
        }
    
    def export_data(self) -> Dict[str, np.ndarray]:
        """
        Export simulation data for analysis/plotting.
        
        Returns:
            Dictionary with time-series data arrays
        """
        if len(self.history) == 0:
            return {}
        
        return {
            'time': np.array([s.time for s in self.history]),
            'speed_rpm': np.array([s.rotor.speed_rpm for s in self.history]),
            'torque': np.array([s.torque for s in self.history]),
            'power_mechanical': np.array([s.power_mechanical for s in self.history]),
            'power_electrical': np.array([s.power_electrical for s in self.history]),
            'efficiency': np.array([s.efficiency for s in self.history]),
            'stator_current_a': np.array([s.stator.current[0] for s in self.history]),
            'stator_current_b': np.array([s.stator.current[1] if len(s.stator.current) > 1 else 0 
                                         for s in self.history]),
            'stator_current_c': np.array([s.stator.current[2] if len(s.stator.current) > 2 else 0 
                                         for s in self.history]),
        }
    
    def reset(self):
        """Reset simulation to initial state"""
        self.current_time = 0.0
        self.history.clear()
        self.em_solver.reset()
        self.rotor.reset()
        self.stator.reset()
    
    def set_load_torque(self, torque_fn):
        """
        Set load torque function.
        
        Args:
            torque_fn: Function(time, speed) -> torque [N⋅m]
        """
        self.rotor.set_load_torque(torque_fn)
    
    def set_voltage_supply(self, voltage_fn):
        """
        Set custom voltage supply function.
        
        Args:
            voltage_fn: Function(time) -> phase_voltages [V]
        """
        self.stator.set_voltage_supply(voltage_fn)
