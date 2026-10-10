#pragma once

// Optional persistence sink used by VirtualHardwareDevice.
// start_session / end_session / record_fault are the operations the drive calls.
// A missing or failing sink must never stop the device.

#include "emec/device/telemetry.hpp"

#include <functional>
#include <map>
#include <memory>
#include <string>

namespace emec {

class DevicePersistenceSink {
public:
    virtual ~DevicePersistenceSink() = default;
    virtual std::string start_session(const std::map<std::string, double>& setpoints) = 0;
    virtual void end_session(const std::string& session_id,
                             const std::map<std::string, double>& metrics,
                             const std::vector<TelemetrySample>& samples,
                             const std::string& status = "stopped") = 0;
    virtual std::string record_fault(const std::string& session_id,
                                     int code,
                                     const std::string& message,
                                     double sim_time) = 0;
};

using RepositoryFactory = std::function<std::shared_ptr<DevicePersistenceSink>()>;

// Test/embedder override. Empty unless a host installs one.
// VirtualHardwareDevice calls this only when NEON_DATABASE_URL is set and no
// repository was passed explicitly. Exceptions are swallowed.
inline RepositoryFactory& repository_factory_override() {
    static RepositoryFactory factory;
    return factory;
}

// Installed by db/scripts/emec_device_repository.hpp. Empty when that header
// is not included, which leaves persistence disabled.
inline RepositoryFactory& default_repository_factory() {
    static RepositoryFactory factory;
    return factory;
}

}  // namespace emec
