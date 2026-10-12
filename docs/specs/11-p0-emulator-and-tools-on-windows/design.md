# Design: Emulator and tools on Windows (seed 11)

How the requirements of this seed are met. Nothing here needs a new design of the tools: the
emulator is a Python program around the shared core with a web page, and all three are
portable. Three things are missing on Windows: a way to build the core, a stand-in for the
virtual serial port, and access to a real serial port. The rest is making the suites and the
pages say the same on both systems.

## What changes, and what does not

| Part | Change |
|---|---|
| `core/src/`, `core/include/` | None. |
| `core/Makefile` | None. macOS keeps building with `make`. |
| `core/build.py` | New: the build script. |
| `emulator/binding.py` | The name of the shared library and the build command of the system. |
| `emulator/lineport.py` | New: the line port. |
| `emulator/serialport.py` | Loads only where the system has a pseudo-terminal. |
| `emulator/app.py` | `--tcp-port`, which ports are opened on which system, the wait for a signal. |
| `emulator/web/` | The header shows the line port. |
| `odrigctl/client.py` | `tcp_exchange`; the serial exchange picks the port of the system. |
| `odrigctl/winserial.py` | New: a real serial port on Windows. |
| `odrigctl/cli.py` | `--tcp`. |
| `tests/` | The suites choose the build command, the JavaScript shell and the way to stop a child by the system. |
| `.gitattributes`, `.gitignore` | No line-ending conversion; `tools/` ignored. |

## The build script

`core/build.py` is one file, run as `python core/build.py [shared|test|clean]` from any
folder. Without a word it builds the static library. It writes into `core/build/`, the
folder `make` uses, and nothing else.

| Command | Builds |
|---|---|
| `python core/build.py` | The static library: `libodrig_core.a`, or `odrig_core.lib` with Microsoft's toolchain. |
| `python core/build.py shared` | The shared library: `odrig_core.dll` on Windows, `libodrig_core.dylib` on macOS, `libodrig_core.so` elsewhere. |
| `python core/build.py test` | The static library and the test host `odrig_host`, then runs the core suite with the Python that runs the script. |
| `python core/build.py clean` | Removes `core/build/`. |

**Finding the compiler.** In this order: `--cxx PROGRAM`; the variable `CXX`; a file
`g++` or `clang++` in a `bin` folder at most three folders below `tools/`; `g++`,
`clang++`, `c++` on the path; on Windows, the newest installation `vswhere.exe` reports with
the C++ tools, used through its `vcvars64.bat`. A compiler whose name is `cl` is Microsoft's;
every other one is GNU-style. `cc`, `ar` and `nm` are the programs beside a GNU-style
compiler: `gcc` or `clang`, `ar` or `llvm-ar`, `nm` or `llvm-nm`.

**Flags.** GNU-style: those of the makefile, `-std=c++11 -O2 -Wall -Wextra -Wpedantic
-Wshadow -Werror -Wframe-larger-than=512 -fno-exceptions -fno-rtti -Iinclude`. The shared
library is linked with `-shared`, and on Windows with `-static` as well, so that the DLL
carries the compiler's run-time and needs only libraries of Windows. A GNU-style toolchain
for Windows exports every function of a DLL that marks none, which gives the seven
functions. Microsoft's: `/std:c++14 /O2 /W4 /WX /EHs-c- /GR- /MT`, the oldest standard that
compiler takes, and one `/EXPORT:` for each function the header declares, read from the
header.

**The test host** is the sources of `tests/core/host/` with a second compilation of the
core's sources, as in the makefile. The makefile adds `-fsanitize=address,undefined`. The
build script tries what the toolchain has, by compiling, linking and running a small
program: the address and undefined-behaviour checks together, then the undefined-behaviour
checks that trap, then none. It prints the line `checks: <what it found>`. GCC for Windows
has no address check.

**What the suite needs to know.** The build script writes `core/build/toolchain.json`:
the kind, `gnu` or `msvc`, and the programs `cxx`, `cc`, `ar` and `nm`. `tests/core/support.py`
reads it. Without the file, which is how `make` leaves the folder, the programs are `c++`,
`cc`, `ar` and `nm` as before.

**Failures.** `error: no-compiler: <detail>` with status 1 when nothing is found; the
compiler's own output and status 1 when a step fails.

## The shared library, by system

`emulator/binding.py` gets `LIBRARY_NAME` and `BUILD_COMMAND`, chosen by `sys.platform`:

| System | `LIBRARY_NAME` | `BUILD_COMMAND` |
|---|---|---|
| macOS | `libodrig_core.dylib` | `make -C core shared` |
| Windows | `odrig_core.dll` | `python core/build.py shared` |
| any other | `libodrig_core.so` | `python core/build.py shared` |

`emulator/app.py` makes its default `--core` from `LIBRARY_NAME`. Nothing else in the
emulator knows the name.

## The line port

`emulator/lineport.py` holds `Port`: a threading TCP server on `127.0.0.1`. The address is
`httpd.ADDRESS`; no second module names an address. Each connection has a thread that reads
what arrives, hands it to `feed`, and writes back what `feed` returns. `feed` is the engine's
entry for bytes, called with the transport name `tcp`, so the core cuts the bytes into
lines exactly as it does for the serial port.

- The core keeps one unfinished line for bytes that arrive, whichever way they come. A line
  begun on one connection and not ended is ended by the next bytes that arrive, as with the
  serial port. A program sends whole lines.
- A reply goes to the connection whose bytes finished the line. A connection that closes
  before its reply is written loses it.
- Closing the emulator closes every connection.

**Which ports open.**

| System | Without options | `--tcp-port N` | `--serial-link PATH` |
|---|---|---|---|
| macOS, and any system with a pseudo-terminal | Serial port. | Serial port and line port. | The link is made there. |
| Windows | Line port on 8601. | Line port on N. | Status 1, `serial-unavailable`. |

The printed lines are `page:`, then `serial:` where there is a serial port, then `tcp:`
where there is a line port. `emulator/serialport.py` imports `termios` and `tty`, which
Windows lacks, so `app.py` imports it only where `os.openpty` exists.

**The event `hello`** gets the member `tcp`, the address as `127.0.0.1:<port>` or `null`;
`serial` is `null` without a serial port. The page shows `serial`, `tcp`, or both.

## Stopping

`app.serve` waits for a signal with `stopped.wait()`. On Windows a wait without a time limit
is not interrupted by Ctrl-C, so the wait is cut into short ones. The handlers are set for
`SIGINT`, `SIGTERM` and, where it exists, `SIGBREAK`. A test on Windows stops its emulator
with `CTRL_BREAK_EVENT`, which needs the child in a process group of its own; elsewhere the
tests keep `SIGTERM` and `SIGINT`.

## The command tool

`--tcp ADDRESS` joins `--port` and `--http` in the group of which exactly one is given.
`client.tcp_exchange(address, data, timeout, accept=is_reply)` connects, sends, and returns
the first line `accept` takes; the loop that cuts received bytes into lines is shared with
the serial exchange. An address without a port is refused as not understood, status 2.

**A real serial port on Windows.** `odrigctl/winserial.py` uses `ctypes` and `kernel32`:
no added package. `Port(name)`:

1. opens `\\.\<name>` with `CreateFileW`;
2. lowers RTS, then DTR, with `EscapeCommFunction`; a refusal is ignored;
3. reads the port's settings, sets 115200 baud, 8 bits, no parity, one stop bit, binary,
   no flow control, and DTR and RTS control off, and writes them with `SetCommState`. The
   lines are low already, so this changes no line, and the port keeps the setting: opening
   it again raises neither;
4. sets the time limits so that a read returns with what has arrived.

Its methods are those the exchange uses: `received(seconds)`, `write(data, seconds)` and
`close()`. `client.py` keeps the functions it has for macOS unchanged and picks: with
`termios` present, the port of POSIX; without it, `winserial.Port`.

Windows raises DTR and RTS when it opens a port that has not been set otherwise, before a
program can say anything. Whether that restarts the board on the first opening cannot be
known without a board on a Windows computer. It is the open check of requirement 8.

## The suites on Windows

- **Building.** `tests/emulator/__init__.py` runs `make -C core shared` on macOS and
  `python core/build.py shared` elsewhere, with the Python that runs the suite.
- **The JavaScript shell.** `tests/emulator/js/shell.js` is a small program for Node.js that
  takes the command line the tests give `jsc`: script files run in order in one global
  scope, `-e CODE`, and what follows `--` as `arguments`, with `print` and `checkSyntax`.
  The tests take `jsc` where macOS has it and `node` with that program elsewhere.
- **The pseudo-terminal.** The tests of the serial port and of the POSIX serial exchange
  are skipped where there is none. Tests of the line port, of `tcp_exchange` and of
  `winserial` with a stand-in for `kernel32` run everywhere they can.
- **The emulator as a child.** The helper reads the lines the emulator prints, whichever
  ports it has, and stops it with the signal of the system.
- **The core's test host.** `tests/core/host/` uses `posix_memalign` and needs its input
  and output unchanged, which on Windows means binary mode. Both get the call of the
  system. The tests that read the object listing read the form `nm` prints for the object
  format of the system.
- **The converter.** Its failures on Windows are in the tests, not in the tool: files
  written with the line ending of the system, paths compared with `/`, and a zlib that
  cannot be told to write one kind of block. Each is settled in its task.

## The pages

The getting-started page's section "On Windows" becomes the setup that works there: what to
install, the commands with `.venv\Scripts\python` and `python core/build.py`, and what is
not available. The page keeps its macOS commands as they are, because the walk-through
suite runs them on the first computer. `tests/onboarding` learns the commands of Windows.

## Risks

- **macOS cannot be checked here.** The diff to what macOS runs is kept small: `client.py`
  keeps its POSIX functions, `serialport.py` is not edited, `app.py` opens the same port by
  default and prints the same two lines. What changed is listed as open for the first
  computer.
- **The first opening of a real port on Windows** may raise the modem lines. See above.
- **Python 3.10 on Windows** sleeps in steps of about 16 ms, so the emulator refreshes
  less evenly than with Python 3.11 or later. The requirement is 20 a second.
