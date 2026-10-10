#pragma once

// Latching protection faults for the virtual drive.
// A trip freezes the device in FAULT until FAULT_RESET, and only after the
// trip condition has cleared. Thresholds reuse the engine current and torque limits.

#include "emec/virtual_engine.hpp"

#include <cmath>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace emec {

enum class FaultCode : int {
    NONE = 0,
    OVER_CURRENT = 1,
    OVER_TORQUE = 2,
    OVER_SPEED = 3,
    ESTOP = 4,
    EFFICIENCY_ANOMALY = 5
};

inline const char* fault_code_name(FaultCode code) {
    switch (code) {
        case FaultCode::NONE: return "NONE";
        case FaultCode::OVER_CURRENT: return "OVER_CURRENT";
        case FaultCode::OVER_TORQUE: return "OVER_TORQUE";
        case FaultCode::OVER_SPEED: return "OVER_SPEED";
        case FaultCode::ESTOP: return "ESTOP";
        case FaultCode::EFFICIENCY_ANOMALY: return "EFFICIENCY_ANOMALY";
    }
    return "NONE";
}

inline std::optional<FaultCode> fault_code_from_name(std::string_view name) {
    for (FaultCode code : {FaultCode::NONE, FaultCode::OVER_CURRENT, FaultCode::OVER_TORQUE, FaultCode::OVER_SPEED,
                           FaultCode::ESTOP, FaultCode::EFFICIENCY_ANOMALY}) {
        if (name == fault_code_name(code)) {
            return code;
        }
    }
    return std::nullopt;
}

struct ProtectionLimits {
    double current_limit_a = CURRENT_LIMIT_AMPS;
    double torque_limit_nm = TORQUE_LIMIT_NM;
    double overspeed_factor = 1.2;
    double efficiency_max_pct = 100.0;
    std::optional<double> efficiency_min_pct;
    double efficiency_min_power_w = 1.0;
};

struct FaultEvent {
    FaultCode code = FaultCode::NONE;
    std::string message;
    double time = 0.0;
};

class FaultManager {
public:
    explicit FaultManager(ProtectionLimits limits = {}) : limits_(limits) {}

    const ProtectionLimits& limits() const { return limits_; }
    ProtectionLimits& limits() { return limits_; }
    const std::optional<FaultEvent>& active_fault() const { return active_fault_; }
    const std::vector<FaultEvent>& history() const { return history_; }

    FaultCode fault_code() const { return active_fault_ ? active_fault_->code : FaultCode::NONE; }
    bool is_faulted() const { return active_fault_.has_value(); }

    FaultEvent trip(FaultCode code, std::string message, double time) {
        if (!active_fault_) {
            active_fault_ = FaultEvent{code, std::move(message), time};
            history_.push_back(*active_fault_);
        }
        return *active_fault_;
    }

    bool clear(bool condition_active = false) {
        if (!active_fault_) {
            return true;
        }
        if (condition_active) {
            return false;
        }
        active_fault_.reset();
        return true;
    }

    std::optional<std::string> efficiency_violated(std::optional<double> efficiency,
                                                   std::optional<double> power_electrical,
                                                   std::optional<double> power_mechanical) const {
        if (!efficiency && !power_electrical && !power_mechanical) {
            return std::nullopt;
        }
        if (efficiency && !std::isfinite(*efficiency)) {
            return std::string("Efficiency anomaly: non-finite efficiency");
        }
        if (efficiency && *efficiency < 0.0) {
            return "Efficiency anomaly: " + format_1(*efficiency) + " % is negative";
        }
        if (efficiency && *efficiency > limits_.efficiency_max_pct + 1e-6) {
            return "Efficiency anomaly: " + format_1(*efficiency) + " % exceeds " +
                   format_1(limits_.efficiency_max_pct) + " % ceiling";
        }
        if (!power_electrical || !power_mechanical) {
            return std::nullopt;
        }
        const double pe = std::abs(*power_electrical);
        const double pm = std::abs(*power_mechanical);
        const double ceiling = limits_.efficiency_max_pct / 100.0;
        if (pe > limits_.efficiency_min_power_w && pm > pe * ceiling + 1e-6) {
            return "Efficiency anomaly: mechanical power " + format_1(pm) + " W exceeds electrical input " +
                   format_1(pe) + " W (over-unity)";
        }
        if (limits_.efficiency_min_pct && pe > limits_.efficiency_min_power_w && efficiency &&
            *efficiency < *limits_.efficiency_min_pct) {
            return "Efficiency anomaly: " + format_1(*efficiency) + " % below " +
                   format_1(*limits_.efficiency_min_pct) + " % floor";
        }
        return std::nullopt;
    }

    std::optional<FaultEvent> check_protections(const Vec& phase_currents,
                                                double torque,
                                                double speed_rpm,
                                                double rated_speed_rpm,
                                                double time,
                                                std::optional<double> efficiency = std::nullopt,
                                                std::optional<double> power_electrical = std::nullopt,
                                                std::optional<double> power_mechanical = std::nullopt) {
        const double max_current = phase_currents.max_abs();
        if (max_current > limits_.current_limit_a) {
            return trip(FaultCode::OVER_CURRENT,
                        "Over-current: " + format_1(max_current) + " A exceeds " + format_1(limits_.current_limit_a) +
                            " A limit",
                        time);
        }
        if (std::abs(torque) > limits_.torque_limit_nm) {
            return trip(FaultCode::OVER_TORQUE,
                        "Over-torque: " + format_1(std::abs(torque)) + " N·m exceeds " +
                            format_1(limits_.torque_limit_nm) + " N·m limit",
                        time);
        }
        const double speed_limit = limits_.overspeed_factor * rated_speed_rpm;
        if (std::abs(speed_rpm) > speed_limit) {
            return trip(FaultCode::OVER_SPEED,
                        "Over-speed: " + format_1(std::abs(speed_rpm)) + " rpm exceeds " + format_1(speed_limit) +
                            " rpm limit",
                        time);
        }
        if (auto anomaly = efficiency_violated(efficiency, power_electrical, power_mechanical)) {
            return trip(FaultCode::EFFICIENCY_ANOMALY, *anomaly, time);
        }
        return active_fault_;
    }

private:
    static std::string format_1(double value) {
        std::ostringstream out;
        out.setf(std::ios::fixed);
        out.precision(1);
        out << value;
        return out.str();
    }

    ProtectionLimits limits_;
    std::optional<FaultEvent> active_fault_;
    std::vector<FaultEvent> history_;
};

}  // namespace emec
