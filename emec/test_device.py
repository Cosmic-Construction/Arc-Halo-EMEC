"""
Tests for Virtual Hardware Device Layer

Tests the device lifecycle, register map, fault handling, telemetry,
server endpoints, CLI, and database repository (mocked).
"""

import sys
import os
import json
import tempfile
import urllib.request
import unittest.mock as mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emec.device import (
    VirtualHardwareDevice,
    DeviceState,
    Register,
    REGISTER_MAP,
    Access,
    FaultCode,
    FaultManager,
    ProtectionLimits,
    TelemetryRecorder,
    RegisterAccessError,
    RegisterValueError,
    InvalidStateError,
)


def test_lifecycle_transitions():
    """Test OFF -> READY -> RUNNING -> READY -> OFF transitions"""
    print("Testing Lifecycle Transitions...")

    device = VirtualHardwareDevice()
    assert device.state == DeviceState.OFF, "Initial state must be OFF"

    # start() from OFF is not permitted
    try:
        device.start()
        raise AssertionError("start() from OFF should raise")
    except InvalidStateError:
        pass

    device.power_on()
    assert device.state == DeviceState.READY, "power_on -> READY"

    device.start()
    assert device.state == DeviceState.RUNNING, "start -> RUNNING"

    # power_off while running is not permitted
    try:
        device.power_off()
        raise AssertionError("power_off while RUNNING should raise")
    except InvalidStateError:
        pass

    device.stop()
    assert device.state == DeviceState.READY, "stop -> READY"

    device.power_off()
    assert device.state == DeviceState.OFF, "power_off -> OFF"

    print("  ✓ Lifecycle Transitions tests passed")
    return True


def test_register_validation():
    """Test register access control and value validation"""
    print("Testing Register Validation...")

    device = VirtualHardwareDevice()

    # Read-only register cannot be written
    try:
        device.write_register(Register.SPEED_RPM, 100.0)
        raise AssertionError("Writing read-only register should raise")
    except RegisterAccessError:
        pass

    # Write-only register cannot be read
    try:
        device.read_register(Register.FAULT_RESET)
        raise AssertionError("Reading write-only register should raise")
    except RegisterAccessError:
        pass

    # Unknown register name
    try:
        device.read_register("NOT_A_REGISTER")
        raise AssertionError("Unknown register should raise")
    except RegisterAccessError:
        pass

    # Out-of-range setpoint value
    try:
        device.write_register(Register.VOLTAGE_SETPOINT, 10000.0)
        raise AssertionError("Out-of-range value should raise")
    except RegisterValueError:
        pass

    # Non-numeric value
    try:
        device.write_register(Register.LOAD_TORQUE_SETPOINT, "high")
        raise AssertionError("Non-numeric value should raise")
    except RegisterValueError:
        pass

    # Valid writes by name and by enum both work
    device.power_on()
    device.write_register("LOAD_TORQUE_SETPOINT", 12.5)
    assert device.read_register(Register.LOAD_TORQUE_SETPOINT) == 12.5
    device.write_register(Register.FREQUENCY_SETPOINT, 60.0)
    assert device.read_register("FREQUENCY_SETPOINT") == 60.0

    # Every register is documented in the map
    for reg in Register:
        assert reg in REGISTER_MAP, f"{reg.name} missing from REGISTER_MAP"
        assert REGISTER_MAP[reg].access in Access, f"{reg.name} access invalid"

    print("  ✓ Register Validation tests passed")
    return True


def test_control_word():
    """Test CONTROL_WORD bit commands"""
    print("Testing Control Word...")

    device = VirtualHardwareDevice()
    device.power_on()

    device.write_register(Register.CONTROL_WORD, 0x1)  # START
    assert device.state == DeviceState.RUNNING

    device.write_register(Register.CONTROL_WORD, 0x2)  # STOP
    assert device.state == DeviceState.READY

    device.write_register(Register.CONTROL_WORD, 0x4)  # RESET
    assert device.state == DeviceState.READY

    print("  ✓ Control Word tests passed")
    return True


def test_fault_trip_and_latch():
    """Test protection trip, latching, and start inhibit"""
    print("Testing Fault Trip and Latch...")

    device = VirtualHardwareDevice()
    device.power_on()
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 200.0)  # Overload
    device.start()
    device.run(1.0)

    assert device.state == DeviceState.FAULT, "Overload must trip to FAULT"
    code = device.read_register(Register.FAULT_CODE)
    assert code != int(FaultCode.NONE), "Fault code must be latched"

    # Start inhibited while faulted
    try:
        device.start()
        raise AssertionError("start() while FAULT should raise")
    except InvalidStateError:
        pass

    # Status word shows fault bit
    status = device.read_register(Register.STATUS_WORD)
    assert status & 0x4, "Status word fault bit not set"

    print("  ✓ Fault Trip and Latch tests passed")
    return True


def test_fault_reset():
    """Test fault clearing semantics"""
    print("Testing Fault Reset...")

    # Fault clears once condition is gone
    device = VirtualHardwareDevice()
    device.power_on()
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 200.0)
    device.start()
    device.run(1.0)
    assert device.state == DeviceState.FAULT

    device.reset()  # Clears engine state (trip condition)
    device.power_on()
    assert device.state == DeviceState.READY, "Reset restores READY"

    # FaultManager refuses to clear while condition active
    fm = FaultManager(ProtectionLimits())
    fm.trip(FaultCode.OVER_CURRENT, "test", 0.0)
    assert not fm.clear(condition_active=True), "Must not clear while active"
    assert fm.is_faulted
    assert fm.clear(condition_active=False), "Must clear when condition gone"
    assert not fm.is_faulted
    assert fm.fault_code == FaultCode.NONE

    print("  ✓ Fault Reset tests passed")
    return True


def test_efficiency_anomaly():
    """Test efficiency-anomaly trip and reuse of engine current/torque limits"""
    print("Testing Efficiency Anomaly...")

    from emec.virtual_engine import CURRENT_LIMIT_AMPS, TORQUE_LIMIT_NM

    limits = ProtectionLimits()
    assert limits.current_limit_a == CURRENT_LIMIT_AMPS
    assert limits.torque_limit_nm == TORQUE_LIMIT_NM

    fm = FaultManager()
    healthy = fm.check_protections(
        [1.0, -0.5, -0.5], 5.0, 100.0, 1500.0, 0.1,
        efficiency=0.08, power_electrical=50000.0, power_mechanical=40.0,
    )
    assert healthy is None, "Startup efficiency must not false-trip"

    over_unity = fm.check_protections(
        [1.0], 1.0, 100.0, 1500.0, 0.2,
        efficiency=150.0, power_electrical=100.0, power_mechanical=200.0,
    )
    assert over_unity is not None and over_unity.code == FaultCode.EFFICIENCY_ANOMALY

    fm_nan = FaultManager()
    non_finite = fm_nan.check_protections(
        [1.0], 1.0, 10.0, 1500.0, 0.0, efficiency=float('nan'),
    )
    assert non_finite.code == FaultCode.EFFICIENCY_ANOMALY

    device = VirtualHardwareDevice()
    device.power_on()
    device.start()

    class _Stator:
        current = [1.0, 1.0, 1.0]

    class _Rotor:
        speed_rpm = 100.0

    class _State:
        time = 0.01
        torque = 1.0
        power_mechanical = 500.0
        power_electrical = 100.0
        efficiency = 500.0
        stator = _Stator()
        rotor = _Rotor()

    device.engine.step = lambda dt=None: _State()
    device.run_cycle(1e-4)
    assert device.state == DeviceState.FAULT
    assert device.read_register(Register.FAULT_CODE) == int(FaultCode.EFFICIENCY_ANOMALY)
    assert device.reset_faults() is False, "Over-unity condition must block clear"

    print("  ✓ Efficiency Anomaly tests passed")
    return True


def test_running_setpoint_interlock():
    """RUNNING must reject setpoints that would trip protections"""
    print("Testing RUNNING Setpoint Interlock...")

    device = VirtualHardwareDevice()
    device.power_on()
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 10.0)
    device.start()

    try:
        device.write_register(Register.LOAD_TORQUE_SETPOINT, 200.0)
        raise AssertionError("Over-torque setpoint must be inhibited while RUNNING")
    except InvalidStateError:
        pass
    assert device.read_register(Register.LOAD_TORQUE_SETPOINT) == 10.0

    device.write_register(Register.LOAD_TORQUE_SETPOINT, 20.0)
    assert device.read_register(Register.LOAD_TORQUE_SETPOINT) == 20.0

    try:
        device.write_register(Register.FREQUENCY_SETPOINT, 80.0)
        raise AssertionError("Over-speed frequency must be inhibited while RUNNING")
    except InvalidStateError:
        pass
    assert device.read_register(Register.FREQUENCY_SETPOINT) == device.params.stator_electrical.rated_frequency

    device.stop()
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 200.0)
    assert device.read_register(Register.LOAD_TORQUE_SETPOINT) == 200.0, \
        "READY must still allow preloading a trip setpoint"

    print("  ✓ RUNNING Setpoint Interlock tests passed")
    return True


def test_estop():
    """Test unconditional emergency stop"""
    print("Testing Emergency Stop...")

    device = VirtualHardwareDevice()
    device.power_on()
    device.start()
    device.run(0.05)

    device.e_stop()
    assert device.state == DeviceState.ESTOP, "e_stop -> ESTOP"
    assert device.read_register(Register.FAULT_CODE) == int(FaultCode.ESTOP)

    status = device.read_register(Register.STATUS_WORD)
    assert status & 0x8, "Status word estop bit not set"

    # Recovery path: power_on from ESTOP returns to READY and clears the latch
    device.power_on()
    assert device.state == DeviceState.READY
    assert device.read_register(Register.FAULT_CODE) == int(FaultCode.NONE)

    # e_stop while OFF is a no-op
    device2 = VirtualHardwareDevice()
    device2.e_stop()
    assert device2.state == DeviceState.OFF

    print("  ✓ Emergency Stop tests passed")
    return True


def test_setpoint_binding():
    """Test that setpoints propagate into the engine"""
    print("Testing Setpoint Binding...")

    device = VirtualHardwareDevice()
    device.power_on()
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 7.5)
    device.write_register(Register.FREQUENCY_SETPOINT, 55.0)

    # Load torque callable reflects setpoint
    load = device.engine.rotor.load_torque_fn(0.0, 100.0)
    assert load == 7.5, f"Load torque binding wrong: {load}"

    # Supply function generates voltages at the set frequency
    v = device.engine.stator.compute_supply_voltage(0.001)
    assert len(v) == 3, "Supply must produce 3 phase voltages"
    assert device.engine.stator.state.frequency == 55.0

    print("  ✓ Setpoint Binding tests passed")
    return True


def test_telemetry_recorder():
    """Test telemetry ring buffer, decimation, and CSV export"""
    print("Testing Telemetry Recorder...")

    recorder = TelemetryRecorder(capacity=5, decimation=2)
    for i in range(10):
        recorder.record({'time': float(i), 'speed_rpm': float(i * 10)})

    # Decimation 2: 5 of 10 offered samples stored; capacity 5 keeps all
    assert len(recorder) == 5, f"Expected 5 samples, got {len(recorder)}"
    samples = recorder.snapshot()
    assert samples[0]['time'] == 1.0, "Decimation should keep even ticks"
    assert recorder.latest()['time'] == 9.0

    # Ring buffer drops oldest beyond capacity
    for i in range(10, 14):
        recorder.record({'time': float(i)})
    assert len(recorder) == 5, "Capacity must bound buffer"
    assert recorder.snapshot()[0]['time'] == 5.0

    # Snapshot window
    assert len(recorder.snapshot(last_n=2)) == 2

    # CSV export
    csv_text = recorder.to_csv(last_n=2)
    assert csv_text.splitlines()[0].startswith('time,speed_rpm'), "CSV header wrong"
    assert len(csv_text.strip().splitlines()) == 3  # header + 2 rows

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'telemetry.csv')
        recorder.export_csv(path, last_n=1)
        with open(path) as f:
            lines = f.read().strip().splitlines()
        assert len(lines) == 2, "CSV file should have header + 1 row"

    recorder.clear()
    assert len(recorder) == 0

    # Validation
    try:
        TelemetryRecorder(capacity=0)
        raise AssertionError("capacity=0 should raise")
    except ValueError:
        pass

    print("  ✓ Telemetry Recorder tests passed")
    return True


def test_device_run_and_readback():
    """Test run cycle, telemetry recording, and register readback"""
    print("Testing Device Run and Readback...")

    device = VirtualHardwareDevice(telemetry_decimation=10)
    device.power_on()
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0)
    device.start()
    cycles = device.run(0.05)

    assert cycles == 500, f"Expected 500 cycles, got {cycles}"
    assert len(device.telemetry) == 50, "Decimation 10 over 500 cycles = 50"

    sim_time = device.read_register(Register.SIMULATION_TIME)
    assert abs(sim_time - 0.05) < 1e-9, "Simulation clock mismatch"

    # Telemetry channels present
    sample = device.telemetry.latest()
    for key in ('time', 'speed_rpm', 'torque', 'power_mechanical',
                'stator_current_a'):
        assert key in sample, f"Telemetry missing channel {key}"

    # Not running: run_cycle is a no-op
    device.stop()
    assert device.run_cycle() is None

    print("  ✓ Device Run and Readback tests passed")
    return True


def test_server_endpoints():
    """Test HTTP server endpoints in-process"""
    print("Testing Server Endpoints...")

    from emec.device.server import serve

    device = VirtualHardwareDevice(telemetry_decimation=10)
    server, _thread = serve(device, host='127.0.0.1', port=18098, background=True)
    base = 'http://127.0.0.1:18098'

    def get(path):
        with urllib.request.urlopen(base + path) as resp:
            return json.loads(resp.read())

    def post(path, payload=None):
        data = json.dumps(payload or {}).encode()
        req = urllib.request.Request(base + path, data=data,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        # Register listing
        registers = get('/registers')
        assert 'SPEED_RPM' in registers and 'CONTROL_WORD' in registers

        # Command lifecycle
        status, body = post('/command/power_on')
        assert status == 200 and body['state'] == 'READY'
        status, body = post('/registers/LOAD_TORQUE_SETPOINT', {'value': 10.0})
        assert status == 200
        status, body = post('/command/start')
        assert body['state'] == 'RUNNING'
        status, body = post('/registers/LOAD_TORQUE_SETPOINT', {'value': 200.0})
        assert status == 400, "RUNNING must reject an over-torque setpoint"
        device.run(0.02)
        status, body = post('/command/stop')
        assert body['state'] == 'READY'

        # Register readback
        speed = get('/registers/SPEED_RPM')
        assert 'value' in speed and speed['unit'] == 'rpm'

        # State and telemetry endpoints
        state = get('/state')
        assert state['state'] == 'READY' and state['fault_code'] == 0
        telemetry = get('/telemetry?last_n=5')
        assert len(telemetry['samples']) == 5

        # Error paths
        status, _ = post('/registers/SPEED_RPM', {'value': 1.0})
        assert status == 404, "Writing read-only register must fail"
        status, _ = post('/registers/BOGUS', {'value': 1.0})
        assert status == 404
        status, _ = post('/registers/VOLTAGE_SETPOINT', {'value': 99999.0})
        assert status == 400, "Out-of-range write must fail"
        status, _ = post('/command/not_a_command')
        assert status == 404
        status, _ = post('/registers/VOLTAGE_SETPOINT')  # Missing body
        assert status == 400
    finally:
        server.shutdown()
        server.server_close()

    print("  ✓ Server Endpoints tests passed")
    return True


def test_cli_commands():
    """Test CLI command dispatch (scripted, non-interactive)"""
    print("Testing CLI Commands...")

    from emec.device.cli import DeviceCLI

    cli = DeviceCLI(VirtualHardwareDevice(telemetry_decimation=10))

    assert cli.dispatch("power_on")
    assert cli.device.state == DeviceState.READY

    assert cli.dispatch("set LOAD_TORQUE_SETPOINT 10")
    assert cli.device.read_register("LOAD_TORQUE_SETPOINT") == 10.0

    assert cli.dispatch("start")
    assert cli.dispatch("run 0.02")
    assert cli.dispatch("get SPEED_RPM")
    assert cli.dispatch("telemetry 3")
    assert cli.dispatch("registers")
    assert cli.dispatch("state")
    assert cli.dispatch("stop")
    assert cli.device.state == DeviceState.READY

    assert cli.dispatch("inject_fault EFFICIENCY_ANOMALY")
    assert cli.device.state == DeviceState.FAULT
    assert cli.device.read_register(Register.FAULT_CODE) == int(FaultCode.EFFICIENCY_ANOMALY)
    assert cli.dispatch("reset_faults")
    assert cli.device.state == DeviceState.READY
    assert cli.dispatch("inject_fault NOT_A_FAULT")  # reported, does not crash

    # Error handling: bad commands don't crash the loop
    assert cli.dispatch("set NOT_A_REGISTER 1")
    assert cli.dispatch("get SPEED_RPM extra_arg")  # malformed: just prints unknown
    assert cli.dispatch("nonsense")

    # quit returns False
    assert not cli.dispatch("quit")

    print("  ✓ CLI Commands tests passed")
    return True


def test_repository_with_mock():
    """Test DB repository against a mocked connection"""
    print("Testing Device Repository (mocked DB)...")

    from db.scripts.emec_device_repository import EMECDeviceRepository

    db = mock.MagicMock()
    db.execute_query.side_effect = [
        [{'device_id': 'dev-uuid'}],    # register_device
        [{'session_id': 'sess-uuid'}],  # start_session
        [{'fault_id': 'fault-uuid'}],   # record_fault
    ]
    db.execute_command.return_value = 1

    # Telemetry bulk insert path uses raw connection
    conn = mock.MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.rowcount = 2
    db.get_connection.return_value = conn

    repo = EMECDeviceRepository(db, device_name='test-device')
    device_id = repo.register_device(params={'rated_power': 5000.0})
    assert device_id == 'dev-uuid'

    session_id = repo.start_session({'load_torque_setpoint': 10.0})
    assert session_id == 'sess-uuid'

    samples = [
        {'time': 0.0, 'speed_rpm': 0.0, 'torque': 0.0},
        {'time': 0.1, 'speed_rpm': 100.0, 'torque': 5.0},
    ]
    repo.end_session(session_id, {'avg_efficiency': 85.0}, samples)
    assert cursor.executemany.called, "Telemetry must be bulk-inserted"

    fault_id = repo.record_fault(session_id, 1, "Over-current test")
    assert fault_id == 'fault-uuid'

    # Env-based factory degrades gracefully without connection string
    from db.scripts.emec_device_repository import create_repository_from_env
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ.pop('NEON_DATABASE_URL', None)
        assert create_repository_from_env() is None

    print("  ✓ Device Repository (mocked DB) tests passed")
    return True


def test_device_repository_integration():
    """Test device hooks calling the repository sink"""
    print("Testing Device-Repository Integration...")

    device = VirtualHardwareDevice(telemetry_decimation=10)
    repo = mock.MagicMock()
    repo.start_session.return_value = 'sess-1'
    device.repository = repo

    device.power_on()
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0)
    device.start()
    device.run(0.02)
    device.stop()

    repo.start_session.assert_called_once()
    repo.end_session.assert_called_once()
    args = repo.end_session.call_args[0]
    assert args[0] == 'sess-1'
    assert isinstance(args[1], dict) and isinstance(args[2], list)
    assert 'duration_s' in args[1]
    assert repo.end_session.call_args.kwargs['status'] == 'stopped'

    # A protection trip closes the session as faulted and stores sim_time
    repo3 = mock.MagicMock()
    repo3.start_session.return_value = 'sess-fault'
    device3 = VirtualHardwareDevice(repository=repo3, telemetry_decimation=10)
    device3.power_on()
    device3.start()
    device3.inject_fault(FaultCode.OVER_CURRENT, "injected over-current")
    repo3.record_fault.assert_called_once()
    fault_args = repo3.record_fault.call_args
    assert fault_args.args[0] == 'sess-fault'
    assert fault_args.args[1] == int(FaultCode.OVER_CURRENT)
    assert fault_args.kwargs['sim_time'] == device3.engine.current_time
    assert repo3.end_session.call_args.kwargs['status'] == 'faulted'

    # Repository errors never break the device
    repo2 = mock.MagicMock()
    repo2.start_session.side_effect = RuntimeError("db down")
    device2 = VirtualHardwareDevice(repository=repo2)
    device2.power_on()
    device2.start()
    device2.run(0.01)
    device2.stop()
    assert device2.state == DeviceState.READY

    print("  ✓ Device-Repository Integration tests passed")
    return True


def test_repository_autowire():
    """Persistence attaches only when NEON_DATABASE_URL is set, and never raises"""
    print("Testing Repository Autowire...")

    os.environ.pop('NEON_DATABASE_URL', None)
    device = VirtualHardwareDevice()
    assert device.repository is None

    explicit = object()
    with mock.patch.dict(os.environ, {'NEON_DATABASE_URL': 'postgresql://example.invalid/db'}):
        device = VirtualHardwareDevice(repository=explicit)
        assert device.repository is explicit

        with mock.patch(
            'db.scripts.emec_device_repository.create_repository_from_env',
            return_value='sink',
        ) as factory:
            device = VirtualHardwareDevice()
            assert device.repository == 'sink'
            factory.assert_called_once()

        with mock.patch(
            'db.scripts.emec_device_repository.create_repository_from_env',
            side_effect=RuntimeError('db down'),
        ):
            device = VirtualHardwareDevice()
            assert device.repository is None
            assert device.state == DeviceState.OFF

    print("  ✓ Repository Autowire tests passed")
    return True


def test_websocket_stream():
    """WS /stream upgrades and pushes one telemetry text frame"""
    print("Testing WebSocket Stream...")

    import socket
    import base64
    import struct

    from emec.device.server import serve

    device = VirtualHardwareDevice()
    device.power_on()
    server, _thread = serve(device, host='127.0.0.1', port=0, background=True)
    port = server.server_address[1]
    key = base64.b64encode(b'arc-halo-emec-ws!!').decode('ascii')

    try:
        sock = socket.create_connection(('127.0.0.1', port), timeout=2.0)
        request = (
            f"GET /stream?rate_hz=50 HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        sock.sendall(request.encode('ascii'))
        sock.settimeout(2.0)
        buffer = b''
        while b'\r\n\r\n' not in buffer:
            chunk = sock.recv(4096)
            assert chunk, "WebSocket handshake closed early"
            buffer += chunk
        header, rest = buffer.split(b'\r\n\r\n', 1)
        status_line = header.split(b'\r\n', 1)[0].decode('ascii')
        assert '101' in status_line, f"Expected 101 Switching Protocols, got {status_line}"
        assert b'Sec-WebSocket-Accept' in header

        frame = rest
        while len(frame) < 2:
            frame += sock.recv(4096)
        length = frame[1] & 0x7F
        offset = 2
        if length == 126:
            while len(frame) < 4:
                frame += sock.recv(4096)
            length = struct.unpack('!H', frame[2:4])[0]
            offset = 4
        while len(frame) < offset + length:
            frame += sock.recv(4096)
        payload = json.loads(frame[offset:offset + length].decode('utf-8'))
        assert payload['state'] == 'READY'
        assert 'fault_code' in payload
        sock.close()
        # Let the handler observe the disconnect before shutdown.
        import time
        time.sleep(0.15)
    finally:
        server.shutdown()
        server.server_close()

    print("  ✓ WebSocket Stream tests passed")
    return True


def run_all_tests():
    """Run all device tests"""
    print("\n" + "=" * 70)
    print("Virtual Hardware Device Test Suite")
    print("=" * 70 + "\n")

    tests = [
        test_lifecycle_transitions,
        test_register_validation,
        test_control_word,
        test_fault_trip_and_latch,
        test_fault_reset,
        test_efficiency_anomaly,
        test_running_setpoint_interlock,
        test_estop,
        test_setpoint_binding,
        test_telemetry_recorder,
        test_device_run_and_readback,
        test_server_endpoints,
        test_cli_commands,
        test_repository_with_mock,
        test_device_repository_integration,
        test_repository_autowire,
        test_websocket_stream,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
