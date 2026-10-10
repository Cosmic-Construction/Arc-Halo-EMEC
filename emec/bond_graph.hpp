#pragma once

// Bond-graph energy model.
// Power = effort × flow. Elements keep their constitutive names:
//   R  e = R·f          dissipates
//   C  e = q/C, q̇ = f   stores potential energy
//   I  f = p/I, ṗ = e   stores kinetic energy
//   TF e2 = n·e1, f1 = n·f2
//   GY e2 = r·f1, e1 = r·f2

#include <map>
#include <memory>
#include <string>

namespace emec {

enum class EnergyDomain {
    ELECTRICAL,
    MECHANICAL_TRANSLATION,
    MECHANICAL_ROTATION,
    HYDRAULIC,
    THERMAL,
    MAGNETIC,
    NEUROLOGICAL,
    GENERIC
};

inline const char* energy_domain_name(EnergyDomain domain) {
    switch (domain) {
        case EnergyDomain::ELECTRICAL: return "electrical";
        case EnergyDomain::MECHANICAL_TRANSLATION: return "mechanical_translation";
        case EnergyDomain::MECHANICAL_ROTATION: return "mechanical_rotation";
        case EnergyDomain::HYDRAULIC: return "hydraulic";
        case EnergyDomain::THERMAL: return "thermal";
        case EnergyDomain::MAGNETIC: return "magnetic";
        case EnergyDomain::NEUROLOGICAL: return "neurological";
        case EnergyDomain::GENERIC: return "generic";
    }
    return "generic";
}

struct PowerVariables {
    double effort = 0.0;
    double flow = 0.0;
    double momentum = 0.0;
    double displacement = 0.0;

    double power() const { return effort * flow; }

    void update_integrals(double dt) {
        momentum += effort * dt;
        displacement += flow * dt;
    }
};

struct DomainMapping {
    EnergyDomain domain = EnergyDomain::GENERIC;
    std::string effort_name;
    std::string flow_name;
    std::string momentum_name;
    std::string displacement_name;
    std::string effort_unit;
    std::string flow_unit;
    std::string momentum_unit;
    std::string displacement_unit;
    std::string description;
    double effort_scale = 1.0;
    double flow_scale = 1.0;
};

inline const std::map<EnergyDomain, DomainMapping>& domain_mappings() {
    static const std::map<EnergyDomain, DomainMapping> mappings = {
        {EnergyDomain::ELECTRICAL,
         {EnergyDomain::ELECTRICAL, "voltage", "current", "flux_linkage", "charge", "V", "A", "Wb", "C",
          "Electrical domain: voltage-current conjugate pair", 1.0, 1.0}},
        {EnergyDomain::MECHANICAL_TRANSLATION,
         {EnergyDomain::MECHANICAL_TRANSLATION, "force", "velocity", "momentum", "position", "N", "m/s", "N·s", "m",
          "Mechanical translation: force-velocity conjugate pair", 1.0, 1.0}},
        {EnergyDomain::MECHANICAL_ROTATION,
         {EnergyDomain::MECHANICAL_ROTATION, "torque", "angular_velocity", "angular_momentum", "angle", "N·m", "rad/s",
          "N·m·s", "rad", "Mechanical rotation: torque-angular velocity conjugate pair", 1.0, 1.0}},
        {EnergyDomain::MAGNETIC,
         {EnergyDomain::MAGNETIC, "magnetomotive_force", "flux_rate", "flux", "flux_linkage", "A·turns", "Wb/s", "Wb",
          "Wb·turns", "Magnetic domain: MMF-flux rate conjugate pair", 1.0, 1.0}},
    };
    return mappings;
}

enum class ElementKind { Base, Resistive, Capacitive, Inertial };

class BondGraphElement {
public:
    BondGraphElement(std::string name, EnergyDomain domain = EnergyDomain::GENERIC)
        : name(std::move(name)), domain(domain) {}
    virtual ~BondGraphElement() = default;

    virtual ElementKind kind() const { return ElementKind::Base; }
    double compute_power() const { return power_vars.power(); }

    std::map<std::string, double> get_state() const {
        return {{"effort", power_vars.effort},
                {"flow", power_vars.flow},
                {"momentum", power_vars.momentum},
                {"displacement", power_vars.displacement},
                {"power", compute_power()}};
    }

    std::string name;
    EnergyDomain domain;
    PowerVariables power_vars;
};

class ResistiveElement : public BondGraphElement {
public:
    ResistiveElement(std::string name, double resistance, EnergyDomain domain = EnergyDomain::GENERIC)
        : BondGraphElement(std::move(name), domain), resistance(resistance) {}

    ElementKind kind() const override { return ElementKind::Resistive; }

    double compute_effort(double flow) {
        power_vars.flow = flow;
        power_vars.effort = resistance * flow;
        return power_vars.effort;
    }

    double compute_flow(double effort) {
        power_vars.effort = effort;
        power_vars.flow = effort / (resistance + 1e-12);
        return power_vars.flow;
    }

    double dissipated_power() const { return resistance * power_vars.flow * power_vars.flow; }

    double resistance;
};

class CapacitiveElement : public BondGraphElement {
public:
    CapacitiveElement(std::string name, double capacitance, EnergyDomain domain = EnergyDomain::GENERIC)
        : BondGraphElement(std::move(name), domain), capacitance(capacitance) {}

    ElementKind kind() const override { return ElementKind::Capacitive; }

    double compute_effort() {
        power_vars.effort = power_vars.displacement / (capacitance + 1e-12);
        return power_vars.effort;
    }

    void update_state(double flow, double dt) {
        power_vars.flow = flow;
        power_vars.displacement += flow * dt;
        compute_effort();
    }

    double stored_energy() const {
        return 0.5 * power_vars.displacement * power_vars.displacement / (capacitance + 1e-12);
    }

    double capacitance;
};

class InertialElement : public BondGraphElement {
public:
    InertialElement(std::string name, double inertance, EnergyDomain domain = EnergyDomain::GENERIC)
        : BondGraphElement(std::move(name), domain), inertance(inertance) {}

    ElementKind kind() const override { return ElementKind::Inertial; }

    double compute_flow() {
        power_vars.flow = power_vars.momentum / (inertance + 1e-12);
        return power_vars.flow;
    }

    void update_state(double effort, double dt) {
        power_vars.effort = effort;
        power_vars.momentum += effort * dt;
        compute_flow();
    }

    double stored_energy() const {
        return 0.5 * power_vars.momentum * power_vars.momentum / (inertance + 1e-12);
    }

    double inertance;
};

class TransformerElement {
public:
    TransformerElement(std::string name, double ratio) : name(std::move(name)), ratio(ratio) {}

    void transform_forward(double effort_1, double flow_2) {
        power_vars_1.effort = effort_1;
        power_vars_2.flow = flow_2;
        power_vars_2.effort = ratio * effort_1;
        power_vars_1.flow = ratio * flow_2;
    }

    void transform_backward(double effort_2, double flow_1) {
        power_vars_2.effort = effort_2;
        power_vars_1.flow = flow_1;
        power_vars_1.effort = effort_2 / (ratio + 1e-12);
        power_vars_2.flow = flow_1 / (ratio + 1e-12);
    }

    std::string name;
    double ratio;
    PowerVariables power_vars_1;
    PowerVariables power_vars_2;
};

class GyratorElement {
public:
    GyratorElement(std::string name, double gyration_ratio)
        : name(std::move(name)), gyration_ratio(gyration_ratio) {}

    void gyrate_forward(double flow_1, double flow_2) {
        power_vars_1.flow = flow_1;
        power_vars_2.flow = flow_2;
        power_vars_2.effort = gyration_ratio * flow_1;
        power_vars_1.effort = gyration_ratio * flow_2;
    }

    double compute_power_transfer() const { return power_vars_1.power() + power_vars_2.power(); }

    std::string name;
    double gyration_ratio;
    PowerVariables power_vars_1;
    PowerVariables power_vars_2;
};

class BondGraphModel {
public:
    explicit BondGraphModel(std::string name = "Bond Graph Model") : name(std::move(name)) {}

    void add_resistive_element(const std::string& element_name,
                               double resistance,
                               EnergyDomain domain = EnergyDomain::GENERIC) {
        elements[element_name] = std::make_unique<ResistiveElement>(element_name, resistance, domain);
    }

    void add_capacitive_element(const std::string& element_name,
                                double capacitance,
                                EnergyDomain domain = EnergyDomain::GENERIC) {
        elements[element_name] = std::make_unique<CapacitiveElement>(element_name, capacitance, domain);
    }

    void add_inertial_element(const std::string& element_name,
                              double inertance,
                              EnergyDomain domain = EnergyDomain::GENERIC) {
        elements[element_name] = std::make_unique<InertialElement>(element_name, inertance, domain);
    }

    void add_transformer(const std::string& element_name, double ratio) {
        transformers.emplace(element_name, TransformerElement(element_name, ratio));
    }

    void add_gyrator(const std::string& element_name, double gyration_ratio) {
        gyrators.emplace(element_name, GyratorElement(element_name, gyration_ratio));
    }

    std::map<std::string, double> get_total_stored_energy() const {
        double capacitive = 0.0;
        double inertial = 0.0;
        for (const auto& entry : elements) {
            if (entry.second->kind() == ElementKind::Capacitive) {
                capacitive += static_cast<const CapacitiveElement&>(*entry.second).stored_energy();
            } else if (entry.second->kind() == ElementKind::Inertial) {
                inertial += static_cast<const InertialElement&>(*entry.second).stored_energy();
            }
        }
        return {{"capacitive", capacitive}, {"inertial", inertial}, {"total", capacitive + inertial}};
    }

    double get_total_dissipated_power() const {
        double power = 0.0;
        for (const auto& entry : elements) {
            if (entry.second->kind() == ElementKind::Resistive) {
                power += static_cast<const ResistiveElement&>(*entry.second).dissipated_power();
            }
        }
        return power;
    }

    std::string name;
    std::map<std::string, std::unique_ptr<BondGraphElement>> elements;
    std::map<std::string, TransformerElement> transformers;
    std::map<std::string, GyratorElement> gyrators;
};

}  // namespace emec
