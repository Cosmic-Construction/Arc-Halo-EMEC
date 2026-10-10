#pragma once

// Polyphase induction winding model.
// Builds stator/rotor inductance matrices and position-dependent flux linkages:
//   λ_s = L_ss * i_s + L_sr(θ) * i_r
//   λ_r = L_rr * i_r + L_sr(θ)^T * i_s
// Three-phase mutual term uses M = -L_mutual/2 (symmetric winding).

#include "emec/numeric.hpp"

#include <cmath>
#include <map>
#include <string>

namespace emec {

inline constexpr double kMutualInductanceDivisor = 2.0;

struct WindingParameters {
    int num_phases = 3;
    int turns_per_phase = 100;
    double resistance_per_phase = 0.5;  // [Ω]
    double self_inductance = 0.01;      // [H]
    double mutual_inductance = 0.005;   // [H]
    double leakage_inductance = 0.001;  // [H]
    int pole_pairs = 2;
    double air_gap = 0.001;             // [m]
    int stator_slots = 36;
    int rotor_slots = 28;
};

struct WindingPower {
    double active = 0.0;
    double apparent = 0.0;
    double reactive = 0.0;
};

class PolyphaseWindingModel {
public:
    PolyphaseWindingModel(WindingParameters stator_params, WindingParameters rotor_params)
        : stator_(stator_params),
          rotor_(rotor_params),
          L_ss_(build_inductance_matrix(stator_params)),
          L_rr_(build_inductance_matrix(rotor_params)),
          stator_current_(static_cast<std::size_t>(stator_params.num_phases), 0.0),
          rotor_current_(static_cast<std::size_t>(rotor_params.num_phases), 0.0) {}

    const WindingParameters& stator() const { return stator_; }
    const WindingParameters& rotor() const { return rotor_; }
    const Mat& L_ss() const { return L_ss_; }
    const Mat& L_rr() const { return L_rr_; }
    const Vec& stator_current() const { return stator_current_; }
    const Vec& rotor_current() const { return rotor_current_; }

    // L_sr(θ) = L_m * cos(θ_r + θ_rotor_phase - θ_stator_phase)
    Mat compute_mutual_inductance(double theta_r) const {
        const int n_s = stator_.num_phases;
        const int n_r = rotor_.num_phases;
        Mat L_sr = Mat::zeros(static_cast<std::size_t>(n_s), static_cast<std::size_t>(n_r));
        const double L_m_max = std::sqrt(stator_.self_inductance * rotor_.self_inductance) * 0.9;
        for (int i = 0; i < n_s; ++i) {
            for (int j = 0; j < n_r; ++j) {
                const double theta_s = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(n_s);
                const double theta_r_phase = 2.0 * kPi * static_cast<double>(j) / static_cast<double>(n_r);
                const double theta = theta_r + theta_r_phase - theta_s;
                L_sr(static_cast<std::size_t>(i), static_cast<std::size_t>(j)) = L_m_max * std::cos(theta);
            }
        }
        return L_sr;
    }

    FluxLinkages compute_flux_linkage(const Vec& stator_current,
                                      const Vec& rotor_current,
                                      double theta_r) {
        Mat L_sr = compute_mutual_inductance(theta_r);
        FluxLinkages flux;
        flux.stator = L_ss_ * stator_current + L_sr * rotor_current;
        flux.rotor = L_rr_ * rotor_current + L_sr.transpose() * stator_current;
        stator_current_ = stator_current.copy();
        rotor_current_ = rotor_current.copy();
        return flux;
    }

    // Residuals of v = R*i + dλ/dt for stator and rotor.
    std::map<std::string, Vec> compute_voltage_equations(const Vec& stator_voltage,
                                                         const Vec& rotor_voltage,
                                                         const Vec& stator_current,
                                                         const Vec& rotor_current,
                                                         const Vec& d_lambda_s_dt,
                                                         const Vec& d_lambda_r_dt) const {
        Vec residual_s(stator_current.size());
        Vec residual_r(rotor_current.size());
        for (std::size_t i = 0; i < stator_current.size(); ++i) {
            residual_s[i] = stator_voltage[i] - stator_.resistance_per_phase * stator_current[i] - d_lambda_s_dt[i];
        }
        for (std::size_t i = 0; i < rotor_current.size(); ++i) {
            residual_r[i] = rotor_voltage[i] - rotor_.resistance_per_phase * rotor_current[i] - d_lambda_r_dt[i];
        }
        return {{"stator", residual_s}, {"rotor", residual_r}};
    }

    static double compute_mmf(const Vec& current, int turns) { return static_cast<double>(turns) * current.sum(); }

    // k_w = k_p * k_d. Full-pitch pitch factor is 1; distribution factor uses slots/pole/phase.
    double compute_winding_factor() const {
        const double k_p = 1.0;
        const double slots_per_pole_per_phase =
            static_cast<double>(stator_.stator_slots) /
            (2.0 * static_cast<double>(stator_.pole_pairs) * static_cast<double>(stator_.num_phases));
        double k_d = 1.0;
        if (slots_per_pole_per_phase >= 1.0) {
            const double q = slots_per_pole_per_phase;
            const double alpha = kPi / (static_cast<double>(stator_.num_phases) * q);
            k_d = std::sin(q * alpha / 2.0) / (q * std::sin(alpha / 2.0));
        }
        return k_p * k_d;
    }

    static WindingPower compute_power(const Vec& voltage, const Vec& current) {
        const double P_total = (voltage * current).sum();
        double S_apparent = std::abs(P_total);
        if (voltage.size() == 3 && current.size() == 3) {
            double v_sq = 0.0;
            double i_sq = 0.0;
            for (std::size_t i = 0; i < 3; ++i) {
                v_sq += voltage[i] * voltage[i];
                i_sq += current[i] * current[i];
            }
            const double V_rms = std::sqrt(v_sq / 3.0);
            const double I_rms = std::sqrt(i_sq / 3.0);
            S_apparent = 3.0 * V_rms * I_rms;
        }
        WindingPower power;
        power.active = P_total;
        power.apparent = S_apparent;
        power.reactive = std::sqrt(std::max(0.0, S_apparent * S_apparent - P_total * P_total));
        return power;
    }

private:
    static Mat build_inductance_matrix(const WindingParameters& params) {
        const int n = params.num_phases;
        Mat L = Mat::zeros(static_cast<std::size_t>(n), static_cast<std::size_t>(n));
        const double L_self_total = params.self_inductance + params.leakage_inductance;
        for (int i = 0; i < n; ++i) {
            L(static_cast<std::size_t>(i), static_cast<std::size_t>(i)) = L_self_total;
        }
        if (n == 3) {
            const double mutual = -params.mutual_inductance / kMutualInductanceDivisor;
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    if (i != j) {
                        L(static_cast<std::size_t>(i), static_cast<std::size_t>(j)) = mutual;
                    }
                }
            }
        } else {
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    if (i != j) {
                        const double phase_diff =
                            2.0 * kPi * std::abs(i - j) / static_cast<double>(n);
                        L(static_cast<std::size_t>(i), static_cast<std::size_t>(j)) =
                            params.mutual_inductance * std::cos(phase_diff);
                    }
                }
            }
        }
        return L;
    }

    WindingParameters stator_;
    WindingParameters rotor_;
    Mat L_ss_;
    Mat L_rr_;
    Vec stator_current_;
    Vec rotor_current_;
};

}  // namespace emec
