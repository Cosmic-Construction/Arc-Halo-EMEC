#pragma once

// Map an induction-motor parameter set onto bond-graph R/I/GY elements.
// Electrical: R = stator resistance, I = stator inductance
// Mechanical: R = viscous friction, I = rotor inertia
// Coupling:   GY ratio k_t = (3/2) * pole_pairs * L_mutual
// Impedances: Z_e = R + jωL, Z_m = B + jωJ

#include "emec/bond_graph.hpp"
#include "emec/numeric.hpp"
#include "emec/virtual_engine.hpp"

#include <complex>
#include <string>
#include <utility>

namespace emec {

struct EMBondGraphMapping {
    double electrical_resistance = 0.0;  // [Ω]
    double electrical_inductance = 0.0;  // [H]
    double mechanical_friction = 0.0;    // [N·m·s/rad]
    double mechanical_inertia = 0.0;     // [kg·m²]
    double torque_constant = 0.0;        // [N·m/A]
    double voltage_constant = 0.0;       // [V·s/rad]
    double supply_voltage = 0.0;         // [V]
    double supply_frequency = 0.0;       // [Hz]
};

inline std::pair<BondGraphModel, EMBondGraphMapping> create_em_bond_graph_from_engine(const EngineParameters& params) {
    const double R_s = params.stator_winding.resistance_per_phase;
    const double L_s = params.stator_winding.self_inductance;
    const double J = params.rotor_mechanical.inertia;
    const double B = params.rotor_mechanical.friction_coefficient;
    const double p = static_cast<double>(params.rotor_mechanical.pole_pairs);
    const double L_m = params.stator_winding.mutual_inductance;
    const double k_t = 1.5 * p * L_m;

    EMBondGraphMapping mapping{R_s, L_s, B, J, k_t, k_t, params.stator_electrical.rated_voltage,
                               params.stator_electrical.rated_frequency};

    BondGraphModel model("Induction Motor Bond Graph");
    model.add_resistive_element("stator_resistance", R_s, EnergyDomain::ELECTRICAL);
    model.add_inertial_element("stator_inductance", L_s, EnergyDomain::ELECTRICAL);
    model.add_resistive_element("rotor_friction", B, EnergyDomain::MECHANICAL_ROTATION);
    model.add_inertial_element("rotor_inertia", J, EnergyDomain::MECHANICAL_ROTATION);
    model.add_gyrator("em_coupling", k_t);
    return {std::move(model), mapping};
}

inline std::map<std::string, double> analyze_power_flow(BondGraphModel& model,
                                                        double voltage,
                                                        double current,
                                                        double torque,
                                                        double omega) {
    if (auto it = model.elements.find("stator_resistance"); it != model.elements.end()) {
        if (it->second->kind() == ElementKind::Resistive) {
            it->second->power_vars.effort = voltage;
            it->second->power_vars.flow = current;
        }
    }
    if (auto it = model.elements.find("rotor_friction"); it != model.elements.end()) {
        if (it->second->kind() == ElementKind::Resistive) {
            it->second->power_vars.effort = torque;
            it->second->power_vars.flow = omega;
        }
    }
    if (auto it = model.elements.find("rotor_inertia"); it != model.elements.end()) {
        if (it->second->kind() == ElementKind::Inertial) {
            it->second->power_vars.effort = torque;
            it->second->power_vars.flow = omega;
        }
    }
    const double P_electrical = voltage * current;
    const double P_mechanical = torque * omega;
    const auto energy = model.get_total_stored_energy();
    return {{"electrical_input_power", P_electrical},
            {"mechanical_output_power", P_mechanical},
            {"resistive_losses", model.get_total_dissipated_power()},
            {"stored_energy_capacitive", energy.at("capacitive")},
            {"stored_energy_inertial", energy.at("inertial")},
            {"stored_energy_total", energy.at("total")},
            {"efficiency", std::abs(P_electrical) > 1e-6 ? (P_mechanical / P_electrical * 100.0) : 0.0}};
}

struct GeneralizedImpedance {
    std::complex<double> electrical_impedance;
    double electrical_magnitude = 0.0;
    double electrical_phase = 0.0;
    std::complex<double> mechanical_impedance;
    double mechanical_magnitude = 0.0;
    double mechanical_phase = 0.0;
};

inline GeneralizedImpedance get_generalized_impedance(const EMBondGraphMapping& mapping, double frequency) {
    const double omega = 2.0 * kPi * frequency;
    GeneralizedImpedance Z;
    Z.electrical_impedance = {mapping.electrical_resistance, omega * mapping.electrical_inductance};
    Z.mechanical_impedance = {mapping.mechanical_friction, omega * mapping.mechanical_inertia};
    Z.electrical_magnitude = std::abs(Z.electrical_impedance);
    Z.electrical_phase = std::arg(Z.electrical_impedance);
    Z.mechanical_magnitude = std::abs(Z.mechanical_impedance);
    Z.mechanical_phase = std::arg(Z.mechanical_impedance);
    return Z;
}

inline std::map<std::string, std::string> compute_energy_domain_equivalences(const EMBondGraphMapping& mapping) {
    return {{"electrical_mechanical_analogy",
             "Voltage (V) ↔ Torque (τ)\n"
             "Current (I) ↔ Angular Velocity (ω)\n"
             "Resistance (R) ↔ Friction (B)\n"
             "Inductance (L) ↔ Inertia (J)\n"
             "Flux Linkage (λ) ↔ Angular Momentum (L)\n"
             "Charge (Q) ↔ Angle (θ)"},
            {"power_conservation",
             "Electrical Power (P_e = V·I) ↔ Mechanical Power (P_m = τ·ω)\n"
             "Coupled through gyrator with ratio k = " +
                 std::to_string(mapping.torque_constant)},
            {"energy_storage",
             "Magnetic Energy (E_mag = ½LI²) ↔ Kinetic Energy (E_kin = ½Jω²)\n"
             "Both stored in I-elements (inertial elements)"},
            {"energy_dissipation",
             "Electrical Losses (P_R = RI²) ↔ Friction Losses (P_B = Bω²)\n"
             "Both dissipated in R-elements (resistive elements)"}};
}

class EMBondGraphSimulator {
public:
    EMBondGraphSimulator(BondGraphModel& model, EMBondGraphMapping mapping) : model_(model), mapping_(mapping) {}

    std::map<std::string, double> step(double voltage, double load_torque, double dt) {
        auto* R_s = element("stator_resistance");
        auto* L_s = dynamic_cast<InertialElement*>(element("stator_inductance"));
        auto* J = dynamic_cast<InertialElement*>(element("rotor_inertia"));
        (void)R_s;

        if (J) {
            const double omega = J->power_vars.flow;
            const double T_friction = mapping_.mechanical_friction * omega;
            double T_net = -load_torque - T_friction;
            if (L_s) {
                T_net += mapping_.torque_constant * L_s->power_vars.flow;
            }
            J->update_state(T_net, dt);
        }
        if (L_s) {
            const double current = L_s->power_vars.flow;
            const double V_resistive = mapping_.electrical_resistance * current;
            const double V_back_emf = J ? mapping_.voltage_constant * J->power_vars.flow : 0.0;
            L_s->update_state(voltage - V_resistive - V_back_emf, dt);
        }
        time_ += dt;

        std::map<std::string, double> state;
        if (J) {
            state["angular_velocity"] = J->power_vars.flow;
            state["angle"] = J->power_vars.displacement;
            state["angular_momentum"] = J->power_vars.momentum;
        }
        if (L_s) {
            state["current"] = L_s->power_vars.flow;
            state["flux_linkage"] = L_s->power_vars.momentum;
            state["charge"] = L_s->power_vars.displacement;
        }
        state["time"] = time_;
        return state;
    }

    double time() const { return time_; }

private:
    BondGraphElement* element(const std::string& name) {
        auto it = model_.elements.find(name);
        return it == model_.elements.end() ? nullptr : it->second.get();
    }

    BondGraphModel& model_;
    EMBondGraphMapping mapping_;
    double time_ = 0.0;
};

}  // namespace emec
