# The core

The core is the C++ library in `core/` that plays an installed show: it reads
`mapping.json`, `show.json` and the `.odrg` and `.odrgx` files, keeps time, handles the commands of
[commands.md](commands.md) and gives the colour of every LED of every leg. The emulator and
the firmware run the same source files, so the two cannot behave differently.

The core is written in C++11 without exceptions, run-time type information, threads or
floating point. It includes no header of a platform and refers to nothing outside itself
but the C library's routines that copy, fill and compare memory and the one that finds the
end of a text, which GCC puts in the place of a loop. It keeps everything it knows in one
object, takes its memory once at startup, and never calls itself.

This page covers the [commands](#commands) that build and test it, the
[host interface](#the-host-interface), [time and refreshes](#time-the-grid-and-refreshes),
the [LED data](#led-data), [command lines](#command-lines), [startup](#startup),
[a drive](#a-drive), [texts](#texts), [clocks](#clocks), [memory](#memory), the
[benchmark](#benchmark) and the [test host](#the-test-host).

## Commands

Run from the repository root.

| Command | What it does | What it needs |
|---|---|---|
| `make -C core` | Builds the library `core/build/libodrig_core.a` from every `core/src/*.cpp`, with every compiler warning treated as an error. | Apple's command-line developer tools: `make`, `c++` and `ar`. |
| `make -C core test` | Builds the library and the test host `core/build/odrig_host`, then runs the suite of `tests/core/`. | The same, and Python 3.10 or later with no added package. |
| `make -C core bench` | Builds `core/build/odrig_bench`, has the dense generator write the dense 60 x 60 clip of 10 seconds and the converter encode it into `core/build/bench/`, compressed and uncompressed, and prints how long a frame takes to decode. | The same as the test command, and Node.js for the converter. |
| `make -C core clean` | Removes `core/build/`. | |
| `python core/build.py` | Builds the library without GNU Make, which is how Windows builds: `core/build/libodrig_core.a`, or `odrig_core.lib` with Microsoft's compiler. It builds again only what changed. | A C++ compiler: `g++` or `clang++`, on the path or unpacked under the folder `tools/`, or Microsoft's C++ build tools. Python 3.10 or later. |
| `python core/build.py test` | Builds the library and the test host, then runs the suite of `tests/core/` with the Python that runs the script. | The same. |
| `python core/build.py clean` | Removes `core/build/`. | |

The test command uses `python3`. Another Python is named on the command line, by its full
path, because `make` runs inside `core/`:

```
make -C core test PYTHON="$PWD/.venv/bin/python"
```

The suite is every `test_*.py` file in `tests/core/`, found by discovery. It drives the
test host as a child process and compares what the core does with the decoder and the
readers of the Python library, [python-library.md](python-library.md), and with a reference
player
written in Python, `ReferencePlayer` in `tests/core/support.py`. The test host is built with
the address and undefined-behaviour sanitizers. The suite needs no hardware and no network
connection.

The build script finds the compiler itself: the one named with `--cxx`, the one the
variable `CXX` names, one unpacked under `tools/`, one on the path, and then Microsoft's.
It builds the test host with the checks for faults at run time that the toolchain has,
and prints which: the two sanitizers where they are; with GCC for Windows, which has no
library for them, the undefined-behaviour checks as traps, the stack protector and the
assertions of the standard library; with Microsoft's compiler its own run-time checks. A
fault that only the address sanitizer finds is therefore found on macOS. With Microsoft's
compiler the tests that need a GNU-style `nm`, `ar`, `cc` or `c++` are skipped.
The emulator's suite compiles every source of the core with Microsoft's compiler, with the
flags the build script gives it, wherever the script finds that compiler, also where the
core is built with GCC. The nine functions the core keeps out of line, so that the frame of
the refresh stays small, are marked with the macro `ODRIG_NOINLINE` of `core_state.h`, which
each compiler reads in its own words.

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
| `open` | `int open(void *ctx, const char *name)`: opens a file of the installed file set by its name, for reading from its start. Returns 1 when it is open, 0 when there is no such file, and -1 on any other failure. The names are `mapping.json`, `show.json` and the `.odrg` and `.odrgx` names of the show, which hold only `a`-`z`, `0`-`9`, `-`, `_` and `.`. |
| `read` | `int32_t read(void *ctx, uint8_t *buffer, size_t capacity)`: the next bytes of the open file. Returns how many it put into `buffer`, from 1 to `capacity`; 0 at the end of the file; -1 on a failure. `capacity` is never above 512. Fewer bytes than asked for are fine. |
| `close` | `void close(void *ctx)`: closes the open file. |
| `log` | `void log(void *ctx, const char *text)`: one line of diagnostic text without a newline. May be `NULL`. The core logs three things: the reason text when the show becomes invalid, `file <name> unavailable: <reason>` when it quarantines a file of the show, and `drive file <name> left out: <reason>` when it leaves out a file of a drive. |
| `write_open` | `int write_open(void *ctx, const char *name)`: begins a new, empty file of this name, in place of one that has it. A file that was being written is given up and removed. Returns 1, or -1 on a failure. `NULL` for a host without storage that can be changed. |
| `write` | `int write(void *ctx, const uint8_t *bytes, size_t length)`: adds bytes to the file being written. `length` is 1 to 1,500. Returns 1, or -1. |
| `write_close` | `int write_close(void *ctx)`: ends the writing. When it has returned 1, the file is whole in storage and stays so through a power cut. Returns 1, or -1 on a failure. |
| `rename` | `int rename(void *ctx, const char *from, const char *to)`: gives the file `from` the name `to`, in place of a file that has it. After a power cut during the call, `to` is its old file or the new one, whole. Returns 1, or -1. |
| `remove` | `int remove(void *ctx, const char *name)`: removes the file of this name. A file being written under it is given up. Returns 1 when it removed one, 0 when there was none, -1 on a failure. |
| `space` | `int space(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes)`: the free and the total bytes of the storage the files are in; a value above 4,294,967,295 is given as that. Returns 1, or -1 when the host cannot tell. |
| `read_at` | `int32_t read_at(void *ctx, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity)`: reads a file apart from the one that `open`, `read` and `close` hold: up to `capacity` bytes from this offset. Returns the number read, 0 at or after the end of the file, -1 on a failure and when there is no such file. `capacity` is never above 512. |
| `drive` | `uint32_t drive(void *ctx)`: the number of the drive of animations that is plugged in now: a number other than 0 that changes each time a drive is plugged in, or 0 while none is. The core calls it at each refresh, before the LED data is made. `NULL` for a host without a drive; see [a drive](#a-drive). |
| `drive_name` | `int drive_name(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity)`: the name of the file at this place, counted from 0, of the list of that drive, as the drive has it, into `buffer` with a zero after it, cut to `capacity - 1` bytes; for a file in a sub-folder of the drive's folder, its path from that folder, the parts joined by `/`. Returns 1, or 0 when that drive has no file at that place or is not plugged in any more. `NULL` when `drive` is. |
| `drive_space` | `int drive_space(void *ctx, uint32_t drive, uint64_t *free_bytes, uint64_t *total_bytes)`: optional mounted-volume capacity; returns 1, or -1 if unavailable or its generation changed. The shared core reports null counters on failure. It performs no writes. |
| `about` | `int about(void *ctx, char *buffer, size_t capacity)`: optional; a text that names the host, its build, its storage and the reason of its last start, into `buffer` with a zero after it, cut to `capacity - 1` bytes. Returns 1, or 0 when it has none. The core asks it at each `status`, with room for 96 bytes, and reports it as `host`. `NULL` for a host without it. |
| `drive_list` | `int32_t drive_list(void *ctx, uint32_t drive)`: optional; lists the drive's folder `odrig` and its sub-folders to three levels now, depth first, a folder's animation files by the bytes of their names and then its sub-folders by the bytes of their names, every file or, as the firmware does, up to the 256th file and the 32nd sub-folder, and returns the number of files listed, or -1 when that drive is not plugged in any more. A host that has it lists the folder only when it is called: the core calls it for a drive without a catalog and for a rebuild of a drive's catalog. |
| `drive_bind` | `int drive_bind(void *ctx, uint32_t drive, uint32_t place, const char *name)`: optional; gives the place to the file of the drive's folder with this name, so that `drive_name` gives the name and `drive/<place>` opens it. Returns 1, or 0 when that drive is not plugged in any more or the name is not one of the drive. Without it every drive is listed. |
| `drive_writable` | `int drive_writable(void *ctx, uint32_t drive)`: optional; 1 when the core may change the files of that drive with the storage functions, by the names `drive/<name>`, 0 otherwise. Without it the drive is read only. |

Capacity callbacks must meet the 50 ms per-call budget and must not start or wait
for an allocation-table scan under a lock playback needs. The microSD firmware
returns a cached pair or unavailable immediately when its storage guard is busy.
Mounted presence and write capability do not depend on known capacity. Unknown
upload preflight capacity is not a promise that a file fits: the existing write,
validation and catalog transaction must still fail safely on out-of-space.

The core has at most one file open. It reads a file from its first byte towards its last,
never goes back, and closes it before it opens another. It reads `mapping.json` and
`show.json` twice each at startup, and reads no clock. With the storage functions it
writes, renames and removes files of the folder, as [the files the core
writes](#the-files-the-core-writes) says, and nothing outside it.

The last seven members are the storage functions: three that write a file, `rename`,
`remove`, `space`, and `read_at`, which reads a second file beside the one that plays.

- A name the core gives any of them is 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_`
  and `.`: `mapping.json`, `show.json`, the name of an `.odrg` file, or one of the names
  the core keeps for itself, `upload.part`, `show.part`, `pending.txt`, `mapping.part`,
  `order.txt`, `order.part`, `repeats.txt`, `repeats.part`, `clocks.txt`, `clocks.part`,
  `playlist.txt`, `playlist.part`, `brightness.txt` and `brightness.part`.
- The core has at most one file being written, gives `write` at most 1,500 bytes in one
  call, and reads a file with `read_at` from offset 0 on, each call where its last call for
  that file ended; only the commands `read` and `catalog page`, and the reads of the files
  of a drive's index and of a rebuild of it, `drive/index-...` and `drive/rebuild...`, begin
  at the offset they are given. Between two
  calls for one file there may be calls for another.
  It renames and removes no file that `open` holds or that is being written.
- A host without storage that can be changed sets `write_open` to `NULL`. The core then
  calls none of the seven but `space`. `space` may be `NULL` too; the command `space` is
  then answered with `storage-error`. With `write_open` set, all seven are set.
- The core calls them only inside `odrig_core_begin`, `odrig_core_command`,
  `odrig_core_feed` and `odrig_core_poll`, never from inside another host function.
- With `write_open` `NULL`, `remove` and `upload begin` are answered with `storage-error`,
  the start removes nothing, and the four blocks that only a change of the show needs are
  not asked for.
- `read_at` reads the file of an upload back from storage while it is checked: one more
  function than writing, renaming and removing, because `open`, `read` and `close` hold
  the one file that plays.

The drive and drive_name members describe the drive. A host with a drive sets both, and has storage that
can be changed; with either of them `NULL`, or with `write_open` `NULL`, the core has no
drive and calls neither. To `open` and `read_at` the core names the file at place `p` of
the drive's list `drive/p`, as `drive/0`; no name of the installed file set has a slash,
and a drive's file is named by its path from the drive's folder, `drive/night/comet.odrg`
for one in a sub-folder. A host that is given such a name for a drive that is gone answers
as for a file that is not there.

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
| `void odrig_core_mini_support(odrig_core *core)` | Opts the host into checked miniature output transitions, on a 60x60 canvas. |
| `int odrig_core_mini(const odrig_core *core, odrig_mini *out)` | Reads miniature support, revision, requested/active/pending/failure state and its borrowed 180-byte RGB buffer. The chain index is `x*6+y` in a 10x6 bottom-left coordinate system. Normal legs are unchanged. |
| `int odrig_core_mini_complete(odrig_core *core, uint32_t revision, int success)` | Completes only the matching pending revision. A failed host setup must hold outputs dark until successful retry. No allocation or persistence. |

`odrig_leg` describes one leg:

| Member | What it is |
|---|---|
| `leg` | The leg's number in the mapping file. |
| `pin` | The data pin the leg is wired to. |
| `led_count` | The number of its LEDs: the strip length of the mapping file times the leg's number of strips. The strips are rows of the canvas in a row-leg file and columns in a column-leg file, see [mapping.md](mapping.md). |
| `rgb` | Its LED data from the last refresh: `led_count * 3` bytes. The pointer stays the same for as long as the core is used; the bytes change at every refresh. |

`odrig_mini` describes the temporary output:

| Member | What it is |
|---|---|
| `revision` | Nonzero setup request number, matched by the host acknowledgement. |
| `active` | The acknowledged miniature mode; zero at boot and after failed setup. |
| `requested` | The desired mode of the current or most recent setup request. |
| `pending` | One while the host clears and configures outputs. |
| `failed` | One after failed setup, until successful retry; status stays unknown while retrying. |

Its `rgb` pointer holds180bytes, with physical index `x*6+y`, x0–9 and y0–5.
`status.mini` reports support and acknowledged state. Its extra fields retain the
1024-byte reply limit by bounding the host description to256escaped bytes as well
as95input bytes; ordinary printable descriptions keep their existing length.
The host serializes these helpers with every other core call and acknowledges only
after the outgoing bus is cleared and the new outputs are checked.

`odrig_reply_fn` is the function `odrig_core_feed` calls:
`void on_reply(void *ctx, const char *line, size_t line_length, const char *reply, size_t reply_length)`.
`ctx` is the `reply_ctx` of the call. The line and the reply are valid during the call only,
and neither ends in a zero.

`ODRIG_LINE_MAX` is 2048, the longest command line in characters. `ODRIG_REPLY_MAX` is 1024,
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

What plays is the playlist or a cycle, never an animation by itself. Its time starts at
the grid time of the first refresh after it was played, by a `play` command or at
power-on. Each refresh shows the frame whose time span holds the time since the start of
the turn, as [format.md](format.md) defines: a cycle counts each turn's time from the
start of the turn, and so does the playlist. Playback time goes on while the LEDs are
switched off.

The playlist of [show.md](show.md) is played in the same way, one turn at a time. The
core keeps the animation whose turn it is and the moment that turn began, which for the
first turn is the grid time of the first refresh. At a refresh, while the time since then
is at or above the length of the turn, the turn of the next animation begins exactly
where this one ended, however late the refresh is; whole rounds of the playlist are taken
off first, by division, so a host that asked for no refresh for a long time costs one
walk over the items. The length of a turn is worked out from the length of the
animation's loop and from `repeat`, `max_seconds` and `min_seconds`. Every turn opens its
file anew.

The length of a loop is the sum of the durations of its frames. The core knows it once a
check has read the file to its end, or once the player has decoded the loop to its end,
whichever comes first. Until then the animation is in its first loop: the player decodes
its records up to the time of the refresh and counts them against the number of frames in
the header, and when the last one ends at or before that time, their durations add up to
the length. So a turn ends where it would end with the length known from the start. When
an animation has a `max_seconds` and the time has reached it, the first loop is decoded
up to that longest time and no further: either the loop ended on the way, or the turn
ended there. Whole rounds are taken off by division only when every length is known.
Otherwise the turns are walked one by one, and an animation whose turn went by without a
refresh is decoded through once, which gives its length.

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

## Temporary miniature output

For a 60x60 canvas the core reserves one optional 188-byte startup block, including
one 180-byte RGB image. `odrig_core_mini_support` opts a capable host in;
`odrig_core_mini` reads active/requested/pending/failed state, request revision and
the image pointer; `odrig_core_mini_complete` accepts only the matching pending
revision and the host's setup result. These helpers share the caller's normal
serialization with other core calls. The pointer belongs to the core until close;
its contents change on polling and acknowledgement, so copy it under that same lock.
A host that does not opt in, another canvas or unavailable startup storage reports
unsupported. Ordinary playback still works. Custom hosts must implement safe output
setup before opting in; no host-interface struct layout changes.

While active, each central miniature cell averages a 10x10 block of the original
logical canvas. Source RGB, palette and widget layers are scaled first with the
normal brightness rounding at `min(selected brightness,40)`, then their 100 samples are
summed and divided with floor rounding. All side columns stay black. Physical
order is `x*6+y`, bottom left, in the [README orientation](../README.md#approved-connection-and-orientation).
The core uses three local channel sums per cell, with no per-frame allocation or
second decoder. The measured host allocation with a drive is 131069 bytes, below
131072. Off, invalid or blank output clears the image.

`debug mini on|off` requests a RAM-only transition. Only the host acknowledgement
changes the confirmed mode; failure reports `on:null` until a successful retry.
The normal leg API, pin permutations, cross-wiring and recording geometry remain
intact. No animation, mapping, show, catalog or persistent setting is written.
Miniature mode starts off on every boot. See [the command contract](commands.md#miniature-display-debug-mode).

## Command lines

The commands and their replies are those of [commands.md](commands.md). The core is the
only place where a command is read; a transport only carries lines.

`odrig_core_command` takes one line of at most 2,048 characters. It drops one newline at
the end of the line and then one carriage return at its end, so the body of an HTTP request
can be passed as it is. The line is split into words at every single space; a command has
five words at most, and a line with more is no valid command. Every line gets exactly one
reply, an empty line too: one JSON object on one line of at most 1,024 bytes, ended by a
newline, without a zero after it. The reply is written into the room the caller gives.

`odrig_core_feed` is for a transport that delivers bytes, such as a serial port. Every
newline ends a line. The core keeps an unfinished line of up to 2,048 characters, and a
carriage return after them, from one call to the next, and of a line without end it keeps
no more than it needs to tell that the line is too long. For each line it calls `on_reply`
with the line as the command entry read it, without its line end and cut to 2,048
characters when it is longer, and with the reply.

The unfinished line and the reply of this entry are two blocks the core takes at startup,
of 2,049 and of 1,024 bytes. When the host could supply neither or only one of them, the
show is invalid with `out-of-memory`, `odrig_core_feed` takes no bytes and calls nothing,
and `odrig_core_command` works as ever.

A line that is no valid command is answered with the first code that applies, in the
order of the table of [commands.md](commands.md): `line-too-long`, `unknown-command`,
`bad-argument`, `show-invalid`, `unsupported`, `no-upload`, `incomplete`, `bad-checksum`, `busy`,
`unknown-id`, `unavailable`, `in-use`, `read-only`, `mapping-conflict`, `stale`, `order-conflict`, `no-space`, `bad-offset`, `bad-file` and
`storage-error`. It
changes nothing, except that `bad-checksum`, `stale`, `bad-file` and `storage-error` discard the
upload they are about.

## Startup

`odrig_core_begin` reads `mapping.json`, then `show.json`, and then opens every different
`.odrg` file the show names, in the order in which the show first names them. Of each
file it reads the header, the first 16 bytes, and compares the canvas with the mapping's.
It decodes no frame record, so the time the start takes does not grow with the files. A
file that is missing or cannot be read, a header that is not sound and another canvas
quarantine that file, as "Unavailable animations" below says, and the start goes on with
the next one.

The bodies of the files are read after the start, while the show plays: see "The check
after the start". A host whose storage cannot be changed has no second decoders for
that. With such a host the start decodes every file from its first frame record to its
last, and nothing is left to check.

A show may have no items. It is valid, and nothing plays.

With a catalog of the board's storage that is `ok`, [catalog.md](catalog.md), a file it has
an entry for is neither opened nor read: its size, its length and its type come from the
entry, and the check after the start passes it over. The start reads the marker once and
the pages twice, first to check every page against the marker and then to take the
entries; an entry for another canvas than the mapping's quarantines its file with
`size-mismatch`. A file without an entry is opened and checked as above. A damaged or an
incompatible catalog is logged and gives nothing: every file is read as without one.

With a host whose storage can be changed, the start also removes what an interrupted
change left:

1. Before anything is read, it finishes the change of the catalog whose commit record is
   whole; when a call of that fails, the record stays and the catalog is `damaged`,
   `interrupted`, for this boot. Then it removes `upload.part`, which stays while a record
   is left, and `show.part`, and `mapping.part`, `order.part` and `repeats.part` when a
   `read_at` of one byte finds them there.
2. When `show.json` was read and its ids are sound, it opens `pending.txt`. Of that file
   it reads at most 1,500 bytes and takes every line that ends in a line feed and is a file
   name under the naming rule of [show.md](show.md). Each such file that no item names is
   removed, and then `pending.txt`. When a file could not be removed, `pending.txt` stays
   for the next start; when it could not be read, nothing is removed.
3. When the mapping or the show file could not be used, `pending.txt` is left alone.
4. When the show is valid, it reads `order.txt` with `read_at`, for the order of the show's
   items, and then `repeats.txt`, for their saved repeats; see [the saved
   order](#the-saved-order) and [the saved repeats](#the-saved-repeats).

A folder with none of the three files is asked to remove two names that are not there and
to open three that are not there, `catalog.do`, `pending.txt` and `catalog.txt`, and for
nothing else.

A show whose mapping file or show file cannot be used, whose ids are wrong, or for which
the host has too little memory is refused as a whole: the LEDs stay dark, `play` is
answered with `show-invalid`, and `odrig_core_error` and `status` give the reason. The
first check that fails decides. The texts are listed in [reasons.md](reasons.md), "The
core". The other commands work as ever. A fault of one `.odrg` file never refuses the
show.

After startup the LEDs are switched on. With a valid show, brightness is the value of
`show.json`, and the playlist plays, from its first usable animation or from the
animation `start` names, or the next usable one after it; a `start` that names a cycle
with a usable animation plays that cycle; a show without a usable animation plays
nothing. With an invalid show nothing is playing, and brightness is the value of
`show.json` when that file and its ids are sound, and 0 otherwise.

A file can also fail while it plays, and the check after the start can find a fault in a
body: the file is gone, cannot be read, or does not follow the format. The file is then
quarantined, until the next startup or an upload that replaces it.

## Unavailable animations

A fault of one `.odrg` file, `file-missing`, `size-mismatch`, `read-error` or a reason of
"ODRG files" in [reasons.md](reasons.md), quarantines that file for the rest of the boot,
wherever it is met: at the start, by the check after the start, by the whole-file check
of a host that cannot change its storage, or by the player. Its animations are
unavailable; the show stays valid.

- The core writes `file <name> unavailable: <reason>` to the log and keeps the fault's
  context, as "Bounded work" says.
- The playlist, the start's choice and every cycle pass over an unavailable animation. A
  cycle's turn whose animation is unavailable shows the first usable animation after it
  in the cycle, its time counted from the start of the turn; a cycle that lists no usable
  animation gives way to the playlist, from its first usable animation, and with none
  nothing plays.
- When the player meets the fault, that refresh keeps the LED data of the refresh before,
  and the next one goes on: the playlist with the next usable animation from its first
  frame. When the check meets it in the animation whose turn it is, the next refresh does
  the same.
- `play <id>` of an unavailable animation, or of a cycle that lists only such, is refused
  with `unavailable`; nothing is read for it. `list` lists it with `"bytes":null` and
  `"fault":"<reason>"`. `space` counts it among the animations.
- The file is not opened again in this boot: not by the player, the check, `list` or
  `play`. Nothing is written for the quarantine, and the file stays as it is. An upload
  that replaces it and passes its check makes the animation usable at once; `ignore`
  does not.
- A new start checks every file again.

The core keeps nothing from one startup to the next but the files of the folder. Given
the same files, the same answers of the host and the same calls with the same timestamps,
it gives the same replies, the same LED data and the same storage calls in the same
order, byte for byte.

## The check after the start

With a host whose storage can be changed, the body of every file is read while the show
plays, by the second source and the second decoders that also check an upload. The check
goes through the files in the order in which the show first names them. It runs in steps
inside `odrig_core_poll`, after the LED data of a refresh is complete:

- the first step of a file opens it with `read_at` and reads its header again;
- each further step decodes one frame record, or takes one slice of the settling of a
  defect, as [Bounded work](#bounded-work) says;
- the step after the last record asks for the end of the file: nothing may follow. The
  core then knows the size of the file, which `list` reports, and the length of its loop.

A file of F frame records takes F + 2 steps. A text or a clock takes three: its payload is
read and checked whole in the second step, as one record. At a refresh that follows the one before it
without a grid time skipped, and comes no more than 2 ms after its grid time, while the
last whole second had 30 refreshes or more, the check takes one step more than at the
refresh before, up to 16 steps. At any other refresh,
one after a gap or one later than that, the count begins again and the check takes no
step, unless it took none at the nine refreshes before either: then it takes one. So
the check is fast beside a show that leaves the host time, takes a step now and then
beside one that does not, and still comes to its end with a host that is late for every
refresh, at one step in ten refreshes.

A fault the check finds quarantines the file from that refresh on, and the check goes on
with the next file; that refresh shows what it shows. A file that cannot be read back is
`read-error`, whether it is damaged or gone: `read_at` has one answer for both. A file
the player quarantined first is not read by the check. Every command works while the
check goes on. `list` gives the `bytes` of a file not read whole yet as `null`. An upload
takes the second decoders: the check takes no step while it is open and then begins the
file it was in again. A file an upload installs was read by the upload's own check and is
not read again; a removal keeps the check at the file it was at. Once the check is
complete it stays so until the next start.

The player can come to a fault before the check does, in the animation that is playing.
It shows the frames before the fault, and quarantines the file at the refresh whose time
lies at their end or after it. A turn that ends before that, by `max_seconds` or as
a turn of a cycle, ends as ever, and the fault waits for the check. Bytes that follow the
last frame record are found by the check alone: the player never reads that far.

What a late refresh costs:

- The check loses its pace. The late refresh takes no step, and the next ones take 1, 2,
  3 and so on again: a single gap costs the check up to 136 steps over the next 17
  refreshes. A host that is late for every refresh gets one step in ten refreshes, and
  that refresh is later by the time one frame record takes to read and decode: on the
  board, beside a dense animation, about an eighth of a second.
- The player, with lengths not known, decodes what lies between the last picture and
  this one, as it does with the lengths known. After a long time without a refresh it
  walks the turns that went by one by one, and decodes each animation among them once,
  to the end of its loop or to its `max_seconds`. That is at most what the start used to
  do for every file, and it is done once for a file: afterwards its length is known.
- The memory is the same in every case. Nothing here asks the host for a block.

The check and the player may have the same file open at the same time, each through its
own source: the player with `open` and `read`, the check with `read_at`.

## Bounded work

No call of the core does more than a bounded piece of work on a file, whatever the file
holds, so that a command never waits long for the core and a bad file cannot hold the
board.

**Settling in slices.** A reader that holds a whole file inflates a compressed body before
it looks at a record, and has every data byte of a record before it looks at a bit; the
reason it gives for a file with several defects is the defect it meets first. The core's
decoder reads front to back, so when it finds a defect inside a body it settles it: it
reads on to the end of the body to find the defect such a reader meets first, a defect of
the stream, bytes after the stream or a record cut short. Settling takes at most 32,768
bytes of the body in one call, inflated bytes of a compressed body; then the decoder gives
the internal result `pending`, keeps where it was, and goes on at its next call. The
reason settling ends with is the same whatever the slices, and every later call gives it
again. A body may be as large as the format allows: a 65 KB file whose stream inflates
64 MiB of zeros after a bad record settles in 2,048 slices.

**`pending` is no reason.** It means "go on later" and goes between the parts of the
core only. No reply, log line or reason text ever holds it.

**The steps of the checks.** A step of the check after the start, of the check of an
uploaded file and of the check of a drive's file decodes one frame record, or takes one
slice of a settling. A step that ends `pending` counts no record and is taken again at
the next step. The check at the start of a host whose storage cannot be changed reads
every file whole inside `odrig_core_begin`, through every slice: nothing waits on it.

**Playback in slices.** At one refresh the player decodes at most 131,072 bytes of a body,
a record's boundary after it, and always one whole record; a slice of settling counts
against it. What is left is decoded at the next refresh, from where it stopped. A refresh
that has not come to the picture of its time yet, or meets a file that settles, keeps the
LED data of the refresh before, and `status` keeps naming the animation that picture is
of. When settling ends with a reason, the player acts on it as on any reason.

**The budgets.**

| Budget | Value | Why |
|---|---|---|
| Settling in one call | 32,768 bytes | The decoder inflates about 30 MB a second on the board's chip; 32 KiB is about a millisecond, far below a refresh of 20 ms. |
| Decoding at one refresh | 131,072 bytes | Twelve dense 60 x 60 records: a pause of a quarter of a second is caught up at once, and a longer one over a few refreshes. |
| One call on the board | 50 ms at most | A command waits for one call; 50 ms keeps a session of commands quick. |
| One read of the host | 250 ms at most | The microSD card's and the USB drive's own drivers time out sooner; a read that fails is `read-error`. |

The emulator's suite measures the wait of `status` while a file with such a tail is played
and checked; the board session measures it on the board.

**The fault's context.** For the latest file that came to a reason the core keeps, in its
object, the work it came in (the check at the start or after it, playback, the check of an
upload, the check of a drive's file), the file's name cut to 32 characters, the frame
record it was at counted from 0, the bytes of its body read so far, and the reason. Each
fault replaces the one before. Keeping it needs no second decode. The test host prints it
with its input line `fault`.

## Readiness

`status` says how far the check after the start is, from the core's own tables: the files
whose check has ended, by being read whole or by a fault, and those still to read, of the
show (a file once however many items name it) and of a drive; the animations unavailable;
and the name of the file the check is at. While a rebuild runs, the files it has read and
those it has still to read take their place, and the file it reads; while a drive's catalog
is read, the file is `catalog`. From these it gives the readiness: `checking`
while a file is still to read, `degraded` when none is and an animation is unavailable,
`ready` otherwise, and `recovery` for an invalid show. Nothing is decoded for it. The
command `fault` gives the fault's context of "Bounded work". [commands.md](commands.md)
has both replies.

## Texts

A text is an ODRGX container of type 2, [format.md](format.md), "The text payload". The
core reads it as the converter wrote it, and draws it at every refresh: the layout, the
order of the characters and the place of each glyph in the block are in the file, so the
core has no layout of its own.

- **Reading.** The payload, at most 3,612 bytes, is read and checked whole, with the
  checks and the order of [reasons.md](reasons.md), "Texts in ODRGX": the start reads
  its header only, the check after the start and the check of an upload read the
  payload in one step. When its turn begins the player reads the payload into the window
  of the DEFLATE decoder, which no frames file uses meanwhile, and closes the file. So a
  text asks for no memory of its own, and a fault in it, met at the start of its turn,
  quarantines it as any file with a fault.
- **Drawing.** At each refresh the picture is the background, and each lit pixel of each
  glyph in the colour, a square of 2 x 2 for the large font, at the place of the block
  the effect gives at the time into the pass: [format.md](format.md), "The text
  payload". The fonts are tables in `core/src/font_tables.cpp`, which `fonts/generate.mjs`
  writes from `fonts/*.txt` with the converter's copy, `converter/lib/fonttables.js`:
  1,464 bytes for the small font and 1,952 for the medium one, in the program's flash.
  Drawing takes no division in a loop and touches each pixel of the canvas once, then
  each lit pixel of each glyph on it.
- **The turn.** The loop of a text is its pass, and a turn ends at the end of a pass:
  [show.md](show.md), "The turn of an animation".

The reference pictures of `tests/vectors/procedural/` are drawn by the converter's
library; the core's suite draws each again with the test host and finds every pixel the
same.

## Clocks

A clock is an ODRGX container of type 3, a widget of 20 bytes: [format.md](format.md),
"The widget payload". It is read and checked as a text is, with the checks and the order
of [reasons.md](reasons.md), "Widgets in ODRGX", and held in the window while it plays.

- **The seed.** The core keeps a 32-bit noise. Every call of `odrig_core_poll` mixes its
  timestamp into it with MurmurHash3's finalizer, `mix`: `noise = mix(noise ^ t)`, t
  taken modulo 2^32. When a refresh finds that a clock's turn has begun, the turn gets
  the seed `mix(noise ^ mix(id ^ start))`, or 1 when that is 0, where `id` is the item's
  id, or the drive's id of the animation, and `start` the time the turn began. The seed
  is kept to the end of the turn: a later refresh, a loop that begins, `list` and
  `status` do not change it, and every new turn, one that `play` began too, gets a new
  one. The host gives no randomness; the times of the refreshes do, so on the board and
  in the emulator every turn differs, while the same timestamps give the same seeds.
  `status` reports the seed: [commands.md](commands.md).
- **Drawing.** At each refresh the clock is drawn at the time since its turn began, not
  since its loop began: the virtual time follows from the seed and that time alone, so
  however the refreshes come, a time of the turn has one picture. The analog and the
  digital clock touch each pixel once and test it against the rim, the pivot, two hands
  and twelve marks; the melting watch first takes each pixel back to the dial through
  its tilt and its fold. Every product fits 64 bits, and nothing is divided but by a
  number that is fixed for the refresh.
- **The turn.** The loop of a clock is its `seconds`, and its turn is as an animation's:
  [show.md](show.md), "The turn of an animation".
- **Picture clocks.** A picture dial or a picture display, [format.md](format.md),
  "Picture clocks", is read and checked as a clock is, in one step, and its picture is
  decoded on the way with a decoder of the reader's: the player's at the start's check,
  the checker's after the start and at an upload. When its turn opens its file, the
  picture is decoded once into the pixel buffer, as palette indices, and the decoder keeps
  its palette; the window keeps the head and the parts from its first byte, and from byte
  128 the layer, a byte for each pixel. At each refresh the layer is written, the hands and
  the caps or the fields at the virtual time with its direction, and the LED data takes for
  each LED the layer's palette index where it has one and the pixel buffer's otherwise. The
  pixel buffer is not written again in the turn. A hand or a cap touches only the pixels
  near it; the time walks the slowest points of the turn so far, one for at least every 6
  seconds of it.

## A drive

A host with a drive gives the core animations that are not in the show: the files of the
folder `odrig` of a USB flash drive or a microSD card. A drive with a catalog is read from
its index, [catalog.md](catalog.md#the-index-of-a-drive), as it is needed, whatever the
number of its files; a drive without one is listed by the host, as its member `drive_name`
says, and the core keeps for each place of the list its state, its size, its length and
its id, and asks the host for a name only when `list` writes it or a log line needs it.

- At each refresh, before the LED data is made, the core asks `drive`. When the number
  differs from the one it holds, it drops what it knew of the old drive. For a number
  other than 0 and a host with `drive_bind`, it reads the drive's catalog first, as the
  next item says; a drive without one, and every drive of a host without `drive_bind`, is
  listed (`drive_list`, when the host has it), its files counted with `drive_name`, each
  given its id and marked to be checked. The core takes the listing's files up to the
  256th, and up to the first whose folder would be the 33rd sub-folder.
- A drive's catalog is read by the check after the start once the installed files are
  read, one step at a time at its pace: a commit record that is whole is finished when
  `drive_writable` says 1 and makes the catalog damaged otherwise; then the marker, of
  version 2. A whole marker makes the drive read from its index at once: every file the
  index names is in the playlist and in `list`, and neither a page, nor a row, nor an
  animation is read for that. A marker of version 1 is `incompatible`. Once read, the
  marker is read again at the first refresh 10,000 ms later, and each 10,000 ms; when it
  differs, the drive's animations are dropped and the catalog is read again.
- The drive's cursor, a block the core takes at the start for a host with a drive, reads
  the index as the core needs it: a line of the table for a folder, a row of a folder's
  file for a file, a line of the map for an id, each by its number, the map and the table
  by binary search. It holds a room of 512 bytes, which takes as many whole lines of a file
  as fit in one read, with the name of the file and the offset they are from; the counts of
  the table's and the map's lines, from the marker; the last two rows read, each with its
  position, id, CRC-32, size, canvas, length, type, fault and path; the folder of the last
  file found; and the files left out since the drive was taken up. A row of another canvas
  is left out with `size-mismatch`, and one whose path and CRC-32 are among the files
  remembered as left out with that fault. A line out of its form, or a file of the index
  shorter than its lines, makes the catalog `damaged`, `line`, at the next refresh, and
  the drive's animations go. The CRC-32s of the index's files, and the pages, are not read:
  the PC tool checks them.
- The check after the start goes on with a listed drive once the installed files are
  read: the drive's files, in the order of their places, at the same pace and through the
  same second decoders. Its first step
  on a file reads the file's first 512 bytes. A file that is whole and made for the canvas
  joins the playlist as soon as its check has ended. One that is not, or one for which no
  id is left, is left out, and the host's log gets
  `drive file <name> left out: <reason>`. The drive's check does not make
  any command answer `busy`. While an upload is open it waits, and the file it was in is
  read again from its start afterwards.
- A listed drive's file gets its id when the drive is taken up, before it is checked: the
  lowest from 60001 up that no item of the show and no file of the drive before it has. The
  same files with the same show get the same ids, and a file left out keeps its id. An
  indexed drive's files and folders have the ids of its map.
- The drive's files are positions of its walk: the root's files, then each folder's in the
  table's order; a drive's file is the position kDriveBase and its position in the walk. A
  listed drive's sub-folders make a tree, built from the names of the places once every
  file has its id: a table of at most 32 folders beside the root, in the listing's order,
  each with the place of the first file at or below it, its own files, its depth and the
  index after its last descendant, so that a folder's subtree is one range of the table
  and its files one range of places, which are the walk. Its folders get ids after the
  files', from the same pool, in the order of the table. An indexed drive's tree is the
  index's table. `list` gives a folder as `{"id":<id>,"playlist":"<path>","external":true,"files":<n>}`
  after the show's items and before the files of its level. The tree is dropped with the
  drive; a removal takes the folders left without a file out of it, the others keeping
  their ids and their order; a file uploaded to the drive lies in the drive's folder
  itself, the root's.
- The playlist is walked in its range: the show's animations by their keys in the saved
  order, then the drive's files in the walk. The range is the current playlist's, the
  files of its folder's subtree, or the root's, the show's animations and every file,
  while the current one has nothing to play; which it is is judged where a turn
  ends, so that the current playlist takes over at the end of the turn in progress, from
  its first animation. The current playlist is kept as its path and its index in the
  table, found again from the path whenever the tree is built, and the root stands for a
  path the tree has not. A jump by `play` outside the range keeps the animation whose turn
  it cut, which plays again after the jumped turn. `status` names the current folder's id
  as `playing` while the tree holds it.
- The window: a playlist becomes current at a timestamp, by a choice or by the rotation,
  and the core keeps that moment and the milliseconds spent in the window before it; the
  window is kWindowMs, 86,400,000, of running time. Whether it has passed is judged by the
  turn's end time where a turn of the playlist ends, by the refresh's time at a refresh
  while a cycle or nothing plays, and when a mapping test ends; the rotation makes the
  next folder of the table current, the root after the last and while the tree is not
  known, and the new playlist plays from its first animation, or a cycle goes on. The
  whole rounds that a long time without a refresh takes off at once end before the
  window's end, and a rotation sums the new playlist's round anew; with an indexed drive
  no round is taken off at once, since summing one would read every row: the turns are
  walked one at each refresh. The root alone,
  current again at its window's end, goes on as it was with a fresh window. `status`
  writes the seconds left as `left`, its last member.
- A drive whose host says it can be written, read from its index, is changed by the core:
  an upload to it is written as `drive/upload.part`, checked, and moved onto its name in
  the root with its entry and its row in one commit of the drive's catalog and index; a
  removal takes the entry and the row out, with the folders left without a file, and
  removes the file in one commit. Each file of the index the change writes is streamed
  from the old one through the chunk buffer, a line at a time, as `.new`. A replacement
  keeps its row and its id, and what plays the file plays the new one from its start; a
  new file goes last among the root's files with the lowest id the map does not hold,
  found by binary search, and the positions the core holds at or after it move on by one;
  a removal moves those after it back by one. The core's own commit gives the marker's
  CRC-32 to the look, which does not read the drive again for it.
- `catalog rebuild external` lists the drive's folder once and reads every listed file
  with the check's steps, without a limit, then writes the drive's catalog and index anew,
  a few lines at each step, through two files of its own that no reader reads,
  `rebuild.tmp` and `rebuild-folders.tmp`: the scan, a line for each listed file; the
  check of the old index, a file at each step; the pages, one pass over the scan for each;
  the draft of the table, a line for each folder that begins at a file that passed; the
  folders' files, each with the rows of its old file of the files that passed, in their
  order, then its other files that passed, those the old pages have no line for, in the
  order of their names, with the walk's ids, and then the sub-folders' rows; the map; the
  table, each
  line with the CRC-32 of its folder's file, read again whole; and the commit, whose record
  also removes the files of the old table's folders whose ids the new one has not. An
  indexed drive plays from its old index meanwhile; a listed drive's places are dropped,
  and each joins as it is read. At the end the drive is read again from its new index, as
  after another marker. `catalog cancel`, a failed call and a drive pulled out end the
  rebuild, and what it wrote is removed, but from a drive that is gone.
- The core remembers the last 16 files of drives it left out for a fault in this boot: the
  name the drive gave each, cut to 32 characters, the number and the CRC-32 of its first
  bytes, at most 512, and the reason; a file of an indexed drive with its row's CRC-32 in
  place of its first bytes. A file of a drive taken up later with the same name and the
  same first bytes is left out again with that reason after its first step, and its body
  is not read; a row of an index with the same path and CRC-32 at once. Another file of
  the same name is checked as any other.
- The playlist is the show's animations in the saved order, then the drive's in its walk.
  A drive's animation has the turn of an animation without `repeat` and
  `max_seconds`. When nothing plays and a drive's animation joins, the playlist plays
  from it: a show without an animation of its own plays the drive's.
- `play <id>` finds an id among the show's items and then among the drive's files and
  folders; `status` names a drive's animation by its id, with its path as `file`. `list`
  lists the root's level after the show's items, and `list in <id>` a folder's, with the
  file's name on the drive written as a JSON string, and in their places the files left
  out with a fault, with `"bytes":null` and `fault`. `play` of a file left out is refused
  with `unavailable`. `remove` of an indexed drive's file removes it when the core may
  write the drive; `remove` of another drive's id, `remove many`, `ignore` and `upload
  begin` of a drive's id are answered with `in-use`.
- When the drive is pulled out, or another one is plugged in, its animations leave the
  playlist and `list`. When one of them was playing, the playlist goes on with the next
  animation that is left, from its first frame, or nothing plays.
- A drive's file that cannot be opened or read, or that turns out not to be sound while it
  plays, is left out from then on and logged in the same way. Its turn ends there, that
  refresh keeps the picture before, the playlist goes on as after a pull, and the show
  stays valid. One file left out never drops the drive's other files.

## The catalogs

The core reads and writes the catalog of the board's storage and of a drive in the format
of [catalog.md](catalog.md), as the PC library does, with the same calls of the storage, so
that the same changes leave the same files. A change of a catalog writes the pages it
touches as `catalog-NN.new`, the marker as `catalog.new` and the commit record
`catalog.do`, through the chunk buffer and the second source; it is made once the record is
whole, and finishing it does its actions, renames its pages and its marker and removes the
record, each step once the one before it is done. Before the record is whole a failed call
refuses the change with `storage-error`, and a file that was being written is removed. A
record that a failed call leaves is finished before the next change of that storage writes
anything; while it cannot be, the change is refused with `storage-error`.

An upload commits the entry of its file, with the size, the CRC-32, the length and the type
its check found, in the same commit that moves `upload.part` onto its name; a removal takes
the entries of the files that go out before the show file is written. A storage without a
catalog, or with one that is not `ok`, gets none from a change.

`catalog rebuild internal` reads the show's files whose names a catalog may hold, page by
page, with the steps of the check after the start (`check_file_step`), at its pace: a file
that passes is entered with what its check found, one that fails is quarantined. The count
and the CRC-32 of each page wait at the end of the chunk buffer, six bytes a page from
byte 1,400; after the last page the marker and a record for all sixteen pages are written
and finished. The check after the start gives way while a rebuild runs, and takes up after
it, or after a cancel, the files neither read nor quarantined. While a rebuild runs, the
commands that write storage are `busy`; `catalog cancel`, a failed call and a drive pulled
out end it without its commit, and the pages it wrote so far are removed, but from a drive
that is gone, where they stay and are never read without a record.

`catalog page` reads one page of the board's catalog, or of the drive's through `drive/`,
from the offset it is given, with one `read_at` of at most 512 bytes into the chunk buffer,
which holds nothing between commands: it asks for no memory and keeps nothing. It is `busy`
while a rebuild of that storage runs, and answers an empty text for a catalog that is not
`ok`.

## The files the core writes

`remove` and `upload` change the show while the core runs: in storage first, then in its
tables. The core keeps three names in the folder for itself:

| Name | What it is |
|---|---|
| `upload.part` | The bytes of the open upload. |
| `show.part` | The next `show.json`, until it is renamed. |
| `pending.txt` | The names of `.odrg` files that a change makes or is about to delete, one on a line, each ended by a line feed. A file named here that no item of `show.json` names is not part of the show. |

The saved order and the saved playlist have files of their own, `order.txt` and
`playlist.txt`, each written as `order.part` or `playlist.part` and renamed: see [the saved
order](#the-saved-order) and [the saved playlist](#the-saved-playlist). No show names any
of these: a name in `show.json` ends in `.odrg` or `.odrgx`.

There are four kinds of change. Each line is one call to the host; "write X" is
`write_open`, one or more `write` of at most 1,500 bytes, and `write_close`.

**A removal.** F is the removed item's file; lines 1, 4 and 5 are left out when the item is
a cycle or another item names F.

```
1  write pending.txt: "F"
2  write show.part: the show without the item
3  rename show.part -> show.json                 <-
4  remove F
5  remove pending.txt
```

**An upload for a new item**, with the file name G:

```
1  write pending.txt: "G"
2  rename upload.part -> G
3  write show.part: the show with the item at its end
4  rename show.part -> show.json                 <-
5  remove pending.txt
```

**An upload that replaces an item's file by one of the same name G:**

```
1  rename upload.part -> G                       <-
```

`show.json` does not change.

**An upload that replaces an item's file F by one of another name G.** F is left out of
lines 1 and 5 when another item names it.

```
1  write pending.txt: "G", "F"
2  rename upload.part -> G
3  write show.part: the show with the item naming G
4  rename show.part -> show.json                 <-
5  remove F
6  remove pending.txt
```

The show changes at the arrow: a power cut before it leaves the old show, one after it
the new show, and the next start removes whatever else is in the folder. `show.json` is
never written in place. The text of `show.json` is the one of [show.md](show.md),
"show.json after a change", with the brightness the file had at startup.

- **When a call fails before the arrow**, the reply is `storage-error`, the core removes
  `show.part`, a G it had just renamed into place, and `pending.txt` again, and the
  tables are as they were. An upload it happened to is discarded with its bytes.
- **When a call fails after the arrow**, the change stands and the reply is
  `{"ok":true}`: a file that could not be removed is named by `pending.txt` and is
  removed before the next change, or at the next start. Before a change the core reads
  `pending.txt` with `read_at`, at most 1,500 bytes, removes every file it names that no
  item names, and then `pending.txt`; while that fails, the change is refused with
  `storage-error` and nothing of it is written. A file the show names is never removed.
- **`remove many`** writes `pending.txt` only when a file goes: when every removed
  animation's file is another item's, it writes the show file alone.
- **The tables** change after the arrow. In a removal the items after the removed one
  move up, the entries of a removed cycle leave the entry table, and a file that no item
  names any more leaves the file table; every position the core holds follows, so what
  plays goes on undisturbed. A new item is written at the end of the item table and of
  the file table. A replaced item's entry of the file table gets the new name, size and
  duration; when another item named the old file too, the item gets an entry of its own.
- **What plays.** When the removed item is the animation whose turn it is in the
  playlist, the file that is open is closed and the playlist goes on with the animation
  after it, whose turn begins at the next refresh; when it was the only animation,
  nothing plays and the next refresh is dark. When the removed item is the cycle that
  plays, the playlist plays from its first animation. When the file of the animation
  whose turn it is is replaced, its turn begins again at the next refresh; when the
  file of an animation the playing cycle lists is replaced, the cycle starts again from
  its first frame. A new item has its turn when the playlist comes to it; when nothing
  played, the playlist starts. Before a file is renamed onto a name or removed, the
  player closes it when it has it open. Every other change leaves the LED data as it
  would have been.
- The item table and the file table have room for 32 items more than `show.json` lists at
  startup, and for at least 128. A new item beyond that is refused with `no-space`.
- An item of the item table has 16 bytes, whatever it is. An animation item keeps its
  `repeat` and its `max_seconds` of [show.md](show.md) in two fields that only a cycle
  used before, each 0 when the show gives none, so the table is no larger for them. The
  show's `min_seconds` is one number of the core, 30 when the show names none. The file
  the core writes has all three as the show had them.

## Uploads and the check

One upload can be open. It belongs to the core and not to an entry: its commands may
come through `odrig_core_command` and `odrig_core_feed` in any mixture.

- **`upload begin`** asks the host for its space and refuses a file for which
  `bytes + bytes / 256 + 16,384` is more than the free bytes; then it begins the file
  `upload.part`.
- **An unchanged file.** After `upload end` installed a file, the upload's record keeps
  its id, its name, its size and its CRC-32, and a byte of its padding says that it is
  installed, until the next upload begins or the core starts again. `upload begin` with a
  CRC-32 compares them, and the item's file, and answers `unchanged` without a call to the
  host when all agree and the file is usable. The core keeps no CRC-32 of the other files:
  8 bytes more an entry of the file table would not fit the memory of the target file.
- **`upload data`** checks the base64 whole, decodes it into the chunk buffer and gives
  the bytes to the host in one `write`. With the last byte the file is closed.
- **The check.** A file must be decoded whole before it joins the show. That is done
  beside playback, with a second source, second decoders, a pixel buffer and a window of
  their own, which read `upload.part` back with `read_at`, 512 bytes at a time. It runs
  in steps inside `odrig_core_poll`, one step after the LED data of a refresh is
  complete, and none after a refresh before which a grid time was skipped: when the host
  is late, the check waits. The first step reads the header and compares the canvas with
  the mapping's; each further step decodes one frame record, which is what playback does
  for a refresh; the step after the last record asks for the end of the file and
  compares the size and the CRC-32 of what was read back with what was received. A file
  of F frame records is checked in F + 2 refreshes, a text or a clock in three. No upload is open while the check
  after the start reads the installed files. The check of a drive's files gives the
  second decoders up when an upload begins and takes them again once it is closed, so
  the two never need them at the same time.
- **`upload expect`** reads the file of the upload's item through `read_at`, 512 bytes
  at a time into the chunk buffer, and compares its CRC-32; it takes no step of the check.
- **`upload end`** is answered with `busy` while the check runs. Afterwards it puts the
  file in place by the sequence of its kind, or reports what the check found:
  `bad-file` with the reason of [reasons.md](reasons.md), "ODRG files", or
  `size-mismatch`; `storage-error` when storage could not be read or gave back other
  bytes.
- **Discarding.** `upload cancel`, a wrong checksum, a failed check and a failed storage
  call discard the upload: `upload.part` is removed. So
  does every call that carries a timestamp 60,000 ms or more after the last progress:
  `upload begin`, an `upload data` that was taken, or a step of the check. The core
  reads no clock for it.

## Memory

The core asks the host for memory only inside `odrig_core_begin`, in up to eighteen
blocks, twenty-one with a drive, in the order of the table: two of a fixed size for the byte
entry, five for a host whose storage can be changed, and the others sized from the mapping
and the show. No
command, no upload and no check asks for memory. The figures are for the target file,
`mapping/legs-20.json`, 60 x 60 on twenty legs, with a show of 100 items: 80 animations
with a file each and 20 cycles of 10 entries. They are measured by the suite.

| Block | Size | Bytes |
|---|---|---:|
| The core object | fixed | 3,944 |
| Line of the byte entry | 2,049 | 2,049 |
| Reply of the byte entry | 1,024 | 1,024 |
| Legs | 12 for each leg | 240 |
| The pixel of each LED | 2 for each LED | 7,200 |
| LED data | 3 for each LED | 10,800 |
| Strip check | 1 bit for each strip: each row of a row-leg file, each column of a column-leg file | 8 |
| Pixel buffer | the smaller of 3 * W * H and 65,534 | 10,800 |
| Window of the DEFLATE decoder | 32,768 | 32,768 |
| Chunk buffer, with storage that can be changed | 1,500 | 1,500 |
| The check: source, DEFLATE decoder, ODRG decoder | fixed | 2,464 |
| The check: pixel buffer | as the player's | 10,800 |
| The check: window | 32,768 | 32,768 |
| Items | 16 for each of 132: the items and room for 32 more, 128 at least | 2,112 |
| Cycle entries | 2 for each entry of a cycle, 2 at least | 400 |
| Files | 48 for each of 132 | 6,336 |
| The saved order, with storage that can be changed | 2 for each of 132 | 264 |
| Miniature state and physical RGB, only for a 60x60 canvas | fixed | 188 |
| **Total** | | **125,665** |

That is 96 percent of the 131,072 bytes the core may use for this canvas: the second
decoders, which serve the check after the start and the check of an uploaded file, take
46,032 of them. The example show on the two-leg mapping asks for 88,954 bytes. A host
without storage that can be changed is not asked for the chunk buffer, the three blocks
of the check and the saved order: 77,869 bytes for the target file. A host with a drive
is asked for three blocks more, after the three of the check: the table of a drive
without a catalog, 12 bytes for each of 256 places, 3,072 bytes; the boot's memory of 16
files of drives left out, 40 bytes each, 640 bytes; and the cursor over a drive's index,
972 bytes: the room of 512 for one read with the name of its file, the two rows read of
160 bytes each, the counts of the index, the folder of the last row and a rebuild's
state, with the lines of the old table it keeps the rows' order of. The block of the saved order holds after the keys the tree of the drive's folders,
a table of 33 records of 8 bytes and 104 bytes of room for the current playlist's path,
368, the saved repeats of32 drive files at6 bytes each (192), and32 brightness
preferences at5 bytes each (160). Positions retain all32 bits. With it
the target file takes 131,069 bytes, below 131,072. The clocks between the animations add
no block: their settings, their counts, the paused turn and the key and the place of their
order are fields of the core object, and the order is a permutation computed from its key. The size and the number of frames
of an `.odrg` file change nothing: the core never holds a file or a frame record, only
the 512 bytes it last read. Picture clocks add no block either: a picture is decoded into
the pixel buffer, its head, its parts and its layer live in the window of the DEFLATE
decoder, and what reading them needs is on the stack; the suite finds the same memory for
a show of picture clocks as for one of clocks.

The miniature block holds one physical image; box averaging uses three local sums.
No second image or decoder is allocated. If this optional last block cannot be supplied,
normal playback stays usable and miniature support remains unavailable. Hosts opt in
only when they implement output transitions; changing the mode never allocates memory.

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
| `odrig_host decode FILE` | Reads one `.odrg` file or ODRGX container with the core's decoder. Prints `container <type> <loop> <payload>` for a container; then, for frames, `header <W> <H> <C> <F> <compressed>` and one `frame <ms> <hex>` for each frame record with the picture as three bytes for each pixel; then `end`; or `rejected <reason>` where the file is refused. A text has no frame records: its payload is read and checked whole. |
| `odrig_host render [--seed N] FILE MS...` | Reads a text or a clock and draws it as the player does at each of these milliseconds into its turn, a clock with the seed N, 1 when none is given; a picture clock as its LEDs show it, its picture through its palette with its layer over it. Prints `picture <W> <H> <hex>` for each, three bytes for each pixel in the pixel order of [format.md](format.md); or `rejected <reason>`. |
| `odrig_host shuffle KEY COUNT` | Prints on one line the permutation of 0 to COUNT - 1, 1 to 65,536, that the 32-bit KEY draws, as the player orders the clocks of its breaks: the place of each index in turn. The suite compares it with the twin `clock_shuffle` of `tests/core/support.py`. |
| `odrig_host decode --batch` | The same for any number of files on standard input. |
| `odrig_host decode --slice BYTES FILE`, `decode --slice BYTES --batch` | The same, with the decoder settling a defect in slices of `BYTES` bytes, not of 32,768: it is called again while it gives `pending`, and `pending <calls>`, how many calls gave it, comes before the last line. |
| `odrig_host inflate` | Decodes standard input as one raw DEFLATE stream with the core's decoder. Prints `data <hex>` and `left <n>`, the number of bytes of input after the stream; or `rejected <reason>`. |
| `odrig_host inflate --batch` | The same for any number of streams on standard input. |
| `odrig_host reasons` | Prints every reason name the core can report, one on a line. |
| `odrig_host guard alloc`, `guard new`, `guard read` | Does what the host must stop: asks the host for memory, or the program, as the core would after startup; or asks for 513 bytes of a file. |
| `odrig_host guard write`, `guard write-none`, `guard close-none`, `guard two-files`, `guard name`, `guard rename-open`, `guard remove-open`, `guard read-at`, `guard read-at-offset` | Uses the storage functions as the core never may: gives `write` 1,501 bytes; calls `write`, or `write_close`, with no file being written; begins a second file while one is being written; names a file that is none of the core's; renames onto, or removes, the file `open` holds; asks `read_at` for 513 bytes, or for an offset that is not where its last call ended. |

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
| `fault` | Reads the context the core keeps of the latest fault of a file | `fault <work> <record> <bytes> <reason> <name>`, the work `start`, `play`, `upload` or `drive`; or `fault none` |
| `drive plug` | With `--drive`: a drive is plugged in, with a number one higher than the last one; its folder is listed when the core calls `drive_list`, as it is then. The core sees it at its next refresh. | nothing |
| `drive plug <folder>` | With `--drive`: as `drive plug`, with a drive that stands for this folder from then on. | nothing |
| `drive pull` | With `--drive`: the drive is pulled out. | nothing |
| `drive replace <folder>` | With `--drive`: the files of the drive's folder `odrig` become those of `<folder>/odrig`, while the drive stays plugged in with its number. | nothing |

| Option of a session | What it does |
|---|---|
| `--alloc-fails-at N` | The N-th call of `alloc` returns `NULL`. |
| `--dirty-memory` | Memory is handed out filled with the byte `0xA5`, not zeroed. |
| `--read-fails FILE OFFSET` | Reading that file fails at that offset: `read` returns -1 there, and so does `read_at`. |
| `--read-fails-after FILE OFFSET N` | `read` fails at that offset once the file has been opened N times. `read_at` is not touched. |
| `--remove-after FILE N` | The file is gone once it has been opened N times. |
| `--swap-after FILE N OTHER` | After N openings the name opens the content of the file `OTHER`. |
| `--trace-files` | Prints `open <name> <result>` for every call of `open`. |
| `--trace-reads` | Prints `read <name> <bytes>` for every call of `close`: how many bytes of the file `read` gave since it was opened. |
| `--trace-calls` | Prints `call <bytes>` after every `poll` and every command: how many bytes `read` and `read_at` gave during that call of the core. |
| `--about TEXT` | The host has `about`, which gives this text. |
| `--check-first` | The check after the start takes all its steps before the startup lines are printed, with no refresh between them. The session then begins as a core that has run for a while: every file is read. |
| `--storage BYTES` | The total space `space` reports, 0 to 4,294,967,295. The free space is the total less the sizes of the files, each rounded up to 4,096, and not below 0. Without it the total is 13,500,416, the size of the board's storage on its bigger layout. |
| `--no-storage` | The seven storage functions are `NULL`. |
| `--only-space` | Of the seven only `space` is there: a host whose storage cannot be changed. |
| `--space-unknown` | `space` returns -1. |
| `--store-fails-at N` | The N-th storage call fails: it does nothing and returns -1. |
| `--cut-at N` | The N-th storage call is not made; the program prints `power cut` and ends with status 75. |
| `--cut-at N --cut-keeps K` | The same, but when that call is a `write`, its first K bytes are written first. |
| `--trace-store` | Prints `store <call> <arguments> <result>` for every storage call: `store write_open upload.part 1`, `store write 1500 1`, `store write_close 1`, `store rename show.part show.json 1`, `store remove pending.txt 0`. |
| `--read-back-fails OFFSET` | `read_at` returns -1 when it is asked for bytes of `upload.part` at or after that offset. |
| `--read-back-differs OFFSET` | `read_at` gives the byte at that offset of `upload.part` with one bit changed. |
| `--drive DIR` | The host has a drive, plugged in at the start: its list is the animation files of the folder `DIR/odrig` and of its sub-folders to three levels, depth first by the rules of `drive_list`, each named by its path from `odrig`. The core then reads them as `drive/0`, `drive/1` and so on. With `--check-first` they are read before the startup lines too. |
| `--drive-pulled` | With `--drive`: no drive is plugged in at the start. |
| `--command-read-fails FILE OFFSET` | `read_at` returns -1 for that file at or after that offset when it is called inside a command, as `read` and `upload expect` call it; the checks read the file whole. |
| `--drive-read-fails NAME OFFSET` | With `--drive`: `read` fails at that offset of the drive's file of that name. `read_at` is not touched, so the check finds the file sound and the player meets the fault. |
| `--drive-read-only` | With `--drive`: `drive_writable` says 0, and every storage call on a name of the drive fails. |
| `--trace-drive` | With `--drive`: prints `drive list <count>` for every `drive_list` and `drive bind <place> <name>` for every `drive_bind`. |
| `--trace-read-at` | Prints `read_at <name> <offset> <count>` for every `read_at`: the name, where it read from and how many bytes it gave. |

A storage call is one of `write_open`, `write`, `write_close`, `rename` and `remove`.
`space` and `read_at` are not counted and not traced. The storage functions work on the
folder of a session, and for `session --batch` on the files held in memory. A file that
was being written when the program ends stays with the bytes written so far.

The host hands out every file in pieces of changing sizes, none above 512 bytes, through
`read` and through `read_at`. It checks the core as it goes and ends the program at once
when a check fails:

| Status | Line printed | When |
|---:|---|---|
| 0 | | The run ended well. |
| 1 | a line that says what | An answer of the core contradicts another one: the legs and their count, a decoder that changes its answer after the end, a reply written into too little room. Also `guard` when nothing stopped it. |
| 64 | a usage message, `bad line` or `bad batch` | The command line or the input was not understood. |
| 70 | `allocation after startup` | The core asked the host for memory, or the program allocated with `new`, during a call after startup. |
| 71 | `file misuse` | The core opened a file while one was open, read or closed with none open, or asked for no byte or for more than 512 in one `read`. Or it gave `write` no byte or more than 1,500; called `write` or `write_close` with no file being written; began a file while one was being written; named a file that is none of its names; renamed or removed the file `open` holds, or renamed the one being written; or asked `read_at` for no byte, for more than 512, or, outside a command, for an offset that is neither 0 nor where its last call for that file ended. |
| 72 | `bad reply` | A reply was not one line of printable characters with a newline, of at most 1,024 bytes, or a line handed back had more than 2,048 characters. |
| 75 | `power cut` | The storage call that `--cut-at` names was reached. |

## Live mapping and its diagnostic

The mapping command family is specified in commands.md. The core accepts only
whole permutations of the existing pins on the canonical twenty-snake canvas.
It validates geometry against its LED-to-pixel table and keeps mapping entry order.
The pin-list CRC revision prevents a stale client from replacing another edit.
The bounded writer uses the existing storage chunk, and commits mapping.part with
one atomic rename before changing in-memory pins. Startup discards a leftover
mapping.part without touching the installed mapping. `mapping cross` writes the
same file with snake 10's leg cross-wired or not, and then writes the 180 entries
of that leg's LED-to-pixel table anew; the geometry check accepts snake 10 in
either wiring and no other leg in another.

Diagnostic entry saves the current playlist or cycle selection, closes playback,
and decodes the embedded converter-built ODRG through the ordinary decoder into
existing pixel memory. Poll uses the normal palette, brightness and LED mapping
on that picture while ordinary show progression is paused. Exit restarts the
saved animation; cycles retain the current entry as their first resumed turn.
The mode is transient and no show file changes. There is no runtime allocation.

The test of a snake is drawn, not decoded, as a clock is: at each refresh the core clears
the pixel buffer, three bytes a pixel and no palette, and lights a white block of 3 x 3
pixels in the snake's three columns, `(now - t0) / 40 ms` rows up from the bottom and back
down from the top, 57 rows each way, with no state kept but the snake's number. The core
keeps which test shows; one that follows another keeps the selection saved by the first.

### Inclusion and batch changes

ItemInfo uses two existing padding bytes for ignored and explicit presence; its size
stays 16 bytes. `ignore` writes and renames the show before changing playback.
`remove many` validates up to 32 distinct animation ids and writes one complete show.
Its pending journal holds up to 32 filenames (1,056 bytes), within the existing
chunk of 1,500 bytes. Cleanup yields an unfinished drive check and uses the checker's
read_at source, preserving the playback file. The drive check then restarts safely.
A failed cleanup keeps the journal; the next metadata change first finishes it, and is
refused with storage-error while that fails, so no transaction overwrites unresolved file
cleanup. The next start retries it too.

## The saved order

The show's animations go in the order of [show.md](show.md#the-saved-playlist-order),
which the core reads from `order.txt`, and the drive's files after them in the drive's
walk. Each animation of the show that can play has a key, and the show's animations go
from the smallest key up:

| The animation | Its key |
|---|---|
| named by entry k of the file, k from 0 | k |
| an item of the show the file does not name | 65,536 and its position in the item table |

The core keeps, for a host whose storage can be changed, the number of the entry that
names each item of the item table, in one block taken at startup; it keeps no name. A line
`x <name>` is passed over. It reads the file with `read_at` through the second source at
startup, once the show is read, and at once, as a whole, after an upload adds an item, so
that an entry with the new item's id gives it its place as a restart would. A removed
item's key leaves with it.

`order get` of the root writes the ids of the show's listed animations by key, then those
of the root's files of the drive in their rows' order; `order get in <id>` those of a
folder's files. A level's revision is the CRC-32 of its ids in that order, each as four
bytes, low byte first.

`order move` of a show's animation writes the next order into `order.part` while it reads
`order.txt` through the second source, after the drive's check has yielded it: the
header, every entry `i` of the file but the moved animation's and those of ids that no item
has, the moved animation's entry before the entry of the animation it goes before, and
after them every listed animation of the show the file did not name, by key, again with
the moved one before its place; the moved one last for `end`, or before a file of the
root. At most 512 entries are written. The text goes through the first 1,000 bytes of the
chunk buffer; the two entries looked for stand after them. `order move` of a drive's file
commits the drive's catalog with its folder's file, the table and the map written anew,
the file's row moved and the rows between following, and no page; the positions the
player holds follow the move.

```
1  write order.part
2  rename order.part -> order.txt              <-
```

Then the core reads `order.txt` again and sets every key. A call that fails before the
arrow removes `order.part` and answers `storage-error`; the keys are as they were. The
start removes an `order.part` that a power cut left.

## The saved repeats

The saved repeats of [show.md](show.md#the-saved-repeats) live in `repeats.txt`. The core
keeps the saved repeat of an item of the show in the upper 16 bits of the item's `count`,
which a `repeat` of `show.json` of at most 65,535 leaves free, and every reader of `count`
masks them; it keeps no name. The turn in progress has its own value from `repeat <id> <n>`
in one 32-bit member of the core object, 0 while none is set, which is set where a turn's
length is made and cleared where a turn ends and wherever a new one begins: in
`player_play_all`, `player_play_cycle` and `player_halt`.

The file is read whole, with `read_at` through the second source, strictly: a line out of
form clears every saved repeat and gives the log `repeats unreadable` once for the reading.
It is read at startup after `order.txt`, and again wherever `order.txt` is read again as a
whole, and after an upload gives an item another file name. A line `f <name>` gives its
loops to every item whose file has that name and has none yet.

On a host with a drive the block of the saved order holds a table of 32 entries of 8 bytes,
the position of a drive's file in its walk and its loops, for the saved repeats of the
drive's files. A line `x <name>` gives its loops to the drive's file of that path, while it
has none yet and an entry is free: a place of a drive without a catalog by the host's name
of it, a row of an indexed drive in the folder of its path. When a drive is counted or
leaves, the table is emptied, and the file is read whole at once before any of the drive's
files plays: a drive without a catalog at the drive's first step, before its files are
checked; an indexed drive when it is published. A change of the drive's files reads the
file again, as their positions move. A take-up that would match more than 32 lines uses the
first 32, and the log says `repeats over` once. A save that would add a 33rd is refused
with `no-space`.

`repeat <id> <n> save` and `repeat <id> default` read the file twice through the second
source, after the drive's check has yielded it: once to count the lines of the other
animations, and of them the lines of files no item names, which a save drops when it finds
the file full; then to write `repeats.part` through the first 1,000 bytes of the chunk
buffer, the header, every other line, and the animation's own line in the place of its
first one or at the end, its own line standing after those 1,000 bytes.

```
1  write repeats.part
2  rename repeats.part -> repeats.txt          <-
```

Then the core reads `repeats.txt` again. A call that fails before the arrow removes
`repeats.part` and answers `storage-error`; the saved repeats are as they were. A read of
the old file that fails after its first byte, or at its first byte while a saved repeat is
in force, answers `storage-error` too, so that a read that failed is never taken for a
missing file. The start removes a `repeats.part` that a power cut left. Last, the command
acts on the reported turn of the animation with the loop that was in progress before the
count changed.

## The saved playlist

The current playlist and the time spent in its window live in `playlist.txt`, beside
`order.txt`, on a host with a drive whose storage can be changed. Its text is three lines:
`odrig-playlist 1`, the playlist's path from the drive's folder or an empty line for the
root, and the milliseconds spent in its window, as `odrig-playlist 1`, `night/deep`,
`5400000`. An absent file, or one that is not of this form, means the root with a fresh
window.

The core reads it at the start, once the show is read and after `order.txt`, through the
second source, and keeps the path and the time: the root is current until the tree is
known, and plays in the folder's place meanwhile; when the tree is built the folder of the
path is current again, or the root when the card has no playlist of that path, with a
fresh window, saved as such. The removal of the current folder's last file makes the root
current the same way.

The file is written as `playlist.part`, one `write` of at most 130 bytes from a buffer on
the stack, `write_close` and `rename`, when the current playlist changes by a choice or by
the rotation, and at most once in 900,000 ms while the tree has a folder, from the
refresh, so that a restart loses at most 15 minutes of the window. A write while an upload
receives its bytes, or while a rebuild holds a page open, waits for the next refresh that
is free. Nothing is written while the tree has no folder and no file exists: a show
without a card, or with a flat card, makes no storage call more than before. When the
host fails the part is removed and nothing is refused. The start probes `playlist.part`
with `read_at` and removes it when it is there, as it does `order.part`.

## Saved animation brightness

The selector in `brightness.cpp` chooses the current file's saved value or the
runtime default before scaling. Player frames, procedural clocks, text, inserted
clock/messages and resumed turns share it; miniature output then applies its 40
cap. Diagnostics without an animation use the default. Power off stays black.
There is no timing, decoding, mapping, quarantine or random-seed restart.

The bounded internal settings store, retained path identities, file grammar,
512/32 record limits, errors and recovery are specified in
[commands.md](commands.md#saved-animation-brightness). Startup/remount fills caches;
playback neither scans media nor reads animation bodies for preferences. Internal
values/presence use existing item padding/flags.32 external values use 5-byte
records beside compact 6-byte repeat records with full 32-bit positions/16-bit counts.
The independent 128-byte reader preserves the 512-byte stack-frame compiler bound.

The measured 100-item Windows host requests 131069 bytes with a drive,21 allocation
blocks, and the Core object is 3944 bytes. Existing 128 KiB/4096 limits remain unchanged;
no allocation is added per frame. The store streams and verifies a part before
publishing it, keeps prior usable cache after failed updates, and discards partial
startup application if the settings file is damaged. `dimming` is additive status;
the existing `brightness` member remains the runtime default.
