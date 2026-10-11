# The core

The core is the C++ library in `core/` that plays an installed show: it reads
`mapping.json`, `show.json` and the `.odrg` files, keeps time, handles the commands of
[commands.md](commands.md) and gives the colour of every LED of every leg. The emulator and
the firmware run the same source files, so the two cannot behave differently.

The core is written in C++11 without exceptions, run-time type information, threads or
floating point. It includes no header of a platform and refers to nothing outside itself
but the C library's routines that copy, fill and compare memory. It keeps everything it
knows in one object, takes its memory once at startup, and never calls itself.

This page covers the [commands](#commands) that build and test it, the
[host interface](#the-host-interface), [time and refreshes](#time-the-grid-and-refreshes),
the [LED data](#led-data), [command lines](#command-lines), [startup](#startup),
[memory](#memory), the [benchmark](#benchmark) and the [test host](#the-test-host).

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core` | Builds the library `core/build/libodrig_core.a` from every `core/src/*.cpp`, with every compiler warning treated as an error. | Apple's command-line developer tools: `make`, `c++` and `ar`. |
| `make -C core test` | Builds the library and the test host `core/build/odrig_host`, then runs the suite of `tests/core/`. | The same, and Python 3.10 or later with no added package. |
| `make -C core bench` | Builds `core/build/odrig_bench`, has the converter write the dense 60 x 60 clip of 10 seconds into `core/build/bench/`, compressed and uncompressed, and prints how long a frame takes to decode. | The same as the test command. |
| `make -C core clean` | Removes `core/build/`. | |

The test command uses `python3`. Another Python is named on the command line:

```
make -C core test PYTHON=.venv/bin/python
```

The suite is every `test_*.py` file in `tests/core/`, found by discovery. It drives the
test host as a child process and compares what the core does with the reference decoder and
the readers of the converter, [converter.md](converter.md), and with a reference player
written in Python, `ReferencePlayer` in `tests/core/support.py`. The test host is built with
the address and undefined-behaviour sanitizers. The suite needs no hardware and no network
connection.

Git ignores `core/build/`.

## The host interface

A host is the program around the core: the emulator, the firmware, or the test host. It
includes one header, `core/include/odrig_core.h`, which is valid as C and as C++ and needs
only `stdint.h` and `stddef.h`, and it compiles every `core/src/*.cpp` with a C++11 compiler
or a later one. The core's own names are in the namespace `odrig`; the only names it adds
outside it are the functions below.

### What the host supplies

The host fills in an `odrig_host` and passes it to `odrig_core_begin`. The core copies it.
Every function receives `ctx` as its first argument.

| Member | What it is |
|---|---|
| `ctx` | Any pointer of the host's. The core only hands it back. |
| `alloc` | `void *alloc(void *ctx, size_t bytes)`: memory of that size, aligned for any object, or `NULL` when the host has none. The core calls it only inside `odrig_core_begin`, never frees what it got, and clears each block itself. |
| `open` | `int open(void *ctx, const char *name)`: opens a file of the installed file set by its name, for reading from its start. Returns 1 when it is open, 0 when there is no such file, and -1 on any other failure. The names are `mapping.json`, `show.json` and the `.odrg` names of the show, which hold only `a`-`z`, `0`-`9`, `-`, `_` and `.`. |
| `read` | `int32_t read(void *ctx, uint8_t *buffer, size_t capacity)`: the next bytes of the open file. Returns how many it put into `buffer`, from 1 to `capacity`; 0 at the end of the file; -1 on a failure. `capacity` is never above 512. Fewer bytes than asked for are fine. |
| `close` | `void close(void *ctx)`: closes the open file. |
| `log` | `void log(void *ctx, const char *text)`: one line of diagnostic text without a newline. May be `NULL`. Today the core logs one thing: the reason text when the show becomes invalid. |

The core has at most one file open. It reads a file from its first byte towards its last,
never goes back, and closes it before it opens another. It reads `mapping.json` and
`show.json` twice each at startup. It never writes, creates or deletes a file, and it reads
no clock.

### What the core offers

| Function | What it does |
|---|---|
| `odrig_core *odrig_core_begin(const odrig_host *host)` | Starts the core: reads and checks the whole installed file set, see [Startup](#startup). Returns the core, or `NULL` when the host could not supply the first block of memory. |
| `int odrig_core_poll(odrig_core *core, uint64_t now_ms)` | Asks for a refresh. Returns 1 when it produced new LED data and 0 when none was due. |
| `uint32_t odrig_core_leg_count(const odrig_core *core)` | The number of legs: those of the mapping file, or 0 without a valid mapping. |
| `int odrig_core_leg(const odrig_core *core, uint32_t index, odrig_leg *out)` | Fills in leg `index`, counted from 0 in the order of the mapping file. Returns 1, or 0 for an index that is not a leg. |
| `size_t odrig_core_command(odrig_core *core, uint64_t now_ms, const char *line, size_t length, char *reply, size_t capacity)` | Takes one command line and writes its reply. Returns the length of the reply. `capacity` must be at least `ODRIG_REPLY_MAX`; with less the core does nothing and returns 0. |
| `void odrig_core_feed(odrig_core *core, uint64_t now_ms, const uint8_t *bytes, size_t length, odrig_reply_fn on_reply, void *reply_ctx)` | Takes bytes of a transport, cuts them into lines, answers each line, and calls `on_reply` once for each. |
| `const char *odrig_core_error(const odrig_core *core)` | The reason the show is invalid, as a text that ends in a zero, or `NULL` when the show is valid. |

`odrig_leg` describes one leg:

| Member | What it is |
|---|---|
| `leg` | The leg's number in the mapping file. |
| `pin` | The data pin the leg is wired to. |
| `led_count` | The number of its LEDs: the strip length of the mapping file times the leg's number of strips. The strips are rows of the canvas in a row-leg file and columns in a column-leg file, see [mapping.md](mapping.md). |
| `rgb` | Its LED data from the last refresh: `led_count * 3` bytes. The pointer stays the same for as long as the core is used; the bytes change at every refresh. |

`odrig_reply_fn` is the function `odrig_core_feed` calls:
`void on_reply(void *ctx, const char *line, size_t line_length, const char *reply, size_t reply_length)`.
`ctx` is the `reply_ctx` of the call. The line and the reply are valid during the call only,
and neither ends in a zero.

`ODRIG_LINE_MAX` is 64, the longest command line in characters. `ODRIG_REPLY_MAX` is 192,
the longest reply in bytes with its newline.

### Rules of use

- `odrig_core_begin` is called once. After it has returned, the other functions may be
  called in any order and any number of times.
- The core is used from one thread at a time, and a function of the host does not call the
  core.
- There is no function that ends the core. The memory belongs to the host, which may
  release it once it makes no further call. A file may still be open then: the one that is
  playing.
- `odrig_core_begin` returns only when the whole file set is checked, which decodes every
  `.odrg` file once. A host that must stay responsive meanwhile does its housekeeping in
  its `read` function, which the core calls at least once for every 512 bytes of a file.
- A function given `NULL` for the core does nothing and returns 0 or `NULL`.

## Time, the grid and refreshes

The core has no clock. The host passes the time with every call as `now_ms`, in whole
milliseconds from any starting point, taken from one clock that does not go backwards.

- The **power-on moment** is the timestamp of the first call that carries one, whichever
  function it is.
- A timestamp below the latest one the core has seen counts as the latest.
- The **grid** is the power-on moment and every 20 ms after it. A refresh is due at each
  grid time.
- `odrig_core_poll` produces a refresh when a grid time at or before `now_ms` is neither
  used nor skipped. It then counts the latest such grid time as used and every earlier
  unused one as skipped. Otherwise it produces nothing and returns 0.
- So a host that polls at every grid time gets one refresh per call; one that polls more
  often gets 0 in between; and one that polls late gets one refresh, with the picture of
  its own timestamp. Nothing is replayed.
- With a valid mapping the core produces refreshes whatever else is the case: with an
  invalid show, with nothing playing and with the LEDs switched off, the refresh is all
  zeros. Without a valid mapping there are no legs and no refreshes.

An item's time starts at the grid time of the first refresh after it was played, by a
`play` command or at power-on. Each refresh shows the frame whose time span holds the time
since then, as [format.md](format.md) defines; a cycle counts each turn's time from the
start of the turn. Playback time goes on while the LEDs are switched off.

`status` reports as `fps` the number of refreshes produced in the last whole second that
ended before the command's timestamp, with seconds counted from the power-on moment.

## LED data

After `odrig_core_poll` has returned 1, the `rgb` of each leg holds three bytes for each of
its LEDs: red, green and blue, in chain order, starting with the LED that is wired to the
board. The host sends them to the leg's pin as they are.

- Which canvas pixel an LED shows is the rule of [mapping.md](mapping.md), "Where each LED
  is", for a leg of rows and for a leg of columns. The core reads the mapping file at
  startup; nothing else defines the layout.
- Brightness is already applied: a colour value v is given as
  `(v * brightness + 127) / 255`, rounded down. The host applies no brightness of its own.
- Every byte is 0 while the show is invalid, nothing is playing, or the LEDs are switched
  off.

## Command lines

The commands and their replies are those of [commands.md](commands.md). The core is the
only place where a command is read; a transport only carries lines.

`odrig_core_command` takes one line. It drops one newline at the end of the line and then
one carriage return at its end, so the body of an HTTP request can be passed as it is. The
line is split into words at every single space. Every line gets exactly one reply, an empty
line too: one JSON object on one line, ended by a newline, without a zero after it.

`odrig_core_feed` is for a transport that delivers bytes, such as a serial port. Every
newline ends a line. The core keeps an unfinished line from one call to the next, and of a
line without end it keeps no more than it needs to tell that the line is too long. For each
line it calls `on_reply` with the line as the command entry read it, without its line end
and cut to 64 characters when it is longer, and with the reply.

A line that is no valid command changes nothing and is answered with the first code that
applies of `line-too-long`, `unknown-command`, `bad-argument`, `show-invalid` and
`unknown-id`.

## Startup

`odrig_core_begin` reads `mapping.json`, then `show.json`, and then decodes every different
`.odrg` file the show names, in the order in which the show first names them, from its
first frame record to its last. For each file it checks the header, then the size against
the mapping, then the body.

A show that is wrong in any way is refused as a whole: the LEDs stay dark, `play` is
answered with `show-invalid`, and `odrig_core_error` and `status` give the reason. The
first check that fails decides. The texts are listed in [reasons.md](reasons.md), "The
core". The other commands work as ever.

After startup the LEDs are switched on. With a valid show, brightness is the value of
`show.json` and the `start` item is playing if there is one. With an invalid show nothing
is playing, and brightness is the value of `show.json` when that file and its ids are
sound, and 0 otherwise.

A file can also fail while it plays: it is gone, cannot be read, or no longer follows the
format. From that refresh on the show is invalid in the same way, until the next startup.

The core keeps nothing from one startup to the next. Given the same files and the same
calls with the same timestamps, it gives the same replies and the same LED data, byte for
byte.

## Memory

The core asks the host for memory only inside `odrig_core_begin`, in up to ten blocks sized
from the mapping and the show. The figures are for the target file, `mapping/legs-20.json`,
60 x 60 on twenty legs, with a show of 100 items: 80 animations with a file each and 20
cycles of 10 entries. They are measured by the suite.

| Block | Size | Bytes |
|---|---|---:|
| The core object | fixed | 3,112 |
| Legs | 12 for each leg | 240 |
| The pixel of each LED | 2 for each LED | 7,200 |
| LED data | 3 for each LED | 10,800 |
| Strip check | 1 bit for each strip: each row of a row-leg file, each column of a column-leg file | 8 |
| Pixel buffer | the smaller of 3 * W * H and 65,534 | 10,800 |
| Window of the DEFLATE decoder | 32,768 | 32,768 |
| Items | 16 for each item | 1,600 |
| Cycle entries | 2 for each entry of a cycle | 400 |
| Files | 48 for each animation item | 3,840 |
| **Total** | | **70,768** |

That is 54 percent of the 131,072 bytes the core may use for this canvas. The example show
on the two-leg mapping asks for 38,933 bytes. The size and the number of frames of an
`.odrg` file change nothing: the core never holds a file or a frame record, only the
512 bytes it last read.

When the host cannot supply the first block, `odrig_core_begin` returns `NULL`. When it
cannot supply a later one, the show is invalid with `out-of-memory`.

## Benchmark

`make -C core bench` decodes each of the two clips ten times, from memory, and prints one
row for each: the size of the file, its number of frames, and the mean and the longest time
one frame record took to decode, in microseconds.

```
file                     bytes  frames  mean_us  max_us
dense-compressed.odrg  1383766     500     83.7   188.2
dense-plain.odrg       1462236     500     45.9   119.4
```

These figures are from a Mac with Apple Silicon. They are a first figure to hold the board
against, nothing more: the benchmark is not part of the test command, and no time makes it
pass or fail. The benchmark program is `tests/core/bench/bench.cpp`; it links the library as
`make -C core` builds it, without the sanitizers.

## The test host

`core/build/odrig_host` is the host the suite drives. Its sources are in
`tests/core/host/`. It has no clock: every timestamp comes from its input, so a run can be
repeated exactly.

| Invocation | What it does |
|---|---|
| `odrig_host session DIR [options]` | Starts the core on the files of the folder `DIR`, prints the startup lines, then obeys the lines of standard input. |
| `odrig_host session --batch [options]` | Runs one session after the other from standard input, which holds a file set and a script for each, and prints `end` after each. |
| `odrig_host decode FILE` | Reads one `.odrg` file with the core's decoder. Prints `header <W> <H> <C> <F> <compressed>`, one `frame <ms> <hex>` for each frame record with the picture as three bytes for each pixel, then `end`; or `rejected <reason>` where the file is refused. |
| `odrig_host decode --batch` | The same for any number of files on standard input. |
| `odrig_host inflate` | Decodes standard input as one raw DEFLATE stream with the core's decoder. Prints `data <hex>` and `left <n>`, the number of bytes of input after the stream; or `rejected <reason>`. |
| `odrig_host inflate --batch` | The same for any number of streams on standard input. |
| `odrig_host reasons` | Prints every reason name the core can report, one on a line. |
| `odrig_host guard alloc`, `guard new`, `guard read` | Does what the host must stop: asks the host for memory, or the program, as the core would after startup; or asks for 513 bytes of a file. |

A batch on standard input is a row of pieces, each after its length as four bytes, least
significant first. For `session --batch` a session is the number of its files as text, a
name and a content for each file, and its script.

The startup lines of a session are `log <text>` for each diagnostic text of the core;
`core ok`, or `core null` when `odrig_core_begin` returned `NULL`; `memory <bytes> <blocks>`,
what the core asked for; `error <text>` or `error none`; `leg <leg> <pin> <count>` for each
leg; and `ready`.

| Input line | What the host does | What it prints |
|---|---|---|
| `poll <ms>` | `odrig_core_poll` | `refresh <ms>` and `data <leg> <hex>` for each leg, or `idle <ms>` |
| `line <ms> <text>` | `odrig_core_command` with the text | `reply <json>` |
| `linehex <ms> <hex>` | `odrig_core_command` with exactly these bytes | `reply <json>` |
| `bytes <ms> <hex>` | `odrig_core_feed` with these bytes | `fed <hex of the line>` and `reply <json>` for each line |
| `error` | `odrig_core_error` | `error <text>` or `error none` |

| Option of a session | What it does |
|---|---|
| `--alloc-fails-at N` | The N-th call of `alloc` returns `NULL`. |
| `--dirty-memory` | Memory is handed out filled with the byte `0xA5`, not zeroed. |
| `--read-fails FILE OFFSET` | `read` fails at that offset of that file. |
| `--read-fails-after FILE OFFSET N` | The same, but the first N openings of the file are spared. |
| `--remove-after FILE N` | The file is gone once it has been opened N times. |
| `--swap-after FILE N OTHER` | After N openings the name opens the content of the file `OTHER`. |
| `--trace-files` | Prints `open <name> <result>` for every call of `open`. |

The host hands out every file in pieces of changing sizes, none above 512 bytes. It checks
the core as it goes and ends the program at once when a check fails:

| Status | Line printed | When |
|---:|---|---|
| 0 | | The run ended well. |
| 1 | a line that says what | An answer of the core contradicts another one: the legs and their count, a decoder that changes its answer after the end, a reply written into too little room. Also `guard` when nothing stopped it. |
| 64 | a usage message, `bad line` or `bad batch` | The command line or the input was not understood. |
| 70 | `allocation after startup` | The core asked the host for memory, or the program allocated with `new`, during a call after startup. |
| 71 | `file misuse` | The core opened a file while one was open, read or closed with none open, or asked for no byte or for more than 512 in one `read`. |
| 72 | `bad reply` | A reply was not one line of printable characters with a newline, of at most 192 bytes. |
