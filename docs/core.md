# The core

The core is the C++ library in `core/` that plays an installed show: it reads
`mapping.json`, `show.json` and the `.odrg` files, keeps time, handles the commands of
[commands.md](commands.md) and gives the colour of every LED of every leg. The emulator and
the firmware run the same source files, so the two cannot behave differently.

The core is written in C++11 without exceptions, run-time type information, threads or
floating point. It includes no header of a platform and refers to nothing outside itself
but the C library's routines that copy, fill and compare memory.

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core` | Builds the library `core/build/libodrig_core.a` from every `core/src/*.cpp`, with every compiler warning treated as an error. | Apple's command-line developer tools: `make`, `c++` and `ar`. |
| `make -C core test` | Builds the library and the test host `core/build/odrig_host`, then runs the suite of `tests/core/`. | The same, and Python 3.10 or later with no added package. |
| `make -C core clean` | Removes `core/build/`. | |

The test command uses `python3`. Another Python is named on the command line:

```
make -C core test PYTHON=.venv/bin/python
```

The suite is every `test_*.py` file in `tests/core/`, found by discovery. It drives the
test host as a child process and compares what the core does with the reference decoder and
the readers of the converter, [converter.md](converter.md). The test host is built with the
address and undefined-behaviour sanitizers. The suite needs no hardware and no network
connection.

Git ignores `core/build/`.
