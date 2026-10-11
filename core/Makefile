# The core: a static library, its test host and its suite.
#
#   make -C core          builds build/libodrig_core.a
#   make -C core test     builds the library and the test host, then runs the suite
#   make -C core bench    builds the benchmark and the dense test clip, then times decoding
#   make -C core shared   builds build/libodrig_core.dylib, the library the emulator loads
#   make -C core clean    removes build/
#
# Written for GNU Make 3.81. Sources are found, never listed.

ifeq ($(origin CXX),default)
CXX = c++
endif
PYTHON ?= python3

BUILD = build
TESTS = ../tests/core

SOURCES = $(wildcard src/*.cpp)
HEADERS = $(wildcard src/*.h) $(wildcard include/*.h)
HOST_SOURCES = $(wildcard $(TESTS)/host/*.cpp)
HOST_HEADERS = $(wildcard $(TESTS)/host/*.h)

OBJECTS = $(patsubst src/%.cpp,$(BUILD)/core/%.o,$(SOURCES))
CHECKED_OBJECTS = $(patsubst src/%.cpp,$(BUILD)/checked/%.o,$(SOURCES))
HOST_OBJECTS = $(patsubst $(TESTS)/host/%.cpp,$(BUILD)/host/%.o,$(HOST_SOURCES))

LIBRARY = $(BUILD)/libodrig_core.a
SHARED = $(BUILD)/libodrig_core.dylib
HOST = $(BUILD)/odrig_host
BENCH = $(BUILD)/odrig_bench
BENCH_CLIPS = $(BUILD)/bench/dense-compressed.odrg $(BUILD)/bench/dense-plain.odrg

WARNINGS = -Wall -Wextra -Wpedantic -Wshadow -Werror
CORE_FLAGS = -std=c++11 -O2 $(WARNINGS) -Wframe-larger-than=512 -fno-exceptions -fno-rtti -Iinclude
SANITIZERS = -fsanitize=address,undefined -fno-sanitize-recover=undefined -O1 -g
HOST_FLAGS = -std=c++17 $(WARNINGS) $(SANITIZERS) -Iinclude -Isrc

.PHONY: all test bench shared clean python

all: $(LIBRARY)

$(LIBRARY): $(OBJECTS)
	rm -f $@
	$(AR) rcs $@ $(OBJECTS)

$(BUILD)/core/%.o: src/%.cpp $(HEADERS) Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(CORE_FLAGS) -c $< -o $@

# The test host links a second compilation of the same sources, with the sanitizers.
$(BUILD)/checked/%.o: src/%.cpp $(HEADERS) Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(CORE_FLAGS) $(SANITIZERS) -c $< -o $@

$(BUILD)/host/%.o: $(TESTS)/host/%.cpp $(HEADERS) $(HOST_HEADERS) Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(HOST_FLAGS) -c $< -o $@

$(HOST): $(CHECKED_OBJECTS) $(HOST_OBJECTS)
	$(CXX) $(SANITIZERS) -o $@ $(CHECKED_OBJECTS) $(HOST_OBJECTS)

python:
	@$(PYTHON) -c 'import sys; sys.exit(sys.version_info < (3, 10))' || \
	    { echo "error: the tests need Python 3.10 or later, and '$(PYTHON)' is older or missing; name one with PYTHON=" >&2; exit 1; }

test: python all $(HOST)
	cd .. && $(PYTHON) -m unittest discover -s tests/core -t .

# The benchmark links the library itself, built with the core's own flags and no sanitizer.
$(BENCH): $(TESTS)/bench/bench.cpp $(LIBRARY) $(HEADERS) Makefile
	$(CXX) -std=c++17 -O2 $(WARNINGS) -Iinclude -Isrc $< $(LIBRARY) -o $@

# The dense 60 x 30 clip of 10 seconds, written and encoded by the converter.
$(BUILD)/bench/dense.json: ../mapping/legs-10.json
	@mkdir -p $(dir $@)
	cd .. && $(PYTHON) -m odrig.generators.dense core/$@ --mapping mapping/legs-10.json --seconds 10

$(BUILD)/bench/dense-compressed.odrg: $(BUILD)/bench/dense.json
	cd .. && $(PYTHON) -m odrig encode core/$< core/$@

$(BUILD)/bench/dense-plain.odrg: $(BUILD)/bench/dense.json
	cd .. && $(PYTHON) -m odrig encode --uncompressed core/$< core/$@

bench: python $(BENCH) $(BENCH_CLIPS)
	$(BENCH) $(BENCH_CLIPS)

# The same objects as the static library, linked as a library a program loads when it runs.
shared: $(SHARED)

$(SHARED): $(OBJECTS)
	$(CXX) -dynamiclib -o $@ $(OBJECTS)

clean:
	rm -rf $(BUILD)
