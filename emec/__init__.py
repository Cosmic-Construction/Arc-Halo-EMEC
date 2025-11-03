"""
Arc-Halo EMEC - Electromagnetic Energy Conversion
Virtual Engine Model with Rotor & Stator Dynamics

This module implements a virtual engine simulator based on electromagnetic field
equations for polyphase induction machines with electro-mechanical energy conversion.

New Features:
- Bond Graph Generalization Framework
- Domain-agnostic energy modeling
- Neurological analogy for EM energy conversion
"""

from .em_field_solver import EMFieldSolver
from .polyphase_winding import PolyphaseWindingModel, WindingParameters
from .rotor_dynamics import RotorDynamics, RotorParameters
from .stator_dynamics import StatorDynamics, StatorParameters
from .virtual_engine import VirtualEngine, EngineParameters
from .bond_graph import (
    BondGraphModel,
    BondGraphElement,
    ResistiveElement,
    CapacitiveElement,
    InertialElement,
    TransformerElement,
    GyratorElement,
    EnergyDomain,
    PowerVariables,
    DomainMapping,
    DOMAIN_MAPPINGS
)
from .em_bond_graph_mapping import (
    EMBondGraphMapping,
    create_em_bond_graph_from_engine,
    analyze_power_flow,
    get_generalized_impedance,
    compute_energy_domain_equivalences,
    EMBondGraphSimulator
)
from .neurological_analogy import (
    NeurologicalEnergyModel,
    CognitiveFieldParameters,
    AffectiveFieldParameters,
    BehavioralParameters,
    PsychophysicalCoupling,
    NeurologicalDomain
)

__version__ = "2.0.0"
__all__ = [
    # Core EMEC components
    'EMFieldSolver',
    'PolyphaseWindingModel',
    'WindingParameters',
    'RotorDynamics',
    'RotorParameters',
    'StatorDynamics',
    'StatorParameters',
    'VirtualEngine',
    'EngineParameters',
    # Bond Graph Framework
    'BondGraphModel',
    'BondGraphElement',
    'ResistiveElement',
    'CapacitiveElement',
    'InertialElement',
    'TransformerElement',
    'GyratorElement',
    'EnergyDomain',
    'PowerVariables',
    'DomainMapping',
    'DOMAIN_MAPPINGS',
    # EM-Bond Graph Mapping
    'EMBondGraphMapping',
    'create_em_bond_graph_from_engine',
    'analyze_power_flow',
    'get_generalized_impedance',
    'compute_energy_domain_equivalences',
    'EMBondGraphSimulator',
    # Neurological Analogy
    'NeurologicalEnergyModel',
    'CognitiveFieldParameters',
    'AffectiveFieldParameters',
    'BehavioralParameters',
    'PsychophysicalCoupling',
    'NeurologicalDomain'
]
