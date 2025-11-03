"""
Arc-Halo EMEC - Electromagnetic Energy Conversion
Virtual Engine Model with Rotor & Stator Dynamics

This module implements a virtual engine simulator based on electromagnetic field
equations for polyphase induction machines with electro-mechanical energy conversion.
"""

from .em_field_solver import EMFieldSolver
from .polyphase_winding import PolyphaseWindingModel, WindingParameters
from .rotor_dynamics import RotorDynamics, RotorParameters
from .stator_dynamics import StatorDynamics, StatorParameters
from .virtual_engine import VirtualEngine, EngineParameters

__version__ = "1.0.0"
__all__ = [
    'EMFieldSolver',
    'PolyphaseWindingModel',
    'WindingParameters',
    'RotorDynamics',
    'RotorParameters',
    'StatorDynamics',
    'StatorParameters',
    'VirtualEngine',
    'EngineParameters'
]
