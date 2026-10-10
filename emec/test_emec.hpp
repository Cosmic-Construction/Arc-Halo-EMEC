#pragma once

// C++ counterpart of emec/test_emec.py.
// Build: g++ -std=c++17 -Wall -Wextra -pthread -I. -DEMEC_TEST_EMEC_MAIN -x c++ emec/test_emec.hpp -o /tmp/test_emec

#include "emec/em_field_solver.hpp"
#include "emec/polyphase_winding.hpp"
#include "emec/rotor_dynamics.hpp"
#include "emec/stator_dynamics.hpp"
#include "emec/virtual_engine.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace emec {
namespace test_emec {

inline int g_failed = 0;

inline void expect(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

inline bool close(double a, double b, double tol = 1e-10) { return std::abs(a - b) <= tol; }

inline bool test_em_field_solver() {
    std::cout << "Testing EM Field Solver...\n";
    EMFieldSolver solver;
    Vec current{1.0, 2.0, 3.0};
    Vec B = solver.compute_magnetic_flux_density(current, 1.0);
    expect(B.size() == current.size(), "B field shape mismatch");
    Vec abc{1.0, -0.5, -0.5};
    Vec dq0 = EMFieldSolver::park_transform(abc, 0.0);
    expect(dq0.size() == 3, "dq0 transform size incorrect");
    Vec abc_back = EMFieldSolver::inverse_park_transform(dq0, 0.0);
    expect(abc_back.size() == 3, "inverse Park size incorrect");
    expect(close(abc[0], abc_back[0]) && close(abc[1], abc_back[1]) && close(abc[2], abc_back[2]),
           "Park transform not invertible");
    EMFieldState state = solver.solve_field_step(current, 100.0, 1e-4);
    expect(state.time >= 0.0, "State time invalid");
    std::cout << "  ✓ EM Field Solver tests passed\n";
    return true;
}

inline bool test_polyphase_winding() {
    std::cout << "Testing Polyphase Winding Model...\n";
    PolyphaseWindingModel winding(WindingParameters{}, WindingParameters{});
    expect(winding.L_ss().rows() == 3 && winding.L_ss().cols() == 3, "Stator inductance matrix wrong shape");
    expect(winding.L_rr().rows() == 3 && winding.L_rr().cols() == 3, "Rotor inductance matrix wrong shape");
    Mat L_sr = winding.compute_mutual_inductance(0.0);
    expect(L_sr.rows() == 3 && L_sr.cols() == 3, "Mutual inductance matrix wrong shape");
    FluxLinkages flux = winding.compute_flux_linkage(Vec{1.0, -0.5, -0.5}, Vec{0.5, -0.25, -0.25}, 0.0);
    expect(flux.stator.size() == 3, "Stator flux wrong shape");
    const double k_w = winding.compute_winding_factor();
    expect(k_w > 0.0 && k_w <= 1.0, "Winding factor out of range");
    std::cout << "  ✓ Polyphase Winding Model tests passed\n";
    return true;
}

inline bool test_rotor_dynamics() {
    std::cout << "Testing Rotor Dynamics...\n";
    RotorParameters params;
    RotorDynamics rotor(params);
    expect(rotor.state().angular_velocity == 0.0, "Initial velocity not zero");
    expect(rotor.state().angle == 0.0, "Initial angle not zero");
    expect(rotor.compute_friction_torque(100.0) > 0.0, "Friction torque should be positive");
    RotorState state = rotor.solve_dynamics(10.0, 0.001);
    expect(state.angular_velocity > 0.0, "Velocity should increase with positive torque");
    expect(state.time > 0.0, "Time not advancing");
    expect(close(rotor.get_electrical_angle(), params.pole_pairs * state.angle), "Electrical angle incorrect");
    const double slip = rotor.get_slip(50.0);
    expect(slip >= -1.0 && slip <= 2.0, "Slip out of reasonable range");
    expect(rotor.get_kinetic_energy() >= 0.0, "Kinetic energy should be non-negative");
    std::cout << "  ✓ Rotor Dynamics tests passed\n";
    return true;
}

inline bool test_stator_dynamics() {
    std::cout << "Testing Stator Dynamics...\n";
    StatorDynamics stator(StatorParameters{});
    Vec V = stator.generate_balanced_voltage(100.0, 50.0, 0.0);
    expect(V.size() == 3, "Voltage vector wrong shape");
    expect(std::abs(V[0]) < 1e-10, "Phase A voltage should be ~0 at t=0");
    Vec V_supply = stator.compute_supply_voltage(0.0);
    expect(V_supply.size() == 3, "Supply voltage wrong shape");
    Vec I = stator.solve_current_dynamics(V_supply, Vec{0.01, 0.01, 0.01}, Vec{0.0, 0.0, 0.0}, 1e-4);
    expect(I.size() == 3, "Current wrong shape");
    StatorState state = stator.update_state(I, V_supply, 1e-4);
    expect(state.time > 0.0, "Time not advancing");
    StatorPower power = stator.compute_power();
    expect(std::isfinite(power.instantaneous) && std::isfinite(power.power_factor), "Power computation invalid");
    expect(stator.compute_losses().copper >= 0.0, "Copper losses should be non-negative");
    std::cout << "  ✓ Stator Dynamics tests passed\n";
    return true;
}

inline bool test_engine_parameters() {
    std::cout << "Testing Engine Parameters...\n";
    EngineParameters params = EngineParameters::create_default();
    expect(params.stator_winding.num_phases == 3, "Wrong number of phases");
    expect(params.rotor_mechanical.pole_pairs > 0, "Invalid pole pairs");
    expect(params.time_step > 0.0, "Invalid time step");
    expect(EngineParameters::create_default(20000.0).time_step > 0.0, "Failed to create high power parameters");
    std::cout << "  ✓ Engine Parameters tests passed\n";
    return true;
}

inline bool test_virtual_engine_basic() {
    std::cout << "Testing Virtual Engine (Basic)...\n";
    VirtualEngine engine;
    SimulationState state = engine.step(1e-4);
    expect(state.time > 0.0, "Time not advancing");
    expect(std::isfinite(state.torque), "Torque not computed");
    engine.reset();
    expect(engine.current_time() == 0.0, "Engine not reset");
    expect(engine.history().empty(), "History not cleared");
    std::cout << "  ✓ Virtual Engine (Basic) tests passed\n";
    return true;
}

inline bool test_virtual_engine_simulation() {
    std::cout << "Testing Virtual Engine (Simulation)...\n";
    VirtualEngine engine;
    engine.set_load_torque([](double, double) { return 5.0; });
    auto states = engine.simulate(0.1, 1e-4);
    expect(!states.empty(), "No states generated");
    expect(states.size() == engine.history().size(), "History length mismatch");
    auto metrics = engine.get_performance_metrics();
    expect(metrics.count("avg_torque") && metrics.count("avg_efficiency"), "Missing metrics");
    expect(metrics["simulation_time"] > 0.0, "Simulation time not recorded");
    std::cout << "  ✓ Virtual Engine (Simulation) tests passed\n";
    return true;
}

inline bool test_virtual_engine_data_export() {
    std::cout << "Testing Virtual Engine (Data Export)...\n";
    VirtualEngine engine;
    engine.set_load_torque([](double, double) { return 3.0; });
    engine.simulate(0.05, 1e-4);
    auto data = engine.export_data();
    expect(data.count("time") && data.count("speed_rpm") && data.count("torque") && data.count("efficiency"),
           "Missing export channels");
    expect(data["speed_rpm"].size() == data["time"].size(), "Speed data shape mismatch");
    expect(data["torque"].size() == data["time"].size(), "Torque data shape mismatch");
    std::cout << "  ✓ Virtual Engine (Data Export) tests passed\n";
    return true;
}

inline bool run_all_tests() {
    std::cout << "\n======================================================================\n";
    std::cout << "Running Virtual Engine EMEC Simulator Tests\n";
    std::cout << "======================================================================\n\n";
    using TestFn = bool (*)();
    TestFn tests[] = {test_em_field_solver,         test_polyphase_winding, test_rotor_dynamics,
                      test_stator_dynamics,         test_engine_parameters, test_virtual_engine_basic,
                      test_virtual_engine_simulation, test_virtual_engine_data_export};
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
    g_failed = failed;
    return failed == 0;
}

}  // namespace test_emec
}  // namespace emec

#ifdef EMEC_TEST_EMEC_MAIN
int main() {
    const bool ok = emec::test_emec::run_all_tests();
    return ok ? 0 : 1;
}
#endif
