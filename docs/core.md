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
| `make -C core bench` | Builds `core/build/odrig_bench`, has the converter write the dense 60 x 30 clip of 10 seconds into `core/build/bench/`, compressed and uncompressed, and prints how long a frame takes to decode. | The same as the test command. |
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

## Benchmark

`make -C core bench` decodes each of the two clips ten times, from memory, and prints one
row for each: the size of the file, its number of frames, and the mean and the longest time
one frame record took to decode, in microseconds.

```
file                     bytes  frames  mean_us  max_us
dense-compressed.odrg   724948     500     42.2   115.1
dense-plain.odrg        765984     500     23.3    73.8
```

These figures are from a Mac with Apple Silicon. They are a first figure to hold the board
against, nothing more: the benchmark is not part of the test command, and no time makes it
pass or fail. The benchmark program is `tests/core/bench/bench.cpp`; it links the library as
`make -C core` builds it, without the sanitizers.

Git ignores `core/build/`.
