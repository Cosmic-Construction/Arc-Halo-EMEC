"""
Polyphase Induction Winding Model

Implements three-phase (and general polyphase) winding configurations
for induction machines with calculation of inductances, resistances,
and flux linkages.
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class WindingParameters:
    """Physical parameters of winding"""
    num_phases: int = 3              # Number of phases
    turns_per_phase: int = 100       # Turns per phase
    resistance_per_phase: float = 0.5  # Resistance [Ω]
    self_inductance: float = 0.01    # Self inductance [H]
    mutual_inductance: float = 0.005 # Mutual inductance [H]
    leakage_inductance: float = 0.001 # Leakage inductance [H]
    
    # Geometric parameters
    pole_pairs: int = 2              # Number of pole pairs
    air_gap: float = 0.001           # Air gap [m]
    stator_slots: int = 36           # Number of stator slots
    rotor_slots: int = 28            # Number of rotor slots


class PolyphaseWindingModel:
    """
    Polyphase winding model for induction machines.
    
    Models the electromagnetic characteristics of stator and rotor windings
    including inductances, resistances, and flux linkages.
    """
    
    def __init__(self, stator_params: WindingParameters, rotor_params: WindingParameters):
        """
        Initialize polyphase winding model.
        
        Args:
            stator_params: Stator winding parameters
            rotor_params: Rotor winding parameters
        """
        self.stator = stator_params
        self.rotor = rotor_params
        
        # Build inductance matrices
        self.L_ss = self._build_inductance_matrix(stator_params)  # Stator self
        self.L_rr = self._build_inductance_matrix(rotor_params)   # Rotor self
        self.L_sr = None  # Stator-rotor mutual (position dependent)
        
        # Current state
        self.stator_current = np.zeros(stator_params.num_phases)
        self.rotor_current = np.zeros(rotor_params.num_phases)
        
    def _build_inductance_matrix(self, params: WindingParameters) -> np.ndarray:
        """
        Build inductance matrix for multiphase winding.
        
        For three-phase:
        L = [[L_s,      -M/2,     -M/2   ],
             [-M/2,     L_s,      -M/2   ],
             [-M/2,     -M/2,     L_s    ]]
        
        where L_s = L_self + L_leakage and M = mutual inductance
        
        Args:
            params: Winding parameters
            
        Returns:
            Inductance matrix [H]
        """
        n = params.num_phases
        L = np.zeros((n, n))
        
        # Diagonal elements (self + leakage inductance)
        L_self_total = params.self_inductance + params.leakage_inductance
        np.fill_diagonal(L, L_self_total)
        
        # Off-diagonal elements (mutual inductance)
        # For symmetric three-phase: M = -L_self/2
        if n == 3:
            M = params.mutual_inductance
            for i in range(n):
                for j in range(n):
                    if i != j:
                        L[i, j] = -M / 2.0
        else:
            # General polyphase mutual inductance
            M = params.mutual_inductance
            for i in range(n):
                for j in range(n):
                    if i != j:
                        # Mutual inductance varies with spatial angle
                        phase_diff = 2 * np.pi * abs(i - j) / n
                        L[i, j] = M * np.cos(phase_diff)
        
        return L
    
    def compute_mutual_inductance(self, theta_r: float) -> np.ndarray:
        """
        Compute stator-rotor mutual inductance matrix.
        
        The mutual inductance varies with rotor position:
        L_sr(θ) = L_m * cos(θ - phase_angle)
        
        Args:
            theta_r: Rotor electrical angle [rad]
            
        Returns:
            Stator-rotor mutual inductance matrix [H]
        """
        n_s = self.stator.num_phases
        n_r = self.rotor.num_phases
        
        L_sr = np.zeros((n_s, n_r))
        
        # Maximum mutual inductance (depends on winding geometry)
        L_m_max = np.sqrt(self.stator.self_inductance * self.rotor.self_inductance) * 0.9
        
        # For three-phase machine
        for i in range(n_s):
            for j in range(n_r):
                # Phase angle for stator phase i
                theta_s = 2 * np.pi * i / n_s
                # Phase angle for rotor phase j
                theta_r_phase = 2 * np.pi * j / n_r
                # Total angle
                theta = theta_r + theta_r_phase - theta_s
                # Mutual inductance
                L_sr[i, j] = L_m_max * np.cos(theta)
        
        return L_sr
    
    def compute_flux_linkage(self,
                           stator_current: np.ndarray,
                           rotor_current: np.ndarray,
                           theta_r: float) -> Dict[str, np.ndarray]:
        """
        Compute flux linkages for stator and rotor windings.
        
        λ_s = L_ss * i_s + L_sr(θ) * i_r
        λ_r = L_rr * i_r + L_sr(θ)^T * i_s
        
        Args:
            stator_current: Stator phase currents [A]
            rotor_current: Rotor phase currents [A]
            theta_r: Rotor electrical angle [rad]
            
        Returns:
            Dictionary with 'stator' and 'rotor' flux linkages [Wb]
        """
        # Update mutual inductance for current rotor position
        L_sr = self.compute_mutual_inductance(theta_r)
        
        # Compute flux linkages
        lambda_s = self.L_ss @ stator_current + L_sr @ rotor_current
        lambda_r = self.L_rr @ rotor_current + L_sr.T @ stator_current
        
        # Update state
        self.stator_current = stator_current.copy()
        self.rotor_current = rotor_current.copy()
        
        return {
            'stator': lambda_s,
            'rotor': lambda_r
        }
    
    def compute_voltage_equations(self,
                                 stator_voltage: np.ndarray,
                                 rotor_voltage: np.ndarray,
                                 stator_current: np.ndarray,
                                 rotor_current: np.ndarray,
                                 d_lambda_s_dt: np.ndarray,
                                 d_lambda_r_dt: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Solve voltage equations for induction machine.
        
        v_s = R_s * i_s + dλ_s/dt
        v_r = R_r * i_r + dλ_r/dt
        
        Returns residuals for iterative solving.
        
        Args:
            stator_voltage: Applied stator voltage [V]
            rotor_voltage: Applied rotor voltage [V] (usually 0 for squirrel cage)
            stator_current: Stator current [A]
            rotor_current: Rotor current [A]
            d_lambda_s_dt: Time derivative of stator flux linkage [Wb/s]
            d_lambda_r_dt: Time derivative of rotor flux linkage [Wb/s]
            
        Returns:
            Dictionary with residuals for stator and rotor equations
        """
        # Resistance voltage drops
        R_s_matrix = np.eye(self.stator.num_phases) * self.stator.resistance_per_phase
        R_r_matrix = np.eye(self.rotor.num_phases) * self.rotor.resistance_per_phase
        
        v_s_resistive = R_s_matrix @ stator_current
        v_r_resistive = R_r_matrix @ rotor_current
        
        # Voltage equation residuals
        residual_s = stator_voltage - v_s_resistive - d_lambda_s_dt
        residual_r = rotor_voltage - v_r_resistive - d_lambda_r_dt
        
        return {
            'stator': residual_s,
            'rotor': residual_r
        }
    
    def compute_mmf(self, current: np.ndarray, turns: int) -> float:
        """
        Compute magnetomotive force (MMF).
        
        MMF = N * I (for a single phase)
        For polyphase, sum of all phase contributions
        
        Args:
            current: Phase currents [A]
            turns: Turns per phase
            
        Returns:
            Total MMF [A-turns]
        """
        return turns * np.sum(current)
    
    def compute_winding_factor(self) -> float:
        """
        Compute winding factor (pitch and distribution factors).
        
        For distributed windings:
        k_w = k_p * k_d
        
        where k_p is pitch factor and k_d is distribution factor
        
        Returns:
            Winding factor (dimensionless, typically 0.85-0.95)
        """
        # Simplified winding factor calculation
        # Full calculation would need detailed slot/coil configuration
        
        # Pitch factor (assuming full-pitch winding)
        k_p = 1.0
        
        # Distribution factor (depends on slots per pole per phase)
        slots_per_pole_per_phase = self.stator.stator_slots / (
            2 * self.stator.pole_pairs * self.stator.num_phases
        )
        
        # Simplified distribution factor
        if slots_per_pole_per_phase >= 1:
            q = slots_per_pole_per_phase
            alpha = np.pi / (self.stator.num_phases * q)
            k_d = np.sin(q * alpha / 2) / (q * np.sin(alpha / 2))
        else:
            k_d = 1.0
        
        return k_p * k_d
    
    def compute_power(self,
                     voltage: np.ndarray,
                     current: np.ndarray) -> Dict[str, float]:
        """
        Compute electrical power.
        
        For three-phase:
        P = 3 * V_phase * I_phase * cos(φ)
        Q = 3 * V_phase * I_phase * sin(φ)
        S = sqrt(P² + Q²)
        
        Args:
            voltage: Phase voltages [V]
            current: Phase currents [A]
            
        Returns:
            Dictionary with active, reactive, and apparent power
        """
        # Instantaneous power per phase
        p_phase = voltage * current
        
        # Total instantaneous power
        P_total = np.sum(p_phase)
        
        # For balanced three-phase (simplified)
        if len(voltage) == 3:
            V_rms = np.sqrt(np.mean(voltage**2))
            I_rms = np.sqrt(np.mean(current**2))
            S_apparent = 3 * V_rms * I_rms
        else:
            S_apparent = abs(P_total)
        
        return {
            'active': P_total,
            'apparent': S_apparent,
            'reactive': np.sqrt(max(0, S_apparent**2 - P_total**2))
        }
