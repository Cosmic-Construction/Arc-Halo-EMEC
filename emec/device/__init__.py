"""
Virtual Hardware Device Layer

Wraps the EMEC VirtualEngine in a hardware-device metaphor: register map,
lifecycle state machine, latching faults, telemetry recording, and optional
database persistence. The physics core is unmodified.
"""

from .registers import Access, Register, RegisterInfo, REGISTER_MAP
from .faults import FaultCode, FaultEvent, FaultManager, ProtectionLimits
from .telemetry import TelemetryRecorder, TELEMETRY_FIELDS
from .device import (
    DeviceState,
    VirtualHardwareDevice,
    RegisterAccessError,
    RegisterValueError,
    InvalidStateError,
)

__all__ = [
    'Access',
    'Register',
    'RegisterInfo',
    'REGISTER_MAP',
    'FaultCode',
    'FaultEvent',
    'FaultManager',
    'ProtectionLimits',
    'TelemetryRecorder',
    'TELEMETRY_FIELDS',
    'DeviceState',
    'VirtualHardwareDevice',
    'RegisterAccessError',
    'RegisterValueError',
    'InvalidStateError',
]
