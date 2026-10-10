#pragma once

// Command-line host for the virtual drive.
// Mirrors a technician talking to a physical motor drive: power_on, set, run, get, estop.
//
//   g++ -std=c++17 -I. -pthread -DEMEC_DEVICE_CLI_MAIN emec/device/cli_main.cpp
// Interactive:  the binary with no arguments
// Scripted:     the binary --demo

#include "emec/device/device.hpp"

#include <cctype>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace emec {

inline constexpr const char* DEVICE_CLI_HELP =
    "Commands:\n"
    "  power_on | power_off        Energize / de-energize the device\n"
    "  start | stop                Start / stop the drive\n"
    "  estop                       Emergency stop (unconditional)\n"
    "  reset_faults                Clear latched faults (when condition cleared)\n"
    "  inject_fault <CODE>         Latch a fault (e.g. EFFICIENCY_ANOMALY) for test\n"
    "  reset                       Full device reset\n"
    "  set <REGISTER> <value>      Write setpoint (e.g. set LOAD_TORQUE_SETPOINT 10)\n"
    "  get <REGISTER>              Read a register (e.g. get SPEED_RPM)\n"
    "  registers                   List all registers with values\n"
    "  run <seconds> [dt]          Run simulation for a duration\n"
    "  telemetry [n]               Show the last n telemetry samples\n"
    "  faults                      Show fault history\n"
    "  state                       Show lifecycle state and status word\n"
    "  help                        Show this help\n"
    "  quit                        Exit\n";

class DeviceCLI {
public:
    explicit DeviceCLI(VirtualHardwareDevice* device = nullptr, std::ostream& out = std::cout, std::istream& in = std::cin)
        : owned_(device ? nullptr : std::make_unique<VirtualHardwareDevice>()),
          device_(device ? device : owned_.get()),
          out_(out),
          in_(in) {}

    VirtualHardwareDevice& device() { return *device_; }
    const VirtualHardwareDevice& device() const { return *device_; }

    bool dispatch(const std::string& line) {
        const std::vector<std::string> parts = split(line);
        if (parts.empty()) {
            return true;
        }
        std::string cmd = lower(parts[0]);
        std::vector<std::string> args(parts.begin() + 1, parts.end());
        try {
            if (cmd == "quit" || cmd == "exit") {
                return false;
            }
            if (cmd == "help") {
                out_ << DEVICE_CLI_HELP;
            } else if (cmd == "power_on") {
                out_ << "state -> " << device_state_name(device_->power_on()) << '\n';
            } else if (cmd == "power_off") {
                out_ << "state -> " << device_state_name(device_->power_off()) << '\n';
            } else if (cmd == "start") {
                out_ << "state -> " << device_state_name(device_->start()) << '\n';
            } else if (cmd == "stop") {
                out_ << "state -> " << device_state_name(device_->stop()) << '\n';
            } else if (cmd == "estop") {
                out_ << "state -> " << device_state_name(device_->e_stop()) << '\n';
            } else if (cmd == "reset") {
                out_ << "state -> " << device_state_name(device_->reset()) << '\n';
            } else if (cmd == "reset_faults") {
                const bool cleared = device_->reset_faults();
                out_ << "faults cleared: " << (cleared ? "True" : "False") << "; state -> "
                     << device_state_name(device_->state) << '\n';
            } else if (cmd == "inject_fault" && args.size() == 1) {
                auto code = fault_code_from_name(upper(args[0]));
                if (!code) {
                    throw std::invalid_argument("unknown fault code");
                }
                out_ << "state -> " << device_state_name(device_->inject_fault(*code)) << '\n';
            } else if (cmd == "set" && args.size() == 2) {
                const std::string name = upper(args[0]);
                device_->write_register(name, std::stod(args[1]));
                out_ << name << " <- " << args[1] << '\n';
            } else if (cmd == "get" && args.size() == 1) {
                const std::string name = upper(args[0]);
                RegisterValue value = device_->read_register(name);
                out_ << name << " = ";
                if (std::holds_alternative<std::string>(value)) {
                    out_ << std::get<std::string>(value);
                } else {
                    out_ << std::get<double>(value);
                }
                out_ << '\n';
            } else if (cmd == "registers") {
                for (Register reg : kAllRegisters) {
                    try {
                        RegisterValue value = device_->read_register(reg);
                        out_ << "  " << register_name(reg) << " = ";
                        if (std::holds_alternative<std::string>(value)) {
                            out_ << std::get<std::string>(value);
                        } else {
                            out_ << std::get<double>(value);
                        }
                        out_ << '\n';
                    } catch (const RegisterAccessError&) {
                        out_ << "  " << register_name(reg) << "   (write-only)\n";
                    }
                }
            } else if (cmd == "run" && (args.size() == 1 || args.size() == 2)) {
                const double duration = std::stod(args[0]);
                std::optional<double> dt;
                if (args.size() == 2) {
                    dt = std::stod(args[1]);
                }
                const int cycles = device_->run(duration, dt);
                out_ << "ran " << cycles << " cycles; state -> " << device_state_name(device_->state) << '\n';
            } else if (cmd == "telemetry") {
                int n = 5;
                if (!args.empty()) {
                    n = std::stoi(args[0]);
                }
                for (const auto& sample : device_->telemetry.snapshot(n)) {
                    out_ << "  ";
                    for (std::size_t i = 0; i < TELEMETRY_FIELDS.size(); ++i) {
                        if (i) {
                            out_ << ", ";
                        }
                        out_ << TELEMETRY_FIELDS[i] << '=' << sample.values[i];
                    }
                    out_ << '\n';
                }
            } else if (cmd == "faults") {
                if (device_->faults.history().empty()) {
                    out_ << "  no faults recorded\n";
                }
                for (const auto& fault : device_->faults.history()) {
                    out_ << "  t=" << fault.time << "s [" << fault_code_name(fault.code) << "] " << fault.message << '\n';
                }
            } else if (cmd == "state") {
                out_ << "  state:       " << device_state_name(device_->state) << '\n';
                out_ << "  status word: " << device_->read_number(Register::STATUS_WORD) << '\n';
                out_ << "  fault code:  " << device_->read_number(Register::FAULT_CODE) << '\n';
            } else {
                out_ << "Unknown or malformed command: '" << line << "' (try 'help')\n";
            }
        } catch (const std::exception& error) {
            out_ << "Error: " << error.what() << '\n';
        }
        return true;
    }

    void loop() {
        out_ << "Arc-Halo EMEC Virtual Hardware Device CLI (type 'help')\n";
        std::string line;
        while (std::getline(in_, line)) {
            if (!dispatch(line)) {
                break;
            }
        }
    }

private:
    static std::string lower(std::string text) {
        for (char& ch : text) {
            ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
        }
        return text;
    }

    static std::string upper(std::string text) {
        for (char& ch : text) {
            ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
        }
        return text;
    }

    static std::vector<std::string> split(const std::string& line) {
        std::istringstream in(line);
        std::vector<std::string> parts;
        std::string part;
        while (in >> part) {
            parts.push_back(part);
        }
        return parts;
    }

    std::unique_ptr<VirtualHardwareDevice> owned_;
    VirtualHardwareDevice* device_;
    std::ostream& out_;
    std::istream& in_;
};

inline void run_demo(DeviceCLI& cli) {
    const char* script[] = {
        "power_on",
        "set LOAD_TORQUE_SETPOINT 10",
        "set VOLTAGE_SETPOINT 400",
        "start",
        "run 0.1",
        "get SPEED_RPM",
        "get TORQUE",
        "get EFFICIENCY",
        "telemetry 3",
        "inject_fault EFFICIENCY_ANOMALY",
        "faults",
        "reset_faults",
        "state",
        "estop",
        "power_on",
        "state",
    };
    for (const char* line : script) {
        cli.dispatch(line);
    }
}

}  // namespace emec

#ifdef EMEC_DEVICE_CLI_MAIN
#include <string>
int main(int argc, char** argv) {
    emec::DeviceCLI cli;
    if (argc > 1 && std::string(argv[1]) == "--demo") {
        emec::run_demo(cli);
        return 0;
    }
    cli.loop();
    return 0;
}
#endif
