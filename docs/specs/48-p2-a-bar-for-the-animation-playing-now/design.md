# Design: a bar for the animation playing now, and a frozen top

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/48-p2-a-bar-for-the-animation-playing-now/seed.md`.

## The core

### The ad hoc value and the counts (`player.cpp`, `player.h`, `core_state.h`)

`Core` gains `uint32_t turn_repeat` right after `turn_item`, the ad hoc value, 0 while
none is set; `turn_item` is followed by the 64-bit `turn_number`, so the value takes the
padding there when `turn_item` stands at a multiple of 8, and the object stays within its
4,096 bytes in any case (its `static_assert`).

- `loops_of` reads `count & 0xFFFF`; `saved_of(core, position)` is `count >> 16` for an
  item and the drive table's entry for a drive's place (see below), 0 for none.
- `turn_ms(core, position)`, used for every turn and for the round of the playlist: a saved
  repeat gives `saved * loop`, not cut by `max_seconds`; otherwise today's rule.
- `current_turn_ms(core)`: `turn_repeat * loop` while an ad hoc value is set, else
  `turn_ms(core, turn_item)`.
- `playlist_turn`: the turn in progress is `current_turn_ms`; while the loop's length is
  not known, `max_seconds` cuts only a turn that has neither an ad hoc value nor a saved
  repeat; the round's division is skipped while `turn_repeat` is set, so that the turn with
  the ad hoc value is taken off on its own first; where a turn ends, `turn_repeat = 0`.
- `player_play_all`, `player_play_cycle` and `player_halt` set `turn_repeat = 0`: every
  new turn and every stop goes through one of them (a jump, an upload, a quarantine, a
  removal, `ignore`, a drive pulled out, a test of the mapping, a restart).
- `player_reported(core)`: the show is valid, no test shows, `playing == kPlaylist`,
  `turn_item != kNothing`, `shown == turn_item` and `!zero_pending`.
- `player_counts(core, now, &counts)`: false while no turn is reported; else
  `counts.repeat` (0 for `null`), `counts.loop` and `counts.saved` (0 for `null`). With the
  length known: `loop = (now - zero) / length + 1`, at most `repeat`; `repeat` is
  `turn_repeat`, else the saved repeat, else `ceil(turn_ms / length)`. Without it: `loop`
  1, `repeat` `turn_repeat`, else the saved repeat, else 0.
- `player_set_repeat(core, id, n, now)`: false unless a turn is reported and its animation
  has the id; else `turn_repeat = max(n, loop in progress)`.
- `player_default_again(core, id, now)`: when a turn of the id is reported: with the
  length unknown, `turn_repeat = 0`; else, the saved repeat being gone, when
  `now - zero >= turn_ms(turn_item)` the turn ends at the end of the loop in progress,
  `turn_repeat = loop`, and otherwise `turn_repeat = 0`.

### The command (`commands.cpp`)

`repeat <id> <n>`, `repeat <id> <n> save`, `repeat <id> default`: the word count is
checked before any word is read; `<id>` and `<n>` by `number_word` 1 to 65,535. Then
`show-invalid`. The first form: `player_set_repeat`, else `stale`. The saving forms:
`busy` while `catalog_rebuilding`, `!check_complete` or an upload is open, then
`repeats_save` or `repeats_restore`. `status` writes `repeat`, `loop` and `saved` after
`seed`, each a number or `null`.

### The saved repeats (`repeats.cpp`, `repeats.h`)

A module of its own beside `order.cpp`, which it follows:

- `kRepeatsFile = "repeats.txt"`, `kRepeatsPart = "repeats.part"`, the header
  `odrig-repeats 1`, `kRepeatsLines = 512`, `kRepeatsDriveMost = 32`.
- The drive table: `RepeatOf {uint16_t place; uint16_t n;}`, 32 of them, `n == 0` for a free
  place, taken by `order_begin` after the order's block only on a host with a drive
  (128 bytes); `Core::repeats_drive` points at it, `nullptr` otherwise.
- A line is read by the order's reader, `core.order_reader`, whose room of 162 bytes holds
  the longest line of 135. `take_line`: the first line must be the header; a line is `<n>
  <kind> <name>` with `<n>` 1 to 65,535 without a leading zero, `<kind>` `f` with a name as
  `is_file_name` takes it, or `x` with 1 to 127 bytes without NUL; anything else, a line
  longer than 135 bytes, bytes after the last line feed and a file without its header make
  the file unreadable. A missing file, `read_at` failing at offset 0, holds nothing and logs
  nothing.
- A line is applied as it is read: `f` to every animation item whose file has the name and
  no saved repeat yet, in the upper 16 bits of `count`; `x` to the drive's place whose name
  it is, by the order's hash and `place_named`, when that place has no entry yet: a new
  entry, or, with the 32 places taken, the log line `repeats over` once for the reading.
  An unreadable file clears every saved repeat in memory, internal and of the drive, and
  logs `repeats unreadable` once for the reading.
- `repeats_start`, called at the end of `order_start`, reads the whole file for the items.
  `repeats_reload`, called at the end of `order_reload`, clears and reads it whole for the
  items and the drive's places; and after an upload that gives an item another file name
  (`storage.cpp`).
- The drive's take-up: `order_drive_found` clears the table, and the order's steps read the
  drive's part of `order.txt` and then, as a second phase of `order_due` (2), the drive's
  lines of `repeats.txt`, one read of 512 bytes at most a step, before any of the drive's
  files joins the playlist; `order_drive_yields` begins that phase again from the file's
  start. A drive pulled out clears the table through the same `order_drive_found`.
- `repeats_save(core, id, n, now, reply)` and `repeats_restore(core, id, now, reply)`: the
  animation by id as `list` lists it, `unknown-id` or, for a cycle or a folder, `in-use`;
  its name and kind; for a save of the value in force, or a restore with nothing saved,
  nothing is written. A save of a drive's file without an entry while the 32 places are
  taken is `no-space`. Then a first reading of the old file through the second source
  (`drive_check_yields` first) counts the lines of other animations and, of them, the `f`
  lines no item of `show.json` names; a readable file whose other lines number 512 drops
  those, and when 512 remain the save is `no-space`. A read that fails after its first
  byte, or at offset 0 while a saved repeat is in force, is `storage-error`. The second
  reading writes `repeats.part` through the first 1,000 bytes of the chunk, as
  `order.part` is written: the header, every other line of a readable file but the dropped
  ones, the new line in the place of the animation's first line or at the end; then the
  rename, and `repeats_reload`. Any failed call removes `repeats.part` and is
  `storage-error`. Last the turn: a save acts as `player_set_repeat`, a restore as
  `player_default_again`.
- `storage_clear_parts` removes a `repeats.part` at the start.
- `content.cpp`'s writer of `show.json` writes `repeat` from `count & 0xFFFF`.

### The memory

The drive table adds 128 bytes to the order's block on a host with a drive, the pointer
and the ad hoc value to the core object. `docs/core.md`'s table and sentences, and
`tests/core/test_drive.py`'s sum, take what the suite measures.

### The reference player (`tests/core/support.py`)

`ReferencePlayer` gains the three forms with their refusals for the board's own files, the
saved repeats read from `repeats.txt` at its start and written into its files, the ad hoc
value with its clearing, the counts of 3.1 in `_turn_ms` and in `_picture`, and the three
members of `status`.

### The test host (`tests/core/host/host.cpp`)

`check_name` accepts `repeats.txt` and `repeats.part`.

## The tools

- `odrigctl/cli.py`: `repeat` in `COMMANDS`; `checked` takes `ID N`, `ID N save` and `ID
  default`; the epilog names the three forms.
- `firmware/fwtool/storage.py`: `REPEATS_NAME = "repeats.txt"` in `KEPT_NAMES`, which
  `install-show` keeps when the folder has none, a folder's check allows, and `read-show`
  copies.
- `docs/emulator.md`: the emulator keeps the file through its host; a seek backward drops an
  ad hoc repeat, not a saved one.

## The app

### The status and the commands

`commands.js`'s `status` checks `repeat` and `loop` (`null` or 1 to 65,535,000) and
`saved` (`null` or 1 to 65,535) and gives `hasRepeat`, `repeat`, `loop`, `hasSaved`,
`saved`; `repeat(id, n)`, `repeatSave(id, n)` and `repeatDefault(id)` send the three lines.
`client.js` gives each through `requestOperation("repeat", …)` and counts the `status`
replies in `state.statusCount`, so that a screen can wait for the first `status` after a
reply.

### The bar (`index.html`, `screens/show.js`, `style.css`)

```html
<div class="now-words">
<p class="label">Now playing</p>
<p id="now" hidden>…</p>
<div id="now-bar" hidden></div>
<p id="playing">-</p>
</div>
```

`.now-words` takes the panel's width (`flex: 1 1 auto`). `drawBar(state)` in `show.js`:

- Whether it shows (7.1): `status` not null, no error, `playing` `"all"` or the id of a
  folder of the list, `animation` in the whole list.
- What it shows: `{id, file, kind}` of the animation and, from `status`, `hasRepeat`,
  `hasSaved`, `repeat`, `saved`. It is kept as it is, the animation and `saved` included,
  while the field has the focus, within a second after it lost it, or while a line of the
  bar is out; otherwise it follows `status`. It is built anew only when the key of what it
  shows changes; the disabled states are set at every draw.
- Line 1: the row menu's actions of that animation, `actions(animation)` without `Move up`
  and `Move down` and without `Edit`, each a button with its first word (`Ignore`,
  `Restore`, `Select`, `Delete`) and the accessible name of the menu's label with the id and
  the file after its first word; or the note, as `External storage is read-only.` or
  `This software allows no change.`.
- Line 2: `Edit` when the menu offers it; then, with `hasRepeat`, `#repeat-this` and
  `#repeat-count`. Line 3, with `hasSaved`: `#repeat-save` and `#repeat-default`.
- `Select` from the bar: `opened = ""`, `filters.reveal(animation)` sets a filter that
  hides it back to All, `selection.enter(id)`, a draw, then the window is scrolled so that
  the row's top stands 8 px below the frozen panel's bottom (or the top band's, while the
  panel does not stick).
- The repeat line: `sendRepeat(kind)`; the text checked 1 to 65,535 (`A repeat is 1 to
  65,535.`, the field showing the value in force); the line goes through the client;
  `out` holds it while it is out; the reply's sentence waits for the first `status` after
  it (`statusCount`), and a refusal or a missing reply is said at once. `main.js`'s
  `focusout` calls `show.fieldLeft(event.target)`, which notes the time the field lost the
  focus.
- `messages.js`: `ofRepeat(file, id, status)`, `ofRepeatSaved`, `ofRepeatDefault`, the
  sentences of 8.5 and 8.7; `REFUSALS` gives `repeat` lines their own `stale`, `in-use` and
  `no-space` sentences.

### The frozen top

- CSS: `#now-panel.frozen {position: sticky; top: var(--bar-top); z-index: 2; background:
  #0f1630;}`, the panel's colour over the midnight made opaque. The top band is z-index 3,
  the tabs 4, the menu and a lifted row 5, the messages 6.
- `freeze()` in `show.js`, called at every draw and on `resize`: the panel sticks while the
  Animations screen is shown, the body is not `typing`, and `innerHeight - band - panel -
  tabs >= 80`, the band's height read from `getComputedStyle(body, "::before")`. While it
  sticks, the root's `scroll-padding-top` is the band and the panel, so that a field
  brought into view stops below it.
- `reorder.js`'s `edges()` takes the frozen panel's bottom as the top edge, and the lifted
  row's top is kept at or below it.

### The bar's look

`#now-bar` is a column of lines `.bar-line`, 8 px apart, 4 px above and below; a line is a
row of 48 px, its items 8 px apart; its buttons `width: auto; margin: 0; padding: 8px 10px`;
`#repeat-count` `width: 5em; margin: 0; padding: 8px 14px; font-variant-numeric:
tabular-nums`; a note is 48 px high in the panel's lesser colour. A bar of two lines is two
lines whatever it holds.

## The tests

- `tests/core/test_repeat.py`: every point of the core's definition of done, against
  sessions of the test host, the reference player where it states the rules, and the
  drive's helpers of `tests/core/test_drive.py`.
- `tests/core/test_status.py`, `tests/core/test_commands.py`: the exact replies with the
  three members; `tests/core/test_docs.py` and `tests/core/test_drive.py`: the memory.
- `tests/emulator/test_tool.py`: the three forms of the command tool.
- `tests/firmware/test_storage.py`: `install-show` keeps `repeats.txt`, `read-show`
  copies it.
- `tests/app/test_now_bar.py` with scenarios of its own, against the emulator and
  stand-ins; `tests/app/test_frozen.py` for the frozen top; `tests/app/test_look.py` for
  the bar's height and look; the scenarios that press `Select` by its words press the list
  head's; the lists of the panel's buttons follow the bar.

## The documents

`docs/commands.md` (the table, the three forms with their refusals, the members, the error
codes), `docs/core.md` (the memory, the file), `docs/show.md` (the counts and
`repeats.txt`), `docs/emulator.md`, `docs/firmware.md` (`install-show` and `read-show`),
`docs/android-app.md` (the bar, the frozen top, the lines, the messages, the check on a
phone, what is verified and open), `agent/vocabulary.md` (the command), and
`docs/decisions.md` (the commands' bullet and the change log).
