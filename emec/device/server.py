"""
Virtual Hardware Device - HTTP/SSE Server

Stdlib-only host API exposing the device register map over HTTP. Telemetry
is streamed on GET /stream: a WebSocket upgrade (WS /stream) when the client
requests one, otherwise Server-Sent Events. No third-party dependencies.

Endpoints:
    GET  /registers                 -> all registers with metadata + values
    GET  /registers/{name}          -> single register value
    POST /registers/{name}          -> write register, JSON body {"value": x}
    GET  /telemetry?last_n=N        -> telemetry samples
    GET  /stream?rate_hz=R          -> WS upgrade, else SSE (R events/s, max 50)
    POST /command/{cmd}             -> power_on|power_off|start|stop|reset|estop
    GET  /state                     -> lifecycle state, status word, fault code

Binds to localhost by default; pass host explicitly to expose on a network
interface (only do so on trusted networks — there is no authentication).
"""

import base64
import hashlib
import json
import re
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from .device import (
    VirtualHardwareDevice,
    RegisterAccessError,
    RegisterValueError,
    InvalidStateError,
)
from .registers import Register, REGISTER_MAP

# Upper bound for SSE/WebSocket stream rate to avoid runaway loops
MAX_STREAM_RATE_HZ = 50.0
# Upper bound for telemetry samples served per request
MAX_TELEMETRY_SAMPLES = 100000
# RFC 6455 magic GUID used only to compute Sec-WebSocket-Accept
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_COMMANDS = {
    'power_on': lambda d: d.power_on(),
    'power_off': lambda d: d.power_off(),
    'start': lambda d: d.start(),
    'stop': lambda d: d.stop(),
    'reset': lambda d: d.reset(),
    'estop': lambda d: d.e_stop(),
}

_JSON_HEADERS = {'Content-Type': 'application/json'}


class DeviceRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler exposing the device register map"""

    # Set by create_server(); the shared device instance
    device: VirtualHardwareDevice = None
    simulation_dt: float = 1e-4

    # Silence default logging to stderr; subclasses/tests can re-enable
    def log_message(self, format, *args):
        pass

    # ------------------------- helpers -------------------------

    def _send_json(self, payload, status: int = 200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str):
        self._send_json({'error': message}, status=status)

    def _read_json_body(self) -> Optional[dict]:
        length = int(self.headers.get('Content-Length') or 0)
        if length <= 0:
            return None
        try:
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return None

    @staticmethod
    def _register_payload(register: Register) -> dict:
        info = REGISTER_MAP[register]
        return {
            'name': register.name,
            'address': register.value,
            'access': info.access.value,
            'unit': info.unit,
            'description': info.description,
            'range': list(info.value_range) if info.value_range else None,
        }

    def _state_payload(self) -> dict:
        d = self.device
        return {
            'state': d.state.value,
            'status_word': d.read_register(Register.STATUS_WORD),
            'fault_code': d.read_register(Register.FAULT_CODE),
            'simulation_time': d.read_register(Register.SIMULATION_TIME),
        }

    # ------------------------- GET -------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        query = parse_qs(parsed.query)

        if path == '/registers':
            out = {}
            for reg in Register:
                entry = self._register_payload(reg)
                if REGISTER_MAP[reg].access.value != 'wo':
                    try:
                        entry['value'] = self.device.read_register(reg)
                    except Exception:
                        entry['value'] = None
                out[reg.name] = entry
            self._send_json(out)
            return

        m = re.fullmatch(r'/registers/([A-Z_]+)', path)
        if m:
            name = m.group(1)
            try:
                value = self.device.read_register(name)
                reg = Register[name]
                payload = self._register_payload(reg)
                payload['value'] = value
                self._send_json(payload)
            except (RegisterAccessError, KeyError) as e:
                self._send_error_json(404, str(e))
            return

        if path == '/telemetry':
            last_n = self._parse_int(query, 'last_n', default=None)
            if last_n is not None:
                last_n = min(last_n, MAX_TELEMETRY_SAMPLES)
            self._send_json({'samples': self.device.telemetry.snapshot(last_n)})
            return

        if path == '/state':
            self._send_json(self._state_payload())
            return

        if path == '/stream':
            rate = self._parse_float(query, 'rate_hz', default=10.0)
            rate = max(0.1, min(rate, MAX_STREAM_RATE_HZ))
            if self._websocket_requested():
                self._handle_websocket(rate)
            else:
                self._handle_stream(rate)
            return

        self._send_error_json(404, f"Unknown path: {path}")

    # ------------------------- POST -------------------------

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        m = re.fullmatch(r'/registers/([A-Z_]+)', path)
        if m:
            name = m.group(1)
            body = self._read_json_body()
            if body is None or 'value' not in body:
                self._send_error_json(400, "Body must be JSON: {\"value\": <number>}")
                return
            try:
                self.device.write_register(name, body['value'])
                self._send_json({'ok': True, 'register': name,
                                 'state': self.device.state.value})
            except RegisterAccessError as e:
                self._send_error_json(404, str(e))
            except (RegisterValueError, InvalidStateError) as e:
                self._send_error_json(400, str(e))
            return

        m = re.fullmatch(r'/command/([a-z_]+)', path)
        if m:
            cmd = m.group(1)
            if cmd not in _COMMANDS:
                self._send_error_json(404, f"Unknown command: {cmd}")
                return
            try:
                state = _COMMANDS[cmd](self.device)
                self._send_json({'ok': True, 'state': state.value})
            except InvalidStateError as e:
                self._send_error_json(409, str(e))
            return

        self._send_error_json(404, f"Unknown path: {path}")

    # ------------------------- telemetry stream -------------------------

    def _websocket_requested(self) -> bool:
        upgrade = (self.headers.get('Upgrade') or '').lower()
        return 'websocket' in upgrade

    def _handle_stream(self, rate_hz: float):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        interval = 1.0 / rate_hz
        try:
            while True:
                data = f"data: {json.dumps(self._stream_payload())}\n\n".encode('utf-8')
                self.wfile.write(data)
                self.wfile.flush()
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected

    def _handle_websocket(self, rate_hz: float):
        """
        RFC 6455 text-frame telemetry stream (WS /stream).

        Server-push only: client frames are not interpreted as commands.
        """
        key = (self.headers.get('Sec-WebSocket-Key') or '').strip()
        if not key:
            self._send_error_json(400, "Missing Sec-WebSocket-Key")
            return

        # RFC 6455 requires SHA-1 for Sec-WebSocket-Accept. This is the
        # protocol handshake, not a password or integrity hash.
        accept = base64.b64encode(
            hashlib.sha1((key + _WS_GUID).encode('ascii')).digest()
        ).decode('ascii')
        self.protocol_version = 'HTTP/1.1'
        self.send_response(101, 'Switching Protocols')
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', accept)
        self.end_headers()

        interval = 1.0 / rate_hz
        try:
            while True:
                payload = json.dumps(self._stream_payload()).encode('utf-8')
                self.wfile.write(_ws_text_frame(payload))
                self.wfile.flush()
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Client disconnected

    def _stream_payload(self) -> dict:
        return {
            'state': self.device.state.value,
            'fault_code': self.device.read_register(Register.FAULT_CODE),
            'sample': self.device.telemetry.latest(),
        }

    # ------------------------- parsing -------------------------

    @staticmethod
    def _parse_int(query: dict, key: str, default: Optional[int]) -> Optional[int]:
        try:
            return int(query[key][0])
        except (KeyError, IndexError, ValueError):
            return default

    @staticmethod
    def _parse_float(query: dict, key: str, default: float) -> float:
        try:
            return float(query[key][0])
        except (KeyError, IndexError, ValueError):
            return default


def _ws_text_frame(payload: bytes) -> bytes:
    """Encode an unmasked WebSocket text frame (server-to-client)."""
    n = len(payload)
    if n < 126:
        header = struct.pack('!BB', 0x81, n)
    elif n < 65536:
        header = struct.pack('!BBH', 0x81, 126, n)
    else:
        header = struct.pack('!BBQ', 0x81, 127, n)
    return header + payload


def create_server(device: VirtualHardwareDevice,
                  host: str = '127.0.0.1',
                  port: int = 8080) -> ThreadingHTTPServer:
    """
    Create (but do not start) the device HTTP server.

    Args:
        device: The VirtualHardwareDevice to expose
        host: Bind address; localhost by default. Only bind to non-local
              interfaces on trusted networks — there is no authentication.
        port: TCP port

    Returns:
        A ThreadingHTTPServer ready for serve_forever()
    """
    handler = type('BoundDeviceRequestHandler', (DeviceRequestHandler,), {
        'device': device,
    })
    return ThreadingHTTPServer((host, port), handler)


def serve(device: VirtualHardwareDevice,
          host: str = '127.0.0.1',
          port: int = 8080,
          background: bool = False) -> Tuple[ThreadingHTTPServer, Optional[threading.Thread]]:
    """
    Start the device HTTP server.

    Args:
        background: When True, serve in a daemon thread and return
                    immediately (server, thread). Otherwise blocks.

    Returns:
        (server, thread) — thread is None when blocking.
    """
    server = create_server(device, host, port)
    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return server, None
