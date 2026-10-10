# Header-only EMEC C++ API. Python physics modules are unchanged.
CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -pthread -I.

.PHONY: test test-emec test-bond-graph test-device examples

test: test-emec test-bond-graph test-device

test-emec:
	$(CXX) $(CXXFLAGS) -DEMEC_TEST_EMEC_MAIN -x c++ emec/test_emec.hpp -o /tmp/emec_test_emec
	/tmp/emec_test_emec

test-bond-graph:
	$(CXX) $(CXXFLAGS) -DEMEC_TEST_BOND_GRAPH_MAIN -x c++ emec/test_bond_graph.hpp -o /tmp/emec_test_bond_graph
	/tmp/emec_test_bond_graph

test-device:
	$(CXX) $(CXXFLAGS) -DEMEC_TEST_DEVICE_MAIN -x c++ emec/test_device.hpp -o /tmp/emec_test_device
	/tmp/emec_test_device

examples:
	$(CXX) $(CXXFLAGS) -DEMEC_EXAMPLES_DEVICE_MAIN -x c++ emec/examples_device.hpp -o /tmp/emec_examples_device
	/tmp/emec_examples_device
