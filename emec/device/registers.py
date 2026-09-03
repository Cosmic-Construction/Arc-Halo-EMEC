"""
Virtual Hardware Device - Register Map

Defines the register/control surface of the virtual hardware device.
Mirrors the register model of a physical motor drive: hosts write setpoints
and control words, and read back telemetry and status registers.

Register categories:
- Writable setpoints: voltage, frequency, load torque
- Writable commands: CONTROL_WORD (start/stop/reset), FAULT_RESET
- Readable telemetry: speed, torque, currents, powers, efficiency
- Readable status: STATUS_WORD, FAULT_CODE, DEVICE_STATE
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class Access(Enum):
    """Register access mode"""
    READ_ONLY = "ro"
    WRITE_ONLY = "wo"
    READ_WRITE = "rw"


class Register(Enum):
    """
    Virtual device register map.

    Address space follows physical drive conventions:
    0x0000-0x00FF: command/control
    0x0100-0x01FF: setpoints
    0x0200-0x02FF: telemetry
    0x0300-0x03FF: status/diagnostics
    """
    # Command / control
    CONTROL_WORD = 0x0000
    FAULT_RESET = 0x0001

    # Setpoints
    VOLTAGE_SETPOINT = 0x0100
    FREQUENCY_SETPOINT = 0x0101
    LOAD_TORQUE_SETPOINT = 0x0102

    # Telemetry
    SPEED_RPM = 0x0200
    TORQUE = 0x0201
    PHASE_CURRENT_A = 0x0202
    PHASE_CURRENT_B = 0x0203
    PHASE_CURRENT_C = 0x0204
    POWER_MECH = 0x0205
    POWER_ELEC = 0x0206
    EFFICIENCY = 0x0207
    SIMULATION_TIME = 0x0208

    # Status / diagnostics
    STATUS_WORD = 0x0300
    FAULT_CODE = 0x0301
    DEVICE_STATE = 0x0302


@dataclass(frozen=True)
class RegisterInfo:
    """Metadata describing a single device register"""
    register: Register
    access: Access
    unit: str
    description: str
    value_range: Optional[Tuple[float, float]] = None  # (min, max) for numeric writes


REGISTER_MAP = {
    Register.CONTROL_WORD: RegisterInfo(
        register=Register.CONTROL_WORD,
        access=Access.READ_WRITE,
        unit="bitfield",
        description="Control word: bit 0 = start, bit 1 = stop, bit 2 = reset",
    ),
    Register.FAULT_RESET: RegisterInfo(
        register=Register.FAULT_RESET,
        access=Access.WRITE_ONLY,
        unit="bitfield",
        description="Write 1 to clear latched faults (only when trip condition cleared)",
    ),
    Register.VOLTAGE_SETPOINT: RegisterInfo(
        register=Register.VOLTAGE_SETPOINT,
        access=Access.READ_WRITE,
        unit="V",
        description="Line voltage setpoint for the three-phase supply",
        value_range=(0.0, 690.0),
    ),
    Register.FREQUENCY_SETPOINT: RegisterInfo(
        register=Register.FREQUENCY_SETPOINT,
        access=Access.READ_WRITE,
        unit="Hz",
        description="Supply frequency setpoint (variable frequency drive input)",
        value_range=(0.0, 400.0),
    ),
    Register.LOAD_TORQUE_SETPOINT: RegisterInfo(
        register=Register.LOAD_TORQUE_SETPOINT,
        access=Access.READ_WRITE,
        unit="N·m",
        description="Constant mechanical load torque applied to the shaft",
        value_range=(0.0, 200.0),
    ),
    Register.SPEED_RPM: RegisterInfo(
        register=Register.SPEED_RPM,
        access=Access.READ_ONLY,
        unit="rpm",
        description="Rotor mechanical speed",
    ),
    Register.TORQUE: RegisterInfo(
        register=Register.TORQUE,
        access=Access.READ_ONLY,
        unit="N·m",
        description="Electromagnetic torque",
    ),
    Register.PHASE_CURRENT_A: RegisterInfo(
        register=Register.PHASE_CURRENT_A,
        access=Access.READ_ONLY,
        unit="A",
        description="Stator phase A current (instantaneous)",
    ),
    Register.PHASE_CURRENT_B: RegisterInfo(
        register=Register.PHASE_CURRENT_B,
        access=Access.READ_ONLY,
        unit="A",
        description="Stator phase B current (instantaneous)",
    ),
    Register.PHASE_CURRENT_C: RegisterInfo(
        register=Register.PHASE_CURRENT_C,
        access=Access.READ_ONLY,
        unit="A",
        description="Stator phase C current (instantaneous)",
    ),
    Register.POWER_MECH: RegisterInfo(
        register=Register.POWER_MECH,
        access=Access.READ_ONLY,
        unit="W",
        description="Mechanical output power",
    ),
    Register.POWER_ELEC: RegisterInfo(
        register=Register.POWER_ELEC,
        access=Access.READ_ONLY,
        unit="W",
        description="Electrical input power",
    ),
    Register.EFFICIENCY: RegisterInfo(
        register=Register.EFFICIENCY,
        access=Access.READ_ONLY,
        unit="%",
        description="Electro-mechanical energy conversion efficiency",
    ),
    Register.SIMULATION_TIME: RegisterInfo(
        register=Register.SIMULATION_TIME,
        access=Access.READ_ONLY,
        unit="s",
        description="Internal simulation clock",
    ),
    Register.STATUS_WORD: RegisterInfo(
        register=Register.STATUS_WORD,
        access=Access.READ_ONLY,
        unit="bitfield",
        description="Status word: bit 0 = powered, bit 1 = running, bit 2 = fault, bit 3 = estop",
    ),
    Register.FAULT_CODE: RegisterInfo(
        register=Register.FAULT_CODE,
        access=Access.READ_ONLY,
        unit="code",
        description="Latched fault code (0 = no fault)",
    ),
    Register.DEVICE_STATE: RegisterInfo(
        register=Register.DEVICE_STATE,
        access=Access.READ_ONLY,
        unit="enum",
        description="Lifecycle state: OFF, READY, RUNNING, FAULT, ESTOP",
    ),
}
