"""
Arc-Halo EMEC - Virtual Hardware Device Repository

Persistence layer for the EMEC virtual hardware device: device registry,
run sessions, telemetry samples, and fault events. Patterned on
ModelRepository in db_utils.py; psycopg2 is imported lazily so the module
(and the emec device layer) work without the database stack installed.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Matches emec/device/__init__.py / emec package version
DEVICE_FIRMWARE_VERSION = "2.1.0"


class EMECDeviceRepository:
    """
    Repository for EMEC virtual hardware device persistence.

    Implements the sink protocol expected by VirtualHardwareDevice:
        start_session(setpoints) -> session_id
        end_session(session_id, metrics, samples)
        record_fault(session_id, code, message)
    """

    def __init__(self, db_connection, device_name: str = "emec-virtual-device-0"):
        """
        Args:
            db_connection: NeonDBConnection (or compatible) instance
            device_name: Registry name of the device (created on first use)
        """
        self.db = db_connection
        self.device_name = device_name
        self._device_id: Optional[str] = None

    # ------------------------- device registry -------------------------

    def register_device(self,
                        device_name: Optional[str] = None,
                        params: Optional[Dict[str, Any]] = None,
                        firmware_version: str = DEVICE_FIRMWARE_VERSION) -> str:
        """
        Register a device (idempotent on device_name).

        Returns:
            UUID of the device record
        """
        name = device_name or self.device_name
        query = """
            INSERT INTO emec_devices (device_name, firmware_version, params, status)
            VALUES (%s, %s, %s::jsonb, 'registered')
            ON CONFLICT (device_name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING device_id::text
        """
        result = self.db.execute_query(
            query, (name, firmware_version, json.dumps(params or {}))
        )
        self._device_id = result[0]['device_id']
        return self._device_id

    def get_device(self, device_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get device by name"""
        query = "SELECT * FROM emec_devices WHERE device_name = %s"
        results = self.db.execute_query(query, (device_name or self.device_name,))
        return results[0] if results else None

    def _ensure_device_id(self) -> str:
        if self._device_id is None:
            device = self.get_device()
            self._device_id = (device['device_id'] if device
                               else self.register_device())
        return str(self._device_id)

    # ------------------------- sessions -------------------------

    def start_session(self, setpoints: Dict[str, Any]) -> str:
        """
        Open a run session for the device.

        Args:
            setpoints: Active setpoints at start (voltage/frequency/load)

        Returns:
            UUID of the session
        """
        device_id = self._ensure_device_id()
        query = """
            INSERT INTO emec_device_sessions (device_id, setpoints, status)
            VALUES (%s::uuid, %s::jsonb, 'running')
            RETURNING session_id::text
        """
        result = self.db.execute_query(query, (device_id, json.dumps(setpoints)))
        return result[0]['session_id']

    def end_session(self,
                    session_id: str,
                    metrics: Optional[Dict[str, Any]] = None,
                    samples: Optional[List[Dict[str, float]]] = None,
                    status: str = 'stopped'):
        """
        Close a run session, storing final metrics and telemetry samples.

        Args:
            session_id: Session UUID from start_session()
            metrics: Performance metrics (from get_performance_metrics())
            samples: Telemetry samples (from TelemetryRecorder.snapshot())
            status: Final status ('stopped' or 'faulted')
        """
        self.store_telemetry(session_id, samples or [])
        query = """
            UPDATE emec_device_sessions
            SET metrics = %s::jsonb, status = %s, end_time = CURRENT_TIMESTAMP
            WHERE session_id = %s::uuid
        """
        self.db.execute_command(query, (json.dumps(metrics or {}), status, session_id))

    # ------------------------- telemetry -------------------------

    def store_telemetry(self, session_id: str, samples: List[Dict[str, float]]) -> int:
        """
        Bulk-insert telemetry samples for a session.

        Returns:
            Number of samples stored
        """
        if not samples:
            return 0
        query = """
            INSERT INTO emec_telemetry
                (session_id, sim_time, speed_rpm, torque,
                 stator_current_a, stator_current_b, stator_current_c,
                 power_mechanical, power_electrical, efficiency)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        rows = [
            (
                session_id,
                s.get('time', 0.0),
                s.get('speed_rpm', 0.0),
                s.get('torque', 0.0),
                s.get('stator_current_a', 0.0),
                s.get('stator_current_b', 0.0),
                s.get('stator_current_c', 0.0),
                s.get('power_mechanical', 0.0),
                s.get('power_electrical', 0.0),
                s.get('efficiency', 0.0),
            )
            for s in samples
        ]
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, rows)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Error storing telemetry: {e}")
            raise
        finally:
            self.db.return_connection(conn)

    def get_telemetry(self, session_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch telemetry samples for a session (oldest first)"""
        query = """
            SELECT * FROM emec_telemetry
            WHERE session_id = %s::uuid
            ORDER BY sim_time ASC
            LIMIT %s
        """
        return self.db.execute_query(query, (session_id, limit))

    # ------------------------- faults -------------------------

    def record_fault(self, session_id: str, code: int, message: str,
                     sim_time: Optional[float] = None) -> str:
        """
        Record a latched fault event.

        Returns:
            UUID of the fault record
        """
        query = """
            INSERT INTO emec_fault_log (session_id, fault_code, message, sim_time)
            VALUES (%s::uuid, %s, %s, %s)
            RETURNING fault_id::text
        """
        result = self.db.execute_query(query, (session_id, code, message, sim_time))
        return result[0]['fault_id']

    def get_faults(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetch fault events for a session"""
        query = """
            SELECT * FROM emec_fault_log
            WHERE session_id = %s::uuid
            ORDER BY created_at ASC
        """
        return self.db.execute_query(query, (session_id,))


def create_repository_from_env(device_name: str = "emec-virtual-device-0",
                               ) -> Optional[EMECDeviceRepository]:
    """
    Build a repository from the NEON_DATABASE_URL environment variable.

    Returns None when the database stack is unavailable (psycopg2 missing
    or no connection string configured) so the device layer degrades
    gracefully to in-memory-only operation.
    """
    connection_string = os.getenv('NEON_DATABASE_URL')
    if not connection_string:
        return None
    try:
        from .db_utils import NeonDBConnection
    except ImportError:
        try:
            from db.scripts.db_utils import NeonDBConnection
        except ImportError:
            logger.warning("psycopg2/db_utils unavailable; device persistence disabled")
            return None
    return EMECDeviceRepository(
        NeonDBConnection(connection_string), device_name=device_name
    )
