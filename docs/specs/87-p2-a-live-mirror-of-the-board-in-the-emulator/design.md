# Design

## Boundaries

The board tells what it will play; the emulator plays it. The core gets the plan, its six
command forms, the ways of the push and one library entry for the mirror; the firmware writes
`#plan` lines on its two serial ways; the emulator gets the ways of its own ports, and with
one of three new options becomes a mirror and a man in the middle; the command tool sends
`plan`. The app's files, the APK, the converter, the Python library's formats, `show.json`,
the catalogs' formats and the firmware tool are unchanged; the firmware images are built
again.

## The core

### What it keeps

The core keeps no table of the plan: the core object with a drive is 27 bytes under the
131,072 the suite allows, and a table with a copy of the playback's state would take
hundreds. A reply of `plan` decides the plan when it is asked, on the stack. The core object
gets, after `clocks_internal_id`:

```
uint32_t plan_version;     // 1 at the start, one more at each change
uint32_t plan_noise;       // the noise of the moment planning was switched on
uint16_t plan_sign;        // a sign of what a refresh found, to see a change
uint16_t plan_ways;        // for ways 1 to 8: bit 2w-2 push on, bit 2w-1 a line is due
uint8_t plan_on : 1;       // planning is on
uint8_t plan_projecting : 1;  // a reply is deciding the turns ahead
```

and, among its pointers, `const odrig_mirror *mirror;`, the host's description of the turn a
mirror shows, null while none. The growth is measured by `tests/core/test_memory.py`; the
memory table of `docs/core.md` and its figure with a drive follow.

### Planning on and off

`plan on`: `plan_on = 1`, `plan_noise = core.noise`; `plan off`: `plan_on = 0`. Both count as
a change (3.2). `breaks.cpp`'s `pick` draws a new order from `draw_noise(core)` and
`show_at` a widget's seed from it, where

```
inline uint32_t draw_noise(const Core &core) { return core.plan_on ? core.plan_noise : core.noise; }
```

so a turn decided ahead and the same turn as it plays draw the same values (5.1); a resumed
turn takes `resume_seed` as before (5.2).

### The projection

A new file `core/src/plan.cpp` with `plan.h`. `struct PlayState` holds every field the
turn's end may change: `zero`, `turn_number`, `break_offset`, `break_due`, `break_rest`,
`window_started`; `window_spent`, `playing`, `shown`, `turn_item`, `turn_repeat`,
`resume_item`, `resume_seed`, `break_back`, `break_repeat`, `break_seed`, `order_key`,
`order_next`, `order_count`, `message_order_key`, `message_order_next`,
`message_order_count`; `in_place`, `break_phase`, `break_paused`, `break_message`,
`break_turns`, `break_held`, `save_due`, `turn_manual`, `break_manual`. `take(core)` copies
them out and `put(core, state)` back; about 120 bytes on the stack.

`player.cpp` exports `player_project(Core &, uint64_t at)`: with `plan_projecting` set it
calls `playlist_turn(core, at, &in_turn)` (which calls `clock_only_turn` in Clocks only), and
returns whether a turn is in progress after it. While `plan_projecting` is set:

- `playlist_turn` and `clock_only_turn` never call `first_loop_to`: a turn whose length is not
  known stays in progress, as the projection stops there anyway;
- `close_stream` and `player_halt` are not called: where nothing would play, `playing` is set
  to `kNothing` in the copy, which the projection reads as its end;
- nothing else of `playlist_turn` writes outside the fields of `PlayState`, but the copy marks
  of `mark_copies` and the drive's cursor, which a later draw writes again.

The window's end is never reached in a projection: `rotate`, which writes the current
playlist, its path and `playlist.txt`'s due flag, is past the projection's stop.

`plan_reply(Core &, uint64_t now, Reply &)` writes the head and then the items:

1. Nothing while the show is invalid, a test shows, nothing plays or the playlist has no turn.
2. A cycle: its turns from `advance`'s arithmetic, the one holding `now` first, each next one
   as long as `whole_passes` makes it, until the limits.
3. The playlist: `saved = take(core)`, `plan_projecting = 1`. The first item is the turn on
   the LEDs: `start` is `zero`, or `next_due` while `zero_pending`, and no `from`. Each item's
   end is `item_end`:
   - the length known: `zero + current_turn_ms(core)`, or the moment 5 minutes are counted,
     `max(break_due, zero)`, when a break would pause the turn there, as `playlist_turn`
     judges it;
   - the length not known: the longest time when the turn is cut by it (`seconds` and no
     repeat), else `null`, and the projection stops after this item.
   While the item's end is known, before `now + 600,000`, the window's end is later
   (`end < window_end(core)`), and fewer than 8 items are written: `player_project(core,
   end)`; when nothing would play, stop; else the next item is `turn_item` with `start = end`
   and `from = end - zero` when not 0. Then `put(core, saved)`, `plan_projecting = 0`.
4. Each item: `id_of`, the key of 4 below, `loop` as `length_of` when not 0, the seed of a
   widget, `brightness` when `brightness_of_position` differs from `core.brightness`. The
   seed of the first item is `core.seed` when `player_seed` has it, else, with planning on,
   `resume_seed` or `clock_seed(plan_noise, id, zero)`; of a later item `resume_seed` when the
   copy has one, else `clock_seed(plan_noise, id, zero)`.
5. An item is written only when it fits with the closing `]}` and the newline; the rest are
   left out.

A drive's file has its key in its row: `drive_row(core, at)`'s `crc` and `bytes`. A file of
the board's own storage has its size in `FileInfo.bytes` and its CRC-32 in the internal
catalog: `catalog_key(core, name, &crc)` in `catalog.cpp` reads the line of its name on its
page (`catalog_page_of`) through `read_at`, 256 bytes at a time on the stack; `null` while the
internal catalog is not `ok` or does not name it.

### Versions

`plan_bump(core)`: `++plan_version`, 0 skipped, and every way whose push is on is marked
due. It is called:

- by `command_answer`, after the reply, for every line whose first word is not one of the
  reading commands of 3.2 (`status`, `space`, `fault`, `list`, `read`, `saved`, `catalog`
  without `rebuild` or `cancel`, `order get`, `mapping get`, `rotation` alone, `time` alone,
  `schedule` alone, `plan` alone and `plan since`);
- by `player_poll` after the refresh, when `plan_sign` differs from `sign(core)`, a 16-bit
  mix of what a refresh can change by itself: `playing`, `turn_item`, `zero`, `break_phase`,
  `turn_repeat`, the length of the turn's animation, `on` and the power, `rotation`, the
  miniature's state, `mapping_test`, `mapping_snake`, `clocks_on`, `clock_message_on`,
  `clocks_error`, `drive_number`, `drive_count`, `tree_known`, `indexed`,
  `catalog_marker_crc`, `check_at`, `check_done`, `drive_check_at`, `remembered_next`,
  `current`, `in_place` and `invalid`;
- by `quarantine_file` and `drive_faulted`, whose effect may come after the refresh's sign.

`plan since V`: `V == plan_version` writes the short reply, else `plan_reply`.

### Ways and the push

`include/odrig_core.h` gets:

```
size_t odrig_core_command_on(odrig_core *, uint64_t now_ms, uint32_t way, const char *line, size_t length,
                             char *reply, size_t capacity);
void odrig_core_feed_on(odrig_core *, uint64_t now_ms, uint32_t way, const uint8_t *bytes, size_t length,
                        odrig_reply_fn on_reply, void *reply_ctx);
size_t odrig_core_plan_line(odrig_core *, uint64_t now_ms, uint32_t way, char *line, size_t capacity);
```

A way is 1 to 8; `odrig_core_command` and `odrig_core_feed` are way 0. `command_answer` takes
the way: `plan push on|off` on way 0 is `unsupported`, else it sets or clears the way's bits
(on sets the due bit too). `odrig_core_plan_line` gives `#plan `, the reply of `plan` and a
newline when the way's push is on and a line is due, clears the due bit, and gives 0
otherwise or when `capacity` is under `ODRIG_REPLY_MAX + 6`. A way that ends is switched off
by its host with `plan push off`.

### The mirror's entry

```
typedef struct odrig_mirror {
    char name[33];          /* the file, as open takes it; empty: nothing plays */
    uint8_t on;             /* the LEDs are on */
    uint8_t brightness;     /* the selected brightness */
    uint8_t rotation;       /* quarter turns clockwise, 0 to 3 */
    uint8_t test;           /* 0, the diagonal 1, a snake's test 2 */
    uint8_t snake;          /* 1 to 20 */
    uint32_t serial;        /* changes when the turn changes */
    uint32_t loop_ms;       /* the loop's length, 0 while not known */
    uint32_t seed;          /* a widget's seed */
    uint64_t zero_ms;       /* the moment the turn's time was 0, on the clock of the polls */
} odrig_mirror;
int odrig_core_mirror(odrig_core *, const odrig_mirror *turn);
```

`odrig_core_mirror` keeps the pointer and returns 1, or 0 for a host whose storage cannot be
changed. `player_poll`, with `mirror` set, takes the clock, the grid and the counts as always
and then `mirror_refresh(core, now)` in a new `mirror.cpp` in place of the playlist: the
position `kMirrorPosition` stands for the host's file in `length_of` (`loop_ms`), `type_of`
(the header read at its open, kept in `stream_item`'s turn), `id_of` (0) and `open_stream`
(the name); `show_at(core, kMirrorPosition, serial, now - zero_ms, zero_ms)` draws it, a widget
with `seed` in place of a draw. `brightness_selected` gives `brightness`, the power gives `on`,
`rotation_pixel` the rotation; a test draws as `mapping test` does, without saving the
playlist. Upload, check, drive, catalog, schedule and playlist steps are not taken while it
is set, so nothing is written.

## The firmware

`odrig_uart.cpp`: lines go to `commandLineOn(1, ...)`, which calls `odrig_core_command_on`;
after `writeLog`, when `Serial0.availableForWrite() - WRITE_MARGIN >= ODRIG_REPLY_MAX + 6` and
no line has ended, `planLine(1, buffer)` under the lock and the line written whole.
`odrig_serial.cpp`: bytes go to `odrig_core_feed_on(..., 2, ...)`; a static buffer of
`ODRIG_REPLY_MAX + 8` holds a `#plan` line, written in pieces as `Serial.availableForWrite()`
gives room, the poll returning before it reads a byte while pieces wait, as the probe build's
long line does. HTTP keeps `odrig_core_command`. The host-only tests of `tests/firmware`
cover the ways and the pieces with the firmware's test doubles.

## The emulator

### The ways of its ports

`binding.py` declares the three entries and `odrig_core_mirror`. `Engine.feed(data,
transport, way=0)` and `Engine.line(..., way=0)` pass the way; `Engine.plan_line(way)` asks
for a due line. The serial port is way 1. `lineport.Port` gives each connection the lowest
free way from 2 to 8, 0 when none is free, and switches it off with `plan push off` when it
closes; a connection's handler waits on its socket with a timeout of 50 ms and, between
replies, writes what `plan_line` and the mirror's queue give it. `serialport.Port` does the
same for way 1.

### The mirror

A package `emulator/mirror/`:

- `link.py`: `SerialLink(name)` with the command tool's opening (`odrigctl.client._ready`,
  kept open, a reader thread), `TcpLink(address)` and `HttpLink(address)`. A serial or TCP
  link splits what arrives into lines: a reply (a JSON object with `ok`) goes to the line that
  waits, a `#plan` line to the keeper, every other line to the listeners. An HTTP link posts
  each line to `/odrig` on its own connection.
- `middle.py`: `Middle.send(line, client)` for a client's line, `Middle.ask(line)` for the
  mirror's own. On a serial or TCP link one worker sends the waiting lines one at a time, a
  client's before the mirror's; a reply is handed to its line's waiter if it still waits,
  else dropped; a line is waited for until its reply comes, its client stops waiting and 30
  seconds pass after, the link is lost or a restart is seen. On an HTTP link each line is a
  request of its own. A lost link fails every waiter, which the transports turn into no reply.
- `keeper.py`: `Keeper` joins (`status`, `plan on`, `plan push on` on serial and TCP, `plan`),
  takes every plan, polls `plan since` (10 s with a push, 2 s without, and after a client's
  line not in the reading list of 3.2), sees a restart (a `now` that went back, `planning`
  false, the loader's lines, a port gone) and joins again, keeps the offset `board - local`
  from `now` and half the round trip, and on its end sends `plan push off` and, when it found
  planning off, `plan off`.
- `files.py`: `Files.path(key)`: `build/mirror/<key>.odrg` when there; else the files of
  `collection/` and of `ODRIG_ANIMATIONS` of `env` whose size is the key's, their CRC-32 taken
  once and kept by path and modification time; else `None`. `Fetcher` reads a missing key's
  file with `read <id> <offset> 720` through `Middle.ask`, checks its CRC-32 and size, and
  writes `build/mirror/<key>.odrg`; it says the bytes fetched.
- `driver.py`: at every tick of the engine, the item of the latest plan whose part holds the
  board's time `local + offset`, and from it the core's `odrig_mirror`: the name `<key>.odrg`
  when `Files` has it, made known to the host, else empty; `zero_ms` the local moment of
  `start - from`; `serial` new when the item's id, start or from change; the plan's on,
  brightness, rotation and test; `debug mini on|off` to the emulator's own core when the
  plan's `mini` changes.

`host.FolderHost` opens a name of the mirror's table, `<key>.odrg`, from its path. The engine
in a mirror holds a `Mirror` that owns the link, the middle, the keeper, the files, the
fetcher and the driver: `line` and `feed` hand the lines to the middle and log them with the
board's reply; `seek` answers `mirror`; the header's status is the latest board `status` the
middle saw, asked for every 2 seconds while no client asks. `httpd` adds `mirror` to `hello`
and sends `mirror` events; `app.py` parses the three options, refuses them beside `--drive`,
`--drive-folder` and `--record`, prints `mirror:`, and widens the `--lan` warning. The page,
`emulator/web/`, shows the link, its state and the version in its header, the bands of a
fetch, of another canvas and of a lost link, marks the board's lines in its log and hides the
seek bar.

## The command tool

`odrigctl/cli.py`: `plan`, `plan since N`, `plan on`, `plan off`, `plan push on`, `plan push
off`; another form is status 2 with nothing sent.

## Tests

- `tests/core/test_plan.py`: the reply's members; planning off as before, the item on the
  LEDs alone; with planning on, every planned turn found in `status` at its start with its
  seed, over turns, a break's pause and resume, Clocks only, a cycle, a jump; the stops at an
  unknown length and at a window's end; versions on changing and reading lines and at a
  turn's change; `plan since`; the push of ways 0, 1 and 2; the memory of the target file
  with a drive; the mirror's entry against `odrig_host render` for frames, a text and a
  clock with a seed.
- `tests/firmware`: the UART's and the USB socket's `#plan` lines, whole and in pieces.
- `tests/emulator/test_plan_push.py`: a line-port connection's push; `test_mirror.py`: an
  emulator mirrored by another over its line port and over HTTP, the pictures within two
  refreshes, a late join, a missing file fetched and kept, a `play` through the mirror and
  through the board, a lost link and its return, the board's restart; `test_middle.py`: the
  middle against a scripted link, replies to their own clients, late replies dropped, `#log`
  and `#plan` lines, the order of lines, a long wait, a lost link.
- `tests/emulator/test_tool.py`: the six forms.

## Documents

`docs/commands.md`: the six forms in the table, a section "The plan", `unsupported` and
`bad-argument` of `plan`, and "Transports" with `#plan` lines. `docs/core.md`: planning, the
three entries of ways, the mirror's entry, the memory table. `docs/show.md`: when a seed is
drawn while planning. `docs/firmware.md`: the push on both sockets. `docs/emulator.md`: the
ways of the ports, "A mirror of a board", the command tool's `plan`, the check list by eye.
`docs/decisions.md`: "Commands", "Emulator", "Animation formats" and the change log.
`agent/vocabulary.md`: plan, way, mirror. `docs/drifts.md`: the answers below.

## Answers given here

- No table: the plan is decided at each reply, since the memory with a drive has 27 bytes left.
- A reply decides up to 8 turns at once rather than one a refresh; on the board it takes some
  milliseconds of one command.
- `loop` is added to an item, so the mirror needs no reading of a file's length.
- The plan stops at the window's end; the next playlist's turns come once it passes.
- The item on the LEDs that went on after a break may name its turn's zero as `start`.
- A version may count a change that left the reply as it was; it never misses one.
- Ways are 1 to 8; the firmware uses 1 and 2, the emulator 1 and 2 to 8.
- The mirror's description lives in the host; the core keeps a pointer.
- A file of the board's own storage gets its key from the internal catalog at each reply.
- The man in the middle waits for a late reply 30 seconds after its client stopped waiting.
- Fetched files are kept in `build/mirror/` under their keys; nothing is written into
  `collection/`.
