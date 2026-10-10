#pragma once

// Virtual hardware device driver.
// Wraps VirtualEngine in a motor-drive register surface. The physics solver is not modified:
// setpoints rebind set_voltage_supply / set_load_torque, and run_cycle() calls engine.step().

#include "emec/device/faults.hpp"
#include "emec/device/persistence.hpp"
#include "emec/device/registers.hpp"
#include "emec/device/telemetry.hpp"
#include "emec/virtual_engine.hpp"

#include <cmath>
#include <cstdlib>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>

namespace emec {

inline constexpr int CTRL_BIT_START = 0x1;
inline constexpr int CTRL_BIT_STOP = 0x2;
inline constexpr int CTRL_BIT_RESET = 0x4;

inline constexpr int STATUS_BIT_POWERED = 0x1;
inline constexpr int STATUS_BIT_RUNNING = 0x2;
inline constexpr int STATUS_BIT_FAULT = 0x4;
inline constexpr int STATUS_BIT_ESTOP = 0x8;

enum class DeviceState { OFF, READY, RUNNING, FAULT, ESTOP };

inline const char* device_state_name(DeviceState state) {
    switch (state) {
        case DeviceState::OFF: return "OFF";
        case DeviceState::READY: return "READY";
        case DeviceState::RUNNING: return "RUNNING";
        case DeviceState::FAULT: return "FAULT";
        case DeviceState::ESTOP: return "ESTOP";
    }
    return "OFF";
}

class RegisterAccessError : public std::runtime_error {
public:
    explicit RegisterAccessError(const std::string& message) : std::runtime_error(message) {}
};

class RegisterValueError : public std::runtime_error {
public:
    explicit RegisterValueError(const std::string& message) : std::runtime_error(message) {}
};

class InvalidStateError : public std::runtime_error {
public:
    explicit InvalidStateError(const std::string& message) : std::runtime_error(message) {}
};

using RegisterValue = std::variant<double, std::string>;

class VirtualHardwareDevice {
public:
    VirtualHardwareDevice(std::optional<EngineParameters> params = std::nullopt,
                          std::optional<ProtectionLimits> limits = std::nullopt,
                          int telemetry_capacity = 10000,
                          int telemetry_decimation = 1,
                          std::shared_ptr<DevicePersistenceSink> repository = nullptr)
        : engine(params),
          params(engine.params()),
          faults(limits.value_or(ProtectionLimits{})),
          telemetry(telemetry_capacity, telemetry_decimation),
          repository(repository ? std::move(repository) : attach_repository_from_env()),
          voltage_setpoint_(this->params.stator_electrical.rated_voltage),
          frequency_setpoint_(this->params.stator_electrical.rated_frequency) {}

    VirtualEngine engine;
    EngineParameters& params;
    FaultManager faults;
    TelemetryRecorder telemetry;
    std::shared_ptr<DevicePersistenceSink> repository;
    DeviceState state = DeviceState::OFF;

    DeviceState power_on() {
        if (state == DeviceState::OFF || state == DeviceState::ESTOP) {
            if (state == DeviceState::ESTOP) {
                faults.clear(false);
            }
            state = DeviceState::READY;
            apply_setpoints();
        }
        return state;
    }

    DeviceState start() {
        if (state == DeviceState::READY) {
            state = DeviceState::RUNNING;
            begin_session();
        } else if (state == DeviceState::OFF) {
            throw InvalidStateError("Power on the device before starting");
        } else if (state == DeviceState::FAULT || state == DeviceState::ESTOP) {
            throw InvalidStateError(std::string("Cannot start from ") + device_state_name(state) +
                                    "; clear the condition first");
        }
        return state;
    }

    DeviceState stop() {
        if (state == DeviceState::RUNNING) {
            state = DeviceState::READY;
            end_session("stopped");
        }
        return state;
    }

    DeviceState power_off() {
        if (state == DeviceState::READY || state == DeviceState::FAULT) {
            state = DeviceState::OFF;
        } else if (state == DeviceState::RUNNING) {
            throw InvalidStateError("Stop the device before powering off");
        }
        return state;
    }

    DeviceState e_stop() {
        if (state != DeviceState::OFF) {
            FaultEvent fault = faults.trip(FaultCode::ESTOP, "Emergency stop engaged", engine.current_time());
            if (state == DeviceState::RUNNING) {
                record_fault(fault);
                end_session("faulted");
            }
            state = DeviceState::ESTOP;
        }
        return state;
    }

    DeviceState inject_fault(FaultCode code, std::optional<std::string> message = std::nullopt) {
        if (state == DeviceState::OFF) {
            throw InvalidStateError("Cannot inject a fault while the device is OFF");
        }
        if (code == FaultCode::NONE) {
            throw InvalidStateError("Cannot inject FaultCode.NONE");
        }
        FaultEvent fault = faults.trip(code, message.value_or(std::string("Injected fault: ") + fault_code_name(code)),
                                        engine.current_time());
        if (state == DeviceState::RUNNING) {
            fault_counts_[static_cast<int>(code)] += 1;
            record_fault(fault);
            end_session("faulted");
        }
        if (state != DeviceState::ESTOP) {
            state = DeviceState::FAULT;
        }
        return state;
    }

    bool reset_faults() {
        if (state != DeviceState::FAULT) {
            return !faults.is_faulted();
        }
        const bool cleared = faults.clear(trip_condition_active());
        if (cleared) {
            state = DeviceState::READY;
        }
        return cleared;
    }

    DeviceState reset() {
        engine.reset();
        telemetry.clear();
        faults = FaultManager(faults.limits());
        last_torque_ = 0.0;
        last_power_mech_ = 0.0;
        last_power_elec_ = 0.0;
        last_efficiency_ = 0.0;
        if (state != DeviceState::OFF) {
            state = DeviceState::READY;
        }
        return state;
    }

    void write_register(Register reg, double value) { write_resolved(reg, value); }

    void write_register(std::string_view name, double value) { write_resolved(resolve_register(name), value); }

    void write_register(Register reg, const std::string& text) { write_resolved(reg, parse_numeric(reg, text)); }

    void write_register(std::string_view name, const std::string& text) {
        const Register reg = resolve_register(name);
        write_resolved(reg, parse_numeric(reg, text));
    }

    RegisterValue read_register(Register reg) const { return read_resolved(reg); }

    RegisterValue read_register(std::string_view name) const { return read_resolved(resolve_register(name)); }

    double read_number(Register reg) const { return std::get<double>(read_register(reg)); }

    double read_number(std::string_view name) const { return std::get<double>(read_register(name)); }

    std::optional<SimulationState> run_cycle(std::optional<double> dt = std::nullopt) {
        if (state != DeviceState::RUNNING) {
            return std::nullopt;
        }
        SimulationState sim = engine.step(dt);
        last_torque_ = sim.torque;
        last_power_mech_ = sim.power_mechanical;
        last_power_elec_ = sim.power_electrical;
        last_efficiency_ = sim.efficiency;

        auto fault = faults.check_protections(sim.stator.current, sim.torque, sim.rotor.speed_rpm,
                                               params.rotor_mechanical.rated_speed, sim.time, sim.efficiency,
                                               sim.power_electrical, sim.power_mechanical);
        if (fault && fault->code != FaultCode::NONE) {
            fault_counts_[static_cast<int>(fault->code)] += 1;
            state = DeviceState::FAULT;
            record_fault(*fault);
            end_session("faulted");
            return sim;
        }
        telemetry.record(sample_from_state(sim));
        return sim;
    }

    int run(double duration, std::optional<double> dt = std::nullopt) {
        const double step_dt = dt.value_or(params.time_step);
        if (step_dt <= 0.0) {
            throw std::invalid_argument("dt must be positive");
        }
        // Match Python int(duration / dt) for the decimal steps used by the device tests.
        const int cycles = static_cast<int>(std::floor((duration / step_dt) + 1e-9));
        int executed = 0;
        for (int i = 0; i < cycles; ++i) {
            if (!run_cycle(step_dt)) {
                break;
            }
            ++executed;
        }
        return executed;
    }

    int status_word() const {
        int word = 0;
        if (state != DeviceState::OFF) {
            word |= STATUS_BIT_POWERED;
        }
        if (state == DeviceState::RUNNING) {
            word |= STATUS_BIT_RUNNING;
        }
        if (state == DeviceState::FAULT || faults.is_faulted()) {
            word |= STATUS_BIT_FAULT;
        }
        if (state == DeviceState::ESTOP) {
            word |= STATUS_BIT_ESTOP;
        }
        return word;
    }

    const std::optional<std::string>& session_id() const { return session_id_; }

private:
    static std::shared_ptr<DevicePersistenceSink> attach_repository_from_env() {
        const char* url = std::getenv("NEON_DATABASE_URL");
        if (url == nullptr || url[0] == '\0') {
            return nullptr;
        }
        try {
            if (repository_factory_override()) {
                return repository_factory_override()();
            }
            if (default_repository_factory()) {
                return default_repository_factory()();
            }
        } catch (...) {
            return nullptr;
        }
        return nullptr;
    }

    static TelemetrySample sample_from_state(const SimulationState& sim) {
        TelemetrySample sample;
        sample.set("time", sim.time);
        sample.set("speed_rpm", sim.rotor.speed_rpm);
        sample.set("torque", sim.torque);
        sample.set("power_mechanical", sim.power_mechanical);
        sample.set("power_electrical", sim.power_electrical);
        sample.set("efficiency", sim.efficiency);
        sample.set("stator_current_a", sim.stator.current.size() > 0 ? sim.stator.current[0] : 0.0);
        sample.set("stator_current_b", sim.stator.current.size() > 1 ? sim.stator.current[1] : 0.0);
        sample.set("stator_current_c", sim.stator.current.size() > 2 ? sim.stator.current[2] : 0.0);
        return sample;
    }

    bool trip_condition_active() const {
        const auto& stator = engine.stator().state();
        const auto& rotor = engine.rotor().state();
        const auto& limits = faults.limits();
        if (stator.current.max_abs() > limits.current_limit_a) {
            return true;
        }
        if (std::abs(last_torque_) > limits.torque_limit_nm) {
            return true;
        }
        const double speed_limit = limits.overspeed_factor * params.rotor_mechanical.rated_speed;
        if (std::abs(rotor.speed_rpm) > speed_limit) {
            return true;
        }
        return faults.efficiency_violated(last_efficiency_, last_power_elec_, last_power_mech_).has_value();
    }

    std::optional<std::string> setpoint_would_trip(Register reg, double value) const {
        if (state != DeviceState::RUNNING) {
            return std::nullopt;
        }
        const auto& limits = faults.limits();
        if (reg == Register::LOAD_TORQUE_SETPOINT && std::abs(value) > limits.torque_limit_nm) {
            return "LOAD_TORQUE_SETPOINT " + std::to_string(value) + " N·m would exceed the " +
                   std::to_string(limits.torque_limit_nm) + " N·m over-torque limit while RUNNING";
        }
        if (reg == Register::FREQUENCY_SETPOINT) {
            const int pole_pairs = params.rotor_mechanical.pole_pairs;
            if (pole_pairs <= 0) {
                return std::nullopt;
            }
            const double sync_rpm = 60.0 * value / static_cast<double>(pole_pairs);
            const double speed_limit = limits.overspeed_factor * params.rotor_mechanical.rated_speed;
            if (std::abs(sync_rpm) > speed_limit) {
                return "FREQUENCY_SETPOINT " + std::to_string(value) +
                       " Hz implies synchronous speed above the over-speed limit while RUNNING";
            }
        }
        return std::nullopt;
    }

    void apply_setpoints() {
        apply_voltage_supply();
        apply_load_torque();
    }

    void apply_voltage_supply() {
        const std::string connection = params.stator_electrical.connection_type;
        const int num_phases = params.stator_electrical.num_phases;
        const double voltage = voltage_setpoint_;
        const double frequency = frequency_setpoint_;
        engine.set_voltage_supply([connection, num_phases, voltage, frequency](double time) {
            const double v_phase = connection == "wye" ? voltage / std::sqrt(3.0) : voltage;
            const double v_peak = v_phase * std::sqrt(2.0);
            const double omega = 2.0 * kPi * frequency;
            Vec voltages(static_cast<std::size_t>(num_phases), 0.0);
            for (int i = 0; i < num_phases; ++i) {
                const double phase = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(num_phases);
                voltages[static_cast<std::size_t>(i)] = v_peak * std::sin(omega * time - phase);
            }
            return voltages;
        });
        engine.stator().set_frequency(frequency);
    }

    void apply_load_torque() {
        const double load = load_torque_setpoint_;
        engine.set_load_torque([load](double, double) { return load; });
    }

    static double parse_numeric(Register reg, const std::string& text) {
        try {
            std::size_t consumed = 0;
            const double value = std::stod(text, &consumed);
            if (consumed != text.size()) {
                throw std::invalid_argument("trailing");
            }
            return value;
        } catch (const std::exception&) {
            throw RegisterValueError(std::string("Register ") + register_name(reg) + " requires a numeric value");
        }
    }

    static Register resolve_register(std::string_view name) {
        auto reg = register_from_name(name);
        if (!reg) {
            throw RegisterAccessError(std::string("Unknown register: ") + std::string(name));
        }
        return *reg;
    }

    static double validate_value(Register reg, double value) {
        if (!std::isfinite(value)) {
            throw RegisterValueError(std::string("Register ") + register_name(reg) + " requires a numeric value");
        }
        const auto& info = register_info(reg);
        if (info.value_range) {
            const double lo = info.value_range->first;
            const double hi = info.value_range->second;
            if (!(lo <= value && value <= hi)) {
                throw RegisterValueError(std::string("Register ") + register_name(reg) + " value outside range");
            }
        }
        return value;
    }

    void write_resolved(Register reg, double raw) {
        if (!register_in_map(reg)) {
            throw RegisterAccessError("Unknown register");
        }
        const auto& info = register_info(reg);
        if (info.access == Access::READ_ONLY) {
            throw RegisterAccessError(std::string("Register ") + register_name(reg) + " is read-only");
        }
        const double value = validate_value(reg, raw);
        if (auto inhibited = setpoint_would_trip(reg, value)) {
            throw InvalidStateError(*inhibited);
        }
        if (reg == Register::CONTROL_WORD) {
            control_word_ = static_cast<int>(value);
            if (control_word_ & CTRL_BIT_RESET) {
                reset();
            } else if (control_word_ & CTRL_BIT_STOP) {
                stop();
            } else if (control_word_ & CTRL_BIT_START) {
                start();
            }
        } else if (reg == Register::FAULT_RESET) {
            if (value != 0.0) {
                reset_faults();
            }
        } else if (reg == Register::VOLTAGE_SETPOINT) {
            voltage_setpoint_ = value;
            apply_voltage_supply();
        } else if (reg == Register::FREQUENCY_SETPOINT) {
            frequency_setpoint_ = value;
            apply_voltage_supply();
        } else if (reg == Register::LOAD_TORQUE_SETPOINT) {
            load_torque_setpoint_ = value;
            apply_load_torque();
        }
    }

    RegisterValue read_resolved(Register reg) const {
        if (!register_in_map(reg)) {
            throw RegisterAccessError("Unknown register");
        }
        const auto& info = register_info(reg);
        if (info.access == Access::WRITE_ONLY) {
            throw RegisterAccessError(std::string("Register ") + register_name(reg) + " is write-only");
        }
        const auto& stator = engine.stator().state();
        const auto& rotor = engine.rotor().state();
        switch (reg) {
            case Register::CONTROL_WORD: return static_cast<double>(control_word_);
            case Register::VOLTAGE_SETPOINT: return voltage_setpoint_;
            case Register::FREQUENCY_SETPOINT: return frequency_setpoint_;
            case Register::LOAD_TORQUE_SETPOINT: return load_torque_setpoint_;
            case Register::SPEED_RPM: return rotor.speed_rpm;
            case Register::TORQUE: return last_torque_;
            case Register::PHASE_CURRENT_A: return stator.current.size() > 0 ? stator.current[0] : 0.0;
            case Register::PHASE_CURRENT_B: return stator.current.size() > 1 ? stator.current[1] : 0.0;
            case Register::PHASE_CURRENT_C: return stator.current.size() > 2 ? stator.current[2] : 0.0;
            case Register::POWER_MECH: return last_power_mech_;
            case Register::POWER_ELEC: return last_power_elec_;
            case Register::EFFICIENCY: return last_efficiency_;
            case Register::SIMULATION_TIME: return engine.current_time();
            case Register::STATUS_WORD: return static_cast<double>(status_word());
            case Register::FAULT_CODE: return static_cast<double>(static_cast<int>(faults.fault_code()));
            case Register::DEVICE_STATE: return std::string(device_state_name(state));
            case Register::FAULT_RESET: break;
        }
        throw RegisterAccessError(std::string("Register ") + register_name(reg) + " not readable");
    }

    void begin_session() {
        if (!repository) {
            return;
        }
        try {
            std::map<std::string, double> setpoints = {{"voltage_setpoint", voltage_setpoint_},
                                                       {"frequency_setpoint", frequency_setpoint_},
                                                       {"load_torque_setpoint", load_torque_setpoint_}};
            session_id_ = repository->start_session(setpoints);
            session_start_time_ = engine.current_time();
        } catch (...) {
            session_id_.reset();
        }
    }

    void end_session(const std::string& status) {
        if (!repository || !session_id_) {
            session_id_.reset();
            return;
        }
        try {
            auto metrics = engine.get_performance_metrics();
            metrics["duration_s"] = engine.current_time() - session_start_time_;
            repository->end_session(*session_id_, metrics, telemetry.snapshot(), status);
        } catch (...) {
        }
        session_id_.reset();
    }

    void record_fault(const FaultEvent& fault) {
        if (!repository || !session_id_) {
            return;
        }
        try {
            repository->record_fault(*session_id_, static_cast<int>(fault.code), fault.message, fault.time);
        } catch (...) {
        }
    }

    int control_word_ = 0;
    double voltage_setpoint_ = 0.0;
    double frequency_setpoint_ = 0.0;
    double load_torque_setpoint_ = 0.0;
    double last_torque_ = 0.0;
    double last_power_mech_ = 0.0;
    double last_power_elec_ = 0.0;
    double last_efficiency_ = 0.0;
    std::optional<std::string> session_id_;
    double session_start_time_ = 0.0;
    std::map<int, int> fault_counts_;
};

}  // namespace emec
