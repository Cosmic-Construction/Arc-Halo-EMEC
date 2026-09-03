"""
Virtual Hardware Device - Examples

End-to-end demonstrations of the virtual hardware device layer:
1. Startup transient driven through the register map
2. Load-step response via setpoint changes while running
3. Fault trip and recovery (over-load → over-torque protection)
4. Telemetry capture and CSV export
5. HTTP/SSE server (started in-process, queried over HTTP)

Run: python -m emec.examples_device
"""

import json
import os
import tempfile
import urllib.request

from emec.device import (
    VirtualHardwareDevice,
    DeviceState,
    Register,
    FaultCode,
)


def example_startup_transient():
    """Power on and start the device, driving it purely through registers"""
    print("\n" + "=" * 70)
    print("Example 1: Startup Transient via Register Map")
    print("=" * 70)

    device = VirtualHardwareDevice(telemetry_decimation=100)
    device.power_on()
    device.write_register(Register.VOLTAGE_SETPOINT, 400.0)
    device.write_register(Register.FREQUENCY_SETPOINT, 50.0)
    device.write_register(Register.LOAD_TORQUE_SETPOINT, 10.0)
    device.start()
    device.run(0.3)

    print(f"  State:      {device.read_register(Register.DEVICE_STATE)}")
    print(f"  Speed:      {device.read_register(Register.SPEED_RPM):.1f} rpm")
    print(f"  Torque:     {device.read_register(Register.TORQUE):.2f} N·m")
    print(f"  Efficiency: {device.read_register(Register.EFFICIENCY):.1f} %")
    device.stop()


def example_load_step():
    """Change the load torque setpoint mid-run and observe the response"""
    print("\n" + "=" * 70)
    print("Example 2: Load-Step Response")
    print("=" * 70)

    device = VirtualHardwareDevice(telemetry_decimation=100)
    device.power_on()
    device.write_register("LOAD_TORQUE_SETPOINT", 5.0)
    device.start()
    device.run(0.3)
    speed_before = device.read_register("SPEED_RPM")

    device.write_register("LOAD_TORQUE_SETPOINT", 15.0)
    device.run(0.3)
    speed_after = device.read_register("SPEED_RPM")

    print(f"  Speed before load step: {speed_before:.1f} rpm")
    print(f"  Speed after load step:  {speed_after:.1f} rpm")
    device.stop()


def example_fault_trip_recovery():
    """Overload the device until protection trips, then clear the fault"""
    print("\n" + "=" * 70)
    print("Example 3: Fault Trip and Recovery")
    print("=" * 70)

    device = VirtualHardwareDevice()
    device.power_on()
    # Load far beyond the over-torque limit (100 N·m)
    device.write_register("LOAD_TORQUE_SETPOINT", 200.0)
    device.start()
    device.run(1.0)

    print(f"  State after overload: {device.state.value}")
    print(f"  Fault code: {FaultCode(device.read_register('FAULT_CODE')).name}")
    print(f"  Fault: {device.faults.history[-1].message}")

    # Fault is latched: start is inhibited until reset
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0)
    device.reset()
    device.power_on()
    cleared = device.reset_faults()
    print(f"  After reset, faults cleared: {cleared}; state: {device.state.value}")


def example_telemetry_export():
    """Capture telemetry and export to CSV"""
    print("\n" + "=" * 70)
    print("Example 4: Telemetry Capture and CSV Export")
    print("=" * 70)

    device = VirtualHardwareDevice(telemetry_decimation=50)
    device.power_on()
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0)
    device.start()
    device.run(0.2)
    device.stop()

    samples = device.telemetry.snapshot()
    print(f"  Recorded {len(samples)} telemetry samples")
    if samples:
        last = samples[-1]
        print(f"  Latest: t={last['time']:.3f}s, "
              f"speed={last['speed_rpm']:.1f} rpm, torque={last['torque']:.2f} N·m")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'telemetry.csv')
        device.telemetry.export_csv(path)
        with open(path) as f:
            header = f.readline().strip()
        print(f"  CSV written to {path} (header: {header})")


def example_http_server():
    """Serve the device over HTTP and query it with stdlib clients"""
    print("\n" + "=" * 70)
    print("Example 5: HTTP/SSE Server (in-process)")
    print("=" * 70)

    from emec.device.server import serve

    device = VirtualHardwareDevice()
    server, _thread = serve(device, host='127.0.0.1', port=18099, background=True)
    try:
        base = 'http://127.0.0.1:18099'

        def post(path, payload=None):
            data = json.dumps(payload or {}).encode()
            req = urllib.request.Request(base + path, data=data,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())

        def get(path):
            with urllib.request.urlopen(base + path) as resp:
                return json.loads(resp.read())

        print(f"  POST /command/power_on -> {post('/command/power_on')}")
        print(f"  POST /registers/LOAD_TORQUE_SETPOINT -> "
              f"{post('/registers/LOAD_TORQUE_SETPOINT', {'value': 10.0})}")
        print(f"  POST /command/start -> {post('/command/start')}")
        device.run(0.2)
        print(f"  POST /command/stop -> {post('/command/stop')}")
        state = get('/state')
        print(f"  GET /state -> {state}")
        speed = get('/registers/SPEED_RPM')
        print(f"  GET /registers/SPEED_RPM -> {speed['value']:.1f} rpm")
    finally:
        server.shutdown()
        server.server_close()


def run_all_examples():
    examples = [
        example_startup_transient,
        example_load_step,
        example_fault_trip_recovery,
        example_telemetry_export,
        example_http_server,
    ]
    for example in examples:
        example()

    print("\n" + "=" * 70)
    print(f"All {len(examples)} device examples completed")
    print("=" * 70)


if __name__ == '__main__':
    run_all_examples()
