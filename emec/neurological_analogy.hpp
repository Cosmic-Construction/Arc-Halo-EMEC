#pragma once

// Cognitive ↔ electric, affective ↔ magnetic, behavioral ↔ mechanical analogy.
// The same bond-graph elements (R, C, I, GY) carry the mapping:
//   mental effort / thought flow          ↔ voltage / current
//   motivational force / emotional flow   ↔ MMF / flux rate
//   behavioral drive / action rate        ↔ torque / angular velocity

#include "emec/bond_graph.hpp"

#include <algorithm>
#include <map>
#include <string>
#include <vector>

namespace emec {

enum class NeurologicalDomain { COGNITIVE, AFFECTIVE, BEHAVIORAL, SENSORY, MEMORY, ATTENTION };

struct CognitiveFieldParameters {
    double mental_resistance = 1.0;
    double cognitive_inductance = 0.5;
    double attention_capacitance = 2.0;
    double processing_rate_max = 10.0;
    double mental_fatigue_rate = 0.1;
};

struct AffectiveFieldParameters {
    double emotional_intensity = 1.0;
    double affective_inertia = 0.8;
    double emotional_capacitance = 3.0;
    double motivation_strength = 5.0;
    double emotional_damping = 0.2;
};

struct BehavioralParameters {
    double behavioral_inertia = 1.0;
    double environmental_friction = 0.5;
    double action_threshold = 0.1;
    double habit_strength = 0.3;
    double fatigue_coefficient = 0.05;
};

struct PsychophysicalCoupling {
    double cognitive_to_behavior = 2.0;
    double affective_to_behavior = 1.5;
    double behavior_to_cognitive = 0.5;
    double behavior_to_affective = 0.3;
    double integration_time = 1.0;
};

class NeurologicalEnergyModel {
public:
    NeurologicalEnergyModel(CognitiveFieldParameters cognitive = {},
                            AffectiveFieldParameters affective = {},
                            BehavioralParameters behavioral = {},
                            PsychophysicalCoupling coupling = {})
        : cognitive_(cognitive),
          affective_(affective),
          behavioral_(behavioral),
          coupling_(coupling),
          bond_graph_(build_bond_graph()) {}

    const BondGraphModel& bond_graph() const { return bond_graph_; }
    BondGraphModel& bond_graph() { return bond_graph_; }
    const std::vector<std::map<std::string, double>>& state_history() const { return state_history_; }
    double time() const { return time_; }

    std::map<std::string, double> process_cognitive_input(double sensory_input, double attention_level, double dt) {
        const double mental_effort = sensory_input * attention_level;
        auto* cognitive_load = resistive("cognitive_load");
        auto* cognitive_momentum = inertial("cognitive_momentum");
        auto* attention_buffer = capacitive("attention_buffer");

        double cognitive_flow = cognitive_load
                                    ? cognitive_load->compute_flow(mental_effort)
                                    : mental_effort / (cognitive_.mental_resistance + 1e-6);
        cognitive_flow = std::min(std::max(cognitive_flow, 0.0), cognitive_.processing_rate_max);
        if (cognitive_momentum) {
            cognitive_momentum->update_state(mental_effort, dt);
        }
        if (attention_buffer) {
            attention_buffer->update_state(cognitive_flow, dt);
        }
        return {{"mental_effort", mental_effort},
                {"cognitive_flow", cognitive_flow},
                {"cognitive_state", cognitive_momentum ? cognitive_momentum->power_vars.momentum : 0.0},
                {"attention_load", attention_buffer ? attention_buffer->power_vars.displacement : 0.0}};
    }

    std::map<std::string, double> process_affective_state(double emotional_stimulus, double motivation, double dt) {
        const double affective_force = emotional_stimulus + motivation * affective_.motivation_strength;
        auto* emotional_regulation = resistive("emotional_regulation");
        auto* emotional_inertia = inertial("emotional_inertia");
        auto* emotional_buffer = capacitive("emotional_buffer");
        const double emotional_flow = emotional_regulation
                                          ? emotional_regulation->compute_flow(affective_force)
                                          : affective_force / (affective_.emotional_damping + 1e-6);
        if (emotional_inertia) {
            emotional_inertia->update_state(affective_force, dt);
        }
        if (emotional_buffer) {
            emotional_buffer->update_state(emotional_flow, dt);
        }
        return {{"affective_force", affective_force},
                {"emotional_flow", emotional_flow},
                {"emotional_state", emotional_inertia ? emotional_inertia->power_vars.momentum : 0.0},
                {"mood_level", emotional_buffer ? emotional_buffer->power_vars.displacement : 0.0}};
    }

    std::map<std::string, double> compute_behavioral_action(double cognitive_drive,
                                                           double affective_drive,
                                                           double task_load,
                                                           double dt) {
        const double behavioral_drive =
            coupling_.cognitive_to_behavior * cognitive_drive + coupling_.affective_to_behavior * affective_drive;
        auto* behavioral_inertia = inertial("behavioral_inertia");
        auto* habit_formation = capacitive("habit_formation");
        const double current_action_rate = behavioral_inertia ? behavioral_inertia->power_vars.flow : 0.0;
        const double friction_force = behavioral_.environmental_friction * current_action_rate;
        const double net_force = behavioral_drive - task_load - friction_force;
        double action_rate = 0.0;
        if (behavioral_inertia) {
            behavioral_inertia->update_state(net_force, dt);
            action_rate = behavioral_inertia->power_vars.flow;
        }
        if (habit_formation) {
            habit_formation->update_state(action_rate, dt);
        }
        return {{"behavioral_drive", behavioral_drive},
                {"action_rate", action_rate},
                {"performance", action_rate * task_load},
                {"habit_strength", habit_formation ? habit_formation->power_vars.displacement : 0.0},
                {"behavioral_momentum", behavioral_inertia ? behavioral_inertia->power_vars.momentum : 0.0}};
    }

    std::map<std::string, double> step(double sensory_input = 1.0,
                                       double attention_level = 0.8,
                                       double emotional_stimulus = 0.5,
                                       double motivation = 0.7,
                                       double task_load = 1.0,
                                       double dt = 0.01) {
        auto cognitive_state = process_cognitive_input(sensory_input, attention_level, dt);
        auto affective_state = process_affective_state(emotional_stimulus, motivation, dt);
        auto behavioral_state = compute_behavioral_action(
            cognitive_state["cognitive_flow"], affective_state["emotional_flow"], task_load, dt);
        const auto energy = bond_graph_.get_total_stored_energy();
        time_ += dt;
        std::map<std::string, double> state{{"time", time_}};
        state.insert(cognitive_state.begin(), cognitive_state.end());
        state.insert(affective_state.begin(), affective_state.end());
        state.insert(behavioral_state.begin(), behavioral_state.end());
        state["stored_energy"] = energy.at("total");
        state["power_dissipated"] = bond_graph_.get_total_dissipated_power();
        state_history_.push_back(state);
        return state;
    }

    std::map<std::string, std::string> get_analogy_mapping() const {
        return {{"electric_field_cognitive",
                 "ELECTRIC FIELD ↔ COGNITIVE FIELD\n"
                 "├─ Voltage → Mental Effort / Cognitive Potential\n"
                 "├─ Current → Thought Flow / Processing Rate\n"
                 "├─ Resistance → Cognitive Load / Mental Resistance\n"
                 "├─ Inductance → Cognitive Inertia / Mental Momentum\n"
                 "├─ Flux Linkage → Accumulated Cognitive State\n"
                 "└─ Charge → Integrated Thought"},
                {"magnetic_field_affective",
                 "MAGNETIC FIELD ↔ AFFECTIVE FIELD\n"
                 "├─ Magnetic Field → Emotional Field Intensity\n"
                 "├─ Magnetic Flux → Affective State Flux\n"
                 "├─ MMF → Motivational Force\n"
                 "├─ Magnetic Energy → Emotional Potential Energy\n"
                 "└─ Permeability → Emotional Susceptibility"},
                {"mechanical_behavioral",
                 "MECHANICAL DOMAIN ↔ BEHAVIORAL ACTION\n"
                 "├─ Torque → Behavioral Drive / Action Impulse\n"
                 "├─ Angular Velocity → Action Rate / Performance Velocity\n"
                 "├─ Inertia → Behavioral Inertia / Habit Strength\n"
                 "├─ Friction → Environmental Constraints\n"
                 "├─ Angular Momentum → Sustained Action Momentum\n"
                 "└─ Angle → Cumulative Behavior"},
                {"em_coupling_psychophysical",
                 "ELECTROMAGNETIC COUPLING ↔ PSYCHOPHYSICAL INTEGRATION\n"
                 "├─ E-field ↔ M-field → Cognitive ↔ Affective Interaction\n"
                 "├─ EM → Mechanical → Mental/Emotional → Behavioral\n"
                 "├─ Torque Constant → Cognitive-Behavioral Coupling\n"
                 "└─ Back-EMF → Behavioral Feedback to Cognition"},
                {"energy_conversion",
                 "ENERGY CONVERSION PROCESS\n"
                 "├─ Electrical Input → Cognitive Input (Attention, Sensory)\n"
                 "├─ Magnetic Field → Affective Modulation (Emotion, Motivation)\n"
                 "├─ Mechanical Output → Behavioral Output (Action, Performance)\n"
                 "├─ Efficiency → Psychomotor Efficiency\n"
                 "├─ Losses → Mental Fatigue + Emotional Regulation + Physical Constraints\n"
                 "└─ Stored Energy → Working Memory + Mood State + Habits"}};
    }

private:
    BondGraphModel build_bond_graph() const {
        BondGraphModel model("Neurological Energy System");
        model.add_resistive_element("cognitive_load", cognitive_.mental_resistance, EnergyDomain::NEUROLOGICAL);
        model.add_inertial_element("cognitive_momentum", cognitive_.cognitive_inductance, EnergyDomain::NEUROLOGICAL);
        model.add_capacitive_element("attention_buffer", cognitive_.attention_capacitance, EnergyDomain::NEUROLOGICAL);
        model.add_resistive_element("emotional_regulation", affective_.emotional_damping, EnergyDomain::NEUROLOGICAL);
        model.add_inertial_element("emotional_inertia", affective_.affective_inertia, EnergyDomain::NEUROLOGICAL);
        model.add_capacitive_element("emotional_buffer", affective_.emotional_capacitance, EnergyDomain::NEUROLOGICAL);
        model.add_resistive_element("behavioral_friction", behavioral_.environmental_friction, EnergyDomain::NEUROLOGICAL);
        model.add_inertial_element("behavioral_inertia", behavioral_.behavioral_inertia, EnergyDomain::NEUROLOGICAL);
        model.add_capacitive_element("habit_formation", behavioral_.habit_strength, EnergyDomain::NEUROLOGICAL);
        model.add_gyrator("cognitive_behavioral_coupling", coupling_.cognitive_to_behavior);
        model.add_gyrator("affective_behavioral_coupling", coupling_.affective_to_behavior);
        return model;
    }

    ResistiveElement* resistive(const std::string& name) {
        auto it = bond_graph_.elements.find(name);
        if (it == bond_graph_.elements.end() || it->second->kind() != ElementKind::Resistive) {
            return nullptr;
        }
        return static_cast<ResistiveElement*>(it->second.get());
    }

    InertialElement* inertial(const std::string& name) {
        auto it = bond_graph_.elements.find(name);
        if (it == bond_graph_.elements.end() || it->second->kind() != ElementKind::Inertial) {
            return nullptr;
        }
        return static_cast<InertialElement*>(it->second.get());
    }

    CapacitiveElement* capacitive(const std::string& name) {
        auto it = bond_graph_.elements.find(name);
        if (it == bond_graph_.elements.end() || it->second->kind() != ElementKind::Capacitive) {
            return nullptr;
        }
        return static_cast<CapacitiveElement*>(it->second.get());
    }

    CognitiveFieldParameters cognitive_;
    AffectiveFieldParameters affective_;
    BehavioralParameters behavioral_;
    PsychophysicalCoupling coupling_;
    BondGraphModel bond_graph_;
    double time_ = 0.0;
    std::vector<std::map<std::string, double>> state_history_;
};

}  // namespace emec
