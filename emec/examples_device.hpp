#pragma once

// End-to-end examples for the C++ virtual hardware device.
// Build: g++ -std=c++17 -pthread -I. -DEMEC_EXAMPLES_DEVICE_MAIN -x c++ emec/examples_device.hpp -o /tmp/examples_device

#include "emec/device/device.hpp"
#include "emec/device/server.hpp"

#include <iostream>
#include <string>

namespace emec {

inline void example_startup_transient() {
    std::cout << "\n======================================================================\n";
    std::cout << "Example 1: Startup Transient via Register Map\n";
    std::cout << "======================================================================\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 100);
    device.power_on();
    device.write_register(Register::VOLTAGE_SETPOINT, 400.0);
    device.write_register(Register::FREQUENCY_SETPOINT, 50.0);
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 10.0);
    device.start();
    device.run(0.3);
    std::cout << "  State:      " << std::get<std::string>(device.read_register(Register::DEVICE_STATE)) << "\n";
    std::cout << "  Speed:      " << device.read_number(Register::SPEED_RPM) << " rpm\n";
    std::cout << "  Torque:     " << device.read_number(Register::TORQUE) << " N·m\n";
    std::cout << "  Efficiency: " << device.read_number(Register::EFFICIENCY) << " %\n";
    device.stop();
}

inline void example_load_step() {
    std::cout << "\n======================================================================\n";
    std::cout << "Example 2: Load-Step Response\n";
    std::cout << "======================================================================\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 100);
    device.power_on();
    device.write_register("LOAD_TORQUE_SETPOINT", 5.0);
    device.start();
    device.run(0.3);
    const double speed_before = device.read_number("SPEED_RPM");
    device.write_register("LOAD_TORQUE_SETPOINT", 15.0);
    device.run(0.3);
    const double speed_after = device.read_number("SPEED_RPM");
    std::cout << "  Speed before load step: " << speed_before << " rpm\n";
    std::cout << "  Speed after load step:  " << speed_after << " rpm\n";
    device.stop();
}

inline void example_fault_trip_recovery() {
    std::cout << "\n======================================================================\n";
    std::cout << "Example 3: Fault Trip and Recovery\n";
    std::cout << "======================================================================\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.start();
    try {
        device.write_register("LOAD_TORQUE_SETPOINT", 200.0);
        std::cout << "  ERROR: overload setpoint should be inhibited while RUNNING\n";
    } catch (const InvalidStateError& error) {
        std::cout << "  RUNNING interlock: " << error.what() << "\n";
    }
    device.stop();
    device.write_register("LOAD_TORQUE_SETPOINT", 200.0);
    device.start();
    device.run(1.0);
    std::cout << "  State after overload: " << device_state_name(device.state) << "\n";
    std::cout << "  Fault code: " << fault_code_name(device.faults.fault_code()) << "\n";
    if (!device.faults.history().empty()) {
        std::cout << "  Fault: " << device.faults.history().back().message << "\n";
    }
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0);
    device.reset();
    device.power_on();
    const bool cleared = device.reset_faults();
    std::cout << "  After reset, faults cleared: " << (cleared ? "true" : "false")
              << "; state: " << device_state_name(device.state) << "\n";
}

inline void example_telemetry_export() {
    std::cout << "\n======================================================================\n";
    std::cout << "Example 4: Telemetry Capture and CSV Export\n";
    std::cout << "======================================================================\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 50);
    device.power_on();
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0);
    device.start();
    device.run(0.2);
    device.stop();
    auto samples = device.telemetry.snapshot();
    std::cout << "  Recorded " << samples.size() << " telemetry samples\n";
    if (!samples.empty()) {
        const auto& last = samples.back();
        std::cout << "  Latest: t=" << last.at("time") << "s, speed=" << last.at("speed_rpm")
                  << " rpm, torque=" << last.at("torque") << " N·m\n";
    }
    device.telemetry.export_csv("/tmp/emec_examples_telemetry.csv");
    std::cout << "  CSV written to /tmp/emec_examples_telemetry.csv\n";
}

inline void example_http_server() {
    std::cout << "\n======================================================================\n";
    std::cout << "Example 5: HTTP/SSE Server (in-process)\n";
    std::cout << "======================================================================\n";
    VirtualHardwareDevice device;
    auto started = serve(device, "127.0.0.1", 0, true);
    const int port = started.first->port();
    try {
        std::cout << "  bound 127.0.0.1:" << port << "\n";
        std::cout << "  POST /command/power_on -> "
                  << http_exchange("127.0.0.1", port, "POST", "/command/power_on", "{}").body << "\n";
        std::cout << "  POST /registers/LOAD_TORQUE_SETPOINT -> "
                  << http_exchange("127.0.0.1", port, "POST", "/registers/LOAD_TORQUE_SETPOINT", "{\"value\":10.0}").body
                  << "\n";
        std::cout << "  POST /command/start -> "
                  << http_exchange("127.0.0.1", port, "POST", "/command/start", "{}").body << "\n";
        device.run(0.2);
        std::cout << "  POST /command/stop -> "
                  << http_exchange("127.0.0.1", port, "POST", "/command/stop", "{}").body << "\n";
        std::cout << "  GET /state -> " << http_exchange("127.0.0.1", port, "GET", "/state").body << "\n";
        std::cout << "  GET /registers/SPEED_RPM -> "
                  << http_exchange("127.0.0.1", port, "GET", "/registers/SPEED_RPM").body << "\n";
    } catch (...) {
        started.first->shutdown();
        if (started.second.joinable()) {
            started.second.join();
        }
        throw;
    }
    started.first->shutdown();
    if (started.second.joinable()) {
        started.second.join();
    }
}

inline void run_device_examples() {
    example_startup_transient();
    example_load_step();
    example_fault_trip_recovery();
    example_telemetry_export();
    example_http_server();
}

}  // namespace emec

#ifdef EMEC_EXAMPLES_DEVICE_MAIN
int main() {
    emec::run_device_examples();
    return 0;
}
#endif
