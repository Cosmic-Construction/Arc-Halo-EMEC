# Virtual Hardware Device Guide

**Arc-Halo EMEC v2.1 — Virtual Engine as a Virtual Hardware Device**

The device layer wraps the EMEC `VirtualEngine` in a hardware-device
metaphor: hosts interact with the simulated induction motor exactly as they
would with a physical motor drive — power on, write setpoints through a
register map, run, read telemetry, and handle latching protection faults.
The physics core is completely unmodified.

## Table of Contents

- [Architecture](#architecture)
- [Lifecycle State Machine](#lifecycle-state-machine)
- [Register Map](#register-map)
- [Fault Model](#fault-model)
- [Telemetry](#telemetry)
- [Python API](#python-api)
- [HTTP/SSE Server](#httpsse-server)
- [Command Line Interface](#command-line-interface)
- [Database Persistence](#database-persistence)
- [Testing](#testing)

## Architecture

```
┌────────────── Host Client (CLI / HTTP / SSE / DB dashboard) ─────────────┐
│                            Device API Layer                               │
│  emec/device/server.py (REST + SSE)   emec/device/cli.py (interactive)    │
├───────────────────────────────────────────────────────────────────────────┤
│                        Device Driver Layer                                │
│  emec/device/device.py     VirtualHardwareDevice                          │
│    - Lifecycle state machine (OFF → READY → RUNNING ⇄ FAULT, ESTOP)       │
│    - emec/device/registers.py    Register map with validation             │
│    - emec/device/faults.py       Latching protection faults               │
│    - emec/device/telemetry.py    Ring-buffer telemetry recorder           │
├───────────────────────────────────────────────────────────────────────────┤
│                        Simulation Core (unmodified)                       │
│  VirtualEngine → EMFieldSolver / Winding / Rotor / Stator                 │
├───────────────────────────────────────────────────────────────────────────┤
│                        Persistence Layer (optional)                       │
│  db/scripts/emec_device_repository.py → db/schema/06_emec_device.sql      │
│  (emec_devices, emec_device_sessions, emec_telemetry, emec_fault_log)     │
└───────────────────────────────────────────────────────────────────────────┘
```

## Lifecycle State Machine

```
                  power_on()        start()               stop()
          ┌───┐ ───────────► ┌───────┐ ───────► ┌─────────┐ ──────► ┌───────┐
          │OFF│              │ READY │          │ RUNNING │         │ READY │
          └───┘ ◄─────────── └───────┘ ◄─────── └─────────┘         └───────┘
            ▲    power_off()     ▲                    │
            │                    │ reset_faults()     │ protection trip
            │                    │ (condition clear)  ▼
            │                    └──────────────── ┌───────┐
            │                                      │ FAULT │
            │                                      └───────┘
            │  e_stop() from any powered state
          ┌─┴─────┐  power_on()  ┌───────┐
          │ (any) │ ───────────► │ ESTOP │ ── power_on() ──► READY
          └───────┘              └───────┘
```

| Method | From | To | Notes |
|--------|------|----|-------|
| `power_on()` | OFF, ESTOP | READY | Applies setpoints to engine supply/load |
| `start()` | READY | RUNNING | Raises `InvalidStateError` from OFF/FAULT/ESTOP |
| `stop()` | RUNNING | READY | Retains telemetry for readout |
| `power_off()` | READY, FAULT | OFF | Raises while RUNNING |
| `e_stop()` | any powered | ESTOP | Unconditional; latches `ESTOP` fault |
| `reset_faults()` | FAULT | READY | Only when trip condition cleared |
| `reset()` | any | READY (or OFF) | Clears engine, telemetry, faults |

## Register Map

Address space follows physical drive conventions:
`0x0000` command/control · `0x0100` setpoints · `0x0200` telemetry · `0x0300` status.

| Register | Address | Access | Unit | Description |
|----------|---------|--------|------|-------------|
| `CONTROL_WORD` | 0x0000 | RW | bitfield | bit 0 = start, bit 1 = stop, bit 2 = reset |
| `FAULT_RESET` | 0x0001 | WO | bitfield | Write 1 to clear latched faults |
| `VOLTAGE_SETPOINT` | 0x0100 | RW | V | Line voltage setpoint (0–690 V) |
| `FREQUENCY_SETPOINT` | 0x0101 | RW | Hz | Supply frequency setpoint (0–400 Hz) |
| `LOAD_TORQUE_SETPOINT` | 0x0102 | RW | N·m | Constant load torque (0–200 N·m) |
| `SPEED_RPM` | 0x0200 | RO | rpm | Rotor mechanical speed |
| `TORQUE` | 0x0201 | RO | N·m | Electromagnetic torque |
| `PHASE_CURRENT_A/B/C` | 0x0202–4 | RO | A | Stator phase currents (instantaneous) |
| `POWER_MECH` | 0x0205 | RO | W | Mechanical output power |
| `POWER_ELEC` | 0x0206 | RO | W | Electrical input power |
| `EFFICIENCY` | 0x0207 | RO | % | Energy conversion efficiency |
| `SIMULATION_TIME` | 0x0208 | RO | s | Internal simulation clock |
| `STATUS_WORD` | 0x0300 | RO | bitfield | bit 0 powered, 1 running, 2 fault, 3 estop |
| `FAULT_CODE` | 0x0301 | RO | code | Latched fault code (0 = none) |
| `DEVICE_STATE` | 0x0302 | RO | enum | OFF / READY / RUNNING / FAULT / ESTOP |

Writes are validated for access mode, type, and range
(`RegisterAccessError`, `RegisterValueError`). Setpoints rebind the engine's
supply and load callables — the physics core is never modified.

## Fault Model

Faults mirror real drive semantics: a trip latches the fault, moves the
device to `FAULT`, and freezes the simulation. Faults clear only via
`reset_faults()` (or the `FAULT_RESET` register) **after** the trip
condition has disappeared.

| Code | Fault | Trip condition (defaults) |
|------|-------|---------------------------|
| 0 | `NONE` | — |
| 1 | `OVER_CURRENT` | max \|phase current\| > 100 A |
| 2 | `OVER_TORQUE` | \|T_em\| > 100 N·m |
| 3 | `OVER_SPEED` | \|speed\| > 1.2 × rated speed |
| 4 | `ESTOP` | Emergency stop engaged |

Limits are configurable via `ProtectionLimits`:

```python
from emec import VirtualHardwareDevice, ProtectionLimits

limits = ProtectionLimits(current_limit_a=80.0, overspeed_factor=1.1)
device = VirtualHardwareDevice(limits=limits)
```

## Telemetry

`TelemetryRecorder` is a fixed-window ring buffer with decimation:

```python
device = VirtualHardwareDevice(telemetry_capacity=10000, telemetry_decimation=50)
# ... run ...
samples = device.telemetry.snapshot(last_n=100)  # list of dicts
latest = device.telemetry.latest()
device.telemetry.export_csv("run.csv")           # CSV export
```

Channels: `time`, `speed_rpm`, `torque`, `power_mechanical`,
`power_electrical`, `efficiency`, `stator_current_a/b/c`.

## Python API

```python
from emec import VirtualHardwareDevice, Register

device = VirtualHardwareDevice()

device.power_on()
device.write_register(Register.VOLTAGE_SETPOINT, 400.0)
device.write_register("FREQUENCY_SETPOINT", 50.0)   # names work too
device.write_register("LOAD_TORQUE_SETPOINT", 10.0)

device.start()
device.run(1.0)                                      # simulated seconds

print(device.read_register("SPEED_RPM"))
print(device.read_register("EFFICIENCY"))
device.stop()
```

## HTTP/SSE Server

Stdlib-only REST + Server-Sent Events API (no third-party dependencies):

```python
from emec import VirtualHardwareDevice
from emec.device.server import serve

device = VirtualHardwareDevice()
serve(device, host='127.0.0.1', port=8080)           # blocking
# or: serve(device, background=True) -> (server, thread)
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/registers` | GET | All registers with metadata and values |
| `/registers/{name}` | GET | Single register value |
| `/registers/{name}` | POST | Write register, body `{"value": x}` |
| `/telemetry?last_n=N` | GET | Telemetry samples |
| `/stream?rate_hz=R` | GET | SSE telemetry stream (≤ 50 events/s) |
| `/command/{cmd}` | POST | `power_on` `power_off` `start` `stop` `reset` `estop` |
| `/state` | GET | Lifecycle state, status word, fault code |

**Security note:** the server binds to localhost by default and has no
authentication. Only bind to non-local interfaces on trusted networks.

## Command Line Interface

```bash
python -m emec.device.cli          # interactive shell
python -m emec.device.cli --demo   # scripted demo sequence
```

```
device> power_on
state -> READY
device> set LOAD_TORQUE_SETPOINT 10
device> start
device> run 0.5
device> get SPEED_RPM
device> telemetry 5
device> estop
```

## Database Persistence

When a repository is attached, sessions/telemetry/faults persist to the
Arc-Halo database (schema `db/schema/06_emec_device.sql`):

```python
from emec import VirtualHardwareDevice
from db.scripts.emec_device_repository import create_repository_from_env

repo = create_repository_from_env()          # uses NEON_DATABASE_URL
device = VirtualHardwareDevice(repository=repo)
```

- A **session** opens on `start()` and closes on `stop()`/fault, storing
  setpoints, final metrics, and buffered telemetry.
- **Faults** are recorded to `emec_fault_log` at trip time.
- Persistence failures never break device operation (fail-safe no-op).
- Query runs via the `v_emec_device_sessions` view.

## Testing

```bash
python -m emec.test_device    # 13 device tests
python -m emec.test_emec      # 8 core physics tests (unmodified)
python -m emec.test_bond_graph  # 18 bond graph / neurological tests
```

The device suite covers lifecycle transitions, register validation, fault
trip/latch/clear, e-stop, setpoint binding, telemetry buffer behavior, HTTP
endpoints (in-process server), CLI dispatch, and the repository (mocked).
