#pragma once

// Drive register map for the virtual hardware device.
// Address space follows a physical motor drive:
//   0x0000 command/control
//   0x0100 setpoints
//   0x0200 telemetry
//   0x0300 status
// Writable: CONTROL_WORD, FAULT_RESET, VOLTAGE_SETPOINT, FREQUENCY_SETPOINT, LOAD_TORQUE_SETPOINT
// Readable telemetry: SPEED_RPM, TORQUE, PHASE_CURRENT_A/B/C, POWER_MECH, POWER_ELEC, EFFICIENCY

#include <array>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace emec {

enum class Access { READ_ONLY, WRITE_ONLY, READ_WRITE };

inline const char* access_name(Access access) {
    switch (access) {
        case Access::READ_ONLY: return "ro";
        case Access::WRITE_ONLY: return "wo";
        case Access::READ_WRITE: return "rw";
    }
    return "ro";
}

enum class Register : int {
    CONTROL_WORD = 0x0000,
    FAULT_RESET = 0x0001,
    VOLTAGE_SETPOINT = 0x0100,
    FREQUENCY_SETPOINT = 0x0101,
    LOAD_TORQUE_SETPOINT = 0x0102,
    SPEED_RPM = 0x0200,
    TORQUE = 0x0201,
    PHASE_CURRENT_A = 0x0202,
    PHASE_CURRENT_B = 0x0203,
    PHASE_CURRENT_C = 0x0204,
    POWER_MECH = 0x0205,
    POWER_ELEC = 0x0206,
    EFFICIENCY = 0x0207,
    SIMULATION_TIME = 0x0208,
    STATUS_WORD = 0x0300,
    FAULT_CODE = 0x0301,
    DEVICE_STATE = 0x0302
};

inline constexpr std::array<Register, 17> kAllRegisters = {
    Register::CONTROL_WORD,       Register::FAULT_RESET,      Register::VOLTAGE_SETPOINT,
    Register::FREQUENCY_SETPOINT, Register::LOAD_TORQUE_SETPOINT, Register::SPEED_RPM,
    Register::TORQUE,             Register::PHASE_CURRENT_A,  Register::PHASE_CURRENT_B,
    Register::PHASE_CURRENT_C,    Register::POWER_MECH,       Register::POWER_ELEC,
    Register::EFFICIENCY,         Register::SIMULATION_TIME,  Register::STATUS_WORD,
    Register::FAULT_CODE,         Register::DEVICE_STATE};

inline const char* register_name(Register reg) {
    switch (reg) {
        case Register::CONTROL_WORD: return "CONTROL_WORD";
        case Register::FAULT_RESET: return "FAULT_RESET";
        case Register::VOLTAGE_SETPOINT: return "VOLTAGE_SETPOINT";
        case Register::FREQUENCY_SETPOINT: return "FREQUENCY_SETPOINT";
        case Register::LOAD_TORQUE_SETPOINT: return "LOAD_TORQUE_SETPOINT";
        case Register::SPEED_RPM: return "SPEED_RPM";
        case Register::TORQUE: return "TORQUE";
        case Register::PHASE_CURRENT_A: return "PHASE_CURRENT_A";
        case Register::PHASE_CURRENT_B: return "PHASE_CURRENT_B";
        case Register::PHASE_CURRENT_C: return "PHASE_CURRENT_C";
        case Register::POWER_MECH: return "POWER_MECH";
        case Register::POWER_ELEC: return "POWER_ELEC";
        case Register::EFFICIENCY: return "EFFICIENCY";
        case Register::SIMULATION_TIME: return "SIMULATION_TIME";
        case Register::STATUS_WORD: return "STATUS_WORD";
        case Register::FAULT_CODE: return "FAULT_CODE";
        case Register::DEVICE_STATE: return "DEVICE_STATE";
    }
    return "";
}

struct RegisterInfo {
    Register reg;
    Access access;
    const char* unit;
    const char* description;
    std::optional<std::pair<double, double>> value_range;
};

inline const RegisterInfo& register_info(Register reg) {
    static const RegisterInfo kMap[] = {
        {Register::CONTROL_WORD, Access::READ_WRITE, "bitfield",
         "Control word: bit 0 = start, bit 1 = stop, bit 2 = reset", std::nullopt},
        {Register::FAULT_RESET, Access::WRITE_ONLY, "bitfield",
         "Write 1 to clear latched faults (only when trip condition cleared)", std::nullopt},
        {Register::VOLTAGE_SETPOINT, Access::READ_WRITE, "V",
         "Line voltage setpoint for the three-phase supply", std::pair<double, double>{0.0, 690.0}},
        {Register::FREQUENCY_SETPOINT, Access::READ_WRITE, "Hz",
         "Supply frequency setpoint (variable frequency drive input)", std::pair<double, double>{0.0, 400.0}},
        {Register::LOAD_TORQUE_SETPOINT, Access::READ_WRITE, "N·m",
         "Constant mechanical load torque applied to the shaft", std::pair<double, double>{0.0, 200.0}},
        {Register::SPEED_RPM, Access::READ_ONLY, "rpm", "Rotor mechanical speed", std::nullopt},
        {Register::TORQUE, Access::READ_ONLY, "N·m", "Electromagnetic torque", std::nullopt},
        {Register::PHASE_CURRENT_A, Access::READ_ONLY, "A", "Stator phase A current (instantaneous)", std::nullopt},
        {Register::PHASE_CURRENT_B, Access::READ_ONLY, "A", "Stator phase B current (instantaneous)", std::nullopt},
        {Register::PHASE_CURRENT_C, Access::READ_ONLY, "A", "Stator phase C current (instantaneous)", std::nullopt},
        {Register::POWER_MECH, Access::READ_ONLY, "W", "Mechanical output power", std::nullopt},
        {Register::POWER_ELEC, Access::READ_ONLY, "W", "Electrical input power", std::nullopt},
        {Register::EFFICIENCY, Access::READ_ONLY, "%", "Electro-mechanical energy conversion efficiency", std::nullopt},
        {Register::SIMULATION_TIME, Access::READ_ONLY, "s", "Internal simulation clock", std::nullopt},
        {Register::STATUS_WORD, Access::READ_ONLY, "bitfield",
         "Status word: bit 0 = powered, bit 1 = running, bit 2 = fault, bit 3 = estop", std::nullopt},
        {Register::FAULT_CODE, Access::READ_ONLY, "code", "Latched fault code (0 = no fault)", std::nullopt},
        {Register::DEVICE_STATE, Access::READ_ONLY, "enum",
         "Lifecycle state: OFF, READY, RUNNING, FAULT, ESTOP", std::nullopt},
    };
    for (const auto& info : kMap) {
        if (info.reg == reg) {
            return info;
        }
    }
    return kMap[0];
}

inline bool register_in_map(Register reg) {
    const char* name = register_name(reg);
    return name[0] != '\0';
}

inline std::optional<Register> register_from_name(std::string_view name) {
    for (Register reg : kAllRegisters) {
        if (name == register_name(reg)) {
            return reg;
        }
    }
    return std::nullopt;
}

}  // namespace emec
