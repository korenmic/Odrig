# Design: a playlist of everything by default

## Overview

The player of the core gets a second thing it can play beside an item: the playlist, which
is every animation item of the show in turn. The playlist is what plays by default. Each
animation has a turn whose length follows from the length of its loop and from three
numbers of the show file, two of the item and one of the show. `play <id>` of an animation
becomes a jump inside the playlist, and `play all` starts it from the top.

Everything is in the core, so the emulator and every firmware get it by being built
again. The show file gains three optional members, which the two converters learn to
read.

## What this design relies on

Read in `core/src/` and in the tests, as they are after seed 07 and seed 11:

| | Fact | Where |
|---|---|---|
| P1 | The player holds the position of the item it plays, `playing`, and the time its play began, `zero`, which is the grid time of the first refresh after the play was asked for. What is on the LEDs is worked out anew at every refresh from the time since `zero`. | `core/src/player.cpp`, `advance` |
| P2 | A cycle is worked out by division: its turns are all `seconds` long. An animation item played by itself is one turn without end. | the same |
| P3 | The length of an animation's loop, the sum of the durations of its frames, is known for every file after the start: `FileInfo.total_ms`. A file that is uploaded gets it from its check. | `core/src/core_state.h`, `core/src/upload.cpp` |
| P4 | An item of the table has 16 bytes. Of an animation item, `seconds` and `count` are not used. | `core/src/core_state.h`, `ItemInfo` |
| P5 | `play` is answered in `command_answer`, with the id read as a number of 1 to 65,535 digits. `status` writes `playing` with `id_or_null`. | `core/src/commands.cpp` |
| P6 | When the show is changed, the player is told: `player_releases_file`, `player_file_replaced`, `player_item_leaves`. | `core/src/player.h`, `core/src/content.cpp` |
| P7 | The core writes `show.json` as one line, the members in a fixed order, `start` only when the show has one. | `core/src/content.cpp`, `docs/show.md` |
| P8 | The reference player reads the show with `odrig.show` and plays as the core does; the core's tests compare the two line by line. | `tests/core/support.py`, `ReferencePlayer` |
| P9 | `pack` copies `show.json` into the installed show as it is, after reading it. | `odrig/pack.py`, `converter/lib/pack.js` |
| P10 | The command tool sends the words of `play` as they are typed. | `odrigctl/cli.py` |
| P11 | The emulator's page writes `playing` of the `status` event as text. | `emulator/web/app.js` |

## The show file

`show.json` stays at version 1. The members that are new are optional, and a file without
them means what the rest of this design says for their absence.

| Where | Member | Type | Meaning |
|---|---|---|---|
| top | `min_seconds` | integer, 1 to 65,535 | How long an animation without `repeat` plays at least. 30 when absent. |
| an animation item | `repeat` | integer, 1 to 65,535 | The number of loops of its turn. |
| an animation item | `max_seconds` | integer, 1 to 65,535 | The longest its turn lasts. |

A cycle item has exactly `id`, `cycle` and `seconds`, as today. The checks are the ones
the other members have: a value that is no whole number written in digits, or outside its
limits, or a member of this kind on a cycle item, is `show-malformed`.

The version is not raised: no file that is valid today changes its meaning in a way a
reader could mistake, except that a show without `start` now plays, which is the purpose.
A firmware from before this seed refuses a show that has one of the new members, as
`show-malformed`, and says so in `status`.

The core writes the file with the members in this order, each optional one only when
the show has it:

```json
{"version":1,"brightness":128,"min_seconds":45,"items":[{"id":1,"file":"hello.odrg","repeat":3,"max_seconds":120},{"id":2,"file":"dvd.odrg"},{"id":4,"cycle":[2,1],"seconds":15}],"start":4}
```

## The turn

For an animation whose loop is L milliseconds long:

```
loops = repeat                               when the item has repeat
loops = ceil(min_seconds * 1000 / L)         otherwise; at least 1
turn  = loops * L
turn  = min(turn, max_seconds * 1000)        when the item has max_seconds
```

So an animation of 4 seconds without numbers of its own plays 8 loops, 32 seconds: at 30
seconds it is in its eighth loop and plays it to the end. An animation of exactly 10
seconds plays 3 loops and ends at 30 seconds. An animation of 45 seconds plays once. L is
at least 1, and every product fits 64 bits.

## The playlist in the player

`playing` gets a second value that is no position of the item table, `kPlaylist`, beside
`kNothing`. While it holds that value, three more fields say where the playlist is:

```cpp
uint32_t turn_item;     // the position of the animation whose turn it is
uint64_t turn_number;   // counts the turns, so that each one opens its file anew
// zero: the moment the turn began, as for an item
```

At a refresh, with `elapsed` the time since `zero`:

1. While `elapsed` is at or above the turn of `turn_item`: `zero` moves on by that turn,
   `turn_item` becomes the next animation item after it in the table, the first one after
   the last, and `turn_number` counts up. A turn so begins exactly where the one before
   ended, however late the refresh is.
2. Before that, when `elapsed` is at or above the sum of the turns of all animations, the
   whole passes are taken off it at once, by division. A host that asked for no refresh
   for a long time costs one walk over the table and not one step for each turn it
   missed.
3. The loop inside the turn and the place inside the loop are worked out from the rest,
   as for an item today, and the file is opened for `(turn_item, turn_number, loop)`.

`shown` is `turn_item`. With the LEDs off the refreshes go on and so does the playlist.

`player_play_all(core, from)` starts the playlist: it closes the open file, sets
`playing` to `kPlaylist` and `turn_item` to the animation given, and leaves `zero` to the
next refresh, as `player_play` does.

`player_start`: an invalid show plays nothing. Otherwise a `start` that names a cycle
plays it; a `start` that names an animation starts the playlist from it; without `start`
the playlist starts from the first animation item, when the show has one.

No memory is added. The item table keeps its 16 bytes for an item: of an animation item,
`seconds` holds `max_seconds` and `count` holds `repeat`, each 0 when the show gives
none. The core object grows by the three fields above and by `min_seconds`; it stays
under its 4,096 bytes, which a `static_assert` holds.

## The commands

```
play <id>     an animation: the playlist from that animation
              a cycle: the cycle, as today
play all      the playlist from its first animation
```

`play all` is read before the id: the word `all` alone. A show without an animation
answers it with `unknown-id`, an invalid show with `show-invalid`, and a third word is
`bad-argument`, all as `play <id>` is answered.

`status`: `playing` is written as `"all"` while `playing` is `kPlaylist`. Nothing else of
the reply changes.

| Command | Effect, in `docs/commands.md` |
|---|---|
| `play <id>` | Plays the animation with that id, from its first frame, and then goes on with the playlist; plays the cycle with that id. |
| `play all` | Plays the playlist, from its first animation. |

## The show changed while the playlist plays

The three calls of P6 learn the playlist:

- **An item is added** at the end of the table. The playlist meets it when its turn
  comes. When nothing plays, the playlist starts from its first animation: after an
  upload, something plays whenever the show is valid and has an animation.
- **An animation gets another file** (`player_file_replaced`). When it is the one whose
  turn it is, the turn begins again: `zero` is left to the next refresh and
  `turn_number` counts up. Otherwise nothing changes for the player.
- **An item leaves** (`player_item_leaves`). When it is the animation whose turn it is,
  the playlist goes on with the animation after it, which begins its turn at the next
  refresh; when no animation is left, nothing plays. When it is the cycle that plays,
  the playlist starts from its first animation. Every other position the player holds
  follows the table, as today.

`docs/commands.md` said of `remove`: "If the item is playing, playback stops and the LEDs
go dark." That sentence becomes the three cases above.

## The reference player

`ReferencePlayer` of `tests/core/support.py` gets the same model, written from this page
and not from the core's source: the turn, the playlist with its three fields, the start,
the two commands, `status`, and the three changes. `odrig.show.Item` gains `repeat` and
`max_seconds`, and `Show` gains `min_seconds`.

## The converters

`odrig/show.py` and `converter/lib/show.js` accept the three members and check them as
the table above says; an item keeps `repeat` and `max_seconds` as `None` or `null` when
absent, and the show keeps 30 for an absent `min_seconds`. `pack` needs no change (P9).
The JavaScript suite's lists of whole and broken shows gain the new cases, and the two
readers are compared on them as on the others.

## The emulator, the command tool and the shows

- The page shows `playlist` where `playing` is `"all"`, and the file name of the
  animation on the LEDs beside it.
- The command tool needs no change (P10). Its usage text names `play all`.
- `shows/demo-20/show.json` becomes two animation items and nothing else. The tests and
  the pages that run the demo show expect the playlist: Hello world and DVD bounce, each
  for the turn its loop gives it, where they expected a cycle of 15 seconds.
- `shows/example/show.json` is not changed: the bench show stays a cycle, and with it
  every test of cycles.

## The firmware

No source of the usermod changes. The firmware is built again with the core and
flashed. A board test installs a show of two animations without `start`, at brightness
32, and reads `status` over USB: `"playing":"all"`, the first animation at power-on, and
the second once the first's turn is over. The session of commands that the board suite
compares with the emulator gains `play all` and a `play <id>` of an animation.

## Tests

- `tests/converter/` and `converter/tests/`: the members at and beside their limits, on
  an animation and on a cycle, in both readers; `pack` with them.
- `tests/core/`: the core against the reference player for the cases of the seed's
  definition of done, each as a script of polls and commands: the default turn for loops
  of 4, 10 and 45 seconds; `repeat` 1 and 3; `max_seconds` that cuts a loop; `min_seconds`
  of the show; three animations in order and around; late polls and a long gap; `off`
  and `on` during a turn; `play <id>`, `play all`, a cycle as `start` and by `play`;
  `status` at each step; an upload of a new item, of a first item into an empty show, and
  onto the animation whose turn it is; the removal of the animation whose turn it is, of
  another, of the last, and of the cycle that plays; the file the core writes. The
  memory test, with its number.
- `tests/emulator/`: the demo show as the playlist; the page's text; `play all` through
  the tool and over HTTP.
- `tests/board/`: as "The firmware" says.
- The documents' tests of each suite, for what the pages say.

## Documents

`docs/show.md`: the members, "The turn of an animation", "The playlist", and what a
change does. `docs/commands.md`: the table, `play`, `status`, `remove`. `docs/core.md`:
the player and the memory. `docs/emulator.md` and `agent/getting-started.md`: the demo
show as it plays now. `docs/firmware.md`: what the board showed. `agent/animation-guide.md`
and `agent/vocabulary.md`: the turn, the playlist, and that there are ten commands with
`play all` counted with `play`. `docs/decisions.md`: a line in the change log.

## Risks

- **Every test that runs the demo show changes.** They are found by running the suites;
  none is listed here.
- **`play <id>` changes its meaning**: an animation no longer loops for ever. The owner
  ruled so. Whoever wants one animation only installs a show with one animation, or
  gives it a cycle of its own.
- **A show with many short animations and a long gap without refreshes**: bounded by
  step 2 of the playlist.
- **An old firmware and a new show file**: refused as malformed; the documents say that
  both are installed together.
