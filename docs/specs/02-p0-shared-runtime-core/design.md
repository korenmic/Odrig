# Design: Shared runtime core (seed 02)

## Overview

The core is a C++11 library in `core/`. A host creates one core object, hands it the time
with every call, and receives LED data for every leg and one reply line for every command
line. Everything the core needs from outside comes through five functions the host supplies.

The core is built from small parts with one direction of dependency:

```
commands  -> player -> odrg_decoder -> inflate -> file_source -> host
startup   -> player
startup   -> mapping, show -> json_reader -> file_source -> host
startup   -> odrg_decoder
startup   -> arena -> host
```

No part includes a system header other than `stdint.h`, `stddef.h` and `string.h`.

Decisions taken where the seed and the documents left a point open are listed in
`docs/drifts.md` under "Seed 02".

## Language level and toolchain

The core is written in **C++11**, restricted to what every later standard also accepts.

Why this is safe for the WLED 16.0.1 build:

- The environment `esp32s3dev_16MB_opi` in WLED v16.0.1's `platformio.ini` takes its platform
  from `[esp32_idf_V4]`: Tasmota's `platform-espressif32` release 2024.06.00, described there
  as Arduino core 2.0.18 on ESP-IDF 4.4.8. The environment removes no build flag and sets no
  `-std` option.
- That platform release lists `toolchain-xtensa-esp32s3` at `8.4.0+2021r2-patch5`, which is
  GCC 8.4.0. GCC 8 implements all of C++11.
- The Arduino core 2.0.x build script for the ESP32-S3 compiles C++ with
  `-std=gnu++11 -fexceptions -fno-rtti`. This was read in the upstream core, version 2.0.17.

**Assumption to verify:** the build script inside Tasmota's 2.0.18 framework package was not
opened, so the exact `-std` flag of the real build is unconfirmed. It cannot be lower than
C++11 on that compiler, and C++11 code compiles under every higher setting, so the choice
holds either way. The first firmware build of seed 04 confirms it.

Rules that keep the code inside this level and free of hidden dependencies:

- No exceptions, no `dynamic_cast` or `typeid`, no threads, no `new` or `delete`, no
  standard containers, strings, streams or algorithms, no `printf` family.
- No virtual functions, and no variable with static storage other than constant tables:
  nothing at namespace scope that can change, and no function-local `static`. State structs
  are plain data, cleared with `memset` and set up by an explicit function.
- No floating-point types.
- Format quantities use fixed-width types (`uint8_t`, `uint16_t`, `uint32_t`, `uint64_t`).
  `size_t` appears only in the host interface. Multi-byte values are assembled from bytes,
  so byte order of the machine does not matter.
- No recursion; no local array above 256 bytes. Larger buffers are members of the core
  object.
- Internal names live in `namespace odrig`. The only names visible to the linker without a
  namespace are the `odrig_core_*` functions.

On the Mac the core is compiled with
`-std=c++11 -O2 -Wall -Wextra -Wpedantic -Wshadow -Wframe-larger-than=512 -Werror
-fno-exceptions -fno-rtti`. The frame limit makes a function with large local arrays a build
error.

## Repository layout

```
core/
  Makefile
  include/
    odrig_core.h            the host interface; the only header a host includes
  src/
    core.cpp                the odrig_core_* functions and startup
    core_state.h            the core object
    reasons.h, reasons.cpp  reason numbers and their names
    arena.h                 startup memory through the host
    file_source.h, .cpp     one host file, read front to back
    inflate.h, .cpp         raw DEFLATE decoder
    odrg_decoder.h, .cpp    ODRG header, palette and frame records
    json_reader.h, .cpp     JSON reader
    mapping.h, .cpp         mapping.json to leg and LED tables
    show.h, .cpp            show.json to item tables
    player.h, .cpp          time, items, cycles, refreshes, LED data
    commands.h, .cpp        command lines, replies, status
tests/
  core/
    __init__.py
    test_*.py               the suite of this seed
    support.py              runs the test host; the reference player; the mapping rule
    allowed_symbols.txt     names the compiled core may refer to
    host/
      host.cpp              the test host program
      guard.cpp             stops the program on allocation after startup
    bench/
      bench.cpp             the benchmark program
docs/
  core.md                   build, test and benchmark commands; the host interface
```

`core/include` and `core/src` are the layout a PlatformIO library uses, so the firmware
build of seed 04 can take `core/` as a library without copying a file. Build output goes to
`core/build/`, which `.gitignore` covers with `/core/build/`.

## The host interface

`core/include/odrig_core.h`, complete:

```c
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ODRIG_LINE_MAX   64     /* longest command line, in characters */
#define ODRIG_REPLY_MAX 192     /* longest reply, in bytes, with its newline */

typedef struct odrig_core odrig_core;

/* What the host supplies. Every function receives ctx as its first argument. */
typedef struct odrig_host {
    void *ctx;

    /* Memory, aligned for any object. Called only inside odrig_core_begin.
       Returns NULL when the host has none to give. The core never frees it. */
    void *(*alloc)(void *ctx, size_t bytes);

    /* Opens a file of the installed file set by its name, for reading from the start.
       Returns 1 when open, 0 when there is no such file, -1 on any other failure.
       The core has at most one file open. */
    int (*open)(void *ctx, const char *name);

    /* Reads the next bytes of the open file: 1 to capacity bytes read, 0 at the end of
       the file, -1 on failure. The core passes a capacity of at most 512. */
    int32_t (*read)(void *ctx, uint8_t *buffer, size_t capacity);

    /* Closes the open file. */
    void (*close)(void *ctx);

    /* Receives one line of diagnostic text, without a newline. May be NULL. */
    void (*log)(void *ctx, const char *text);
} odrig_host;

/* One leg, as the mapping file lists it, and its LED data from the last refresh:
   led_count * 3 bytes, red, green, blue per LED, in chain order. */
typedef struct odrig_leg {
    uint16_t leg;
    uint16_t pin;
    uint32_t led_count;
    const uint8_t *rgb;
} odrig_leg;

/* Called by odrig_core_feed once for every complete line. */
typedef void (*odrig_reply_fn)(void *ctx, const char *line, size_t line_length,
                               const char *reply, size_t reply_length);

/* Starts the core: reads and checks the installed file set. Returns NULL only when the
   host could not supply the first block of memory. */
odrig_core *odrig_core_begin(const odrig_host *host);

/* Asks for a refresh. Returns 1 when new LED data was produced, 0 when none was due. */
int odrig_core_poll(odrig_core *core, uint64_t now_ms);

/* The legs. Valid from odrig_core_begin on; rgb changes at every refresh. */
uint32_t odrig_core_leg_count(const odrig_core *core);
int odrig_core_leg(const odrig_core *core, uint32_t index, odrig_leg *out);

/* One command line in, one reply out. The line may end with a newline, with or without a
   carriage return before it. Writes the reply, with its newline and without a terminating
   zero, to reply and returns its length. capacity must be at least ODRIG_REPLY_MAX. */
size_t odrig_core_command(odrig_core *core, uint64_t now_ms,
                          const char *line, size_t length,
                          char *reply, size_t capacity);

/* For transports that deliver bytes. Splits them into lines, answers each line through
   odrig_core_command, and calls on_reply for each. Keeps an unfinished line for the
   next call. */
void odrig_core_feed(odrig_core *core, uint64_t now_ms,
                     const uint8_t *bytes, size_t length,
                     odrig_reply_fn on_reply, void *reply_ctx);

/* The reason the show is invalid, as status reports it, or NULL when it is valid. */
const char *odrig_core_error(const odrig_core *core);

#ifdef __cplusplus
}
#endif
```

Rules of use:

- `odrig_core_begin` is called once. The core copies the `odrig_host` struct. After it
  returns, the other functions may be called in any order and any number of times.
- The core is used from one thread, and a host function does not call the core.
- Every `now_ms` comes from one clock that does not go backwards. The first call that
  carries a timestamp sets the power-on moment.
- There is no function to end the core. The memory belongs to the host, which may release
  it once it makes no further call.
- `odrig_core_begin` returns only after the whole file set is checked. A host that must
  stay responsive during that time does its housekeeping inside its `read` function, which
  the core calls at least once for every 512 bytes of file.

The interface is plain C, so a C++ firmware module calls it directly and a Python program
can call the same functions in a shared library through `ctypes`.

## Data structures

All state is in one `odrig::Core` object (`core_state.h`), obtained from the host. A
`static_assert` keeps `sizeof(Core)` at or below 4,096 bytes. Its main members:

| Member | Content |
|---|---|
| `host` | A copy of the host's functions. |
| `error_text[96]`, `invalid` | The reason text and whether the show is invalid. |
| `width`, `height`, `leg_count`, `led_total` | From the mapping. |
| `legs`, `led_pixel`, `led_data`, `pixels`, `window` | Pointers to the startup blocks below. |
| `items`, `item_count`, `entries`, `files`, `file_count` | The show tables. |
| `file` | `FileSource`: the open file and its 512-byte buffer. |
| `inflate` | `Inflate`: bit buffer, block state, code tables. |
| `decoder` | `OdrgDecoder`: header fields, records left, palette (768 bytes). |
| `scale[256]` | Brightness table: `scale[v] = (v * brightness + 127) / 255`. |
| `on`, `brightness`, `playing`, `shown`, `zero`, `zero_pending` | Playback state. |
| `stream_*` | Which file is open for playback, its turn and loop numbers, the end time of the decoded frame. |
| `started`, `t0`, `latest`, `next_due` | Clock: power-on moment, latest timestamp, next grid time due. |
| `second_*` | Refresh counts of the running and the previous second. |
| `line[65]`, `line_length`, `line_over` | The unfinished line of `odrig_core_feed`. |

Blocks obtained during startup, with their sizes for the ten-leg mapping and 100 items:

| Block | Size | Bytes |
|---|---|---:|
| Core object | fixed | at most 4,096 |
| `legs` | 12 per leg | 120 |
| `led_pixel` | 2 per LED: the pixel index of each LED | 3,600 |
| `led_data` | 3 per LED | 5,400 |
| Row check | 1 bit per row | 4 |
| `pixels` | the smaller of 3 * W * H and 65,534 | 5,400 |
| `window` | 32,768 | 32,768 |
| `items` | 16 per item | 1,600 |
| `entries` | 2 per cycle entry | at most a few hundred |
| `files` | 48 per animation item: name, total duration, frame count | at most 4,800 |

The total is below 60 KB. `arena.h` holds the one function that calls `host.alloc`; it
refuses to run once startup has ended.

```cpp
namespace odrig {
struct LegInfo  { uint16_t leg; uint16_t pin; uint32_t first; uint32_t count; };
struct ItemInfo { uint16_t id; uint16_t seconds; uint8_t kind; uint32_t first; uint32_t count; };
    // animation: first is its index in files. cycle: first and count select its entries.
struct FileInfo { char name[33]; uint32_t frames; uint64_t total_ms; };
}
```

## Parts and their interfaces

All in `namespace odrig`. Every function that can fail returns a `Reason`; `kNone` is
success.

### `reasons`

`enum Reason` has one value for every reason of `docs/reasons.md` that the core can report,
and `const char *reason_name(Reason)` gives its text. One more value, `kEnd`, marks the end
of a stream and is used inside the core only.

### `file_source`

```cpp
struct FileSource {
    Reason open(const odrig_host &host, const char *name);  // kNone, kFileMissing, kReadError
    int get();              // 0..255, or -1 at the end of the file, or -2 on a read failure
    void close();
};
```

`get` refills its 512-byte buffer with one `host.read` call when it is empty. A return
value of `read` above the capacity counts as a failure.

### `inflate`

```cpp
struct Inflate {
    void start(FileSource *in, uint8_t *window);
    int get();              // 0..255, -1 at the end of the stream, or a negative Reason
};
```

A pull decoder: each `get` returns the next byte of output. Its state is one of: block
start, inside a stored block (bytes left), decoding codes, copying a match (length left and
distance), ended.

- Bits are taken from the input one byte at a time, only when needed, so the decoder never
  reads a byte beyond the last one of the stream.
- Codes are decoded bit by bit against two tables per code, the number of codes of each
  length and the symbols in code order: 16 + 288 entries for literals and lengths, 16 + 30
  for distances, 16 bits each.
- Every output byte is also written to `window`, a ring of 32,768 bytes, from which matches
  are copied.

It rejects, as `bad-deflate`, exactly what zlib rejects: block type 3; a stored block whose
length and its complement disagree; more than 286 literal and length codes or more than 30
distance codes; a repeat code with nothing to repeat or running past the end; a set of code
lengths that is over-subscribed; a set that is incomplete, unless it is a literal and length
set or a distance set with a single code of one bit; no code for the end of block; a
decoded length symbol above 285 or distance symbol above 29; a distance greater than the
number of bytes produced so far. The end of the file before the last block is complete is
`truncated`.

### `odrg_decoder`

```cpp
struct OdrgDecoder {
    Reason open(FileSource *file, Inflate *inflate, uint8_t *window);  // header and palette
    Reason next(uint8_t *pixels, uint16_t *duration);                  // one frame record
    Reason finish();                                                   // nothing may follow
    uint16_t width, height, colours;    // W, H, C
    uint32_t frames, n;                 // F, N
    uint8_t  palette[768];
};
```

- `open` reads the 16 header bytes from the file and checks them in the order of their
  offsets. The body is then read through one function that returns the next byte from the
  file or from `Inflate`. The palette is read into `palette`.
- `next` reads the five bytes of the record, checks duration, L and mode, and decodes the
  data straight into `pixels`, which holds the previous picture. Nothing of the record is
  buffered: the bit reader holds at most 32 bits, and counts the record's bytes so that it
  never takes one that belongs to the next record.
- Rice codes are read from a 16-bit look-ahead, padded with zero bits at the end of the
  record, with a 256-entry table giving the number of leading one-bits of a byte. A code
  longer than the bits that are left is `out-of-bits`.
- A Gamma code is read bit by bit to its end before its value is judged.
- There is one loop per predictor and mode. Predictor 0 skips zero runs without touching
  the buffer. Predictor 1 keeps two pixels of running values: the difference of the
  previous pixel and of the first pixel of the current row. Predictor 2 reads its
  neighbours from `pixels` itself.
- In a palette file every byte written is compared with C. A byte of C or more is
  remembered and reported as `bad-palette-index` when the record's bits have been checked.
- After the N codes, a byte of the record not yet taken is `too-much-padding`.
- `finish` asks the body for one more byte, which must be the end, and then the file for one
  more byte, which must be the end of the file; otherwise `trailing-bytes`.

The same `OdrgDecoder` checks files at startup and decodes them for playback. In both uses
W and H are compared with the mapping before the first record is decoded, so N never exceeds
the size of `pixels`.

### `json_reader`

```cpp
struct JsonReader {
    void start(FileSource *in);
    bool object_begin();
    bool object_next(char *name, uint8_t capacity);   // false at the closing brace
    bool array_begin();
    bool array_next();                                // false at the closing bracket
    bool integer(uint32_t *value);                    // digits only; false for anything else
    bool string(char *text, uint8_t capacity);
    bool end();                                       // only white space is left
    bool failed;
};
```

A reader that pulls one token at a time from the file. The readers of the two files call it
in the order their format dictates, so the nesting is in their code and nothing recurses.

- White space is space, tab, line feed and carriage return.
- A string may hold the escapes of JSON. A `\u` escape below 0080 gives that character; any
  other gives a byte that no expected name contains. A string longer than its capacity
  fails, as no valid name or value is that long.
- An integer is an optional minus sign, then `0` or a digit from 1 to 9 followed by digits,
  not followed by `.`, `e` or `E`. The value saturates above 4,294,967,295. A minus sign
  before anything but zero fails.
- The caller keeps one bit for each member of an object and fails on a member seen twice,
  an unknown member, or a required member that is absent.

### `mapping`

`Reason read_mapping(Core &core)` reads `mapping.json` twice. The first pass checks the form
and the range of every member and counts the legs and rows; W * H is then checked, and the
tables are obtained. The second pass fills `legs` and `led_pixel`, marks each row in the row
check, and compares each leg with those before it. A leg number or pin used twice, a row
outside 1 to H, or a row marked twice is `mapping-malformed`.

For row position r of a leg and distance i along the row, the LED at index
`first + r * W + i` gets pixel index `(y - 1) * W + (x - 1)`, with y and x from the rule of
Requirement 6.

### `show`

`Reason read_show(Core &core)` reads `show.json` twice: the first pass checks the format and
counts items, cycle entries and animation items; then the tables are obtained; the second
pass fills them. Then three loops, in this order: every pair of items for `duplicate-id`;
every entry of every cycle in file order, then `start`, for `undefined-id`; every entry of
every cycle in file order for `nested-cycle`. Animation items with the same file name share
one entry of `files`.

### `player`

```cpp
void     player_start(Core &core);                       // power-on state
void     player_play(Core &core, uint32_t item);
int      player_poll(Core &core, uint64_t now_ms);       // odrig_core_poll
void     player_set_brightness(Core &core, uint8_t value);
uint32_t player_fps(const Core &core, uint64_t now_ms);
```

### `commands`

Implements `odrig_core_command` and `odrig_core_feed`, and writes replies with a small
routine that appends text and decimal numbers to the reply buffer.

## Algorithms

### Startup

`odrig_core_begin`:

1. Obtain the core object. No memory: return NULL. Clear it; copy the host; `on` is true.
2. `read_mapping`. On failure: record the reason, leave zero legs, finish.
3. Obtain `pixels` and `window`.
4. `read_show`, including the three id loops. On success so far, brightness is the show's.
5. For each entry of `files`, in order of first use: open it (`file-missing`,
   `read-error`); `decoder.open` (`file-malformed`); compare W and H with the mapping
   (`size-mismatch`); call `decoder.next` F times, adding up the durations
   (`file-malformed`); `decoder.finish`; close. Store the total duration and F.
6. No failure: when the show has `start`, that item is playing.
7. Mark startup as ended. From here on `arena` refuses.

A failed `alloc` at any step after the first records `out-of-memory`. A failure of
`host.read` records `read-error <name>`. The first failure ends the checks. The reason text
is also passed to `host.log`.

### Clock, grid and refreshes

Every entry point first passes its timestamp through `touch(now)`: a timestamp below
`latest` becomes `latest`; the first one sets `t0` and `next_due = t0`.

`player_poll(now)`:

1. No legs, or `now < next_due`: return 0.
2. `g = t0 + ((now - t0) / 20) * 20`, the latest grid time at or before now;
   `next_due = g + 20`.
3. Count the refresh for `second = (now - t0) / 1000`.
4. Show invalid or nothing playing: the picture is dark. Otherwise:
   - if `zero_pending`, set `zero = g` and clear it;
   - `e = now - zero`;
   - an animation item: `turn = 0`, `t = e`. A cycle with n entries and turn length
     `T = seconds * 1000`: `turn = e / T`, `t = e mod T`, and the animation is entry
     `turn mod n`;
   - with D the animation's total duration: `loop = t / D`, `q = t mod D`;
   - if the stream is not open on this animation with this `turn` and `loop`: close it,
     open the file, `decoder.open`, compare W and H with the mapping (`size-mismatch`),
     clear `pixels` to zero, set the frame end to 0;
   - while the frame end is at or before q: `decoder.next`, and add the duration to the
     frame end. A record needed after the file's last one is `truncated`;
   - set `shown` to the animation;
   - any failure makes the show invalid as Requirement 16 states: the reason is recorded,
     nothing is playing, and the picture is dark.
5. Fill `led_data`: zero when dark or switched off; otherwise, for every LED,
   `scale[c]` of the three colour values of pixel `led_pixel[led]`, taken through the
   palette in a palette file.
6. Return 1.

Decoding continues while the LEDs are switched off, so switching on needs no catching up.
After a long gap between calls the stream is reopened at most once and decoded forward
within one loop.

`player_play` sets `playing`, sets `zero_pending`, closes the stream and sets `shown` to the
item's first animation. `player_set_brightness` rebuilds `scale`.

### Refresh rate

The core keeps the number of the running second with its count, and the number of the
second before it that had a refresh with its count. `player_fps(now)` takes
`s = (now - t0) / 1000`; it returns 0 when s is 0, the running count when the running second
is `s - 1`, the previous count when the previous second is `s - 1`, and 0 otherwise.

### Commands

`odrig_core_command`:

1. `touch(now)`. Drop one final newline, then one final carriage return.
2. More than 64 characters: `line-too-long`.
3. Split at every space. The first word must equal a command name, byte for byte:
   otherwise `unknown-command`.
4. `on`, `off`, `status`: no further word. `play`, `brightness`: exactly one, made of
   decimal digits only, with a value from 1 to 65,535 or from 0 to 255; leading zeros do
   not matter. Otherwise `bad-argument`.
5. `play`: `show-invalid` when the show is invalid; `unknown-id` when no item has the id;
   otherwise `player_play`.
6. Write the reply.

`odrig_core_feed`, for each byte: a newline ends the line; when the line overflowed, the
reply is `line-too-long`, otherwise the kept bytes go to `odrig_core_command`; `on_reply`
receives the kept bytes, at most 64, and the reply. Any other byte is kept while fewer than
65 are held, which leaves room for 64 characters and a carriage return; beyond that the line
is marked as overflowed.

## Determinism

The core's output is a function of the files, the calls and their timestamps. Every block
obtained from the host is cleared before use. No value is derived from an address, no
uninitialised byte is read, and the only notion of time is the timestamp of the current
call. The host's `log` function receives text but nothing it does comes back to the core.

## Error handling

- There are no exceptions and no aborts. Every failure is a `Reason` returned to the
  caller, and the first one decides.
- A failure at startup or during playback sets `invalid` and the reason text once. The text
  does not change afterwards.
- Arguments from the host are trusted to be well formed pointers; the core checks sizes and
  indexes it receives (`index` in `odrig_core_leg`, `capacity` in `odrig_core_command`) and
  returns 0 when they are out of range.
- Every count read from a file is checked before it is used as a size or an index.

## Third-party code

None. The DEFLATE decoder and the JSON reader are written for the core from RFC 1951 and
RFC 8259. Reasons for not bringing in an existing decompressor:

- the ESP32 ROM already exports the names of the common small one (miniz), so a second copy
  would need its names changed to link safely;
- the core must know the exact byte at which a stream ends, to reject bytes after it;
- a pull decoder that returns one byte at a time fits the streaming ODRG decoder directly
  and needs about 1 KB of state besides the window.

The suite checks the decoder against zlib on generated and damaged streams.

## Build

`core/Makefile`, written for the GNU Make 3.81 that Apple ships:

| Command | Result |
|---|---|
| `make -C core` | `core/build/libodrig_core.a` from every `core/src/*.cpp`. Needs Apple's command-line developer tools. |
| `make -C core test` | The library, then `core/build/odrig_host`, then the suite. Also needs Python 3.10 or later, as `python3` or given with `PYTHON=`. |
| `make -C core bench` | `core/build/odrig_bench`, the two clips, and the benchmark's report. |
| `make -C core clean` | Removes `core/build/`. |

Source files are found with `$(wildcard src/*.cpp)`; no file is listed. The test host links
a second compilation of the same sources, with the core's flags plus
`-fsanitize=address,undefined -fno-sanitize-recover=undefined -O1 -g`. The host's own files
are compiled as C++17.

## Testing strategy

The suite is Python `unittest` in `tests/core/`, run by `make -C core test` as

```
python3 -m unittest discover -s tests/core -t .
```

from the repository root. It drives the test host as a child process and compares its
output with the reference of seed 01, which needs only the Python standard library.

### The test host

`odrig_host` implements `odrig_host` over a folder on disk and prints what the core does. It
has no clock: every timestamp comes from its input.

| Invocation | Behaviour |
|---|---|
| `odrig_host session DIR [options]` | Starts the core on DIR, prints `core ok` or `core null`, `memory <bytes> <blocks>`, `error <text>` or `error none`, and `leg <leg> <pin> <count>` for each leg. Then obeys lines from standard input. |
| `odrig_host decode FILE` | Uses `OdrgDecoder` directly. Prints `header <W> <H> <C> <F> <compressed>`, one `frame <ms> <hex of the picture as colours>` per record, then `end`, or `rejected <reason>`. |
| `odrig_host inflate` | Decodes standard input with `Inflate`. Prints `data <hex>` or `rejected <reason>`. |
| `odrig_host guard alloc` and `guard new` | Calls `host.alloc`, or `operator new`, as the core would after startup. Must stop with status 70. |
| `odrig_host reasons` | Prints every name `reason_name` can return, one per line. |

The host's file functions check how the core uses them: opening a file while another is
open, or reading or closing with none open, prints `file misuse` and stops the program with
status 71.

Session input lines:

| Line | Action | Output |
|---|---|---|
| `poll <ms>` | `odrig_core_poll` | `refresh <ms>` and one `data <leg> <hex>` per leg, or `idle <ms>` |
| `line <ms> <text>` | `odrig_core_command` with the text | `reply <json>` |
| `linehex <ms> <hex>` | `odrig_core_command` with exactly these bytes | `reply <json>` |
| `bytes <ms> <hex>` | `odrig_core_feed` with the bytes | for each reply, `fed <hex of the line>` and `reply <json>` |
| `error` | `odrig_core_error` | `error <text>` or `error none` |

Session options: `--alloc-fails-at N` makes the N-th `alloc` return NULL; `--dirty-memory`
fills every block with the byte `0xA5` before handing it out; `--read-fails FILE OFFSET`
makes `read` fail at that offset of that file; `--remove-after FILE N` makes a file
disappear from the host's view after it has been opened N times; `--swap-after FILE N OTHER`
serves the content of OTHER under the name FILE from then on.

### Allocation after startup

`guard.cpp` replaces the global `operator new` and `operator delete` family. The host sets a
flag when it enters a core function after startup and clears it when it leaves, and its own
`alloc`, `open`, `read`, `close` and `log` functions lower the flag while they run. With the
flag up, `operator new` and the host's `alloc` print `allocation after startup` and stop the
program with status 70. The guard is part of the one test host, so every test runs with it.

Allocation that bypasses both, such as a direct `malloc`, is ruled out by the symbol test
below: the compiled core does not refer to any allocation routine at all.

### Tests

| File | What it proves |
|---|---|
| `test_build.py` | The names `core/build/libodrig_core.a` refers to and does not define are all in `allowed_symbols.txt` (memory copy, fill and compare, and compiler support); the library has no symbol in a writable data section (`__data`, `__bss`, `__common`); no core source includes a header other than `stdint.h`, `stddef.h`, `string.h` and its own, and none uses `float` or `double`; `odrig_core.h` compiles as C; every name of `odrig_host reasons` is in `docs/reasons.md`. |
| `test_docs.py` | Every function and every member of `odrig_core.h` is named in `docs/core.md`. |
| `test_inflate.py` | For seeded data compressed by zlib at levels 0, 1 and 9, with the fixed strategy, with matches at distance 32,768 and of length 258, and in several blocks: output equal to zlib's. For seeded damaged copies: accepted or rejected as zlib does, with equal output when accepted. A stream cut short is `truncated`. |
| `test_vectors.py` | Every valid vector of `tests/vectors/valid` decodes to its expected frames record by record; every file of `tests/vectors/invalid` is rejected with the reason in its name. The folders are listed at run time. |
| `test_decoder.py` | Files written by seed 01's encoder from seeded animations, with and without a palette, compressed and not, including N of 65,534 and a body above 32,768 bytes: equal to the reference decoder. Damaged copies: accepted or rejected as the reference decoder does. |
| `test_json.py` | A set of texts, valid and invalid, used as `mapping.json` and as `show.json`: the core and seed 01's readers agree on each. |
| `test_mapping.py` | The leg list for both tracked mappings and for made-up ones (a leg starting on the left, legs of two and of four rows, legs in another order); each broken rule gives `mapping-malformed`. |
| `test_startup.py` | Each text of Requirement 3: LEDs dark and the text reported by `odrig_core_error` and by `status`; the order of the checks; brightness and state after a valid and an invalid startup; `out-of-memory` at each `alloc`; `core null`. |
| `test_playback.py` | Hello world and DVD bounce on the two-leg mapping and the dense clip on the ten-leg mapping: the LED data of every refresh over one loop and into the next equals the reference player. A one-frame animation in which every pixel has its own colour, on each tracked and made-up mapping: every LED shows the pixel the rule of Requirement 6 gives it. Late and skipped polls; timestamps going backwards. |
| `test_cycle.py` | Turn changes at the right refresh; each turn starts from the first frame, also with one animation listed twice; an animation shorter than a turn loops. |
| `test_commands.py` | Every command and every error code, the order of the codes, empty words, a carriage return, lines of 64 and 65 characters, byte input split across calls, an over-long line in byte input. |
| `test_session.py` | The scripted session of Requirement 17: replies and refreshes equal to the reference player. |
| `test_status.py` | `fps` for regular, late and missing polls; `animation` during a cycle; the exact bytes of the status reply. |
| `test_failure.py` | A read failure, a removed file and a file replaced by one of another size while playing: dark LEDs, the reason, `show-invalid`. |
| `test_memory.py` | Memory for the ten-leg mapping and 100 items is below 131,072 bytes; equal for a short and a long file; `guard alloc` and `guard new` stop with status 70; two runs of one session give identical output. |

`support.py` holds the reference player: a second, independent statement of Requirements 4
to 12 in Python, built on `odrig.odrg.decode`, `odrig.mapping.read` and `odrig.show.read`.
It applies the mapping rule itself and answers the same input lines as the test host with
the same output lines, so a test compares two texts.

## Benchmark

`odrig_bench FILE` decodes the file ten times with `OdrgDecoder` and measures each
`next` call with `std::chrono::steady_clock`. It is compiled with the core's own flags, no
sanitizer. `make -C core bench` writes the dense 60 x 30 clip of 10 seconds with seed 01's
generator, encodes it compressed and uncompressed into `core/build/bench/`, runs the
program on both and prints:

```
file                    bytes  frames  mean_us  max_us
dense-compressed.odrg  ......     500     ....    ....
dense-plain.odrg       ......     500     ....    ....
```

## Documentation

- `docs/core.md`: the three commands and what each needs; the host interface with every
  function, the rules of use, the rules of time and refreshes, the LED data and the memory
  table; the test host's invocations.
- `docs/reasons.md`: `read-error` and `out-of-memory`, and the texts of Requirement 3 with
  what follows each name.
- `README.md`: one sentence pointing to `docs/core.md`.

## How the two hosts use the core

- **Emulator (seed 03).** A Python program can reach the C interface through `ctypes` on a
  shared library built from `core/src/*.cpp`; how the emulator loads the core, and the
  build target for it, belong to seed 03. Its real-time loop and its record mode both call
  `odrig_core_poll`, with a real and a virtual clock. Serial bytes go to `odrig_core_feed`,
  an HTTP request body to `odrig_core_command`; `on_reply` and the return value give the
  page its command log, and `odrig_core_error` the reason of an invalid show.
- **Firmware (seed 04).** A WLED module includes `odrig_core.h` and compiles `core/src` as
  a library. It supplies memory from the heap it chooses, files from WLED's file system and
  the time from the millisecond counter, sets one LED output per `odrig_leg` at startup,
  copies `rgb` to the outputs when `odrig_core_poll` returns 1, and passes serial bytes and
  HTTP bodies to the two command entries.
