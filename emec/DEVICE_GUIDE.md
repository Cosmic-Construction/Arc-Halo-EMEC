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
- [C++ Header API](#c-header-api)
- [Testing](#testing)

## Architecture

```
┌────────────── Host Client (CLI / HTTP / SSE / DB dashboard) ─────────────┐
│                            Device API Layer                               │
│  emec/device/server.py (REST + WS/SSE) emec/device/cli.py (interactive)   │
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
| `power_on()` | OFF, ESTOP | READY | Applies setpoints; clears a latched ESTOP |
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

While `RUNNING`, a setpoint that would trip a protection is rejected
(`InvalidStateError`): load torque above the torque limit, and a supply
frequency whose synchronous speed exceeds the over-speed limit. Those
setpoints can still be preloaded in `READY` before `start()`.

## Fault Model

Faults mirror real drive semantics: a trip latches the fault, moves the
device to `FAULT`, and freezes the simulation. Faults clear only via
`reset_faults()` (or the `FAULT_RESET` register) **after** the trip
condition has disappeared.

| Code | Fault | Trip condition (defaults) |
|------|-------|---------------------------|
| 0 | `NONE` | — |
| 1 | `OVER_CURRENT` | max \|phase current\| > `CURRENT_LIMIT_AMPS` (100 A) |
| 2 | `OVER_TORQUE` | \|T_em\| > `TORQUE_LIMIT_NM` (100 N·m) |
| 3 | `OVER_SPEED` | \|speed\| > 1.2 × rated speed |
| 4 | `ESTOP` | Emergency stop engaged |
| 5 | `EFFICIENCY_ANOMALY` | non-finite, negative, or over-unity efficiency |

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
| `/stream?rate_hz=R` | GET | WS upgrade if requested, otherwise SSE (≤ 50 events/s) |
| `/command/{cmd}` | POST | `power_on` `power_off` `start` `stop` `reset` `estop` |
| `/state` | GET | Lifecycle state, status word, fault code |

`GET /stream` speaks WebSocket (RFC 6455 text frames) when the request
includes `Upgrade: websocket` and `Sec-WebSocket-Key`. Otherwise it falls
back to Server-Sent Events so stdlib HTTP clients keep working. The socket
is server-push telemetry only; client frames are not executed as commands.

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
device> inject_fault EFFICIENCY_ANOMALY
device> reset_faults
device> estop
```

## Database Persistence

When `NEON_DATABASE_URL` is set, `VirtualHardwareDevice()` attaches the
repository automatically. Pass `repository=` to override, or leave the
variable unset for in-memory operation. Connection failures are a no-op.
Sessions, telemetry, and faults persist to schema `db/schema/06_emec_device.sql`:

```python
from emec import VirtualHardwareDevice
from db.scripts.emec_device_repository import create_repository_from_env

repo = create_repository_from_env()          # uses NEON_DATABASE_URL
device = VirtualHardwareDevice(repository=repo)
```

- A **session** opens on `start()` and closes on `stop()` (`stopped`) or
  fault (`faulted`), storing setpoints, duration, final metrics, and
  buffered telemetry.
- **Faults** are recorded to `emec_fault_log` at trip time.
- Persistence failures never break device operation (fail-safe no-op).
- Query runs via the `v_emec_device_sessions` view.

## C++ Header API

The same device is available as a header-only C++17 port. Physics, bond-graph,
and neurological headers mirror the Python core; the device headers mirror
`emec/device/*.py`. Names stay hardware-direct (`VOLTAGE_SETPOINT`,
`LOAD_TORQUE_SETPOINT`, `set_voltage_supply`, `set_load_torque`, Park, R/C/I,
TF/GY). No extra libraries: the server is POSIX sockets, JSON is a small
writer, and Neon persistence is an optional `libpq` hook (`EMEC_HAS_LIBPQ`).

```bash
g++ -std=c++17 -Wall -Wextra -pthread -I. -DEMEC_TEST_DEVICE_MAIN \
    -x c++ emec/test_device.hpp -o /tmp/test_device && /tmp/test_device
make test          # core + bond graph + device
make examples      # emec/examples_device.hpp
```

```cpp
#include "emec/device/device.hpp"

emec::VirtualHardwareDevice device;
device.power_on();
device.write_register("VOLTAGE_SETPOINT", 400.0);
device.write_register("LOAD_TORQUE_SETPOINT", 10.0);
device.start();
device.run(0.05);
double rpm = std::get<double>(device.read_register("SPEED_RPM"));
```

Headers: `emec/virtual_engine.hpp`, `emec/bond_graph.hpp`,
`emec/neurological_analogy.hpp`, `emec/device/{registers,faults,telemetry,device,server,cli}.hpp`,
`db/scripts/emec_device_repository.hpp`.

## Testing

```bash
python -m emec.test_device    # 17 device tests
python -m emec.test_emec      # 8 core physics tests (unmodified)
python -m emec.test_bond_graph  # 18 bond graph / neurological tests
make test                     # same three suites, C++ headers
```

The device suite covers lifecycle transitions, register validation, fault
trip/latch/clear, e-stop, setpoint binding, telemetry buffer behavior, HTTP
endpoints (in-process server), CLI dispatch, and the repository (mocked).
