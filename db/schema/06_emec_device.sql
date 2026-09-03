-- Arc-Halo EMEC - Virtual Hardware Device Schema
-- Part 6: Device registry, run sessions, telemetry, and fault log
-- for the EMEC virtual hardware device layer (emec/device/).

-- EMEC Devices Table
-- Registry of virtual hardware device instances
CREATE TABLE IF NOT EXISTS emec_devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_name VARCHAR(255) NOT NULL UNIQUE,
    device_type VARCHAR(100) NOT NULL DEFAULT 'virtual_induction_motor',
    firmware_version VARCHAR(50) NOT NULL,
    params JSONB NOT NULL DEFAULT '{}'::jsonb, -- Engine/protection parameters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'registered', -- registered, active, decommissioned
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create index for device lookups
CREATE INDEX IF NOT EXISTS idx_emec_devices_name ON emec_devices(device_name);
CREATE INDEX IF NOT EXISTS idx_emec_devices_status ON emec_devices(status);

-- EMEC Device Sessions Table
-- One record per start → stop (or start → fault) run of a device
CREATE TABLE IF NOT EXISTS emec_device_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES emec_devices(device_id) ON DELETE CASCADE,
    setpoints JSONB NOT NULL DEFAULT '{}'::jsonb, -- voltage/frequency/load setpoints
    metrics JSONB DEFAULT '{}'::jsonb, -- performance metrics at session end
    status VARCHAR(50) DEFAULT 'running', -- running, stopped, faulted
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for session queries
CREATE INDEX IF NOT EXISTS idx_emec_sessions_device ON emec_device_sessions(device_id);
CREATE INDEX IF NOT EXISTS idx_emec_sessions_status ON emec_device_sessions(status);
CREATE INDEX IF NOT EXISTS idx_emec_sessions_start_time ON emec_device_sessions(start_time);

-- EMEC Telemetry Table
-- Time-series operating-point samples captured during a session
CREATE TABLE IF NOT EXISTS emec_telemetry (
    telemetry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES emec_device_sessions(session_id) ON DELETE CASCADE,
    sim_time DOUBLE PRECISION NOT NULL, -- Simulation clock [s]
    speed_rpm DOUBLE PRECISION,
    torque DOUBLE PRECISION,
    stator_current_a DOUBLE PRECISION,
    stator_current_b DOUBLE PRECISION,
    stator_current_c DOUBLE PRECISION,
    power_mechanical DOUBLE PRECISION,
    power_electrical DOUBLE PRECISION,
    efficiency DOUBLE PRECISION,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for telemetry queries
CREATE INDEX IF NOT EXISTS idx_emec_telemetry_session ON emec_telemetry(session_id);
CREATE INDEX IF NOT EXISTS idx_emec_telemetry_sim_time ON emec_telemetry(session_id, sim_time);

-- EMEC Fault Log Table
-- Latched fault events recorded during sessions
CREATE TABLE IF NOT EXISTS emec_fault_log (
    fault_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES emec_device_sessions(session_id) ON DELETE CASCADE,
    fault_code INTEGER NOT NULL, -- Matches emec.device.FaultCode
    message TEXT NOT NULL,
    sim_time DOUBLE PRECISION, -- Simulation time at trip [s]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fault log queries
CREATE INDEX IF NOT EXISTS idx_emec_fault_log_session ON emec_fault_log(session_id);
CREATE INDEX IF NOT EXISTS idx_emec_fault_log_code ON emec_fault_log(fault_code);

-- View: Device Session Overview
CREATE OR REPLACE VIEW v_emec_device_sessions AS
SELECT
    s.session_id,
    d.device_name,
    s.status,
    s.setpoints,
    s.metrics,
    s.start_time,
    s.end_time,
    COUNT(t.telemetry_id) AS telemetry_samples,
    COUNT(f.fault_id) AS fault_count
FROM emec_device_sessions s
JOIN emec_devices d ON s.device_id = d.device_id
LEFT JOIN emec_telemetry t ON t.session_id = s.session_id
LEFT JOIN emec_fault_log f ON f.session_id = s.session_id
GROUP BY s.session_id, d.device_name, s.status, s.setpoints, s.metrics,
         s.start_time, s.end_time
ORDER BY s.start_time DESC;

COMMENT ON VIEW v_emec_device_sessions IS 'Overview of EMEC device run sessions with telemetry and fault counts';
