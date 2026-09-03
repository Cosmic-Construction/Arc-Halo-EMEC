"""
Virtual Hardware Device - Command Line Interface

Interactive and scripted control of the virtual hardware device through its
register map, mirroring how a host would drive a physical motor drive.

Usage:
    python -m emec.device.cli            # interactive shell
    python -m emec.device.cli --demo     # scripted demo sequence
"""

import argparse
import shlex

from .device import (
    VirtualHardwareDevice,
    RegisterAccessError,
    RegisterValueError,
    InvalidStateError,
)
from .registers import Register


HELP_TEXT = """\
Commands:
  power_on | power_off        Energize / de-energize the device
  start | stop                Start / stop the drive
  estop                       Emergency stop (unconditional)
  reset_faults                Clear latched faults (when condition cleared)
  reset                       Full device reset
  set <REGISTER> <value>      Write setpoint (e.g. set LOAD_TORQUE_SETPOINT 10)
  get <REGISTER>              Read a register (e.g. get SPEED_RPM)
  registers                   List all registers with values
  run <seconds> [dt]          Run simulation for a duration
  telemetry [n]               Show the last n telemetry samples
  faults                      Show fault history
  state                       Show lifecycle state and status word
  help                        Show this help
  quit                        Exit
"""


class DeviceCLI:
    """Interactive command-line interface to a VirtualHardwareDevice"""

    def __init__(self, device: VirtualHardwareDevice = None):
        self.device = device or VirtualHardwareDevice()

    # ------------------------- command handlers -------------------------

    def cmd_power_on(self):
        print(f"state -> {self.device.power_on().value}")

    def cmd_power_off(self):
        print(f"state -> {self.device.power_off().value}")

    def cmd_start(self):
        print(f"state -> {self.device.start().value}")

    def cmd_stop(self):
        print(f"state -> {self.device.stop().value}")

    def cmd_estop(self):
        print(f"state -> {self.device.e_stop().value}")

    def cmd_reset(self):
        print(f"state -> {self.device.reset().value}")

    def cmd_reset_faults(self):
        cleared = self.device.reset_faults()
        print(f"faults cleared: {cleared}; state -> {self.device.state.value}")

    def cmd_set(self, name: str, value: str):
        self.device.write_register(name, float(value))
        print(f"{name} <- {value}")

    def cmd_get(self, name: str):
        print(f"{name} = {self.device.read_register(name)}")

    def cmd_registers(self):
        for reg in Register:
            try:
                value = self.device.read_register(reg)
                print(f"  {reg.name:24s} = {value}")
            except RegisterAccessError:
                print(f"  {reg.name:24s}   (write-only)")

    def cmd_run(self, duration: str, dt: str = None):
        dt_val = float(dt) if dt is not None else None
        cycles = self.device.run(float(duration), dt_val)
        print(f"ran {cycles} cycles; state -> {self.device.state.value}")

    def cmd_telemetry(self, n: str = "5"):
        for sample in self.device.telemetry.snapshot(int(n)):
            print("  " + ", ".join(f"{k}={v:.4g}" for k, v in sample.items()))

    def cmd_faults(self):
        if not self.device.faults.history:
            print("  no faults recorded")
        for fault in self.device.faults.history:
            print(f"  t={fault.time:.4f}s [{fault.code.name}] {fault.message}")

    def cmd_state(self):
        print(f"  state:       {self.device.state.value}")
        print(f"  status word: {self.device.read_register(Register.STATUS_WORD):#06x}")
        print(f"  fault code:  {self.device.read_register(Register.FAULT_CODE)}")

    # ------------------------- dispatch -------------------------

    def dispatch(self, line: str) -> bool:
        """
        Execute one command line. Returns False to exit.
        Raises nothing: user errors are reported and swallowed.
        """
        parts = shlex.split(line)
        if not parts:
            return True
        cmd, args = parts[0].lower(), parts[1:]

        try:
            if cmd in ('quit', 'exit'):
                return False
            elif cmd == 'help':
                print(HELP_TEXT)
            elif cmd == 'power_on':
                self.cmd_power_on()
            elif cmd == 'power_off':
                self.cmd_power_off()
            elif cmd == 'start':
                self.cmd_start()
            elif cmd == 'stop':
                self.cmd_stop()
            elif cmd == 'estop':
                self.cmd_estop()
            elif cmd == 'reset':
                self.cmd_reset()
            elif cmd == 'reset_faults':
                self.cmd_reset_faults()
            elif cmd == 'set' and len(args) == 2:
                self.cmd_set(args[0].upper(), args[1])
            elif cmd == 'get' and len(args) == 1:
                self.cmd_get(args[0].upper())
            elif cmd == 'registers':
                self.cmd_registers()
            elif cmd == 'run' and 1 <= len(args) <= 2:
                self.cmd_run(*args)
            elif cmd == 'telemetry':
                self.cmd_telemetry(*args) if args else self.cmd_telemetry()
            elif cmd == 'faults':
                self.cmd_faults()
            elif cmd == 'state':
                self.cmd_state()
            else:
                print(f"Unknown or malformed command: {line!r} (try 'help')")
        except (RegisterAccessError, RegisterValueError, InvalidStateError,
                ValueError) as e:
            print(f"Error: {e}")
        return True

    def loop(self):
        """Interactive REPL"""
        print("Arc-Halo EMEC Virtual Hardware Device CLI (type 'help')")
        while True:
            try:
                line = input("device> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not self.dispatch(line):
                break


def run_demo(cli: DeviceCLI):
    """Scripted demo: power on, load, run, read telemetry, estop"""
    script = [
        "power_on",
        "set LOAD_TORQUE_SETPOINT 10",
        "set VOLTAGE_SETPOINT 400",
        "start",
        "run 0.1",
        "get SPEED_RPM",
        "get TORQUE",
        "get EFFICIENCY",
        "telemetry 3",
        "stop",
        "estop",
        "faults",
        "power_on",
        "state",
    ]
    for line in script:
        print(f"device> {line}")
        cli.dispatch(line)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m emec.device.cli",
        description="Arc-Halo EMEC virtual hardware device CLI",
    )
    parser.add_argument('--demo', action='store_true',
                        help='run a scripted demo sequence and exit')
    args = parser.parse_args(argv)

    cli = DeviceCLI()
    if args.demo:
        run_demo(cli)
    else:
        cli.loop()


if __name__ == '__main__':
    main()
