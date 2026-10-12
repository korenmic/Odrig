# Requirements: Emulator and tools on Windows (seed 11)

Source seed: `project-seeds/11-p0-emulator-and-tools-on-windows/seed.md`. It depends on
seeds 01 to 05, which built the converter, the core, the emulator and the command tool, and
on seed 10, whose pages for newcomers it extends. These requirements rely on that code as it
is and name it where they extend it.

`docs/emulator.md`, `docs/core.md`, `docs/converter.md` and `docs/commands.md` define the
behaviour around this seed. Where they and the seed leave a point open, the answer used
here is recorded in `docs/drifts.md` under "Seed 11".

Terms:

- **the first computer**: the Mac on which seeds 01 to 10 were built and which has the board.
- **the Windows computer**: the computer on which this seed is built and checked: Windows 11,
  64-bit.
- **the build script**: `core/build.py`, the tracked script that builds the core without
  GNU Make.
- **a toolchain**: a C++ compiler with the programs that go with it. **A GNU-style
  toolchain** is GCC or Clang, started as `g++` or `clang++`. **Microsoft's toolchain** is
  the compiler `cl` of Microsoft's C++ build tools.
- **the shared library**: the core as a library a program loads when it runs:
  `core/build/libodrig_core.dylib` on macOS, `core/build/odrig_core.dll` on Windows.
- **the line protocol**: one command line in, one reply line out, as `docs/commands.md`
  defines it.
- **the line port**: a TCP port on 127.0.0.1 on which the emulator offers the line protocol,
  with the bytes handled as those of its virtual serial port are.
- **the serial port**: on macOS the emulator's pseudo-terminal behind its link. A **real
  serial port** is one the system gives a device: `/dev/cu.*` on macOS, `COM<n>` on Windows.
- **the JavaScript shell**: the program the emulator suite runs the page's scripts in: `jsc`
  of macOS there, Node.js elsewhere.
- **the quick suites**: the suites of `tests/converter`, `tests/core`, `tests/emulator` and
  `tests/onboarding`.
- **open for the first computer**: something this seed changes that only the first computer
  can check. It is listed in `docs/emulator.md` and said to the owner.

## Requirement 1: One command builds the core on Windows

**User Story:** As a contributor on Windows, I want one command that builds the core, so
that I can run the emulator without installing GNU Make.

### Acceptance Criteria

1. `python core/build.py shared` SHALL build the shared library from every `core/src/*.cpp`,
   found and not listed, with no source file of `core/` changed.
2. The build script SHALL use only the Python standard library and SHALL run with Python
   3.10 or later.
3. The build script SHALL work with a GNU-style toolchain and with Microsoft's toolchain. It
   SHALL take the compiler named with `--cxx`, then the one the variable `CXX` names, then a
   GNU-style compiler under the folder `tools/` of the repository, then `g++`, `clang++` or
   `c++` on the path, then Microsoft's toolchain as `vswhere` finds it.
4. With a GNU-style toolchain the sources SHALL be compiled with the flags `make -C core`
   uses. With Microsoft's toolchain they SHALL be compiled with warnings as errors and
   without exceptions and run-time type information.
5. The shared library SHALL export the seven functions of `core/include/odrig_core.h` and
   SHALL load on a computer that has no compiler: it SHALL need no library other than those
   of Windows.
6. When no toolchain is found the build script SHALL end with status 1 and one line
   `error: no-compiler: <detail>` that names what to install.
7. When the compiler fails the build script SHALL end with status 1 and show the compiler's
   output.
8. `python core/build.py clean` SHALL remove `core/build/`.
9. The folder `tools/` SHALL be ignored by git, and nothing in it SHALL be tracked.

## Requirement 2: The emulator starts on Windows

**User Story:** As a contributor on Windows, I want the emulator to start with the command
the documents give, so that I can see a show without the board.

### Acceptance Criteria

1. `python -m emulator SHOW_DIR` SHALL start on Windows, serve the page and the event stream
   and accept commands over HTTP as `docs/emulator.md` describes.
2. Without `--core` the emulator SHALL load the shared library of the system it runs on.
   When it is missing, the detail of `core-not-built` SHALL name the command that builds it
   on that system.
3. The emulator SHALL end with status 0 on Ctrl-C on every system, and on Windows also on
   Ctrl-Break. It SHALL then leave no listening address behind.
4. Record mode SHALL work on Windows as on macOS and SHALL write the same bytes for the same
   folder, length and script.
5. On Windows the demo show SHALL be refreshed 20 times a second or more.

## Requirement 3: The line port

**User Story:** As a contributor on Windows, which has no pseudo-terminal, I want the line
protocol of the serial port on a local TCP port, so that a tool that speaks lines reaches
the emulator.

### Acceptance Criteria

1. The emulator SHALL have the option `--tcp-port N`: the port of the line port on
   127.0.0.1, where 0 takes any free port.
2. On Windows the emulator SHALL open the line port always, on port 8601 without the option,
   and SHALL open no serial port. Its second printed line SHALL be `tcp: 127.0.0.1:<port>`.
3. On macOS the emulator SHALL open the serial port as before. With `--tcp-port` it SHALL
   also open the line port and print `tcp: 127.0.0.1:<port>` as a third line. Without the
   option it SHALL print the two lines it printed before.
4. Every byte a program writes to a connection of the line port SHALL reach the core's entry
   for bytes, unchanged and in order, and every reply to a line those bytes finish SHALL be
   written back to that connection. The port SHALL not echo and SHALL change no byte.
5. A program MAY open and close connections any number of times, and several at once.
6. A command that arrived by the line port SHALL be in the command log with the transport
   `tcp`.
7. The event `hello` SHALL carry `tcp`: the address of the line port, or `null`. On Windows
   its `serial` SHALL be `null`. The page SHALL show the line port where it shows the serial
   port.
8. When the line port cannot be opened the emulator SHALL end with status 1 and the reason
   `address-in-use`.
9. On Windows `--serial-link` SHALL end the emulator with status 1 and the reason
   `serial-unavailable`.
10. `--tcp-port` SHALL not go with `--record`.

## Requirement 4: The command tool reaches every target

**User Story:** As an operator, I want one tool for the emulator and the board on every
computer, so that what I learn on one works on the other.

### Acceptance Criteria

1. The command tool SHALL have the option `--tcp ADDRESS`, beside `--port` and `--http`:
   exactly one of the three is given. `ADDRESS` is `host:port`.
2. Over TCP the tool SHALL send the line, take the first received line that is a reply as
   the reply, and end with status 3 when the target cannot be reached or does not answer in
   time.
3. On Windows `--port NAME` SHALL open the real serial port `NAME`, such as `COM3`, also
   above `COM9`, at 115200 baud, 8 data bits, no parity and one stop bit.
4. On Windows the tool SHALL lower RTS before it lowers DTR, and SHALL leave the port set so
   that opening it again raises neither.
5. On Windows a name that is no serial port, or one that cannot be opened, SHALL end the
   tool with status 3.
6. The tool SHALL still use only the Python standard library, and its exit statuses SHALL be
   as before.
7. On macOS `--port` and `--http` SHALL behave as before.

## Requirement 5: The suites run on Windows

**User Story:** As a contributor on Windows, I want to run the suites before I merge, so
that I do not break what I cannot see.

### Acceptance Criteria

1. `python -m unittest discover -s tests/converter -t .` SHALL pass on Windows.
2. `python core/build.py test` SHALL build the core and its test host and run the core
   suite, which SHALL pass on Windows with a GNU-style toolchain. The test host SHALL be
   built with the checks for memory faults the toolchain has.
3. `python -m unittest discover -s tests/emulator -t .` SHALL build the shared library with
   the build script and SHALL pass on Windows, with Node.js as the JavaScript shell.
4. `python -m unittest discover -s tests/onboarding -t .` SHALL pass on Windows.
5. A test that needs something Windows lacks, a pseudo-terminal or a signal, SHALL be
   skipped there with a reason, and what it checks SHALL be checked through the line port
   where that is possible.
6. No test SHALL be removed, and every test SHALL still run on macOS.
7. The JavaScript converter is not in the repository; its suite is not run.

## Requirement 6: Tracked files are the same on every system

**User Story:** As a contributor, I want a checkout on Windows to hold the bytes a checkout
on macOS holds, so that the tools and the tests see the same files.

### Acceptance Criteria

1. `.gitattributes` SHALL have git convert no line ending of any tracked file, whatever the
   settings of the computer.
2. The tools SHALL write the files they make with the same bytes on every system.

## Requirement 7: The pages say what a Windows contributor needs

**User Story:** As a newcomer on Windows, I want the pages to give me my commands, so that
I get from a clone to a show in the emulator.

### Acceptance Criteria

1. `agent/getting-started.md` SHALL say what Windows needs: Python 3.10 or later, git, a
   toolchain and which one to install when there is none, and Node.js for the emulator
   suite. It SHALL give the setup, the four quick suites, the demo show, the emulator, the
   command tool and record mode with the commands of Windows.
2. `agent/animation-guide.md` SHALL say how its commands are written on Windows.
3. `docs/emulator.md` SHALL describe the build script's command, the line port, `--tcp-port`,
   `--tcp` and the serial port of Windows, and SHALL list what is open for the first
   computer and for whoever has a board on a Windows computer.
4. `docs/core.md` SHALL describe the build script. `docs/commands.md` SHALL name the line
   port among the transports.
5. `AGENTS.md`, `agent/README.md`, `agent/vocabulary.md` and `README.md` SHALL no longer say
   that the emulator and the command tool run on macOS only.
6. The pages SHALL say what is not available on Windows: the firmware tool and everything
   that needs the board.

## Requirement 8: What is checked, and where

**User Story:** As the owner, I want to know what was seen working and what was not, so
that I know what is left.

### Acceptance Criteria

1. On the Windows computer the four quick suites SHALL pass from a fresh clone that is set
   up as the getting-started page says.
2. On the Windows computer the demo show SHALL play in the emulator, the page SHALL show the
   LEDs view and the mapping view in Edge and in Chrome, and `play`, `brightness` and
   `status` SHALL give the expected replies over HTTP and over the line port.
3. On the Windows computer a GIF and a video SHALL be imported for the target, packed into a
   show and played in the emulator as the animation guide describes.
4. The check of a real board on a `COM` port SHALL be listed as open for whoever has a board
   on a Windows computer.
5. That the suites still pass on macOS and that the serial port works there as before SHALL
   be listed as open for the first computer.
