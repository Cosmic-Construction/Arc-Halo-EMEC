"""
Virtual Hardware Device - Telemetry Recorder

Ring-buffer telemetry recorder capturing the device operating point each
cycle. Supports decimation (record every Nth sample), snapshots, and CSV
export. Fields mirror VirtualEngine.export_data().
"""

import csv
import io
from collections import deque
from typing import Dict, List, Optional

# Telemetry channels captured each cycle
TELEMETRY_FIELDS = (
    'time',
    'speed_rpm',
    'torque',
    'power_mechanical',
    'power_electrical',
    'efficiency',
    'stator_current_a',
    'stator_current_b',
    'stator_current_c',
)


class TelemetryRecorder:
    """
    Fixed-window ring buffer of telemetry samples.

    Args:
        capacity: Maximum number of retained samples (oldest dropped)
        decimation: Record every Nth call to record() (1 = every sample)
    """

    def __init__(self, capacity: int = 10000, decimation: int = 1):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if decimation < 1:
            raise ValueError("decimation must be >= 1")
        self.capacity = capacity
        self.decimation = decimation
        self._buffer: deque = deque(maxlen=capacity)
        self._tick = 0

    def record(self, sample: Dict[str, float]) -> bool:
        """
        Offer a telemetry sample. Records it when the decimation counter
        aligns. Returns True if the sample was stored.
        """
        self._tick += 1
        if self._tick % self.decimation != 0:
            return False
        self._buffer.append({k: sample.get(k, 0.0) for k in TELEMETRY_FIELDS})
        return True

    def snapshot(self, last_n: Optional[int] = None) -> List[Dict[str, float]]:
        """
        Return recorded samples (oldest first).

        Args:
            last_n: If given, only the most recent N samples.
        """
        samples = list(self._buffer)
        if last_n is not None:
            samples = samples[-last_n:]
        return samples

    def latest(self) -> Optional[Dict[str, float]]:
        """Return the most recent recorded sample, or None if empty"""
        return self._buffer[-1] if self._buffer else None

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self):
        """Drop all recorded samples"""
        self._buffer.clear()
        self._tick = 0

    def to_csv(self, last_n: Optional[int] = None) -> str:
        """Export recorded samples as CSV text"""
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=list(TELEMETRY_FIELDS))
        writer.writeheader()
        writer.writerows(self.snapshot(last_n))
        return out.getvalue()

    def export_csv(self, path: str, last_n: Optional[int] = None):
        """Write recorded samples to a CSV file"""
        with open(path, 'w', newline='') as f:
            f.write(self.to_csv(last_n))
