#pragma once

// C++ counterpart of emec/test_device.py.
// Build: g++ -std=c++17 -Wall -Wextra -pthread -I. -DEMEC_TEST_DEVICE_MAIN -x c++ emec/test_device.hpp -o /tmp/test_device

#include "db/scripts/emec_device_repository.hpp"
#include "emec/device/cli.hpp"
#include "emec/device/server.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

namespace emec {
namespace test_device {

inline void expect(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

inline bool close(double a, double b, double tol = 1e-9) { return std::abs(a - b) <= tol; }

class ScriptedDb : public DbConnection {
public:
    std::vector<QueryRow> execute_query(const std::string&, const std::vector<std::string>& = {}) override {
        expect(!scripted.empty(), "unexpected query");
        auto rows = scripted.front();
        scripted.erase(scripted.begin());
        return rows;
    }
    int execute_command(const std::string&, const std::vector<std::string>& = {}) override {
        ++commands;
        return 1;
    }
    int executemany(const std::string&, const std::vector<std::vector<std::string>>& rows) override {
        executemany_called = true;
        executemany_rows = static_cast<int>(rows.size());
        return executemany_rows;
    }
    void execute_script(const std::string&) override {}

    std::vector<std::vector<QueryRow>> scripted;
    int commands = 0;
    bool executemany_called = false;
    int executemany_rows = 0;
};

class MockSink : public DevicePersistenceSink {
public:
    std::string start_session(const std::map<std::string, double>&) override {
        ++start_calls;
        if (throw_on_start) {
            throw std::runtime_error("db down");
        }
        return session_id;
    }
    void end_session(const std::string& id,
                     const std::map<std::string, double>& metrics,
                     const std::vector<TelemetrySample>& samples,
                     const std::string& status = "stopped") override {
        ++end_calls;
        last_session = id;
        last_metrics = metrics;
        last_samples = samples;
        last_status = status;
    }
    std::string record_fault(const std::string& id, int code, const std::string&, double sim_time) override {
        ++fault_calls;
        fault_session = id;
        fault_code = code;
        fault_time = sim_time;
        return "fault-id";
    }

    int start_calls = 0;
    int end_calls = 0;
    int fault_calls = 0;
    bool throw_on_start = false;
    std::string session_id = "sess-1";
    std::string last_session;
    std::string last_status;
    std::map<std::string, double> last_metrics;
    std::vector<TelemetrySample> last_samples;
    std::string fault_session;
    int fault_code = 0;
    double fault_time = -1.0;
};

inline bool test_lifecycle_transitions() {
    std::cout << "Testing Lifecycle Transitions...\n";
    VirtualHardwareDevice device;
    expect(device.state == DeviceState::OFF, "Initial state must be OFF");
    bool raised = false;
    try {
        device.start();
    } catch (const InvalidStateError&) {
        raised = true;
    }
    expect(raised, "start() from OFF should raise");
    device.power_on();
    expect(device.state == DeviceState::READY, "power_on -> READY");
    device.start();
    expect(device.state == DeviceState::RUNNING, "start -> RUNNING");
    raised = false;
    try {
        device.power_off();
    } catch (const InvalidStateError&) {
        raised = true;
    }
    expect(raised, "power_off while RUNNING should raise");
    device.stop();
    expect(device.state == DeviceState::READY, "stop -> READY");
    device.power_off();
    expect(device.state == DeviceState::OFF, "power_off -> OFF");
    std::cout << "  ✓ Lifecycle Transitions tests passed\n";
    return true;
}

inline bool test_register_validation() {
    std::cout << "Testing Register Validation...\n";
    VirtualHardwareDevice device;
    bool raised = false;
    try {
        device.write_register(Register::SPEED_RPM, 100.0);
    } catch (const RegisterAccessError&) {
        raised = true;
    }
    expect(raised, "Writing read-only register should raise");
    raised = false;
    try {
        device.read_register(Register::FAULT_RESET);
    } catch (const RegisterAccessError&) {
        raised = true;
    }
    expect(raised, "Reading write-only register should raise");
    raised = false;
    try {
        device.read_register("NOT_A_REGISTER");
    } catch (const RegisterAccessError&) {
        raised = true;
    }
    expect(raised, "Unknown register should raise");
    raised = false;
    try {
        device.write_register(Register::VOLTAGE_SETPOINT, 10000.0);
    } catch (const RegisterValueError&) {
        raised = true;
    }
    expect(raised, "Out-of-range value should raise");
    raised = false;
    try {
        device.write_register(Register::LOAD_TORQUE_SETPOINT, std::string("high"));
    } catch (const RegisterValueError&) {
        raised = true;
    }
    expect(raised, "Non-numeric value should raise");
    device.power_on();
    device.write_register("LOAD_TORQUE_SETPOINT", 12.5);
    expect(device.read_number(Register::LOAD_TORQUE_SETPOINT) == 12.5, "named write failed");
    device.write_register(Register::FREQUENCY_SETPOINT, 60.0);
    expect(device.read_number("FREQUENCY_SETPOINT") == 60.0, "enum write failed");
    for (Register reg : kAllRegisters) {
        const auto& info = register_info(reg);
        expect(info.access == Access::READ_ONLY || info.access == Access::WRITE_ONLY || info.access == Access::READ_WRITE,
               "access invalid");
    }
    std::cout << "  ✓ Register Validation tests passed\n";
    return true;
}

inline bool test_control_word() {
    std::cout << "Testing Control Word...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.write_register(Register::CONTROL_WORD, 0x1);
    expect(device.state == DeviceState::RUNNING, "START bit");
    device.write_register(Register::CONTROL_WORD, 0x2);
    expect(device.state == DeviceState::READY, "STOP bit");
    device.write_register(Register::CONTROL_WORD, 0x4);
    expect(device.state == DeviceState::READY, "RESET bit");
    std::cout << "  ✓ Control Word tests passed\n";
    return true;
}

inline bool test_fault_trip_and_latch() {
    std::cout << "Testing Fault Trip and Latch...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 200.0);
    device.start();
    device.run(1.0);
    expect(device.state == DeviceState::FAULT, "Overload must trip to FAULT");
    expect(static_cast<int>(device.read_number(Register::FAULT_CODE)) != static_cast<int>(FaultCode::NONE),
           "Fault code must be latched");
    bool raised = false;
    try {
        device.start();
    } catch (const InvalidStateError&) {
        raised = true;
    }
    expect(raised, "start() while FAULT should raise");
    expect((static_cast<int>(device.read_number(Register::STATUS_WORD)) & 0x4) != 0, "Status word fault bit not set");
    std::cout << "  ✓ Fault Trip and Latch tests passed\n";
    return true;
}

inline bool test_fault_reset() {
    std::cout << "Testing Fault Reset...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 200.0);
    device.start();
    device.run(1.0);
    expect(device.state == DeviceState::FAULT, "expected FAULT");
    device.reset();
    device.power_on();
    expect(device.state == DeviceState::READY, "Reset restores READY");
    FaultManager fm;
    fm.trip(FaultCode::OVER_CURRENT, "test", 0.0);
    expect(!fm.clear(true), "Must not clear while active");
    expect(fm.is_faulted(), "still faulted");
    expect(fm.clear(false), "Must clear when condition gone");
    expect(!fm.is_faulted(), "cleared");
    expect(fm.fault_code() == FaultCode::NONE, "code cleared");
    std::cout << "  ✓ Fault Reset tests passed\n";
    return true;
}

inline bool test_efficiency_anomaly() {
    std::cout << "Testing Efficiency Anomaly...\n";
    ProtectionLimits limits;
    expect(limits.current_limit_a == CURRENT_LIMIT_AMPS, "current limit");
    expect(limits.torque_limit_nm == TORQUE_LIMIT_NM, "torque limit");
    FaultManager fm;
    auto healthy = fm.check_protections(Vec{1.0, -0.5, -0.5}, 5.0, 100.0, 1500.0, 0.1, 0.08, 50000.0, 40.0);
    expect(!healthy, "Startup efficiency must not false-trip");
    auto over_unity = fm.check_protections(Vec{1.0}, 1.0, 100.0, 1500.0, 0.2, 150.0, 100.0, 200.0);
    expect(over_unity && over_unity->code == FaultCode::EFFICIENCY_ANOMALY, "over-unity trip");
    FaultManager fm_nan;
    auto non_finite = fm_nan.check_protections(Vec{1.0}, 1.0, 10.0, 1500.0, 0.0, std::nan(""), std::nullopt, std::nullopt);
    expect(non_finite && non_finite->code == FaultCode::EFFICIENCY_ANOMALY, "non-finite trip");

    VirtualHardwareDevice device;
    device.power_on();
    device.start();
    device.engine.step_override = [](std::optional<double>) {
        SimulationState state;
        state.time = 0.01;
        state.torque = 1.0;
        state.power_mechanical = 500.0;
        state.power_electrical = 100.0;
        state.efficiency = 500.0;
        state.stator.current = Vec{1.0, 1.0, 1.0};
        state.rotor.speed_rpm = 100.0;
        return state;
    };
    device.run_cycle(1e-4);
    expect(device.state == DeviceState::FAULT, "device should fault");
    expect(static_cast<int>(device.read_number(Register::FAULT_CODE)) == static_cast<int>(FaultCode::EFFICIENCY_ANOMALY),
           "efficiency fault code");
    expect(device.reset_faults() == false, "Over-unity condition must block clear");
    std::cout << "  ✓ Efficiency Anomaly tests passed\n";
    return true;
}

inline bool test_running_setpoint_interlock() {
    std::cout << "Testing RUNNING Setpoint Interlock...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 10.0);
    device.start();
    bool raised = false;
    try {
        device.write_register(Register::LOAD_TORQUE_SETPOINT, 200.0);
    } catch (const InvalidStateError&) {
        raised = true;
    }
    expect(raised, "Over-torque setpoint must be inhibited while RUNNING");
    expect(device.read_number(Register::LOAD_TORQUE_SETPOINT) == 10.0, "setpoint unchanged");
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 20.0);
    expect(device.read_number(Register::LOAD_TORQUE_SETPOINT) == 20.0, "legal setpoint");
    raised = false;
    try {
        device.write_register(Register::FREQUENCY_SETPOINT, 80.0);
    } catch (const InvalidStateError&) {
        raised = true;
    }
    expect(raised, "Over-speed frequency must be inhibited while RUNNING");
    expect(device.read_number(Register::FREQUENCY_SETPOINT) == device.params.stator_electrical.rated_frequency,
           "frequency unchanged");
    device.stop();
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 200.0);
    expect(device.read_number(Register::LOAD_TORQUE_SETPOINT) == 200.0, "READY must still allow preloading a trip setpoint");
    std::cout << "  ✓ RUNNING Setpoint Interlock tests passed\n";
    return true;
}

inline bool test_estop() {
    std::cout << "Testing Emergency Stop...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.start();
    device.run(0.05);
    device.e_stop();
    expect(device.state == DeviceState::ESTOP, "e_stop -> ESTOP");
    expect(static_cast<int>(device.read_number(Register::FAULT_CODE)) == static_cast<int>(FaultCode::ESTOP), "ESTOP code");
    expect((static_cast<int>(device.read_number(Register::STATUS_WORD)) & 0x8) != 0, "estop bit");
    device.power_on();
    expect(device.state == DeviceState::READY, "power_on clears ESTOP");
    expect(static_cast<int>(device.read_number(Register::FAULT_CODE)) == static_cast<int>(FaultCode::NONE), "latch cleared");
    VirtualHardwareDevice device2;
    device2.e_stop();
    expect(device2.state == DeviceState::OFF, "e_stop while OFF is a no-op");
    std::cout << "  ✓ Emergency Stop tests passed\n";
    return true;
}

inline bool test_setpoint_binding() {
    std::cout << "Testing Setpoint Binding...\n";
    VirtualHardwareDevice device;
    device.power_on();
    device.write_register(Register::LOAD_TORQUE_SETPOINT, 7.5);
    device.write_register(Register::FREQUENCY_SETPOINT, 55.0);
    expect(device.engine.rotor().load_torque_fn()(0.0, 100.0) == 7.5, "Load torque binding wrong");
    Vec v = device.engine.stator().compute_supply_voltage(0.001);
    expect(v.size() == 3, "Supply must produce 3 phase voltages");
    expect(device.engine.stator().state().frequency == 55.0, "frequency not bound");
    std::cout << "  ✓ Setpoint Binding tests passed\n";
    return true;
}

inline bool test_telemetry_recorder() {
    std::cout << "Testing Telemetry Recorder...\n";
    TelemetryRecorder recorder(5, 2);
    for (int i = 0; i < 10; ++i) {
        recorder.record_partial({{"time", static_cast<double>(i)}, {"speed_rpm", static_cast<double>(i * 10)}});
    }
    expect(recorder.size() == 5, "Expected 5 samples");
    expect(recorder.snapshot()[0].at("time") == 1.0, "Decimation should keep even ticks");
    expect(recorder.latest()->at("time") == 9.0, "latest tick");
    for (int i = 10; i < 14; ++i) {
        recorder.record_partial({{"time", static_cast<double>(i)}});
    }
    expect(recorder.size() == 5, "Capacity must bound buffer");
    expect(recorder.snapshot()[0].at("time") == 5.0, "oldest dropped");
    expect(recorder.snapshot(2).size() == 2, "snapshot window");
    const std::string csv_text = recorder.to_csv(2);
    expect(csv_text.rfind("time,speed_rpm", 0) == 0, "CSV header wrong");
    int lines = 0;
    for (char ch : csv_text) {
        if (ch == '\n') {
            ++lines;
        }
    }
    expect(lines == 3, "CSV row count");
    recorder.export_csv("/tmp/emec_telemetry_test.csv", 1);
    recorder.clear();
    expect(recorder.size() == 0, "clear");
    bool raised = false;
    try {
        TelemetryRecorder bad(0);
    } catch (const std::invalid_argument&) {
        raised = true;
    }
    expect(raised, "capacity=0 should raise");
    std::cout << "  ✓ Telemetry Recorder tests passed\n";
    return true;
}

inline bool test_device_run_and_readback() {
    std::cout << "Testing Device Run and Readback...\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 10);
    device.power_on();
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0);
    device.start();
    const int cycles = device.run(0.05);
    expect(cycles == 500, "Expected 500 cycles");
    expect(device.telemetry.size() == 50, "Decimation 10 over 500 cycles = 50");
    expect(close(device.read_number(Register::SIMULATION_TIME), 0.05, 1e-6), "Simulation clock mismatch");
    auto sample = device.telemetry.latest();
    expect(sample && sample->contains("time") && sample->contains("speed_rpm") && sample->contains("torque") &&
               sample->contains("power_mechanical") && sample->contains("stator_current_a"),
           "Telemetry missing channel");
    device.stop();
    expect(!device.run_cycle(), "Not running: run_cycle is a no-op");
    std::cout << "  ✓ Device Run and Readback tests passed\n";
    return true;
}

inline bool test_server_endpoints() {
    std::cout << "Testing Server Endpoints...\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 10);
    auto started = serve(device, "127.0.0.1", 0, true);
    const int port = started.first->port();
    try {
        auto registers = http_exchange("127.0.0.1", port, "GET", "/registers");
        expect(registers.status == 200, "registers status");
        expect(registers.body.find("SPEED_RPM") != std::string::npos && registers.body.find("CONTROL_WORD") != std::string::npos,
               "register listing");
        auto power = http_exchange("127.0.0.1", port, "POST", "/command/power_on", "{}");
        expect(power.status == 200 && power.body.find("READY") != std::string::npos, "power_on");
        auto set = http_exchange("127.0.0.1", port, "POST", "/registers/LOAD_TORQUE_SETPOINT", "{\"value\":10.0}");
        expect(set.status == 200, "set torque");
        auto start = http_exchange("127.0.0.1", port, "POST", "/command/start", "{}");
        expect(start.body.find("RUNNING") != std::string::npos, "start");
        auto blocked = http_exchange("127.0.0.1", port, "POST", "/registers/LOAD_TORQUE_SETPOINT", "{\"value\":200.0}");
        expect(blocked.status == 400, "RUNNING must reject an over-torque setpoint");
        device.run(0.02);
        auto stop = http_exchange("127.0.0.1", port, "POST", "/command/stop", "{}");
        expect(stop.body.find("READY") != std::string::npos, "stop");
        auto speed = http_exchange("127.0.0.1", port, "GET", "/registers/SPEED_RPM");
        expect(speed.body.find("value") != std::string::npos && speed.body.find("rpm") != std::string::npos, "speed readback");
        auto state = http_exchange("127.0.0.1", port, "GET", "/state");
        expect(state.body.find("READY") != std::string::npos && state.body.find("\"fault_code\":0") != std::string::npos, "state");
        auto telemetry = http_exchange("127.0.0.1", port, "GET", "/telemetry?last_n=5");
        expect(telemetry.body.find("samples") != std::string::npos, "telemetry");
        auto ro = http_exchange("127.0.0.1", port, "POST", "/registers/SPEED_RPM", "{\"value\":1.0}");
        expect(ro.status == 404, "Writing read-only register must fail");
        auto bogus = http_exchange("127.0.0.1", port, "POST", "/registers/BOGUS", "{\"value\":1.0}");
        expect(bogus.status == 404, "unknown register");
        auto range = http_exchange("127.0.0.1", port, "POST", "/registers/VOLTAGE_SETPOINT", "{\"value\":99999.0}");
        expect(range.status == 400, "Out-of-range write must fail");
        auto cmd = http_exchange("127.0.0.1", port, "POST", "/command/not_a_command", "{}");
        expect(cmd.status == 404, "unknown command");
        auto missing = http_exchange("127.0.0.1", port, "POST", "/registers/VOLTAGE_SETPOINT", "{}");
        expect(missing.status == 400, "missing value");
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
    std::cout << "  ✓ Server Endpoints tests passed\n";
    return true;
}

inline bool test_cli_commands() {
    std::cout << "Testing CLI Commands...\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 10);
    std::ostringstream cli_out;
    DeviceCLI cli(&device, cli_out);
    expect(cli.dispatch("power_on"), "power_on");
    expect(device.state == DeviceState::READY, "cli ready");
    expect(cli.dispatch("set LOAD_TORQUE_SETPOINT 10"), "set");
    expect(device.read_number("LOAD_TORQUE_SETPOINT") == 10.0, "set value");
    expect(cli.dispatch("start") && cli.dispatch("run 0.02") && cli.dispatch("get SPEED_RPM"), "run");
    expect(cli.dispatch("telemetry 3") && cli.dispatch("registers") && cli.dispatch("state") && cli.dispatch("stop"), "poll");
    expect(device.state == DeviceState::READY, "stopped");
    expect(cli.dispatch("inject_fault EFFICIENCY_ANOMALY"), "inject");
    expect(device.state == DeviceState::FAULT, "faulted");
    expect(static_cast<int>(device.read_number(Register::FAULT_CODE)) == static_cast<int>(FaultCode::EFFICIENCY_ANOMALY),
           "injected code");
    expect(cli.dispatch("reset_faults"), "reset faults");
    expect(device.state == DeviceState::READY, "cleared");
    expect(cli.dispatch("inject_fault NOT_A_FAULT"), "unknown fault does not crash");
    expect(cli.dispatch("set NOT_A_REGISTER 1"), "bad set");
    expect(cli.dispatch("get SPEED_RPM extra_arg"), "malformed get");
    expect(cli.dispatch("nonsense"), "unknown");
    expect(!cli.dispatch("quit"), "quit");
    std::cout << "  ✓ CLI Commands tests passed\n";
    return true;
}

inline bool test_repository_with_mock() {
    std::cout << "Testing Device Repository (mocked DB)...\n";
    auto db = std::make_shared<ScriptedDb>();
    db->scripted = {{{{"device_id", "dev-uuid"}}}, {{{"session_id", "sess-uuid"}}}, {{{"fault_id", "fault-uuid"}}}};
    EMECDeviceRepository repo(db, "test-device");
    expect(repo.register_device("{\"rated_power\":5000.0}") == "dev-uuid", "device id");
    const std::string session_id = repo.start_session({{"load_torque_setpoint", 10.0}});
    expect(session_id == "sess-uuid", "session id");
    TelemetrySample a;
    a.set("time", 0.0);
    TelemetrySample b;
    b.set("time", 0.1);
    b.set("speed_rpm", 100.0);
    b.set("torque", 5.0);
    repo.end_session(session_id, {{"avg_efficiency", 85.0}}, {a, b});
    expect(db->executemany_called, "Telemetry must be bulk-inserted");
    expect(repo.record_fault(session_id, 1, "Over-current test", 0.0) == "fault-uuid", "fault id");
    unsetenv("NEON_DATABASE_URL");
    expect(create_repository_from_env() == nullptr, "no URL returns null");
    std::cout << "  ✓ Device Repository (mocked DB) tests passed\n";
    return true;
}

inline bool test_device_repository_integration() {
    std::cout << "Testing Device-Repository Integration...\n";
    VirtualHardwareDevice device(std::nullopt, std::nullopt, 10000, 10);
    auto repo = std::make_shared<MockSink>();
    device.repository = repo;
    device.power_on();
    device.write_register("LOAD_TORQUE_SETPOINT", 10.0);
    device.start();
    device.run(0.02);
    device.stop();
    expect(repo->start_calls == 1 && repo->end_calls == 1, "session hooks");
    expect(repo->last_session == "sess-1", "session id");
    expect(repo->last_metrics.count("duration_s") == 1, "duration");
    expect(!repo->last_samples.empty(), "samples");
    expect(repo->last_status == "stopped", "status");

    auto repo3 = std::make_shared<MockSink>();
    repo3->session_id = "sess-fault";
    VirtualHardwareDevice device3(std::nullopt, std::nullopt, 10000, 10, repo3);
    device3.power_on();
    device3.start();
    device3.inject_fault(FaultCode::OVER_CURRENT, "injected over-current");
    expect(repo3->fault_calls == 1, "fault recorded");
    expect(repo3->fault_session == "sess-fault", "fault session");
    expect(repo3->fault_code == static_cast<int>(FaultCode::OVER_CURRENT), "fault code");
    expect(repo3->fault_time == device3.engine.current_time(), "sim_time");
    expect(repo3->last_status == "faulted", "faulted status");

    auto repo2 = std::make_shared<MockSink>();
    repo2->throw_on_start = true;
    VirtualHardwareDevice device2(std::nullopt, std::nullopt, 10000, 1, repo2);
    device2.power_on();
    device2.start();
    device2.run(0.01);
    device2.stop();
    expect(device2.state == DeviceState::READY, "repository errors never break the device");
    std::cout << "  ✓ Device-Repository Integration tests passed\n";
    return true;
}

inline bool test_repository_autowire() {
    std::cout << "Testing Repository Autowire...\n";
    unsetenv("NEON_DATABASE_URL");
    repository_factory_override() = nullptr;
    VirtualHardwareDevice plain;
    expect(plain.repository == nullptr, "no URL, no repository");

    auto explicit_sink = std::make_shared<MockSink>();
    setenv("NEON_DATABASE_URL", "postgresql://example.invalid/db", 1);
    VirtualHardwareDevice kept(std::nullopt, std::nullopt, 10000, 1, explicit_sink);
    expect(kept.repository.get() == explicit_sink.get(), "explicit repository wins");

    int calls = 0;
    repository_factory_override() = [&]() -> std::shared_ptr<DevicePersistenceSink> {
        ++calls;
        return std::make_shared<MockSink>();
    };
    VirtualHardwareDevice wired;
    expect(wired.repository != nullptr, "factory sink attached");
    expect(calls == 1, "factory called once");

    repository_factory_override() = []() -> std::shared_ptr<DevicePersistenceSink> {
        throw std::runtime_error("db down");
    };
    VirtualHardwareDevice failed;
    expect(failed.repository == nullptr && failed.state == DeviceState::OFF, "factory failure is fail-safe");
    repository_factory_override() = nullptr;
    unsetenv("NEON_DATABASE_URL");
    std::cout << "  ✓ Repository Autowire tests passed\n";
    return true;
}

inline bool test_websocket_stream() {
    std::cout << "Testing WebSocket Stream...\n";
    VirtualHardwareDevice device;
    device.power_on();
    auto started = serve(device, "127.0.0.1", 0, true);
    const int port = started.first->port();
    const std::string key_raw = "arc-halo-emec-ws!!";
    const std::string key = base64_encode(reinterpret_cast<const std::uint8_t*>(key_raw.data()), key_raw.size());
    const Sha1Digest abc = sha1(reinterpret_cast<const std::uint8_t*>("abc"), 3);
    const std::uint8_t abc_expected[20] = {0xa9, 0x99, 0x3e, 0x36, 0x47, 0x06, 0x81, 0x6a, 0xba, 0x3e,
                                           0x25, 0x71, 0x78, 0x50, 0xc2, 0x6c, 0x9c, 0xd0, 0xd8, 0x9d};
    expect(std::memcmp(abc.bytes, abc_expected, 20) == 0, "SHA-1 self-check failed");
    try {
        const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<std::uint16_t>(port));
        ::inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
        expect(::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0, "connect");
        const std::string request = "GET /stream?rate_hz=50 HTTP/1.1\r\nHost: 127.0.0.1:" + std::to_string(port) +
                                    "\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
                                    "\r\nSec-WebSocket-Version: 13\r\n\r\n";
        expect(::send(fd, request.data(), request.size(), MSG_NOSIGNAL) == static_cast<ssize_t>(request.size()), "send");
        std::string buffer;
        char chunk[4096];
        while (buffer.find("\r\n\r\n") == std::string::npos) {
            const ssize_t n = ::recv(fd, chunk, sizeof(chunk), 0);
            expect(n > 0, "WebSocket handshake closed early");
            buffer.append(chunk, chunk + n);
        }
        const std::size_t split = buffer.find("\r\n\r\n");
        const std::string header = buffer.substr(0, split);
        std::string frame = buffer.substr(split + 4);
        expect(header.find("101") != std::string::npos, "Expected 101 Switching Protocols");
        expect(header.find("Sec-WebSocket-Accept") != std::string::npos, "missing accept");
        expect(header.find(websocket_accept_key(key)) != std::string::npos, "accept mismatch");
        while (frame.size() < 2) {
            const ssize_t n = ::recv(fd, chunk, sizeof(chunk), 0);
            expect(n > 0, "frame closed");
            frame.append(chunk, chunk + n);
        }
        std::size_t length = static_cast<unsigned char>(frame[1]) & 0x7F;
        std::size_t offset = 2;
        if (length == 126) {
            while (frame.size() < 4) {
                const ssize_t n = ::recv(fd, chunk, sizeof(chunk), 0);
                frame.append(chunk, chunk + n);
            }
            length = (static_cast<unsigned char>(frame[2]) << 8) | static_cast<unsigned char>(frame[3]);
            offset = 4;
        }
        while (frame.size() < offset + length) {
            const ssize_t n = ::recv(fd, chunk, sizeof(chunk), 0);
            expect(n > 0, "payload closed");
            frame.append(chunk, chunk + n);
        }
        const std::string payload = frame.substr(offset, length);
        expect(payload.find("READY") != std::string::npos && payload.find("fault_code") != std::string::npos, "payload");
        ::close(fd);
        std::this_thread::sleep_for(std::chrono::milliseconds(150));
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
    bool rejected = false;
    try {
        DeviceServer remote(device, "0.0.0.0", 0, false);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    expect(rejected, "non-loopback bind must require allow_remote");
    std::cout << "  ✓ WebSocket Stream tests passed\n";
    return true;
}

inline bool run_all_tests() {
    unsetenv("NEON_DATABASE_URL");
    repository_factory_override() = nullptr;
    std::cout << "\n======================================================================\n";
    std::cout << "Virtual Hardware Device Test Suite\n";
    std::cout << "======================================================================\n\n";
    using TestFn = bool (*)();
    TestFn tests[] = {test_lifecycle_transitions, test_register_validation,     test_control_word,
                      test_fault_trip_and_latch,  test_fault_reset,             test_efficiency_anomaly,
                      test_running_setpoint_interlock, test_estop,              test_setpoint_binding,
                      test_telemetry_recorder,    test_device_run_and_readback, test_server_endpoints,
                      test_cli_commands,          test_repository_with_mock,    test_device_repository_integration,
                      test_repository_autowire,   test_websocket_stream};
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

}  // namespace test_device
}  // namespace emec

#ifdef EMEC_TEST_DEVICE_MAIN
int main() { return emec::test_device::run_all_tests() ? 0 : 1; }
#endif
