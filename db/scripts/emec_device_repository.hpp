#pragma once

// Persistence for the virtual hardware device: device registry, run sessions,
// telemetry samples, and fault events. Optional. A missing driver or a failed
// connection must not stop the drive.

#include "db/scripts/db_utils.hpp"
#include "emec/device/persistence.hpp"
#include "emec/json_lite.hpp"

#include <cstdlib>
#include <memory>
#include <string>

namespace emec {

inline constexpr const char* DEVICE_FIRMWARE_VERSION = "2.1.0";

inline std::string json_object_from_map(const std::map<std::string, double>& values) {
    Json object = Json::object();
    for (const auto& entry : values) {
        object.set(entry.first, Json::number(entry.second));
    }
    return object.dump();
}

inline std::string with_connect_timeout(std::string connection_string, int seconds = 5) {
    if (connection_string.find("connect_timeout=") != std::string::npos) {
        return connection_string;
    }
    if (connection_string.find("://") != std::string::npos) {
        connection_string += (connection_string.find('?') != std::string::npos ? "&" : "?");
        connection_string += "connect_timeout=" + std::to_string(seconds);
        return connection_string;
    }
    return connection_string + " connect_timeout=" + std::to_string(seconds);
}

class EMECDeviceRepository : public DevicePersistenceSink {
public:
    EMECDeviceRepository(std::shared_ptr<DbConnection> db, std::string device_name = "emec-virtual-device-0")
        : db_(std::move(db)), device_name_(std::move(device_name)) {}

    DbConnection& db() { return *db_; }
    const std::string& device_name() const { return device_name_; }

    std::string register_device(const std::string& params_json = "{}",
                                const std::string& firmware_version = DEVICE_FIRMWARE_VERSION,
                                std::optional<std::string> device_name = std::nullopt) {
        const std::string name = device_name.value_or(device_name_);
        const char* query =
            "INSERT INTO emec_devices (device_name, firmware_version, params, status) "
            "VALUES ($1, $2, $3::jsonb, 'registered') "
            "ON CONFLICT (device_name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP "
            "RETURNING device_id::text";
        auto rows = db_->execute_query(query, {name, firmware_version, params_json});
        device_id_ = rows.at(0).at("device_id");
        return device_id_;
    }

    std::optional<QueryRow> get_device(std::optional<std::string> device_name = std::nullopt) {
        auto rows = db_->execute_query("SELECT * FROM emec_devices WHERE device_name = $1",
                                       {device_name.value_or(device_name_)});
        if (rows.empty()) {
            return std::nullopt;
        }
        return rows[0];
    }

    std::string start_session(const std::map<std::string, double>& setpoints) override {
        const std::string device_id = ensure_device_id();
        const char* query =
            "INSERT INTO emec_device_sessions (device_id, setpoints, status) "
            "VALUES ($1::uuid, $2::jsonb, 'running') RETURNING session_id::text";
        auto rows = db_->execute_query(query, {device_id, json_object_from_map(setpoints)});
        return rows.at(0).at("session_id");
    }

    void end_session(const std::string& session_id,
                     const std::map<std::string, double>& metrics,
                     const std::vector<TelemetrySample>& samples,
                     const std::string& status = "stopped") override {
        store_telemetry(session_id, samples);
        const char* query =
            "UPDATE emec_device_sessions SET metrics = $1::jsonb, status = $2, end_time = CURRENT_TIMESTAMP "
            "WHERE session_id = $3::uuid";
        db_->execute_command(query, {json_object_from_map(metrics), status, session_id});
    }

    int store_telemetry(const std::string& session_id, const std::vector<TelemetrySample>& samples) {
        if (samples.empty()) {
            return 0;
        }
        const char* query =
            "INSERT INTO emec_telemetry (session_id, sim_time, speed_rpm, torque, "
            "stator_current_a, stator_current_b, stator_current_c, "
            "power_mechanical, power_electrical, efficiency) "
            "VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10)";
        std::vector<std::vector<std::string>> rows;
        rows.reserve(samples.size());
        for (const auto& sample : samples) {
            rows.push_back({session_id, std::to_string(sample.at("time")), std::to_string(sample.at("speed_rpm")),
                            std::to_string(sample.at("torque")), std::to_string(sample.at("stator_current_a")),
                            std::to_string(sample.at("stator_current_b")), std::to_string(sample.at("stator_current_c")),
                            std::to_string(sample.at("power_mechanical")), std::to_string(sample.at("power_electrical")),
                            std::to_string(sample.at("efficiency"))});
        }
        return db_->executemany(query, rows);
    }

    std::vector<QueryRow> get_telemetry(const std::string& session_id, int limit = 1000) {
        return db_->execute_query(
            "SELECT * FROM emec_telemetry WHERE session_id = $1::uuid ORDER BY sim_time ASC LIMIT $2",
            {session_id, std::to_string(limit)});
    }

    std::string record_fault(const std::string& session_id, int code, const std::string& message, double sim_time) override {
        const char* query =
            "INSERT INTO emec_fault_log (session_id, fault_code, message, sim_time) "
            "VALUES ($1::uuid, $2, $3, $4) RETURNING fault_id::text";
        auto rows = db_->execute_query(query, {session_id, std::to_string(code), message, std::to_string(sim_time)});
        return rows.at(0).at("fault_id");
    }

    std::vector<QueryRow> get_faults(const std::string& session_id) {
        return db_->execute_query(
            "SELECT * FROM emec_fault_log WHERE session_id = $1::uuid ORDER BY created_at ASC", {session_id});
    }

private:
    std::string ensure_device_id() {
        if (device_id_.empty()) {
            if (auto existing = get_device()) {
                device_id_ = existing->at("device_id");
            } else {
                register_device();
            }
        }
        return device_id_;
    }

    std::shared_ptr<DbConnection> db_;
    std::string device_name_;
    std::string device_id_;
};

inline std::shared_ptr<EMECDeviceRepository> create_repository_from_env(const std::string& device_name = "emec-virtual-device-0") {
    const char* url = std::getenv("NEON_DATABASE_URL");
    if (url == nullptr || url[0] == '\0') {
        return nullptr;
    }
    try {
        auto db = std::make_shared<NeonDBConnection>(with_connect_timeout(url));
        return std::make_shared<EMECDeviceRepository>(db, device_name);
    } catch (...) {
        return nullptr;
    }
}

inline void install_default_repository_factory() {
    default_repository_factory() = []() -> std::shared_ptr<DevicePersistenceSink> { return create_repository_from_env(); };
}

namespace {
struct DefaultRepositoryFactoryInstaller {
    DefaultRepositoryFactoryInstaller() { install_default_repository_factory(); }
};
const DefaultRepositoryFactoryInstaller kDefaultRepositoryFactoryInstaller;
}  // namespace

}  // namespace emec
