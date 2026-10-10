#pragma once

// Stator electrical dynamics: 3-phase supply generation and voltage/current/power.
// Balanced supply:
//   v_i = V_peak * sin(ωt - 2π i / N)
// Wye line-to-phase: V_phase = V_line / √3, V_peak = V_phase * √2
// Current from the voltage equation: i = (v - dλ/dt) / R

#include "emec/numeric.hpp"

#include <functional>
#include <string>

namespace emec {

struct StatorParameters {
    int num_phases = 3;
    double rated_voltage = 400.0;     // line voltage [V]
    double rated_frequency = 50.0;    // [Hz]
    double resistance_per_phase = 0.5;  // [Ω]
    std::string connection_type = "wye";  // "wye" or "delta"
};

struct StatorState {
    Vec voltage;
    Vec current;
    double frequency = 0.0;    // [Hz]
    double phase_angle = 0.0;  // [rad]
    double time = 0.0;         // [s]
};

struct StatorPower {
    double instantaneous = 0.0;
    double apparent = 0.0;
    double power_factor = 0.0;
    double reactive = 0.0;
};

struct StatorLosses {
    double copper = 0.0;
    double core = 0.0;
    double total = 0.0;
};

class StatorDynamics {
public:
    using VoltageSupplyFn = std::function<Vec(double time)>;

    explicit StatorDynamics(StatorParameters params)
        : params_(std::move(params)),
          state_{Vec(static_cast<std::size_t>(params_.num_phases), 0.0),
                 Vec(static_cast<std::size_t>(params_.num_phases), 0.0),
                 params_.rated_frequency,
                 0.0,
                 0.0} {}

    const StatorParameters& params() const { return params_; }
    const StatorState& state() const { return state_; }
    StatorState& state() { return state_; }

    void set_voltage_supply(VoltageSupplyFn voltage_fn) { voltage_supply_fn_ = std::move(voltage_fn); }
    const VoltageSupplyFn& voltage_supply_fn() const { return voltage_supply_fn_; }

    Vec generate_balanced_voltage(double amplitude, double frequency, double time) const {
        const double omega = 2.0 * kPi * frequency;
        const double theta = omega * time;
        Vec voltages(static_cast<std::size_t>(params_.num_phases), 0.0);
        for (int i = 0; i < params_.num_phases; ++i) {
            const double phase_shift = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(params_.num_phases);
            voltages[static_cast<std::size_t>(i)] = amplitude * std::sin(theta - phase_shift);
        }
        return voltages;
    }

    Vec compute_supply_voltage(double time) const {
        if (voltage_supply_fn_) {
            return voltage_supply_fn_(time);
        }
        const double V_phase = params_.connection_type == "wye"
                                   ? params_.rated_voltage / std::sqrt(3.0)
                                   : params_.rated_voltage;
        const double V_peak = V_phase * std::sqrt(2.0);
        return generate_balanced_voltage(V_peak, params_.rated_frequency, time);
    }

    Vec solve_current_dynamics(const Vec& voltage,
                               const Vec& /*flux_linkage*/,
                               const Vec& d_flux_dt,
                               double /*dt*/) const {
        const double R = params_.resistance_per_phase;
        if (R <= 0.0) {
            return zeros_like(voltage);
        }
        return (voltage - d_flux_dt) / R;
    }

    StatorState update_state(const Vec& current, const Vec* voltage, double dt) {
        const double time = state_.time + dt;
        Vec applied = voltage ? voltage->copy() : compute_supply_voltage(time);
        const double omega = 2.0 * kPi * state_.frequency;
        const double phase_angle = positive_mod(state_.phase_angle + omega * dt, 2.0 * kPi);
        state_ = StatorState{std::move(applied), current.copy(), state_.frequency, phase_angle, time};
        return state_;
    }

    StatorState update_state(const Vec& current, const Vec& voltage, double dt) {
        return update_state(current, &voltage, dt);
    }

    StatorPower compute_power() const {
        const double P_inst = (state_.voltage * state_.current).sum();
        double v_sq = 0.0;
        double i_sq = 0.0;
        const std::size_t n = state_.voltage.size();
        for (std::size_t i = 0; i < n; ++i) {
            v_sq += state_.voltage[i] * state_.voltage[i];
            i_sq += state_.current[i] * state_.current[i];
        }
        const double denom = n == 0 ? 1.0 : static_cast<double>(n);
        const double V_rms = std::sqrt(v_sq / denom);
        const double I_rms = std::sqrt(i_sq / denom);
        const double S = static_cast<double>(params_.num_phases) * V_rms * I_rms;
        double pf = S > 0.0 ? std::abs(P_inst / S) : 0.0;
        pf = std::min(pf, 1.0);
        StatorPower power;
        power.instantaneous = P_inst;
        power.apparent = S;
        power.power_factor = pf;
        power.reactive = std::sqrt(std::max(0.0, S * S - P_inst * P_inst));
        return power;
    }

    StatorLosses compute_losses() const {
        double I_squared = 0.0;
        for (std::size_t i = 0; i < state_.current.size(); ++i) {
            I_squared += state_.current[i] * state_.current[i];
        }
        StatorLosses losses;
        losses.copper = I_squared * params_.resistance_per_phase;
        losses.core = 0.0;
        losses.total = losses.copper + losses.core;
        return losses;
    }

    double get_line_voltage() const {
        double v_sq = 0.0;
        const std::size_t n = state_.voltage.size();
        for (std::size_t i = 0; i < n; ++i) {
            v_sq += state_.voltage[i] * state_.voltage[i];
        }
        const double V_phase_rms = std::sqrt(v_sq / (n == 0 ? 1.0 : static_cast<double>(n)));
        if (params_.connection_type == "wye") {
            return std::sqrt(3.0) * V_phase_rms;
        }
        return V_phase_rms;
    }

    double get_line_current() const {
        double i_sq = 0.0;
        const std::size_t n = state_.current.size();
        for (std::size_t i = 0; i < n; ++i) {
            i_sq += state_.current[i] * state_.current[i];
        }
        const double I_phase_rms = std::sqrt(i_sq / (n == 0 ? 1.0 : static_cast<double>(n)));
        if (params_.connection_type == "wye") {
            return I_phase_rms;
        }
        return std::sqrt(3.0) * I_phase_rms;
    }

    void set_frequency(double frequency) { state_.frequency = frequency; }

    void reset() {
        state_ = StatorState{Vec(static_cast<std::size_t>(params_.num_phases), 0.0),
                             Vec(static_cast<std::size_t>(params_.num_phases), 0.0),
                             params_.rated_frequency,
                             0.0,
                             0.0};
    }

private:
    StatorParameters params_;
    StatorState state_;
    VoltageSupplyFn voltage_supply_fn_;
};

}  // namespace emec
