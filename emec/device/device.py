"""
Virtual Hardware Device - Driver

Wraps the EMEC VirtualEngine in a hardware-device metaphor: hosts interact
through a register/control surface exactly as with a physical motor drive —
power on, write setpoints (voltage, frequency, load torque), run, read
telemetry, and handle latching faults. The physics core is unmodified.
"""

from enum import Enum
from typing import Optional, Union

import numpy as np

from ..virtual_engine import VirtualEngine, EngineParameters
from .faults import FaultCode, FaultManager, ProtectionLimits
from .registers import Access, Register, REGISTER_MAP
from .telemetry import TelemetryRecorder

# Control word bit positions
CTRL_BIT_START = 0x1
CTRL_BIT_STOP = 0x2
CTRL_BIT_RESET = 0x4

# Status word bit positions
STATUS_BIT_POWERED = 0x1
STATUS_BIT_RUNNING = 0x2
STATUS_BIT_FAULT = 0x4
STATUS_BIT_ESTOP = 0x8


class DeviceState(Enum):
    """Device lifecycle state"""
    OFF = "OFF"
    READY = "READY"
    RUNNING = "RUNNING"
    FAULT = "FAULT"
    ESTOP = "ESTOP"


class RegisterAccessError(Exception):
    """Raised on invalid register access (unknown, wrong access mode)"""


class RegisterValueError(Exception):
    """Raised when a written value fails type or range validation"""


class InvalidStateError(Exception):
    """Raised when an operation is not permitted in the current state"""


class VirtualHardwareDevice:
    """
    Virtual hardware device driver for the EMEC virtual engine.

    Lifecycle:

        power_on()     start()                stop()
        OFF ─────────► READY ─────────► RUNNING ──────► READY
                          ▲                  │  │
                          │   fault cleared  │  │ protection trip
                          └──────────────────┘  ▼
                      ┌──── reset_faults() ── FAULT
                      │
        e_stop() from any powered state ─► ESTOP ── power_on() ─► READY

    Args:
        params: Engine parameters (defaults if None)
        limits: Protection limits (defaults if None)
        telemetry_capacity: Telemetry ring buffer capacity
        telemetry_decimation: Record every Nth cycle
        repository: Optional persistence sink (e.g. EMECDeviceRepository);
                    when set, sessions/telemetry/faults are stored on stop.
    """

    def __init__(self,
                 params: Optional[EngineParameters] = None,
                 limits: Optional[ProtectionLimits] = None,
                 telemetry_capacity: int = 10000,
                 telemetry_decimation: int = 1,
                 repository=None):
        self.engine = VirtualEngine(params)
        self.params = self.engine.params
        self.faults = FaultManager(limits)
        self.telemetry = TelemetryRecorder(
            capacity=telemetry_capacity,
            decimation=telemetry_decimation,
        )
        self.repository = repository

        self.state = DeviceState.OFF
        self._control_word = 0

        # Setpoints (applied to engine supply/load callables)
        self._voltage_setpoint = float(self.params.stator_electrical.rated_voltage)
        self._frequency_setpoint = float(self.params.stator_electrical.rated_frequency)
        self._load_torque_setpoint = 0.0

        # Latest cycle results for readback
        self._last_torque = 0.0
        self._last_power_mech = 0.0
        self._last_power_elec = 0.0
        self._last_efficiency = 0.0

        # Persistence bookkeeping
        self._session_id = None
        self._fault_counts = {code: 0 for code in FaultCode if code != FaultCode.NONE}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def power_on(self) -> DeviceState:
        """Energize the device. From OFF or ESTOP, enters READY."""
        if self.state in (DeviceState.OFF, DeviceState.ESTOP):
            self.state = DeviceState.READY
            self._apply_setpoints()
        return self.state

    def start(self) -> DeviceState:
        """Start the drive (begin stepping the simulation)."""
        if self.state == DeviceState.READY:
            self.state = DeviceState.RUNNING
            self._begin_session()
        elif self.state == DeviceState.OFF:
            raise InvalidStateError("Power on the device before starting")
        elif self.state in (DeviceState.FAULT, DeviceState.ESTOP):
            raise InvalidStateError(
                f"Cannot start from {self.state.value}; clear the condition first"
            )
        return self.state

    def stop(self) -> DeviceState:
        """Stop the drive; retains telemetry for readout."""
        if self.state == DeviceState.RUNNING:
            self.state = DeviceState.READY
            self._end_session()
        return self.state

    def power_off(self) -> DeviceState:
        """De-energize. Only possible when not running."""
        if self.state in (DeviceState.READY, DeviceState.FAULT):
            self.state = DeviceState.OFF
        elif self.state == DeviceState.RUNNING:
            raise InvalidStateError("Stop the device before powering off")
        return self.state

    def e_stop(self) -> DeviceState:
        """Unconditional emergency stop from any powered state."""
        if self.state != DeviceState.OFF:
            if self.state == DeviceState.RUNNING:
                self._end_session()
            self.faults.trip(
                FaultCode.ESTOP, "Emergency stop engaged",
                self.engine.current_time,
            )
            self.state = DeviceState.ESTOP
        return self.state

    def reset_faults(self) -> bool:
        """
        Clear latched faults. Only succeeds when the trip condition has
        cleared and the device is in FAULT state.
        """
        if self.state != DeviceState.FAULT:
            return not self.faults.is_faulted
        cleared = self.faults.clear(condition_active=self._trip_condition_active())
        if cleared:
            self.state = DeviceState.READY
        return cleared

    def reset(self) -> DeviceState:
        """Full device reset: engine state, telemetry, and faults."""
        self.engine.reset()
        self.telemetry.clear()
        self.faults = FaultManager(self.faults.limits)
        self._last_torque = 0.0
        self._last_power_mech = 0.0
        self._last_power_elec = 0.0
        self._last_efficiency = 0.0
        if self.state != DeviceState.OFF:
            self.state = DeviceState.READY
        return self.state

    # ------------------------------------------------------------------
    # Register interface
    # ------------------------------------------------------------------

    def write_register(self, register: Union[Register, str], value) -> None:
        """
        Write a writable register with access, type, and range validation.

        Args:
            register: Register enum member or its name (e.g. "VOLTAGE_SETPOINT")
            value: New value (numeric unless the register takes a bitfield)

        Raises:
            RegisterAccessError: Unknown register or not writable
            RegisterValueError: Value fails validation
        """
        register = self._resolve_register(register)
        info = REGISTER_MAP[register]
        if info.access == Access.READ_ONLY:
            raise RegisterAccessError(f"Register {register.name} is read-only")

        value = self._validate_value(register, value)

        if register == Register.CONTROL_WORD:
            self._control_word = int(value)
            if self._control_word & CTRL_BIT_RESET:
                self.reset()
            elif self._control_word & CTRL_BIT_STOP:
                self.stop()
            elif self._control_word & CTRL_BIT_START:
                self.start()
        elif register == Register.FAULT_RESET:
            if value:
                self.reset_faults()
        elif register == Register.VOLTAGE_SETPOINT:
            self._voltage_setpoint = value
            self._apply_voltage_supply()
        elif register == Register.FREQUENCY_SETPOINT:
            self._frequency_setpoint = value
            self._apply_voltage_supply()
        elif register == Register.LOAD_TORQUE_SETPOINT:
            self._load_torque_setpoint = value
            self._apply_load_torque()

    def read_register(self, register: Union[Register, str]):
        """
        Read a readable register.

        Args:
            register: Register enum member or its name

        Raises:
            RegisterAccessError: Unknown register or write-only
        """
        register = self._resolve_register(register)
        info = REGISTER_MAP[register]
        if info.access == Access.WRITE_ONLY:
            raise RegisterAccessError(f"Register {register.name} is write-only")

        stator = self.engine.stator.state
        rotor = self.engine.rotor.state

        if register == Register.CONTROL_WORD:
            return self._control_word
        if register == Register.VOLTAGE_SETPOINT:
            return self._voltage_setpoint
        if register == Register.FREQUENCY_SETPOINT:
            return self._frequency_setpoint
        if register == Register.LOAD_TORQUE_SETPOINT:
            return self._load_torque_setpoint
        if register == Register.SPEED_RPM:
            return rotor.speed_rpm
        if register == Register.TORQUE:
            return self._last_torque
        if register == Register.PHASE_CURRENT_A:
            return float(stator.current[0]) if len(stator.current) > 0 else 0.0
        if register == Register.PHASE_CURRENT_B:
            return float(stator.current[1]) if len(stator.current) > 1 else 0.0
        if register == Register.PHASE_CURRENT_C:
            return float(stator.current[2]) if len(stator.current) > 2 else 0.0
        if register == Register.POWER_MECH:
            return self._last_power_mech
        if register == Register.POWER_ELEC:
            return self._last_power_elec
        if register == Register.EFFICIENCY:
            return self._last_efficiency
        if register == Register.SIMULATION_TIME:
            return self.engine.current_time
        if register == Register.STATUS_WORD:
            return self._status_word()
        if register == Register.FAULT_CODE:
            return int(self.faults.fault_code)
        if register == Register.DEVICE_STATE:
            return self.state.value
        raise RegisterAccessError(f"Register {register.name} not readable")  # pragma: no cover

    # ------------------------------------------------------------------
    # Simulation cycle
    # ------------------------------------------------------------------

    def run_cycle(self, dt: Optional[float] = None):
        """
        Execute one device cycle. Only steps the engine while RUNNING.
        Evaluates protections after each step; a trip latches the fault and
        moves the device to FAULT (the engine freezes).

        Returns the engine SimulationState, or None when not running.
        """
        if self.state != DeviceState.RUNNING:
            return None

        state = self.engine.step(dt)

        self._last_torque = state.torque
        self._last_power_mech = state.power_mechanical
        self._last_power_elec = state.power_electrical
        self._last_efficiency = state.efficiency

        fault = self.faults.check_protections(
            phase_currents=state.stator.current,
            torque=state.torque,
            speed_rpm=state.rotor.speed_rpm,
            rated_speed_rpm=self.params.rotor_mechanical.rated_speed,
            time=state.time,
        )
        if fault is not None and fault.code not in (FaultCode.NONE,):
            self._fault_counts[fault.code] += 1
            self.state = DeviceState.FAULT
            self._record_fault(fault)
            self._end_session()
            return state

        self.telemetry.record(self._sample_from_state(state))
        return state

    def run(self, duration: float, dt: Optional[float] = None):
        """
        Run the device for a simulated duration, stopping early if a
        protection fault trips. Returns the number of cycles executed.
        """
        if dt is None:
            dt = self.params.time_step
        cycles = int(duration / dt)
        executed = 0
        for _ in range(cycles):
            if self.run_cycle(dt) is None:
                break
            executed += 1
        return executed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sample_from_state(self, state) -> dict:
        currents = state.stator.current
        return {
            'time': state.time,
            'speed_rpm': state.rotor.speed_rpm,
            'torque': state.torque,
            'power_mechanical': state.power_mechanical,
            'power_electrical': state.power_electrical,
            'efficiency': state.efficiency,
            'stator_current_a': float(currents[0]) if len(currents) > 0 else 0.0,
            'stator_current_b': float(currents[1]) if len(currents) > 1 else 0.0,
            'stator_current_c': float(currents[2]) if len(currents) > 2 else 0.0,
        }

    def _status_word(self) -> int:
        word = 0
        if self.state != DeviceState.OFF:
            word |= STATUS_BIT_POWERED
        if self.state == DeviceState.RUNNING:
            word |= STATUS_BIT_RUNNING
        if self.state == DeviceState.FAULT or self.faults.is_faulted:
            word |= STATUS_BIT_FAULT
        if self.state == DeviceState.ESTOP:
            word |= STATUS_BIT_ESTOP
        return word

    def _trip_condition_active(self) -> bool:
        """Re-evaluate protection limits at the frozen operating point"""
        stator = self.engine.stator.state
        rotor = self.engine.rotor.state
        limits = self.faults.limits
        max_current = max((abs(c) for c in stator.current), default=0.0)
        if max_current > limits.current_limit_a:
            return True
        if abs(self._last_torque) > limits.torque_limit_nm:
            return True
        speed_limit = limits.overspeed_factor * self.params.rotor_mechanical.rated_speed
        if abs(rotor.speed_rpm) > speed_limit:
            return True
        return False

    def _apply_setpoints(self):
        """Push current setpoints into the engine callables"""
        self._apply_voltage_supply()
        self._apply_load_torque()

    def _apply_voltage_supply(self):
        """Bind the stator supply to the voltage/frequency setpoints"""
        connection = self.params.stator_electrical.connection_type
        num_phases = self.params.stator_electrical.num_phases
        voltage = self._voltage_setpoint
        frequency = self._frequency_setpoint

        def supply(time: float) -> np.ndarray:
            v_phase = voltage / np.sqrt(3) if connection == "wye" else voltage
            v_peak = v_phase * np.sqrt(2)
            omega = 2 * np.pi * frequency
            return np.array([
                v_peak * np.sin(omega * time - 2 * np.pi * i / num_phases)
                for i in range(num_phases)
            ])

        self.engine.set_voltage_supply(supply)
        self.engine.stator.set_frequency(frequency)

    def _apply_load_torque(self):
        """Bind the rotor load torque to the setpoint (constant load)"""
        load = self._load_torque_setpoint
        self.engine.set_load_torque(lambda t, omega: load)

    def _resolve_register(self, register: Union[Register, str]) -> Register:
        if isinstance(register, Register):
            return register
        if isinstance(register, str):
            try:
                return Register[register]
            except KeyError:
                raise RegisterAccessError(f"Unknown register: {register}")
        raise RegisterAccessError(f"Unknown register: {register!r}")

    def _validate_value(self, register: Register, value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise RegisterValueError(
                f"Register {register.name} requires a numeric value, got {value!r}"
            )
        info = REGISTER_MAP[register]
        if info.value_range is not None:
            lo, hi = info.value_range
            if not (lo <= value <= hi):
                raise RegisterValueError(
                    f"Register {register.name} value {value} outside range [{lo}, {hi}]"
                )
        return value

    # ------------------------------------------------------------------
    # Persistence hooks (optional repository sink)
    # ------------------------------------------------------------------

    def _begin_session(self):
        if self.repository is None:
            return
        try:
            setpoints = {
                'voltage_setpoint': self._voltage_setpoint,
                'frequency_setpoint': self._frequency_setpoint,
                'load_torque_setpoint': self._load_torque_setpoint,
            }
            self._session_id = self.repository.start_session(setpoints)
        except Exception:
            self._session_id = None  # Persistence must never break the device

    def _end_session(self):
        if self.repository is None or self._session_id is None:
            return
        try:
            metrics = self.engine.get_performance_metrics()
            samples = self.telemetry.snapshot()
            self.repository.end_session(self._session_id, metrics, samples)
        except Exception:
            pass  # Persistence must never break the device
        finally:
            self._session_id = None

    def _record_fault(self, fault):
        if self.repository is None or self._session_id is None:
            return
        try:
            self.repository.record_fault(
                self._session_id, int(fault.code), fault.message
            )
        except Exception:
            pass  # Persistence must never break the device
