#pragma once

// Electromagnetic field solver for a rotating induction machine.
// Maxwell relations used by the virtual engine:
//   Faraday:  EMF = -dλ/dt
//   Ampere:   H = B / μ
//   torque:   T = (3/2) * pole_pairs * (λ_d * i_q - λ_q * i_d)
// Park (abc → dq0) and inverse Park are the reference-frame transforms.

#include "emec/numeric.hpp"

#include <optional>

namespace emec {

struct EMFieldState {
    Vec magnetic_flux_density;  // B [T]
    Vec electric_field;         // E [V/m]
    Vec current_density;        // J [A/m²]
    Vec magnetic_field;         // H [A/m]
    double time = 0.0;          // [s]
};

class EMFieldSolver {
public:
    explicit EMFieldSolver(double permeability = 4.0 * kPi * 1e-7,
                           double permittivity = 8.854e-12,
                           double conductivity = 5.96e7)
        : mu_(permeability), epsilon_(permittivity), sigma_(conductivity) {}

    double permeability() const { return mu_; }
    double permittivity() const { return epsilon_; }
    double conductivity() const { return sigma_; }

    // B ≈ μ * (geometry_factor * I) for the air-gap model.
    Vec compute_magnetic_flux_density(const Vec& current, double geometry_factor = 1.0) const {
        return current * (mu_ * geometry_factor);
    }

    Vec compute_induced_emf(const Vec& flux_linkage, double dt) const {
        if (dt <= 0.0 || !current_state_) {
            return zeros_like(flux_linkage);
        }
        return (flux_linkage - current_state_->magnetic_flux_density) * (-1.0 / dt);
    }

    EMFieldState solve_field_step(const Vec& current,
                                  double /*angular_velocity*/,
                                  double dt,
                                  double geometry_factor = 1.0) {
        Vec B = compute_magnetic_flux_density(current, geometry_factor);
        Vec H = B * (1.0 / mu_);
        Vec J = current * geometry_factor;
        Vec E = sigma_ > 0.0 ? J * (1.0 / sigma_) : zeros_like(J);
        double new_time = current_state_ ? current_state_->time + dt : 0.0;
        current_state_ = EMFieldState{B, E, J, H, new_time};
        return *current_state_;
    }

    // dq-frame electromagnetic torque [N·m].
    static double compute_torque(const Vec& stator_flux, const Vec& rotor_current, int pole_pairs = 2) {
        if (stator_flux.size() < 2 || rotor_current.size() < 2) {
            return 0.0;
        }
        const double lambda_d = stator_flux[0];
        const double lambda_q = stator_flux.size() > 1 ? stator_flux[1] : 0.0;
        const double i_d = rotor_current[0];
        const double i_q = rotor_current.size() > 1 ? rotor_current[1] : 0.0;
        return (3.0 / 2.0) * static_cast<double>(pole_pairs) * (lambda_d * i_q - lambda_q * i_d);
    }

    static Vec park_transform(const Vec& abc, double theta) {
        if (abc.size() < 3) {
            return Vec(3, 0.0);
        }
        const double a = abc[0];
        const double b = abc[1];
        const double c = abc[2];
        const double cos_theta = std::cos(theta);
        const double sin_theta = std::sin(theta);
        const double cos_120 = std::cos(theta - 2.0 * kPi / 3.0);
        const double sin_120 = std::sin(theta - 2.0 * kPi / 3.0);
        const double cos_240 = std::cos(theta + 2.0 * kPi / 3.0);
        const double sin_240 = std::sin(theta + 2.0 * kPi / 3.0);
        const double d = (2.0 / 3.0) * (a * cos_theta + b * cos_120 + c * cos_240);
        const double q = (2.0 / 3.0) * (-a * sin_theta - b * sin_120 - c * sin_240);
        const double zero = (1.0 / 3.0) * (a + b + c);
        return Vec{d, q, zero};
    }

    static Vec inverse_park_transform(const Vec& dq0, double theta) {
        if (dq0.size() < 2) {
            return Vec(3, 0.0);
        }
        const double d = dq0[0];
        const double q = dq0[1];
        const double zero = dq0.size() > 2 ? dq0[2] : 0.0;
        const double a = d * std::cos(theta) - q * std::sin(theta) + zero;
        const double b = d * std::cos(theta - 2.0 * kPi / 3.0) - q * std::sin(theta - 2.0 * kPi / 3.0) + zero;
        const double c = d * std::cos(theta + 2.0 * kPi / 3.0) - q * std::sin(theta + 2.0 * kPi / 3.0) + zero;
        return Vec{a, b, c};
    }

    void reset() { current_state_.reset(); }

    const std::optional<EMFieldState>& current_state() const { return current_state_; }

private:
    double mu_;
    double epsilon_;
    double sigma_;
    std::optional<EMFieldState> current_state_;
};

}  // namespace emec
