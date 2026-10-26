# Design: Aurora Glass UI and playlist revamp

## What this design relies on

- The playlist is walked by `next_animation` (`core/src/player.cpp`), which takes the
  positions of the item table and then the drive's places in their order. The first
  animation is found by `player_first_animation` and `player_first_in_playlist`.
- The core writes its files through the chunk buffer and renames a `.part` file into
  place (`show.part`, `mapping.part`). It reads a second file beside the one that plays
  with `read_at`, through the checker's `FileSource`, which the drive's check, the cleanup
  of `remove many` and an upload's check share; `drive_check_yields` lets the drive's
  check begin its file again when something else took the source.
- A host requires `read_at` to go on where its last call ended, or to begin at 0.
- The core's memory is taken at startup in blocks (`arena_take`); the test host prints
  them and the suites count them.
- The diagonal is `core/assets/mapping-diagonal.json`, encoded by the converter into
  `core/src/diagonal_data.h` by `core/diagonal.py`, decoded by `decode_diagonal`
  (`core/src/mapping_control.cpp`) into the core's pixel buffer.
- `app/www/` is one page with a section for each screen, a module for each screen, and
  one serialized request stream, `client.js`.

## The order file

`order.txt`, in the folder of the show, written only by the core:

```
odrig-order 1
i 12
x sunrise.odrg
i 3
```

The first line is the header. Every further line is an entry and ends in a line feed:
`i <id>`, the id in decimal from 1 to 65,535 without a leading zero, or `x <name>`, the
file name of an external animation as the drive gives it, 1 to 127 bytes, no line feed
and no zero byte. The core keeps the first 512 entries; a malformed line is no entry and
takes no place; when the header is not that line the file names nothing. The core's own
names gain `order.txt` and `order.part`.

### Keys

Each animation that can play has a key, and the playlist goes in the order of the keys:

| The animation | Its key |
|---|---|
| named by entry k of the file | k, 0 to 511 |
| an internal animation the file does not name | 0x10000 + its position in the item table |
| an external animation the file does not name | 0x20000 + its place in the drive's list |

The keys are kept in one block of the core, taken at startup for a host whose storage can
be changed, after the tables of the show: a `uint16_t` for each item of the item table
and, for a host with a drive, a `uint16_t` and a one-byte hash of its name for each of the
256 places. A stored 0xFFFF means "not named"; the key of such an animation is computed
from its position, so removing an item shifts the stored values with the item table and
nothing else.

```cpp
// core/src/order.h
const uint32_t kOrderMost = 512;          // entries the file holds at most
const uint16_t kOrderUnnamed = 0xFFFF;
uint32_t order_key(const Core &core, uint32_t position);   // position: item or kDriveBase + place
void order_start(Core &core);                              // startup: the internal keys
void order_drive_found(Core &core);                        // drive_touch: places counted
bool order_drive_step(Core &core);                         // one step of the drive's part
void order_reload(Core &core);                             // the whole file again, at once
uint32_t order_get(const Core &core, uint32_t from, Reply &reply);
uint32_t order_move(Core &core, uint32_t revision, uint32_t id, uint32_t before, Reply &reply);
```

### Reading it

One reader takes the file's bytes line by line and gives each entry to two matchers:

- **internal**: `i <id>` gives entry k to the animation item with that id, when it has no
  key yet. This runs at startup, in `order_start`, which reads the file through the
  checker's source before the first refresh, and again at `order_reload`.
- **external**: `x <name>` hashes the name (FNV-1a, its low byte) and looks among the
  places with that hash and no key yet; the host's `drive_name` confirms the whole name.
  This runs when a drive is found, as the first part of the drive's check, and again at
  `order_reload`.

When a drive is plugged in, `drive_touch` counts its places with `drive_name` into a
buffer of 128 bytes, hashes each name and clears each place's key, and marks the drive's
part of the order as due (`order_drive_found`). The drive's check then reads `order.txt`
before it checks any file of the drive: one step takes the bytes of one read of at most
512 bytes, keeps an unfinished line in the core object (130 bytes), and ends the part at
the end of the file. Only then do the drive's files join the playlist, each with its key
already set. When the source is taken meanwhile, `drive_check_yields` begins the part
again from the start. A pulled drive keeps its places' keys until the next drive is
counted, so that the playlist goes on after the animation that left, in the saved order.

`order_reload` reads the whole file at once through the checker's source, after
`drive_check_yields`, clears every key and sets both kinds; the drive's part is then no
longer due. It runs after a move, and after an upload has added an item, so that an id
named by an old entry takes that entry's place at once as it would after a restart. Both
run in a command, where the checker is free: a move is refused while an upload is open or
the startup check runs, and an upload's own check has ended before it is installed.

### The playlist

`next_animation(position)` gives the animation that plays with the smallest key above the
key of `position`, or, when there is none, the one with the smallest key; `kNothing` when
none plays. `player_first_animation` gives the internal one with the smallest key, and
`player_first_in_playlist` the one with the smallest key of all. Whole rounds and the
lengths of turns do not depend on the order. A move changes keys only, so the turn in
progress, its time, power and brightness stay; the next turn follows the new order.

### `order get`

```
order get
{"ok":true,"ids":[3,60002,1],"next":null,"revision":2805384113}
```

The ids are those of the animations `list` lists, in key order, from the position `<from>`
(0 to 65,535, 0 when left out), as many as fit, with `next` as in `list`. The revision is
the CRC-32 of, for each listed animation in the order `list` gives them, its id as two
bytes and its key as four, low byte first. It is refused as `list` is: `show-invalid`,
and `busy` until the startup check has ended.

### `order move`

```
order move 2805384113 1 3
{"ok":true}
```

The words are read first (`bad-argument`); then `show-invalid`; `busy` while the startup
check runs or an upload is open; `unknown-id` when the id or the before-id is no listed
animation; `in-use` when one is a cycle; `order-conflict` when the revision is not the
current one; nothing written when the animation already stands right before `<before>`,
or last for `end`, or `<before>` is itself; `storage-error` without storage that can be
changed.

The new file is written into `order.part` while the old one is read through the checker's
source: the header; every entry of the old file but those of the moved animation and those
of internal ids that do not exist, with the moved animation's entry written before the
entry of `<before>`; then every listed animation the old file did not name, internal
ones first, in key order, again with the moved one before `<before>`; and the moved one
last for `end`. At most 512 entries are written. Then `order.part` is renamed onto
`order.txt`, which is where the order changes, and `order_reload` sets the keys. A failed
call before the rename removes `order.part` and answers `storage-error`; the keys stay.

```
1  write order.part
2  rename order.part -> order.txt              <-
```

Startup removes an `order.part` that is there, found with a `read_at` of one byte as
`mapping.part` is, so a folder without one gets no new storage call.

## `external` in `list`

An internal animation item gains `,"external":false` after `ignored`, a drive's animation
`,"external":true` after `bytes`. `listed_size` and the drive's size count them; the
longest item of a drive still fits a reply with the head and the tail.

## The test animations

`core/assets/mapping-snakes.json` has 20 frames of 1,000 ms on 60 x 60: frame n is white
at (3n-2 + (y-1) / 20, y) for y from 1 to 60, in whole-number division, and black elsewhere.
`core/snakes.py` writes it, encodes it with the converter into `core/src/snakes_data.h`
(`kSnakes[]`), and `--check` compares both with what it would write. `decode_snake(core, n)`
opens the embedded file as `decode_diagonal` does and decodes records 1 to n into the
pixel buffer.

`mapping test snake <n>` takes the entry rules of `mapping test on`. The core keeps
`mapping_snake`, 0 for the diagonal. Entering a test while one shows does not save the
selection again; the same test again is idempotent. `mapping get` writes
`,"snake":<n>` or `,"snake":null` after `test`. `mapping_test_stop` clears it.

## Routes

The core's one parser takes the new lines; the transports carry them. `odrigctl` gains the
forms `order get [FROM]`, `order move REV ID BEFORE` and `mapping test snake N`. The
emulator and the firmware need no change: their storage functions take any name of the
core, and `order.part` fits the firmware's 32 characters.

## The app

### Files

| File | What it holds |
|---|---|
| `index.html` | the top bar, four sections `animations`, `upload`, `settings`, `target`, the message, the question, the menu and the four tabs |
| `style.css` | the Aurora Glass tokens and every rule |
| `main.js` | the tabs, back, the keyboard's room, the long-press rule |
| `client.js` | the request stream; `state.order`, `orderGet`, `orderMove`, `mappingTest`, `testState` |
| `commands.js` | `orderGet`, `orderMove`, `mappingTestSnake`, the replies' checks |
| `screens/show.js` | Animations: now playing, power, brightness, capacity, the list, rows and menus |
| `screens/selection.js` | the selection mode and the bulk and single deletion |
| `screens/reorder.js` | the long press, the drag, the placeholder, scrolling, the move |
| `screens/tests.js` | the Tests group and the active test |
| `screens/storage.js` | Upload: choosing, fitting, the part, making, the preview, uploading |
| `screens/mapping.js` | Settings: the test checkbox and the mapping editor |
| `screens/target.js` | Target |

### The order in the client

After every complete list the client asks `order get` and its further parts, and keeps
`state.order = {ids, revision}` once every part has come and its ids are exactly the
listed animations' ids; otherwise it asks for the list again. An `unknown-command` (an
older target) gives `state.order = null`, and the list stays in the list's order with
dragging off. The rows are drawn in `state.order.ids` order.

`client.orderMove(id, before)` sends `order move <revision> <id> <before>` with the
revision the rows were drawn from, on the one request stream, and asks for the list and
the order again whatever the outcome.

### Dragging

`reorder.js` listens to `pointerdown` on the list. A press that stays within 8 pixels for
450 ms lifts the row: the row follows the pointer, a placeholder of its height takes its
place among the other rows, and a non-passive `touchmove` listener stops the page from
scrolling under the finger. While the pointer is within 56 pixels of the top bar or of the
tabs, the page scrolls by up to 12 pixels each animation frame. `pointerup` drops the row
before the row after the placeholder, or at the end; `pointercancel` and Escape put it back.
A press that moves before 450 ms is a scroll, and a short press is a tap that plays.
Move up and Move down compute the same `before`.

### Tests and Settings

The checkbox's value is kept in `localStorage` under `odrig.tests`. The Tests group
has the 21 entries in a grid of buttons; a press sends `mapping test on` or
`mapping test snake <n>` and then `mapping get`. The client asks `mapping get` every two
seconds while Animations shows and the newest status says nothing plays on a valid show,
which is the case during a test, and always after a test command; `state.test` is
`null`, `"diagonal"` or the snake's number. The now-playing area shows the active test
with Stop test (`mapping test off`).

### The look

```css
:root {
  --back: #050816;            /* midnight */
  --panel: rgba(18, 26, 56, 0.78);
  --edge: rgba(122, 214, 255, 0.22);
  --text: #eef3ff;
  --lesser: #b9c4e4;
  --teal: #45e0d2;
  --violet: #b49cff;
  --on-accent: #04121a;
}
```

The page's background is `--back` with two fixed radial gradients of teal and violet at
low strength. Panels are `--panel` with an `--edge` border, a radius of 18 pixels and a
soft outer glow. Primary actions are `--teal` with `--on-accent` text. The `in` badge is
teal on its panel, the `ex` badge violet. Every text keeps 7:1 against what lies behind
it, panels composited onto `--back`.

## Verification

- Core: `tests/core/test_order.py` and `tests/core/test_snakes.py`; the earlier suites
  updated for `external` and the order block.
- Routes: `tests/emulator/test_order.py`, `tests/mapping/test_hosts.py`.
- App: the scenarios of `tests/app/page/scenarios/` and their tests rewritten for the four
  tabs; new ones for menus, reordering, the Tests group and the layouts.
- Memory: the target with a show of 100 items, with and without a drive, stays under
  131,072 bytes; docs/core.md's table gains the block.
