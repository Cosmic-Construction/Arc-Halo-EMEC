"""
Virtual Hardware Device - Fault Model

Protection and fault latching for the virtual hardware device, mirroring the
behavior of a physical motor drive: faults trip the drive into the FAULT
state, latch until explicitly cleared, and can only be cleared once the
underlying trip condition has disappeared.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional


class FaultCode(IntEnum):
    """Latched fault codes (0 = no fault)"""
    NONE = 0
    OVER_CURRENT = 1
    OVER_TORQUE = 2
    OVER_SPEED = 3
    ESTOP = 4


@dataclass
class ProtectionLimits:
    """
    Trip thresholds for device protection.

    Defaults are conservative for the default engine parameters
    (5 kW class, 400 V / 50 Hz, 1500 rpm rated).
    """
    current_limit_a: float = 100.0       # Phase current trip threshold [A]
    torque_limit_nm: float = 100.0       # Electromagnetic torque trip threshold [N·m]
    overspeed_factor: float = 1.2        # Trip at factor × rated speed


@dataclass
class FaultEvent:
    """Record of a fault trip"""
    code: FaultCode
    message: str
    time: float  # Simulation time at trip [s]


class FaultManager:
    """
    Latching fault manager.

    A fault latches on trip and stays latched until clear() is called with
    no active trip condition present. Mirrors real drive semantics.
    """

    def __init__(self, limits: Optional[ProtectionLimits] = None):
        self.limits = limits or ProtectionLimits()
        self.active_fault: Optional[FaultEvent] = None
        self.history: List[FaultEvent] = []

    @property
    def fault_code(self) -> FaultCode:
        """Currently latched fault code (NONE if healthy)"""
        return self.active_fault.code if self.active_fault else FaultCode.NONE

    @property
    def is_faulted(self) -> bool:
        """True while a fault is latched"""
        return self.active_fault is not None

    def trip(self, code: FaultCode, message: str, time: float) -> FaultEvent:
        """
        Latch a fault. If a fault is already latched, the first (oldest)
        fault is retained, matching drive behavior.

        Returns the latched fault event.
        """
        if self.active_fault is None:
            self.active_fault = FaultEvent(code=code, message=message, time=time)
            self.history.append(self.active_fault)
        return self.active_fault

    def clear(self, condition_active: bool = False) -> bool:
        """
        Attempt to clear the latched fault.

        Args:
            condition_active: True if the trip condition is still present.
                              Faults cannot be cleared while it is.

        Returns:
            True if the fault was cleared.
        """
        if self.active_fault is None:
            return True
        if condition_active:
            return False
        self.active_fault = None
        return True

    def check_protections(self,
                          phase_currents,
                          torque: float,
                          speed_rpm: float,
                          rated_speed_rpm: float,
                          time: float) -> Optional[FaultEvent]:
        """
        Evaluate protection limits against the latest operating point and
        trip on violation. Returns the latched fault, or None if healthy.

        Args:
            phase_currents: Sequence of phase currents [A]
            torque: Electromagnetic torque [N·m]
            speed_rpm: Rotor speed [rpm]
            rated_speed_rpm: Rated speed for overspeed reference [rpm]
            time: Current simulation time [s]
        """
        max_current = max((abs(c) for c in phase_currents), default=0.0)
        if max_current > self.limits.current_limit_a:
            return self.trip(
                FaultCode.OVER_CURRENT,
                f"Over-current: {max_current:.1f} A exceeds "
                f"{self.limits.current_limit_a:.1f} A limit",
                time,
            )

        if abs(torque) > self.limits.torque_limit_nm:
            return self.trip(
                FaultCode.OVER_TORQUE,
                f"Over-torque: {abs(torque):.1f} N·m exceeds "
                f"{self.limits.torque_limit_nm:.1f} N·m limit",
                time,
            )

        speed_limit = self.limits.overspeed_factor * rated_speed_rpm
        if abs(speed_rpm) > speed_limit:
            return self.trip(
                FaultCode.OVER_SPEED,
                f"Over-speed: {abs(speed_rpm):.1f} rpm exceeds "
                f"{speed_limit:.1f} rpm limit",
                time,
            )

        return self.active_fault
