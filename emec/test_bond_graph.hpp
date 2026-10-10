#pragma once

// C++ counterpart of emec/test_bond_graph.py (18 tests).
// Build: g++ -std=c++17 -Wall -Wextra -pthread -I. -DEMEC_TEST_BOND_GRAPH_MAIN -x c++ emec/test_bond_graph.hpp -o /tmp/test_bond_graph

#include "emec/bond_graph.hpp"
#include "emec/em_bond_graph_mapping.hpp"
#include "emec/neurological_analogy.hpp"
#include "emec/virtual_engine.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace emec {
namespace test_bond_graph {

inline void expect(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

inline bool close(double a, double b, double tol = 1e-9) { return std::abs(a - b) <= tol; }

inline bool test_power_variables() {
    std::cout << "Testing Power Variables...\n";
    PowerVariables pv;
    pv.effort = 10.0;
    pv.flow = 2.0;
    expect(close(pv.power(), 20.0), "Power calculation incorrect");
    pv.update_integrals(0.1);
    expect(close(pv.momentum, 1.0), "Momentum integration incorrect");
    expect(close(pv.displacement, 0.2), "Displacement integration incorrect");
    std::cout << "  ✓ Power Variables tests passed\n";
    return true;
}

inline bool test_resistive_element() {
    std::cout << "Testing Resistive Element...\n";
    ResistiveElement R("test_resistor", 10.0, EnergyDomain::ELECTRICAL);
    expect(close(R.compute_effort(2.0), 20.0), "Effort calculation incorrect");
    expect(close(R.compute_flow(30.0), 3.0), "Flow calculation incorrect");
    R.power_vars.flow = 2.0;
    expect(close(R.dissipated_power(), 40.0), "Power dissipation incorrect");
    std::cout << "  ✓ Resistive Element tests passed\n";
    return true;
}

inline bool test_capacitive_element() {
    std::cout << "Testing Capacitive Element...\n";
    CapacitiveElement C("test_capacitor", 0.01, EnergyDomain::ELECTRICAL);
    C.update_state(1.0, 0.1);
    expect(close(C.power_vars.displacement, 0.1), "Displacement update incorrect");
    expect(close(C.compute_effort(), 0.1 / 0.01, 1e-6), "Effort calculation incorrect");
    expect(close(C.stored_energy(), 0.5 * 0.1 * 0.1 / 0.01, 1e-6), "Stored energy incorrect");
    std::cout << "  ✓ Capacitive Element tests passed\n";
    return true;
}

inline bool test_inertial_element() {
    std::cout << "Testing Inertial Element...\n";
    InertialElement I("test_inductor", 0.1, EnergyDomain::ELECTRICAL);
    I.update_state(5.0, 0.1);
    expect(close(I.power_vars.momentum, 0.5), "Momentum update incorrect");
    expect(close(I.compute_flow(), 0.5 / 0.1), "Flow calculation incorrect");
    expect(close(I.stored_energy(), 0.5 * 0.5 * 0.5 / 0.1, 1e-6), "Stored energy incorrect");
    std::cout << "  ✓ Inertial Element tests passed\n";
    return true;
}

inline bool test_transformer_element() {
    std::cout << "Testing Transformer Element...\n";
    TransformerElement TF("test_transformer", 2.0);
    TF.transform_forward(10.0, 3.0);
    expect(close(TF.power_vars_2.effort, 20.0), "Effort transformation incorrect");
    expect(close(TF.power_vars_1.flow, 6.0), "Flow transformation incorrect");
    expect(close(TF.power_vars_1.power(), TF.power_vars_2.power()), "Power not conserved in transformer");
    std::cout << "  ✓ Transformer Element tests passed\n";
    return true;
}

inline bool test_gyrator_element() {
    std::cout << "Testing Gyrator Element...\n";
    GyratorElement GY("test_gyrator", 5.0);
    GY.gyrate_forward(2.0, 3.0);
    expect(close(GY.power_vars_2.effort, 10.0), "Gyrator effort_2 incorrect");
    expect(close(GY.power_vars_1.effort, 15.0), "Gyrator effort_1 incorrect");
    expect(std::isfinite(GY.compute_power_transfer()), "Power transfer computed");
    std::cout << "  ✓ Gyrator Element tests passed\n";
    return true;
}

inline bool test_bond_graph_model() {
    std::cout << "Testing Bond Graph Model...\n";
    BondGraphModel model("Test Model");
    model.add_resistive_element("R1", 10.0);
    model.add_capacitive_element("C1", 0.01);
    model.add_inertial_element("I1", 0.1);
    model.add_transformer("TF1", 2.0);
    model.add_gyrator("GY1", 3.0);
    expect(model.elements.size() == 3, "Element count incorrect");
    expect(model.transformers.size() == 1, "Transformer count incorrect");
    expect(model.gyrators.size() == 1, "Gyrator count incorrect");
    model.elements["R1"]->power_vars.flow = 2.0;
    model.elements["R1"]->power_vars.effort = 20.0;
    auto energy = model.get_total_stored_energy();
    expect(energy.count("total") && energy.count("capacitive") && energy.count("inertial"), "Energy dictionary incomplete");
    expect(model.get_total_dissipated_power() >= 0.0, "Power dissipation should be non-negative");
    std::cout << "  ✓ Bond Graph Model tests passed\n";
    return true;
}

inline bool test_em_bond_graph_mapping() {
    std::cout << "Testing EM Bond Graph Mapping...\n";
    auto created = create_em_bond_graph_from_engine(EngineParameters::create_default(5000.0));
    expect(created.first.name == "Induction Motor Bond Graph", "Model name incorrect");
    expect(created.first.elements.count("stator_resistance"), "Stator resistance missing");
    expect(created.first.elements.count("stator_inductance"), "Stator inductance missing");
    expect(created.first.elements.count("rotor_friction"), "Rotor friction missing");
    expect(created.first.elements.count("rotor_inertia"), "Rotor inertia missing");
    expect(created.first.gyrators.count("em_coupling"), "EM coupling gyrator missing");
    expect(created.second.electrical_resistance > 0.0, "Electrical resistance invalid");
    expect(created.second.mechanical_inertia > 0.0, "Mechanical inertia invalid");
    expect(created.second.torque_constant > 0.0, "Torque constant invalid");
    std::cout << "  ✓ EM Bond Graph Mapping tests passed\n";
    return true;
}

inline bool test_generalized_impedance() {
    std::cout << "Testing Generalized Impedance...\n";
    auto created = create_em_bond_graph_from_engine(EngineParameters::create_default());
    GeneralizedImpedance Z = get_generalized_impedance(created.second, 50.0);
    expect(Z.electrical_magnitude > 0.0, "Electrical magnitude invalid");
    expect(Z.mechanical_magnitude > 0.0, "Mechanical magnitude invalid");
    std::cout << "  ✓ Generalized Impedance tests passed\n";
    return true;
}

inline bool test_power_flow_analysis() {
    std::cout << "Testing Power Flow Analysis...\n";
    auto created = create_em_bond_graph_from_engine(EngineParameters::create_default());
    auto analysis = analyze_power_flow(created.first, 400.0, 10.0, 20.0, 157.08);
    expect(analysis.count("electrical_input_power") && analysis.count("mechanical_output_power") && analysis.count("efficiency"),
           "Power flow keys missing");
    expect(analysis["electrical_input_power"] > 0.0, "Electrical power should be positive");
    expect(analysis["mechanical_output_power"] > 0.0, "Mechanical power should be positive");
    expect(analysis["efficiency"] >= 0.0 && analysis["efficiency"] <= 100.0, "Efficiency out of range");
    std::cout << "  ✓ Power Flow Analysis tests passed\n";
    return true;
}

inline bool test_bond_graph_simulator() {
    std::cout << "Testing Bond Graph Simulator...\n";
    auto created = create_em_bond_graph_from_engine(EngineParameters::create_default());
    EMBondGraphSimulator simulator(created.first, created.second);
    std::map<std::string, double> state;
    for (int i = 0; i < 10; ++i) {
        state = simulator.step(400.0, 10.0, 0.001);
    }
    expect(state.count("time") && state["time"] > 0.0, "Time not advancing");
    std::cout << "  ✓ Bond Graph Simulator tests passed\n";
    return true;
}

inline bool test_neurological_model_basic() {
    std::cout << "Testing Neurological Model (Basic)...\n";
    NeurologicalEnergyModel model;
    expect(model.bond_graph().name == "Neurological Energy System", "Model name incorrect");
    expect(!model.bond_graph().elements.empty(), "No elements in bond graph");
    auto state = model.step();
    expect(state.count("mental_effort") && state.count("cognitive_flow") && state.count("behavioral_drive") &&
               state.count("performance"),
           "Basic neurological state incomplete");
    std::cout << "  ✓ Neurological Model (Basic) tests passed\n";
    return true;
}

inline bool test_cognitive_processing() {
    std::cout << "Testing Cognitive Processing...\n";
    CognitiveFieldParameters cognitive;
    cognitive.mental_resistance = 1.0;
    cognitive.cognitive_inductance = 0.5;
    cognitive.processing_rate_max = 10.0;
    NeurologicalEnergyModel model(cognitive);
    auto state = model.process_cognitive_input(2.0, 0.8, 0.01);
    expect(close(state["mental_effort"], 1.6), "Mental effort calculation incorrect");
    expect(state["cognitive_flow"] <= cognitive.processing_rate_max, "Flow exceeds max");
    std::cout << "  ✓ Cognitive Processing tests passed\n";
    return true;
}

inline bool test_affective_processing() {
    std::cout << "Testing Affective Processing...\n";
    AffectiveFieldParameters affective;
    affective.emotional_intensity = 1.0;
    affective.motivation_strength = 5.0;
    NeurologicalEnergyModel model({}, affective);
    auto state = model.process_affective_state(0.5, 0.7, 0.01);
    expect(state.count("affective_force") && state.count("emotional_flow") && state.count("emotional_state"),
           "Affective state incomplete");
    std::cout << "  ✓ Affective Processing tests passed\n";
    return true;
}

inline bool test_behavioral_action() {
    std::cout << "Testing Behavioral Action...\n";
    BehavioralParameters behavioral;
    behavioral.behavioral_inertia = 1.0;
    behavioral.environmental_friction = 0.5;
    NeurologicalEnergyModel model({}, {}, behavioral);
    auto state = model.compute_behavioral_action(2.0, 1.5, 1.0, 0.01);
    expect(state.count("behavioral_drive") && state.count("action_rate") && state.count("performance"),
           "Behavioral state incomplete");
    std::cout << "  ✓ Behavioral Action tests passed\n";
    return true;
}

inline bool test_neurological_simulation() {
    std::cout << "Testing Neurological Simulation...\n";
    NeurologicalEnergyModel model;
    std::map<std::string, double> state;
    for (int i = 0; i < 50; ++i) {
        state = model.step(1.0, 0.8, 0.5, 0.7, 1.0, 0.01);
    }
    expect(model.state_history().size() == 50, "State history count incorrect");
    expect(state["time"] > 0.0, "Time not advancing");
    expect(state.count("stored_energy") && state.count("power_dissipated"), "Energy channels missing");
    std::cout << "  ✓ Neurological Simulation tests passed\n";
    return true;
}

inline bool test_analogy_mapping() {
    std::cout << "Testing Analogy Mapping...\n";
    auto mapping = NeurologicalEnergyModel().get_analogy_mapping();
    expect(mapping.count("electric_field_cognitive") && mapping.count("magnetic_field_affective") &&
               mapping.count("mechanical_behavioral") && mapping.count("em_coupling_psychophysical") &&
               mapping.count("energy_conversion"),
           "Analogy mapping incomplete");
    std::cout << "  ✓ Analogy Mapping tests passed\n";
    return true;
}

inline bool test_psychophysical_coupling() {
    std::cout << "Testing Psychophysical Coupling...\n";
    PsychophysicalCoupling weak;
    weak.cognitive_to_behavior = 0.5;
    weak.affective_to_behavior = 0.3;
    PsychophysicalCoupling strong;
    strong.cognitive_to_behavior = 4.0;
    strong.affective_to_behavior = 3.0;
    NeurologicalEnergyModel model_weak({}, {}, {}, weak);
    NeurologicalEnergyModel model_strong({}, {}, {}, strong);
    std::map<std::string, double> state_weak;
    std::map<std::string, double> state_strong;
    for (int i = 0; i < 10; ++i) {
        state_weak = model_weak.step(1.0, 1.0, 0.0, 0.0, 0.0, 0.01);
        state_strong = model_strong.step(1.0, 1.0, 0.0, 0.0, 0.0, 0.01);
    }
    expect(state_strong["action_rate"] >= state_weak["action_rate"], "Strong coupling should produce higher action rate");
    std::cout << "  ✓ Psychophysical Coupling tests passed\n";
    return true;
}

inline bool run_all_tests() {
    std::cout << "\n======================================================================\n";
    std::cout << "Running Bond Graph and Neurological Analogy Tests\n";
    std::cout << "======================================================================\n\n";
    using TestFn = bool (*)();
    TestFn tests[] = {test_power_variables,       test_resistive_element,      test_capacitive_element,
                      test_inertial_element,      test_transformer_element,    test_gyrator_element,
                      test_bond_graph_model,      test_em_bond_graph_mapping,  test_generalized_impedance,
                      test_power_flow_analysis,   test_bond_graph_simulator,   test_neurological_model_basic,
                      test_cognitive_processing,  test_affective_processing,   test_behavioral_action,
                      test_neurological_simulation, test_analogy_mapping,      test_psychophysical_coupling};
    int passed = 0;
    int failed = 0;
    for (TestFn test : tests) {
        try {
            if (test()) {
                ++passed;
            }
        } catch (const std::exception& error) {
            std::cout << "  ✗ failed: " << error.what() << "\n";
            ++failed;
        }
    }
    std::cout << "\n======================================================================\n";
    std::cout << "Test Results: " << passed << " passed, " << failed << " failed\n";
    std::cout << "======================================================================\n";
    return failed == 0;
}

}  // namespace test_bond_graph
}  // namespace emec

#ifdef EMEC_TEST_BOND_GRAPH_MAIN
int main() { return emec::test_bond_graph::run_all_tests() ? 0 : 1; }
#endif
