# The core: a static library, its test host and its suite.
#
#   make -C core          builds build/libodrig_core.a
#   make -C core test     builds the library and the test host, then runs the suite
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
HOST = $(BUILD)/odrig_host

WARNINGS = -Wall -Wextra -Wpedantic -Wshadow -Werror
CORE_FLAGS = -std=c++11 -O2 $(WARNINGS) -Wframe-larger-than=512 -fno-exceptions -fno-rtti -Iinclude
SANITIZERS = -fsanitize=address,undefined -fno-sanitize-recover=undefined -O1 -g
HOST_FLAGS = -std=c++17 $(WARNINGS) $(SANITIZERS) -Iinclude -Isrc

.PHONY: all test clean python

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

clean:
	rm -rf $(BUILD)
