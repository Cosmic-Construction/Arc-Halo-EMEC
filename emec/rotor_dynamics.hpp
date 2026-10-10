#pragma once

// Rotor mechanical dynamics.
// Equation of motion:
//   J * dω/dt = T_em - T_load - T_friction
//   T_friction = B*ω + T_c*sign(ω) + K_w*ω*|ω|
// Slip: s = (ω_sync - ω_r) / ω_sync
// Kinetic energy: E_k = 0.5 * J * ω²

#include "emec/numeric.hpp"

#include <functional>
#include <optional>

namespace emec {

inline constexpr double kVelocityDeadband = 0.01;  // [rad/s] Coulomb friction deadband

struct RotorParameters {
    double inertia = 0.01;                  // [kg·m²]
    double friction_coefficient = 0.001;    // [N·m·s/rad]
    int pole_pairs = 2;
    double rated_speed = 1500.0;            // [rpm]
    double coulomb_friction = 0.0;          // [N·m]
    double windage_coefficient = 0.0;
};

struct RotorState {
    double angle = 0.0;                 // mechanical angle [rad]
    double angular_velocity = 0.0;      // [rad/s]
    double angular_acceleration = 0.0;  // [rad/s²]
    double speed_rpm = 0.0;
    double time = 0.0;                  // [s]
};

class RotorDynamics {
public:
    using LoadTorqueFn = std::function<double(double time, double omega)>;

    explicit RotorDynamics(RotorParameters params) : params_(params) {}

    const RotorParameters& params() const { return params_; }
    const RotorState& state() const { return state_; }
    RotorState& state() { return state_; }

    void set_load_torque(LoadTorqueFn torque_fn) { load_torque_fn_ = std::move(torque_fn); }
    const LoadTorqueFn& load_torque_fn() const { return load_torque_fn_; }

    double compute_friction_torque(double omega) const {
        const double T_viscous = params_.friction_coefficient * omega;
        double T_coulomb = 0.0;
        if (std::abs(omega) > kVelocityDeadband) {
            T_coulomb = params_.coulomb_friction * (omega > 0.0 ? 1.0 : -1.0);
        }
        const double T_windage = params_.windage_coefficient * omega * std::abs(omega);
        return T_viscous + T_coulomb + T_windage;
    }

    double compute_load_torque(double time, double omega) const {
        if (load_torque_fn_) {
            return load_torque_fn_(time, omega);
        }
        return 0.0;
    }

    // Forward Euler: ω += α*dt, θ += ω_new*dt, θ wrapped to [0, 2π).
    RotorState solve_dynamics(double T_em, double dt) {
        const double omega = state_.angular_velocity;
        const double theta = state_.angle;
        const double time = state_.time;
        const double T_friction = compute_friction_torque(omega);
        const double T_load = compute_load_torque(time, omega);
        const double T_net = T_em - T_load - T_friction;
        const double alpha = params_.inertia != 0.0 ? T_net / params_.inertia : 0.0;
        const double omega_new = omega + alpha * dt;
        const double theta_new = positive_mod(theta + omega_new * dt, 2.0 * kPi);
        const double speed_rpm = omega_new * 60.0 / (2.0 * kPi);
        state_ = RotorState{theta_new, omega_new, alpha, speed_rpm, time + dt};
        return state_;
    }

    // θ_electrical = pole_pairs * θ_mechanical
    double get_electrical_angle() const { return static_cast<double>(params_.pole_pairs) * state_.angle; }

    // Synchronous speed uses supply frequency and pole pairs: ω_s = 2π f / p
    double get_slip(double synchronous_frequency) const {
        const double omega_sync = 2.0 * kPi * synchronous_frequency / static_cast<double>(params_.pole_pairs);
        if (omega_sync > 0.0) {
            return (omega_sync - state_.angular_velocity) / omega_sync;
        }
        return 1.0;
    }

    double get_kinetic_energy() const {
        return 0.5 * params_.inertia * state_.angular_velocity * state_.angular_velocity;
    }

    void set_state(double angle, double angular_velocity) {
        state_.angle = positive_mod(angle, 2.0 * kPi);
        state_.angular_velocity = angular_velocity;
        state_.speed_rpm = angular_velocity * 60.0 / (2.0 * kPi);
        state_.angular_acceleration = 0.0;
    }

    void reset() { state_ = RotorState{}; }

private:
    RotorParameters params_;
    RotorState state_;
    LoadTorqueFn load_torque_fn_;
};

}  // namespace emec
