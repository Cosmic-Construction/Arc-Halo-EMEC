#pragma once

// VirtualEngine: integrated induction-motor simulator.
// One step couples supply voltage, winding flux, EM torque, rotor motion, and stator current.
// Hosts rebind the shaft load and the phase supply without changing this solver:
//   set_load_torque(fn)     fn(time, omega) -> T_load [N·m]
//   set_voltage_supply(fn)  fn(time) -> phase voltages [V]

#include "emec/em_field_solver.hpp"
#include "emec/polyphase_winding.hpp"
#include "emec/rotor_dynamics.hpp"
#include "emec/stator_dynamics.hpp"

#include <functional>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace emec {

inline constexpr double SLIP_LIMIT_MIN = -0.5;
inline constexpr double SLIP_LIMIT_MAX = 1.5;
inline constexpr double ROTOR_CURRENT_SCALE = 0.1;
inline constexpr double CURRENT_LIMIT_AMPS = 100.0;
inline constexpr double TORQUE_LIMIT_NM = 100.0;

struct EngineParameters {
    WindingParameters stator_winding;
    WindingParameters rotor_winding;
    RotorParameters rotor_mechanical;
    StatorParameters stator_electrical;
    double time_step = 1e-4;  // [s]

    // rated_power is accepted for call-site compatibility; default parameters
    // are the 5 kW-class industrial set used by the Python engine.
    static EngineParameters create_default(double /*rated_power*/ = 5000.0) {
        EngineParameters params;
        params.stator_winding = WindingParameters{3, 100, 0.5, 0.01, 0.005, 0.001, 2, 0.001, 36, 28};
        params.rotor_winding = WindingParameters{3, 80, 0.3, 0.008, 0.004, 0.0008, 2, 0.001, 36, 28};
        params.rotor_mechanical = RotorParameters{0.02, 0.001, 2, 1500.0, 0.05, 1e-6};
        params.stator_electrical = StatorParameters{3, 400.0, 50.0, 0.5, "wye"};
        params.time_step = 1e-4;
        return params;
    }
};

struct SimulationState {
    double time = 0.0;
    RotorState rotor;
    StatorState stator;
    std::optional<EMFieldState> em_field;
    double torque = 0.0;
    double power_mechanical = 0.0;
    double power_electrical = 0.0;
    double efficiency = 0.0;
};

class VirtualEngine {
public:
    using LoadTorqueFn = RotorDynamics::LoadTorqueFn;
    using VoltageSupplyFn = StatorDynamics::VoltageSupplyFn;
    using StepOverride = std::function<SimulationState(std::optional<double> dt)>;

    explicit VirtualEngine(std::optional<EngineParameters> params = std::nullopt)
        : params_(params ? *params : EngineParameters::create_default()),
          em_solver_(),
          winding_model_(params_.stator_winding, params_.rotor_winding),
          rotor_(params_.rotor_mechanical),
          stator_(params_.stator_electrical) {}

    const EngineParameters& params() const { return params_; }
    EngineParameters& params() { return params_; }
    EMFieldSolver& em_solver() { return em_solver_; }
    PolyphaseWindingModel& winding_model() { return winding_model_; }
    RotorDynamics& rotor() { return rotor_; }
    const RotorDynamics& rotor() const { return rotor_; }
    StatorDynamics& stator() { return stator_; }
    const StatorDynamics& stator() const { return stator_; }
    double current_time() const { return current_time_; }
    const std::vector<SimulationState>& history() const { return history_; }

    // Test/host hook. When set, step() returns this result and does not advance the solver.
    StepOverride step_override;

    SimulationState step(std::optional<double> dt = std::nullopt) {
        if (step_override) {
            return step_override(dt);
        }
        return step_impl(dt);
    }

    std::vector<SimulationState> simulate(double duration, std::optional<double> dt = std::nullopt) {
        const double step_dt = dt.value_or(params_.time_step);
        const int num_steps = static_cast<int>(duration / step_dt);
        for (int i = 0; i < num_steps; ++i) {
            step(step_dt);
        }
        return history_;
    }

    std::map<std::string, double> get_performance_metrics() const {
        if (history_.empty()) {
            return {{"avg_torque", 0.0},
                    {"avg_power_mechanical", 0.0},
                    {"avg_power_electrical", 0.0},
                    {"avg_efficiency", 0.0},
                    {"final_speed_rpm", 0.0},
                    {"max_torque", 0.0},
                    {"steady_state_speed", 0.0}};
        }
        std::vector<double> torques;
        std::vector<double> speeds;
        std::vector<double> P_mech;
        std::vector<double> P_elec;
        std::vector<double> efficiencies;
        torques.reserve(history_.size());
        for (const auto& sample : history_) {
            torques.push_back(sample.torque);
            speeds.push_back(sample.rotor.speed_rpm);
            P_mech.push_back(sample.power_mechanical);
            P_elec.push_back(sample.power_electrical);
            efficiencies.push_back(sample.efficiency);
        }
        const std::size_t steady_idx = static_cast<std::size_t>(static_cast<double>(history_.size()) * 0.8);
        return {{"avg_torque", mean_from(torques, steady_idx)},
                {"avg_power_mechanical", mean_from(P_mech, steady_idx)},
                {"avg_power_electrical", mean_from(P_elec, steady_idx)},
                {"avg_efficiency", mean_from(efficiencies, steady_idx)},
                {"final_speed_rpm", speeds.back()},
                {"max_torque", max_abs(torques)},
                {"steady_state_speed", mean_from(speeds, steady_idx)},
                {"simulation_time", history_.back().time}};
    }

    std::map<std::string, std::vector<double>> export_data() const {
        if (history_.empty()) {
            return {};
        }
        std::map<std::string, std::vector<double>> data;
        for (const auto& sample : history_) {
            data["time"].push_back(sample.time);
            data["speed_rpm"].push_back(sample.rotor.speed_rpm);
            data["torque"].push_back(sample.torque);
            data["power_mechanical"].push_back(sample.power_mechanical);
            data["power_electrical"].push_back(sample.power_electrical);
            data["efficiency"].push_back(sample.efficiency);
            data["stator_current_a"].push_back(sample.stator.current.size() > 0 ? sample.stator.current[0] : 0.0);
            data["stator_current_b"].push_back(sample.stator.current.size() > 1 ? sample.stator.current[1] : 0.0);
            data["stator_current_c"].push_back(sample.stator.current.size() > 2 ? sample.stator.current[2] : 0.0);
        }
        return data;
    }

    void reset() {
        current_time_ = 0.0;
        history_.clear();
        em_solver_.reset();
        rotor_.reset();
        stator_.reset();
    }

    void set_load_torque(LoadTorqueFn torque_fn) { rotor_.set_load_torque(std::move(torque_fn)); }
    void set_voltage_supply(VoltageSupplyFn voltage_fn) { stator_.set_voltage_supply(std::move(voltage_fn)); }

private:
    static double mean_from(const std::vector<double>& values, std::size_t start) {
        if (start >= values.size()) {
            return 0.0;
        }
        double sum = 0.0;
        for (std::size_t i = start; i < values.size(); ++i) {
            sum += values[i];
        }
        return sum / static_cast<double>(values.size() - start);
    }

    static double max_abs(const std::vector<double>& values) {
        double peak = 0.0;
        for (double value : values) {
            peak = std::max(peak, std::abs(value));
        }
        return peak;
    }

    SimulationState step_impl(std::optional<double> dt_opt) {
        const double dt = dt_opt.value_or(params_.time_step);
        const Vec stator_voltage = stator_.compute_supply_voltage(current_time_);
        const double theta_r = rotor_.get_electrical_angle();

        const double omega_e = 2.0 * kPi * params_.stator_electrical.rated_frequency;
        const double Z_mag = std::sqrt(
            params_.stator_winding.resistance_per_phase * params_.stator_winding.resistance_per_phase +
            std::pow(omega_e * params_.stator_winding.self_inductance, 2.0));
        Vec stator_current = stator_voltage / (Z_mag + 1e-6);

        Vec rotor_current_init(static_cast<std::size_t>(params_.rotor_winding.num_phases), 0.0);
        FluxLinkages flux = winding_model_.compute_flux_linkage(stator_current, rotor_current_init, theta_r);

        double slip = rotor_.get_slip(params_.stator_electrical.rated_frequency);
        slip = clip(slip, SLIP_LIMIT_MIN, SLIP_LIMIT_MAX);
        Vec rotor_current = rotor_current_init;
        if (std::abs(slip) > 0.01) {
            rotor_current = flux.rotor * (slip * ROTOR_CURRENT_SCALE);
        }

        stator_current = clip(stator_current, -CURRENT_LIMIT_AMPS, CURRENT_LIMIT_AMPS);
        rotor_current = clip(rotor_current, -CURRENT_LIMIT_AMPS, CURRENT_LIMIT_AMPS);

        flux = winding_model_.compute_flux_linkage(stator_current, rotor_current, theta_r);
        EMFieldState em_state = em_solver_.solve_field_step(stator_current, rotor_.state().angular_velocity, dt, 1.0);
        const double T_em_raw = EMFieldSolver::compute_torque(
            flux.stator, rotor_current, params_.rotor_mechanical.pole_pairs);
        const double T_em = clip(T_em_raw, -TORQUE_LIMIT_NM, TORQUE_LIMIT_NM);

        RotorState rotor_state = rotor_.solve_dynamics(T_em, dt);
        StatorState stator_state = stator_.update_state(stator_current, stator_voltage, dt);

        const double P_electrical = (stator_state.voltage * stator_state.current).sum();
        const double P_mechanical = T_em * rotor_state.angular_velocity;
        double efficiency = 0.0;
        if (std::abs(P_electrical) > 1e-6) {
            efficiency = std::abs(P_mechanical / P_electrical) * 100.0;
        }
        efficiency = std::min(efficiency, 100.0);

        current_time_ += dt;
        SimulationState state;
        state.time = current_time_;
        state.rotor = rotor_state;
        state.stator = stator_state;
        state.em_field = em_state;
        state.torque = T_em;
        state.power_mechanical = P_mechanical;
        state.power_electrical = P_electrical;
        state.efficiency = efficiency;
        history_.push_back(state);
        return state;
    }

    EngineParameters params_;
    EMFieldSolver em_solver_;
    PolyphaseWindingModel winding_model_;
    RotorDynamics rotor_;
    StatorDynamics stator_;
    double current_time_ = 0.0;
    std::vector<SimulationState> history_;
};

}  // namespace emec
