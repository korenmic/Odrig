# The core

The core is the C++ library in `core/` that plays an installed show: it reads
`mapping.json`, `show.json` and the `.odrg` files, keeps time, handles the commands of
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
[a drive](#a-drive), [memory](#memory), the [benchmark](#benchmark) and the
[test host](#the-test-host).

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
| `log` | `void log(void *ctx, const char *text)`: one line of diagnostic text without a newline. May be `NULL`. The core logs two things: the reason text when the show becomes invalid, and `drive file <name> left out: <reason>` when it leaves out a file of a drive. |
| `write_open` | `int write_open(void *ctx, const char *name)`: begins a new, empty file of this name, in place of one that has it. A file that was being written is given up and removed. Returns 1, or -1 on a failure. `NULL` for a host without storage that can be changed. |
| `write` | `int write(void *ctx, const uint8_t *bytes, size_t length)`: adds bytes to the file being written. `length` is 1 to 1,500. Returns 1, or -1. |
| `write_close` | `int write_close(void *ctx)`: ends the writing. When it has returned 1, the file is whole in storage and stays so through a power cut. Returns 1, or -1 on a failure. |
| `rename` | `int rename(void *ctx, const char *from, const char *to)`: gives the file `from` the name `to`, in place of a file that has it. After a power cut during the call, `to` is its old file or the new one, whole. Returns 1, or -1. |
| `remove` | `int remove(void *ctx, const char *name)`: removes the file of this name. A file being written under it is given up. Returns 1 when it removed one, 0 when there was none, -1 on a failure. |
| `space` | `int space(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes)`: the free and the total bytes of the storage the files are in; a value above 4,294,967,295 is given as that. Returns 1, or -1 when the host cannot tell. |
| `read_at` | `int32_t read_at(void *ctx, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity)`: reads a file apart from the one that `open`, `read` and `close` hold: up to `capacity` bytes from this offset. Returns the number read, 0 at or after the end of the file, -1 on a failure and when there is no such file. `capacity` is never above 512. |
| `drive` | `uint32_t drive(void *ctx)`: the number of the drive of animations that is plugged in now: a number other than 0 that changes each time a drive is plugged in, or 0 while none is. The core calls it at each refresh, before the LED data is made. `NULL` for a host without a drive; see [a drive](#a-drive). |
| `drive_name` | `int drive_name(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity)`: the name of the file at this place, counted from 0, of the list of that drive, as the drive has it, into `buffer` with a zero after it, cut to `capacity - 1` bytes. Returns 1, or 0 when that drive has no file at that place or is not plugged in any more. `NULL` when `drive` is. |
| `drive_space` | `int drive_space(void *ctx, uint32_t drive, uint64_t *free_bytes, uint64_t *total_bytes)`: optional mounted-volume capacity; returns 1, or -1 if unavailable or its generation changed. The shared core reports null counters on failure. It performs no writes. |

The core has at most one file open. It reads a file from its first byte towards its last,
never goes back, and closes it before it opens another. It reads `mapping.json` and
`show.json` twice each at startup, and reads no clock. With the storage functions it
writes, renames and removes files of the folder, as [the files the core
writes](#the-files-the-core-writes) says, and nothing outside it.

The last seven members are the storage functions: three that write a file, `rename`,
`remove`, `space`, and `read_at`, which reads a second file beside the one that plays.

- A name the core gives any of them is 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_`
  and `.`: `mapping.json`, `show.json`, the name of an `.odrg` file, or one of the three
  names the core keeps for itself, `upload.part`, `show.part` and `pending.txt`.
- The core has at most one file being written, gives `write` at most 1,500 bytes in one
  call, and reads a file with `read_at` from offset 0 on, each call where the last ended.
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
the drive's list `drive/p`, as `drive/0`; no name of the installed file set has a slash. A
host that is given such a name for a drive that is gone answers as for a file that is not
there.

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
`bad-argument`, `show-invalid`, `no-upload`, `incomplete`, `bad-checksum`, `busy`,
`unknown-id`, `in-use`, `mapping-conflict`, `no-space`, `bad-offset`, `bad-file` and `storage-error`. It
changes nothing, except that `bad-checksum`, `bad-file` and `storage-error` discard the
upload they are about.

## Startup

`odrig_core_begin` reads `mapping.json`, then `show.json`, and then opens every different
`.odrg` file the show names, in the order in which the show first names them. Of each
file it reads the header, the first 16 bytes, and compares the canvas with the mapping's.
It decodes no frame record, so the time the start takes does not grow with the files. A
file that is missing or cannot be read, a header that is not sound and another canvas
make the show invalid there.

The bodies of the files are read after the start, while the show plays: see "The check
after the start". A host whose storage cannot be changed has no second decoders for
that. With such a host the start decodes every file from its first frame record to its
last, and nothing is left to check.

A show may have no items. It is valid, and nothing plays.

With a host whose storage can be changed, the start also removes what an interrupted
change left:

1. Before anything is read, it removes `upload.part` and `show.part`.
2. When `show.json` was read and its ids are sound, it opens `pending.txt`. Of that file
   it reads at most 1,500 bytes and takes every line that ends in a line feed and is a file
   name under the naming rule of [show.md](show.md). Each such file that no item names is
   removed, and then `pending.txt`. When a file could not be removed, `pending.txt` stays
   for the next start; when it could not be read, nothing is removed.
3. When the mapping or the show file could not be used, `pending.txt` is left alone.

A folder with none of the three files is asked to remove two names that are not there and
to open one that is not there, and for nothing else.

A show that is wrong in any way is refused as a whole: the LEDs stay dark, `play` is
answered with `show-invalid`, and `odrig_core_error` and `status` give the reason. The
first check that fails decides. The texts are listed in [reasons.md](reasons.md), "The
core". The other commands work as ever.

After startup the LEDs are switched on. With a valid show, brightness is the value of
`show.json`, and the playlist plays, from its first animation or from the animation
`start` names; a `start` that names a cycle plays that cycle; a show without an animation
plays nothing. With an invalid show nothing is playing, and brightness is the value of
`show.json` when that file and its ids are sound, and 0 otherwise.

A file can also fail while it plays, and the check after the start can find a fault in a
body: the file is gone, cannot be read, or does not follow the format. From that refresh
on the show is invalid in the same way, until the next startup.

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
- each further step decodes one frame record;
- the step after the last record asks for the end of the file: nothing may follow. The
  core then knows the size of the file, which `list` reports, and the length of its loop.

A file of F frame records takes F + 2 steps. At a refresh that follows the one before it
without a grid time skipped, and comes no more than 2 ms after its grid time, while the
last whole second had 30 refreshes or more, the check takes one step more than at the
refresh before, up to 16 steps. At any other refresh,
one after a gap or one later than that, the count begins again and the check takes no
step, unless it took none at the nine refreshes before either: then it takes one. So
the check is fast beside a show that leaves the host time, takes a step now and then
beside one that does not, and still comes to its end with a host that is late for every
refresh, at one step in ten refreshes.

A fault the check finds makes the show invalid from that refresh on, with the text
[reasons.md](reasons.md) has for it; that refresh is dark already. A file that cannot be
read back is `read-error`, whether it is damaged or gone: `read_at` has one answer for
both. Until the last file is read, `list`, `remove` and `upload begin` are answered with
`busy`, and every other command works. Once the check is complete it stays so until the
next start: a file that an upload adds was read by the upload's own check.

The player can come to a fault before the check does, in the animation that is playing.
It shows the frames before the fault, and the show turns invalid at the refresh whose
time lies at their end or after it. A turn that ends before that, by `max_seconds` or as
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

## A drive

A host with a drive gives the core animations that are not in the show: the files of the
folder `odrig` of a USB flash drive. The host makes the drive's list, as its member
`drive_name` says; the core keeps for each place of the list its state, its size, its
length and its id, and asks the host for a name only when `list` writes it or a log line
needs it.

- At each refresh, before the LED data is made, the core asks `drive`. When the number
  differs from the one it holds, it drops what it knew of the old drive and, for a number
  other than 0, counts the new drive's files with `drive_name`, at most 256, and marks
  them to be checked.
- The check after the start goes on with the drive's files once the installed ones are
  read, in the order of their places, at the same pace and through the same second
  decoders. A file that is whole and made for the canvas joins the playlist as soon as its
  check has ended. One that is not, or one for which no id is left, is left out, and the
  host's log gets `drive file <name> left out: <reason>`. The drive's check does not make
  any command answer `busy`. While an upload is open it waits, and the file it was in is
  read again from its start afterwards.
- A drive's animation gets the lowest id from 60001 up that no item of the show and no
  animation of the drive before it has. The same files with the same show get the same
  ids.
- The playlist is the show's animations and then the drive's, in the order of their
  places. A drive's animation has the turn of an animation without `repeat` and
  `max_seconds`. When nothing plays and a drive's animation joins, the playlist plays
  from it: a show without an animation of its own plays the drive's.
- `play <id>` finds an id among the show's items and then among the drive's animations;
  `status` names a drive's animation by its id. `list` lists the drive's animations
  after the show's items, with the file's name on the drive written as a JSON string.
  `remove` and `upload begin` of a drive's id are answered with `in-use`.
- When the drive is pulled out, or another one is plugged in, its animations leave the
  playlist and `list`. When one of them was playing, the playlist goes on with the next
  animation that is left, from its first frame, or nothing plays.
- A drive's file that cannot be opened or read, or that turns out not to be sound while it
  plays, is left out from then on and logged in the same way. Its turn ends there, the
  playlist goes on as after a pull, and the show stays valid.

## The files the core writes

`remove` and `upload` change the show while the core runs: in storage first, then in its
tables. The core keeps three names in the folder for itself:

| Name | What it is |
|---|---|
| `upload.part` | The bytes of the open upload. |
| `show.part` | The next `show.json`, until it is renamed. |
| `pending.txt` | The names of `.odrg` files that a change makes or is about to delete, one on a line, each ended by a line feed. A file named here that no item of `show.json` names is not part of the show. |

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
  removed at the next start.
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
  of F frame records is checked in F + 2 refreshes. No upload is open while the check
  after the start reads the installed files. The check of a drive's files gives the
  second decoders up when an upload begins and takes them again once it is closed, so
  the two never need them at the same time.
- **`upload end`** is answered with `busy` while the check runs. Afterwards it puts the
  file in place by the sequence of its kind, or reports what the check found:
  `bad-file` with the reason of [reasons.md](reasons.md), "ODRG files", or
  `size-mismatch`; `storage-error` when storage could not be read or gave back other
  bytes.
- **Discarding.** `upload cancel`, a wrong checksum, a failed check, a failed storage
  call, and a show that becomes invalid discard the upload: `upload.part` is removed. So
  does every call that carries a timestamp 60,000 ms or more after the last progress:
  `upload begin`, an `upload data` that was taken, or a step of the check. The core
  reads no clock for it.

## Memory

The core asks the host for memory only inside `odrig_core_begin`, in up to sixteen
blocks, seventeen with a drive, in the order of the table: two of a fixed size for the byte entry, four for a host
whose storage can be changed, and the others sized from the mapping and the show. No
command, no upload and no check asks for memory. The figures are for the target file,
`mapping/legs-20.json`, 60 x 60 on twenty legs, with a show of 100 items: 80 animations
with a file each and 20 cycles of 10 entries. They are measured by the suite.

| Block | Size | Bytes |
|---|---|---:|
| The core object | fixed | 3,416 |
| Line of the byte entry | 2,049 | 2,049 |
| Reply of the byte entry | 1,024 | 1,024 |
| Legs | 12 for each leg | 240 |
| The pixel of each LED | 2 for each LED | 7,200 |
| LED data | 3 for each LED | 10,800 |
| Strip check | 1 bit for each strip: each row of a row-leg file, each column of a column-leg file | 8 |
| Pixel buffer | the smaller of 3 * W * H and 65,534 | 10,800 |
| Window of the DEFLATE decoder | 32,768 | 32,768 |
| Chunk buffer, with storage that can be changed | 1,500 | 1,500 |
| The check: source, DEFLATE decoder, ODRG decoder | fixed | 2,440 |
| The check: pixel buffer | as the player's | 10,800 |
| The check: window | 32,768 | 32,768 |
| Items | 16 for each of 132: the items and room for 32 more, 128 at least | 2,112 |
| Cycle entries | 2 for each entry of a cycle, 2 at least | 400 |
| Files | 48 for each of 132 | 6,336 |
| **Total** | | **124,661** |

That is 95 percent of the 131,072 bytes the core may use for this canvas: the second
decoders, which serve the check after the start and the check of an uploaded file, take
46,008 of them. The example show on the two-leg mapping asks for 88,146 bytes. A host
without storage that can be changed is not asked for the chunk buffer and the three
blocks of the check: 77,153 bytes for the target file. A host with a drive is asked for
one block more, after the three of the check: the drive's table, 16 bytes for each of
256 places, 4,096 bytes. With it the target file takes 128,757 bytes, 98 percent. The size and the number of frames
of an `.odrg` file change nothing: the core never holds a file or a frame record, only
the 512 bytes it last read.

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
| `drive plug` | With `--drive`: a drive is plugged in, with a number one higher than the last one and the list of the folder as it is now. The core sees it at its next refresh. | nothing |
| `drive pull` | With `--drive`: the drive is pulled out. | nothing |

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
| `--drive DIR` | The host has a drive, plugged in at the start: its list is the files of the folder `DIR/odrig` by the rules of `drive_name`. The core then reads them as `drive/0`, `drive/1` and so on. With `--check-first` they are read before the startup lines too. |
| `--drive-pulled` | With `--drive`: no drive is plugged in at the start. |
| `--drive-read-fails NAME OFFSET` | With `--drive`: `read` fails at that offset of the drive's file of that name. `read_at` is not touched, so the check finds the file sound and the player meets the fault. |

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
| 71 | `file misuse` | The core opened a file while one was open, read or closed with none open, or asked for no byte or for more than 512 in one `read`. Or it gave `write` no byte or more than 1,500; called `write` or `write_close` with no file being written; began a file while one was being written; named a file that is none of its names; renamed or removed the file `open` holds, or renamed the one being written; or asked `read_at` for no byte, for more than 512, or for an offset that is neither 0 nor where its last call for that file ended. |
| 72 | `bad reply` | A reply was not one line of printable characters with a newline, of at most 1,024 bytes, or a line handed back had more than 2,048 characters. |
| 75 | `power cut` | The storage call that `--cut-at` names was reached. |

## Live mapping and its diagnostic

The mapping command family is specified in commands.md. The core accepts only
whole permutations of the existing pins on the canonical twenty-snake canvas.
It validates geometry against its LED-to-pixel table and keeps mapping entry order.
The pin-list CRC revision prevents a stale client from replacing another edit.
The bounded writer uses the existing storage chunk, and commits mapping.part with
one atomic rename before changing in-memory pins. Startup discards a leftover
mapping.part without touching the installed mapping.

Diagnostic entry saves the current playlist or cycle selection, closes playback,
and decodes the embedded converter-built ODRG through the ordinary decoder into
existing pixel memory. Poll uses the normal palette, brightness and LED mapping
on that picture while ordinary show progression is paused. Exit restarts the
saved animation; cycles retain the current entry as their first resumed turn.
The mode is transient and no show file changes. There is no runtime allocation.

### Inclusion and batch changes

ItemInfo uses two existing padding bytes for ignored and explicit presence; its size
stays 16 bytes. `ignore` writes and renames the show before changing playback.
`remove many` validates up to 32 distinct animation ids and writes one complete show.
Its pending journal holds up to 32 filenames (1,056 bytes), within the existing
chunk of 1,500 bytes. Cleanup yields an unfinished drive check and uses the checker's
read_at source, preserving the playback file. The drive check then restarts safely.
A failed cleanup keeps the journal and blocks later metadata changes with storage-error
until reboot retries cleanup, so no transaction overwrites unresolved file cleanup.
