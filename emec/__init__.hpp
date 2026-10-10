#pragma once

// Arc-Halo EMEC 2.1.0
// Header-only electromagnetic energy conversion simulator and virtual hardware device.
// Include this header for the public C++ API. Compile with:
//   g++ -std=c++17 -pthread -I. your_program.cpp

#include "emec/bond_graph.hpp"
#include "emec/device/cli.hpp"
#include "emec/device/device.hpp"
#include "emec/device/faults.hpp"
#include "emec/device/registers.hpp"
#include "emec/device/server.hpp"
#include "emec/device/telemetry.hpp"
#include "emec/em_bond_graph_mapping.hpp"
#include "emec/em_field_solver.hpp"
#include "emec/neurological_analogy.hpp"
#include "emec/polyphase_winding.hpp"
#include "emec/rotor_dynamics.hpp"
#include "emec/stator_dynamics.hpp"
#include "emec/virtual_engine.hpp"

namespace emec {

inline constexpr const char* EMEC_VERSION = "2.1.0";

}  // namespace emec
