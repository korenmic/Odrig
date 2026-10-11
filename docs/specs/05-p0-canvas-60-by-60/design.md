# Design: Canvas 60 by 60 (seed 05)

## Overview

The target is a canvas of 60 x 60 on twenty legs whose strips stand upright. Five things
change for it:

1. **The mapping file format** gains column legs: a top-level `height` in place of `width`,
   `columns` in place of `rows`, and a `first_led` of `bottom` or `top`. Three readers
   learn it: the converter's (`odrig/mapping.py`), the core's (`core/src/mapping.cpp`) and
   the page's (`emulator/web/layout.js`). Row-leg files are read as before.
2. **The target file** `mapping/legs-20.json` takes the place of `mapping/legs-10.json`,
   and `shows/demo-20` the place of `shows/demo-10`. Tests, the benchmark and the documents
   move from 60 x 30 to 60 x 60.
3. **The page** draws upright legs: the LEDs view with a band of leg labels along the
   canvas, and the mapping view with the board, twenty lines in two channels, and twenty
   snakes.
4. **The firmware** gets twenty LED outputs: four through WLED's RMT driver and sixteen
   through the parallel driver, which a small patch to WLED switches to the sixteen-lane
   form its LED library already has. Whether that works is proven first, on the board.
5. **`docs/mapping.md`** gets its drawings and tables from a tool, `python -m odrig.mapdoc`,
   and a test compares the page with the mapping files.

The host interface of the core does not change, so the emulator's Python code, the command
tool and the usermod's way of making outputs need no change for column legs: they take the
legs from the core.

Decisions taken where the seed and the documents left a point open are in `docs/drifts.md`
under "Seed 05".

## What this design relies on

The code of seeds 01 to 04 was read for this design. A task that finds it different
follows the code and records the difference in `docs/drifts.md`.

| Where | What is there today |
|---|---|
| `odrig/mapping.py` | `read`, `loads`, `Leg(leg, pin, first_led, rows)`, `Mapping(width, height, legs)`. The only reader of a mapping file in Python; `cli.py`, `pack.py`, the generators and `firmware/fwtool/storage.py` use it. |
| `core/src/mapping.cpp` | Reads `mapping.json` twice through the streaming JSON reader. The first reading checks the form and counts legs and rows; then the tables are taken from the host; the second reading checks legs against each other and fills `led_pixel`, the position in pixel order of the pixel of every LED. |
| `core/include/odrig_core.h` | `odrig_leg` has the leg's number, pin, LED count and LED bytes. Nothing in it says row or column. |
| `emulator/*.py`, `odrigctl/` | Neither reads a mapping file. The emulator takes the legs from the core and serves `mapping.json` byte for byte. |
| `emulator/web/layout.js` | `read`, `position`, `find`, `rows`, `path`, `runs`, `side`, `tracks`, `fit`, `wires`, `chain`: all written for rows. `fit` has three arrangements: the LEDs view, the mapping view with the board beside the canvas, and with the board below it. |
| `emulator/web/view.js` | Draws labels, chains, the board and the lines from what `layout.js` gives. Twelve leg colours, used in turn. |
| `emulator/web/board.js` | The two rows of pin labels of the board. |
| `firmware/usermod/odrig_leds.cpp` | Makes one output for each leg the core lists, asking for RMT; WLED gives RMT to the first four and its parallel driver to the next eight. |
| `firmware/usermod/odrig_usermod.cpp` | `loop()` asks the core for a refresh in every pass until one is produced, and sends it when the outputs can take data. |
| `firmware/usermod/odrig_probe.cpp` | The probe build's report: outputs with their driver and the CRC of what they hold, times of requests and sends, the limiter. |
| `firmware/fwtool/wled.py` | Before a build: WLED's files back to the pinned commit, then every `firmware/patches/*.patch` with `git apply`. The folder holds no patch. |
| `docs/mapping.md` | Says its drawings and tables are generated. No tool that does it is tracked. |
| `tests/core/support.py` | `mapping_texts()` gives every `mapping/*.json` and the made-up mappings to the suites of the core and of the emulator; `led_pixels` and `ReferencePlayer` are the reference. |

## The mapping file format

This section is what `docs/mapping.md` states after this seed. Seeds 06 and 07 build on
it.

### The two kinds

One JSON file describes one physical build. It is a row-leg file or a column-leg file.

```json
{
  "version": 1,
  "width": 60,
  "legs": [
    {"leg": 1, "pin": 1, "first_led": "right", "rows": [6, 5, 4]},
    {"leg": 2, "pin": 2, "first_led": "right", "rows": [3, 2, 1]}
  ]
}
```

```json
{
  "version": 1,
  "height": 60,
  "legs": [
    {"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1, 2, 3]},
    {"leg": 2, "pin": 2, "first_led": "bottom", "columns": [4, 5, 6]}
  ]
}
```

| Member | Row-leg file | Column-leg file |
|---|---|---|
| `version` | 1 | 1 |
| `width` | The number of LEDs in every row, 1 to 65,535. | Absent. |
| `height` | Absent. | The number of LEDs in every column, 1 to 65,535. |
| `legs` | One entry for each leg. | One entry for each leg. |
| `leg` | The leg's number, 1 to 255. | The same. |
| `pin` | The data pin (GPIO number), 0 to 255. | The same. |
| `first_led` | `"left"` or `"right"`: the side of the leg's first row where its first LED sits. | `"bottom"` or `"top"`: the end of the leg's first column where its first LED sits. |
| `rows` | The canvas row (y) of each strip, in chain order. | Absent. |
| `columns` | Absent. | The canvas column (x) of each strip, in chain order. |

The kind of a file is told by its top level: a file with `width` and without `height` is a
row-leg file, a file with `height` and without `width` is a column-leg file. Nothing else
is a mapping file.

| | Row-leg file | Column-leg file |
|---|---|---|
| Strip length | `width` | `height` |
| Canvas width W | `width` | the number of columns of all legs |
| Canvas height H | the number of rows of all legs | `height` |
| What must appear exactly once | every y from 1 to H | every x from 1 to W |
| LEDs of a leg | W times its rows | H times its columns |

### Rules

A mapping file is valid when all of these hold. The first four are as before.

1. It is read as strictly as a JSON frames file: UTF-8 without a byte-order mark, exactly
   one JSON value, no member named twice in one object, integers written without a
   fraction and without an exponent.
2. The top level is an object. `version` is 1.
3. `legs` is an array of one or more objects. Every `leg` is an integer from 1 to 255 and
   no two legs have the same number. Every `pin` is an integer from 0 to 255 and no two
   legs have the same pin.
4. W * H is at most 65,534.
5. The top level has exactly the members `version`, `legs` and one of `width` and `height`.
   That member is an integer from 1 to 65,535.
6. In a row-leg file every leg has exactly the members `leg`, `pin`, `first_led` and
   `rows`, and `first_led` is `"left"` or `"right"`. In a column-leg file every leg has
   exactly the members `leg`, `pin`, `first_led` and `columns`, and `first_led` is
   `"bottom"` or `"top"`.
7. `rows` or `columns` is an array of one or more integers. A leg may have any number of
   strips, and the legs need not have the same number.
8. The strips of all legs together hold every number from 1 to their total exactly once.

So these are invalid: both `width` and `height`, or neither; a leg with `rows` in a
column-leg file, with `columns` in a row-leg file, with both or with neither; `"left"` in a
column-leg file and `"bottom"` in a row-leg file.

### Reasons

No reason name is added. A file that breaks a rule is `mapping-malformed`, and a file that
does not exist is `mapping-missing`, for both kinds and in every reader. The core reports
the name alone, as `docs/reasons.md` has it under "The core". The converter adds a detail
for people.

### Where each LED is

For a row leg the rule is the one `docs/mapping.md` has. For a column leg whose `columns`
has C entries, with H the strip length, and for LED number n from 1 to H * C:

- s = (n - 1) div H is the position of its column in `columns` (0 to C - 1), and
  i = (n - 1) mod H is how far along that column it is.
- x = `columns[s]`.
- The column starts at the `first_led` end when s is even and at the opposite end when s
  is odd.
- y = 1 + i when the column starts at the bottom, and y = H - i when it starts at the top.

Both rules are one rule with the two axes exchanged: a strip has a place across the
strips, `rows[r]` or `columns[s]`, and LEDs along it; the strips of a leg alternate their
direction along the chain.

### What seeds 06 and 07 take from this

- **Seed 06** writes a second reader. It follows the rules above and the order of the
  checks under "The converter" below, and it reports `mapping-malformed` and
  `mapping-missing`. It gives the same things as the Python reader: the kind, W, H, and for
  each leg its number, pin, `first_led`, strips and LED count.
- **Seed 07** needs the canvas only: the core holds W and H after `read_mapping` whatever
  the kind, an uploaded file is judged against them, and the host interface this seed
  leaves is the one seed 04 left.

## The target file and what goes

`mapping/legs-20.json`, with a line feed after the last brace:

```json
{
  "version": 1,
  "height": 60,
  "legs": [
    {"leg": 1, "pin": 1, "first_led": "bottom", "columns": [1, 2, 3]},
    {"leg": 2, "pin": 2, "first_led": "bottom", "columns": [4, 5, 6]},
    {"leg": 3, "pin": 3, "first_led": "bottom", "columns": [7, 8, 9]},
    {"leg": 4, "pin": 4, "first_led": "bottom", "columns": [10, 11, 12]},
    {"leg": 5, "pin": 5, "first_led": "bottom", "columns": [13, 14, 15]},
    {"leg": 6, "pin": 6, "first_led": "bottom", "columns": [16, 17, 18]},
    {"leg": 7, "pin": 7, "first_led": "bottom", "columns": [19, 20, 21]},
    {"leg": 8, "pin": 8, "first_led": "bottom", "columns": [22, 23, 24]},
    {"leg": 9, "pin": 9, "first_led": "bottom", "columns": [25, 26, 27]},
    {"leg": 10, "pin": 10, "first_led": "bottom", "columns": [28, 29, 30]},
    {"leg": 11, "pin": 11, "first_led": "bottom", "columns": [31, 32, 33]},
    {"leg": 12, "pin": 12, "first_led": "bottom", "columns": [34, 35, 36]},
    {"leg": 13, "pin": 13, "first_led": "bottom", "columns": [37, 38, 39]},
    {"leg": 14, "pin": 14, "first_led": "bottom", "columns": [40, 41, 42]},
    {"leg": 15, "pin": 15, "first_led": "bottom", "columns": [43, 44, 45]},
    {"leg": 16, "pin": 16, "first_led": "bottom", "columns": [46, 47, 48]},
    {"leg": 17, "pin": 17, "first_led": "bottom", "columns": [49, 50, 51]},
    {"leg": 18, "pin": 18, "first_led": "bottom", "columns": [52, 53, 54]},
    {"leg": 19, "pin": 21, "first_led": "bottom", "columns": [55, 56, 57]},
    {"leg": 20, "pin": 47, "first_led": "bottom", "columns": [58, 59, 60]}
  ]
}
```

`mapping/legs-2.json` keeps its bytes. `mapping/legs-10.json` and `shows/demo-10/` are
removed in one task, after every test and tool that named them has moved to the target
file, so that every commit passes its suites.

What named them, found by searching the tracked files:

| Where | What changes |
|---|---|
| `core/Makefile` | The benchmark clip is made with `mapping/legs-20.json`. |
| `tests/converter/` | `test_mapping.py`, `test_generators.py`, `test_import_timeline.py`, `test_show_pack.py`. |
| `tests/core/` | `test_mapping.py`, `test_memory.py`, `test_playback.py`, `test_cycle.py`, `test_startup.py`, `test_decoder.py` (a size of its list). |
| `tests/emulator/` | `support.py`, `test_layout.py`, `test_board.py`, `test_demo.py`, `test_docs.py`, `test_realtime.py`. |
| `tests/firmware/` | `test_storage.py`, which takes the ten-leg file for a canvas of another size. |
| `tests/board/` | `support.py`, `test_probe.py`, `test_fps.py`, `test_measure.py`. |
| Documents | `docs/mapping.md`, `docs/emulator.md`, `docs/firmware.md`, `docs/converter.md`, `docs/core.md`, `docs/format.md`, `docs/decisions.md`. |

## The converter

### The reader (`odrig/mapping.py`)

```python
ROWS = "rows"
COLUMNS = "columns"

@dataclasses.dataclass(frozen=True)
class Leg:
    leg: int
    pin: int
    first_led: str            # "left" or "right" in a row leg, "bottom" or "top" in a column leg
    strips: tuple[int, ...]   # the y of each row, or the x of each column, in chain order

@dataclasses.dataclass(frozen=True)
class Mapping:
    kind: str                 # ROWS or COLUMNS
    width: int
    height: int
    legs: tuple[Leg, ...]

    @property
    def strip_length(self): ...        # width for ROWS, height for COLUMNS
    def led_count(self, leg): ...      # strip_length * len(leg.strips)

def read(path): ...                    # as today
def loads(data): ...                   # as today
def position(canvas, leg, n): ...      # (x, y) of LED n of a leg, by the rule of the kind
```

`Leg.rows` becomes `Leg.strips`; its users, which are tests, follow. `position` is new and
is used by `odrig.mapdoc`. The tests keep their own statement of the rule: the reference
must not come from the code it checks.

The checks run in this order, and the first that fails decides the detail:

1. Strict JSON; the top level is an object.
2. `version` is present, is an integer and is 1.
3. The kind: with both `width` and `height` the detail is `the file has both "width" and
   "height"`; with neither, `the file has neither "width" nor "height"`.
4. The top level has `legs` and no member beyond the three of its kind; a missing member is
   reported before an unknown one, as `strictjson.members` does.
5. The strip length is an integer from 1 to 65,535.
6. `legs` is an array and is not empty.
7. Each leg in file order: it is an object with exactly the four members of the kind, so a
   leg of a column-leg file that has `rows` is first found to lack `columns`; `leg`; no
   leg number twice; `pin`; no pin twice; `first_led` is one of the two values of the kind;
   the strips are an array, not empty, of integers.
8. With the total number of strips known: every strip is from 1 to that total, and none is
   listed twice.
9. W * H is at most 65,534.

The details for a column-leg file are those for a row-leg file with `columns`, `column`
and `height` where they have `rows`, `row` and `width`, and with `"bottom" or "top"` where
they have `"left" or "right"`. Every rejection leaves `loads` as `mapping-malformed`, as
today.

### What uses the reader

`cli.py` (`import`), `pack.py` and the generators read `canvas.width` and `canvas.height`
only and need no change. `pack` copies the mapping file's bytes, so a packed show holds
the file as it is tracked. `docs/converter.md` says of `import` that the canvas is "as wide
as the mapping's `width` and as high as the number of rows": that sentence is rewritten for
both kinds.

The generators stay as they are, and `animations/hello.json` and `animations/dvd.json`
keep their bytes. On a square canvas the square of DVD bounce meets a side wall and the top
or the bottom wall in the same frame, so it runs to and fro along one diagonal: 116 frames
of 180 ms on 60 x 60. It still passes over every column. See "Seed 05: DVD bounce on a
square canvas" in `docs/drifts.md`.

## The core

Only `core/src/mapping.cpp` changes, with the comments in `core_state.h` and
`odrig_core.h` that say "rows" where both kinds are meant.

- **First reading.** At the top level the names `version`, `width`, `height` and `legs`
  are known; the file must have `version`, `legs` and exactly one of the other two. In a
  leg the names `leg`, `pin`, `first_led`, `rows` and `columns` are known; a leg must have
  the first three and exactly one of the last two. A JSON object may list its members in
  any order, and the reader is a streaming one, so `legs` can come before `width` or
  `height`: the reading notes the kind the first leg has, requires every leg to have it,
  and compares it with the top level when the object ends. A leg's `first_led` is read as
  one of four words and is judged against the leg's kind when the leg ends, because
  `first_led` can come before `rows` or `columns`.
- **Between the readings** the kind, the strip length and the number of strips are known:
  W and H follow as the table of "The two kinds" says. The check of W * H, the tables and
  their sizes are as today. The block that marks every row once now marks every strip
  once: one bit for each row of a row-leg file, for each column of a column-leg file.
- **Second reading.** For a row leg the table `led_pixel` is filled as today. For strip s
  of a column leg, with x its column and `up` true when the column starts at the bottom,
  entry i of the strip is the position (y - 1) * W + (x - 1) with y = 1 + i when `up` and
  H - i otherwise.

The second reading knows the kind from the first, so the core object gains no member and
the host interface no function. `odrig_leg.led_count` is the strip length times the number
of strips of the leg.

### Memory

The blocks are the ones the core asks for today. For the target file with a show of 100
items, 80 animations with a file each and 20 cycles of 10 entries:

| Block | Size | Bytes |
|---|---|---:|
| The core object | fixed | 3,112 today |
| Legs | 12 for each leg | 240 |
| The pixel of each LED | 2 for each LED | 7,200 |
| LED data | 3 for each LED | 10,800 |
| Strip check | 1 bit for each strip of the canvas | 8 |
| Pixel buffer | the smaller of 3 * W * H and 65,534 | 10,800 |
| Window of the DEFLATE decoder | 32,768 | 32,768 |
| Items | 16 for each item | 1,600 |
| Cycle entries | 2 for each entry of a cycle | 400 |
| Files | 48 for each animation item | 3,840 |
| **Total** | | **70,768** |

The nine tables come to 67,656 bytes; with a core object of 3,112 bytes the total is 70,768,
54 percent of the 131,072 the core may use. `tests/core/test_memory.py` measures the total,
and `docs/core.md` gets the measured figures in place of the ten-leg ones.

## The emulator and the command tool

No file of `emulator/*.py` and none of `odrigctl/` changes. Their tests move to the target:
the demo show recorded for 31 seconds against the reference, the `hello` event with twenty
legs, a refresh of 10,800 bytes, the real-time rate with the demo show and with the dense
60 x 60 clip, and the command tool's session against an emulator that runs the demo show.

A refresh for the page is 10,800 bytes, 14,400 characters in base64, 50 times a second. The
event stream keeps one place for the newest refresh on each connection, as today.

## The page

### Reading and placing (`layout.js`)

`read(text)` gives `{kind, width, height, legs}`, each leg with `leg`, `pin`, `first_led`,
`strips` and `count`. The kind is `"columns"` when the file has `height`. The page does not
judge a file: it draws only when the core lists legs, and the core lists legs only for a
valid file.

`position(m, pin, n)` and `find(m, x, y)` apply the rule of the kind. The functions that
describe a leg are written for strips: for each strip of a leg in chain order, its place
across (the y of a row or the x of a column), the end it starts at (`left`, `right`,
`bottom` or `top`) and the LED numbers at its start and its end; the corner points of the
chain; and the runs of neighbouring strips. A row-leg file gets from them what it gets
today.

`side(m)` is the feed edge: `"right"` or `"left"` for a row-leg file, as today, and
`"bottom"` or `"top"` for a column-leg file, `"bottom"` when as many legs start at the top
as at the bottom.

Row-leg files keep `fitLeds`, `fitBeside` and `fitBelow` with their sizes. Column-leg files
get arrangements of their own, below. `fit(m, width, height, board)` chooses by the kind.

### Colours

The list of leg colours grows from twelve to twenty: the first twelve stay, eight are
added, and a leg beyond the twentieth takes the colours again from the start. So twenty
legs side by side have twenty different colours, and the drawings of files with twelve legs
or fewer keep their look.

### The LEDs view for column legs

```
           x=1       10        20        30        40        50      x=60
  leg       1   2   3   4   5   6   7  ...                      19  20
  pin       1   2   3   4   5   6   7  ...                      21  47
           |_| |_| |_| |_| |_| |_| |_|                          |_| |_|
  y=60     ooo ooo ooo ooo ooo ooo ooo ...                      ooo ooo
           ooo ooo ooo ooo ooo ooo ooo                          ooo ooo
  50       ooo ooo ooo ooo ooo ooo ooo                          ooo ooo
   :
  y=1      ooo ooo ooo ooo ooo ooo ooo ...                      ooo ooo
```

- **The leg band** lies along the canvas on the side away from the feed edge: above the
  canvas when the snakes start at the bottom. For every leg it has a bracket that spans the
  leg's columns, and above the bracket the leg's number and, under it, its pin, both
  centred on the bracket in the leg's colour. The words `leg` and `pin` stand once, at the
  left end of the band. A leg whose columns are not neighbours gets a bracket with both
  numbers for each run. With twenty legs of three columns and cells of 8 pixels a leg has
  24 pixels of the band, which holds a leg number of two digits and a pin of three.
- **A faint band** of the leg's colour lies behind the leg's columns.
- **Rows and columns.** At the left of the canvas the rows y = 1, 10, 20 and so on, and the
  top row, are marked, the first and the last with `y=`. The header above the leg band
  marks the columns x = 1, 10, 20 and so on, and the last, as the page does today.
- **The LED numbers** at the two ends of every column stand in a band above and a band
  below the canvas, written upright, to be read from bottom to top, each in the width of
  its column. They are drawn where the cells are 9 pixels or more. Below that the two
  bands are left out, and the mapping view is the place to read the numbers.
- **The cell** is the largest from 4 to 28 pixels at which the canvas, the leg band, the
  header and the marks fit the drawing area. In an area of 1280 x 546 the height decides:
  about 50 pixels go to the header, the leg band and the margins, which leaves cells of 8
  pixels and a canvas of 480 x 480.

### The mapping view for column legs

The view is the LEDs view with the number bands always drawn, the outline and the path of
every leg, the board, and the lines. Two channels carry the lines: the **level channel**
along the feed edge of the canvas, with one level track for each leg, and the **upright
channel** beside the board, with one upright track for each leg that needs one.

**Wide: the board beside the canvas.** Used where the area is wide enough for cells of 9
pixels with the board beside the canvas. The level channel lies under the canvas and
reaches on under the upright channel, the board and the far zone.

```
   header: x=1, 10, 20 ... x=60
   leg band: the number and the pin of every leg
   number band: 60 61 180 ...
  +----------------------------------------+  +---------+       +-------+  +------+
  |                                        |  | upright | names |       |  | far  |
  |           canvas, 60 x 60              |  | channel | of    | board |  | zone |
  |                                        |  |         | legs  |       |  |      |
  +----------------------------------------+  |         |       +-------+  |      |
   number band: (1) 120 121 ...               |         |                  |      |
  +-------------------------------------------+---------+------------------+------+
  |                              level channel                                    |
  +-------------------------------------------------------------------------------+
```

**Narrow: the board below the canvas.** Used where the area is narrower. The level channel
lies between the canvas and the board. The board stands at the left under it, with the
upright channel at its left, and the canvas begins to the right of the upright channel, so
that every first LED is to the right of every upright track. The margin this leaves at the
left of the canvas holds the marks of the rows.

```
              header, leg band, number band
  +---------+----------------------------------------+
  | marks   |                                        |
  | of the  |           canvas, 60 x 60              |
  | rows    |                                        |
  +---------+----------------------------------------+
              number band: (1) 120 121 ...
  +--------------------------------------------------+
  |                  level channel                   |
  +---------+-------+-------+------+-----------------+
  | upright | names |       | far  |
  | channel | of    | board | zone |
  |         | legs  |       |      |
  +---------+-------+-------+------+
```

**The line of a leg** runs from the pad of its pin, level, to its upright track; along the
upright track to its level track; along the level track to the x of the leg's first LED;
and upright to that LED at the feed edge, where it ends in an arrow head. The number 1 of
the first LED is a tag on this last piece.

**Which track.** The rules are the same in both arrangements, and they are what keeps two
lines from lying on each other and from crossing twice.

- *Level tracks.* The lines reach the level channel from one side: from the right in the
  wide arrangement, from the left in the narrow one. The leg whose first LED is farthest
  from that side takes the level track farthest from the canvas, and so on inward. So no
  line crosses another between its level track and its first LED.
- *Upright tracks of the row of pads that faces the channel.* The pad nearest the level
  channel takes the upright track nearest the board. So no line crosses another between
  its pad and its upright track. The lines of this row cross where an upright track passes
  a level track, in the corner between the two channels, and nowhere else.

  Three legs A, B and C, from left to right on the canvas, whose pads stand in the order
  A, C, B down the row that faces the upright channel, in the wide arrangement:

  ```
      A   B   C               upright tracks     board
      ^   ^   ^                 A  C  B       +---------
      |   |   |                 ,-------------o pad of A
      |   |   |                 |  ,----------o pad of C
      |   |   |                 |  |  ,-------o pad of B
      |   |   |                 |  |  |       +---------
      |   |   `-----------------|--'  |         level track of C
      |   `---------------------|-----'         level track of B
      `-------------------------'               level track of A
  ```

  The line of A crosses the lines of B and of C, because the pad of A is above theirs while
  its leg is to their left; the lines of B and C do not cross.
- *The row of pads on the other side of the board.* A line from it goes round the board in
  a loop, one of two ways. **The short way** is round the end of the board that faces the
  level channel; the line reaches its level track from the far side of the board. **The
  long way** is round the other end of the board and then along the side that faces the
  upright channel, on a track beyond every other upright track. A leg takes the short way
  when its level track is in the half of the level channel farthest from the canvas, and
  the long way otherwise. The loops of each way nest, so that they do not cross each
  other.
- A leg whose pin the board does not have gets a pad of its own beyond the end of the
  board that faces the level channel, labelled `GPIO <pin>`, and is treated as the pad
  nearest the level channel.
- A leg whose first LED is at the far edge of the canvas, at the top when the feed edge is
  the bottom, is reached through the gap at the left of the leg's first column: the last
  piece of its line runs in that gap from the feed edge to the far edge and turns into the
  LED from outside the canvas.
- When the feed edge is the top, both arrangements are mirrored top to bottom: the level
  channel lies above the canvas, the leg band below it, and in the narrow arrangement the
  board stands above the canvas.

**Crossings cannot be avoided.** Going down the row of pads that faces the channel, the
board has the pins 4, 5, 6, 7, 15, 16, 17, 18, 8, 3, 9, 10, 11, 12, 13, 14, while the legs
stand in the order of their numbers. Whatever the routing, lines that start in one order
and must end in another cross. For the target file, counted for this design from the order
of the pads round the board and the order of the legs along the bottom of the canvas, no
drawing in which the lines reach the snakes from below has fewer than 76 crossings. With
the rules above the lines of the target file cross 88 times, in both arrangements, and no
two lines cross more than once; this was counted by placing the twenty lines by the rules.
What keeps the drawing readable is that every crossing is at a right angle between two
tracks, that every line has its leg's colour and its leg's name at both ends, and that
pointing at a leg fades all the others.

**The snake of a leg**, for three columns that start at the bottom:

```
      60 | 61   180        the number band above the canvas
      .--.      ==         a turn outside the top edge; a bar where the chain ends
      ^  |      ^
      |  |      |          the path, behind the dots, with small arrows
      ^  v      ^          along every column, between two LEDs
      |  |      |
      |  `--.   |
      o  o  `---'          a turn outside the bottom edge
     (1) 120   121         the number band below; 1 is the tag on the leg's line
      ^
      |                    the line from the pad
```

- The path runs through the centres of the LEDs of the first column from its first LED to
  its last, turns outside the edge of the canvas into the second column, and so on. An
  arrow head marks where the chain comes back into the canvas after a turn, and a bar
  marks its end.
- Three small arrows along every column, between two LEDs, point the way the numbers grow.
- The outline of the leg is a rounded frame round each run of its columns, in its colour.
- The numbers at the ends of every column are written upright in the two number bands, in
  the leg's colour, clear of the turns.

**Sizes.** A level or upright track takes 7 pixels. With twenty legs the level channel is
150 pixels deep and the upright channel 136 pixels wide. The cell is the largest from 4 to
28 at which the drawing fits the area in both directions; when that is below 9, it is the
largest up to 9 that fits the width, and the drawing is then higher than the area and the
stage scrolls up and down. In an area of 1280 x 546 the wide arrangement has cells of 9
pixels and is about 770 pixels high; in an area 756 wide the narrow arrangement has cells
of 9 pixels. The pads of the board are 10 to 20 pixels apart, as today.

**Pointing** works as today, with the columns of a leg in place of its rows.

### `view.js` and `board.js`

`view.js` draws what `layout.js` gives. Its label code gets the leg band, the upright
numbers and the marks of the rows for column legs; its chain code draws turns outside the
top and the bottom edge. `board.js` does not change: the pads are the board's.

### Drawing 3,600 LEDs

The page draws a dot again only when its bytes changed. With the dense clip every one of
3,600 LEDs changes at every refresh. Requirement 8 criterion 9 is checked by eye; if the
page falls below 49, the dots of cells under 9 pixels are drawn as filled squares in place
of circles, which costs a fraction of an arc, and the finding is recorded.

## The tool that writes docs/mapping.md (`odrig/mapdoc.py`)

```
python -m odrig.mapdoc [--check] [--page PATH] [--mapping-dir DIR]
```

It is a module of the package `odrig`, beside the reader it uses, and not a subcommand of
`python -m odrig`: the converter's command line stays as seed 06 will mirror it. It uses
only the standard library. `--page` and `--mapping-dir` default to `docs/mapping.md` and
`mapping/` of the repository and exist for the test, which runs the tool on copies.

**Generated parts** of the page are marked:

```
<!-- generated by `python -m odrig.mapdoc`: board legs-20 -->
...
<!-- end of generated part -->
```

The names are `board <file>`, `drawing <file>` and `table <file>`, with the file's name
without `.json`. The tool replaces what stands between a marker and the next end marker and
leaves every other byte. A marker that names a file that is not there, a marker without an
end, and a name it does not know are failures with status 1.

The page has five generated parts: `board legs-20`, `drawing legs-2`, `table legs-2`,
`drawing legs-20` and `table legs-20`.

**The board.** The two rows of labels are a table in `mapdoc.py`, in the order of the real
board. `tests/emulator/test_board.py` goes on comparing the rows of `emulator/web/board.js`
with the drawing of the page, and the legs of the drawing with the pins of the target
file. The drawing is the one the page has today, with the legs of the named file beside
their pins:

```
                      +-----------------+
                      |     antenna     |
             3V3  o---|                 |---o  GND
             3V3  o---|                 |---o  TX
             RST  o---|                 |---o  RX
   leg 4  --   4  o---|                 |---o  1   --  leg 1
   leg 5  --   5  o---|    ESP32-S3     |---o  2   --  leg 2
   leg 6  --   6  o---|     N16R8       |---o  42
   leg 7  --   7  o---|                 |---o  41
   leg 15 --  15  o---|                 |---o  40
   leg 16 --  16  o---|                 |---o  39
   leg 17 --  17  o---|                 |---o  38
   leg 18 --  18  o---|                 |---o  37
   leg 8  --   8  o---|                 |---o  36
   leg 3  --   3  o---|                 |---o  35
              46  o---|                 |---o  0
   leg 9  --   9  o---|                 |---o  45
   leg 10 --  10  o---|                 |---o  48
   leg 11 --  11  o---|                 |---o  47  --  leg 20
   leg 12 --  12  o---|                 |---o  21  --  leg 19
   leg 13 --  13  o---|                 |---o  20
   leg 14 --  14  o---|                 |---o  19
            5Vin  o---|                 |---o  GND
             GND  o---|  [USB]   [USB]  |---o  GND
                      +-----------------+
```

A leg whose pin is not on the board is named in a line under the drawing.

**The drawing of a file** has one line for each strip. For a row-leg file it is today's:
the rows from the top one down, the LED numbers at x = 1 and x = W, and the arrow. For a
column-leg file the lines are the columns from x = 1 on, each drawn lying down, with the
LED numbers at y = 1 and y = H:

```
       y=1                                            y=60
x=1   |   1 ------------------------------------------->  60 |  leg 1, pin 1
x=2   | 120 <-------------------------------------------  61 |
x=3   | 121 -------------------------------------------> 180 |
x=4   |   1 ------------------------------------------->  60 |  leg 2, pin 2
```

The page says in a sentence above it that each line is one column, with the bottom of the
canvas at its left end.

**The table of a file** has, for each leg, its number, its pin, its strips in chain order,
and the place of the first and the last LED of every strip. The heading of a strip's two
columns names the LED numbers, and the third column is headed `Rows (y)` or `Columns (x)`:

```
| Leg | Pin | Columns (x) | LED 1 | LED 60 | LED 61 | LED 120 | LED 121 | LED 180 |
|---:|---:|---|---|---|---|---|---|---|
| 1 | 1 | 1, 2, 3 | (1,1) | (1,60) | (2,60) | (2,1) | (3,1) | (3,60) |
| 20 | 47 | 58, 59, 60 | (58,1) | (58,60) | (59,60) | (59,1) | (60,1) | (60,60) |
```

A file whose legs have different numbers of strips gets as many pairs of columns as its
longest leg, empty for a shorter one.

For `legs-2.json` the tool writes the bytes the page has today; this was tried for this
design with a sketch of the two functions, which also gave the board drawing above.

**`--check`** builds the page in memory and compares. Equal: status 0, nothing printed.
Different: one line `error: page-differs: <part>` on standard error, naming the first
generated part that differs, and status 1. `page-differs` is a word of this module and not
a reason of `docs/reasons.md`, which lists what the converter says about its inputs.

`tests/converter/test_mapping_page.py` runs the check on the tracked files; copies the page
and the mapping folder, changes in turn a pin, a `first_led` and the order of two columns
of `legs-20.json`, and the first row of `legs-2.json`, and sees the check fail naming a part
of that file; writes the page again on the copy and sees the check pass; and sees that the
bytes outside the generated parts are the tracked page's.

## Twenty outputs in the firmware

### What was read

Read in WLED's source at the pinned commit `29b389df1c1aaec6ff53aea742d17063b985906c`, in
the checkout the tool keeps in `build/firmware/WLED`, and in the copy of NeoPixelBus the
build fetched for WLED's pin, commit `1d7ff38f14d04a976f9c6e365c83a232bcba04fc`. Nothing
of the firmware was built or flashed for this design, and the board was not touched.

| # | Fact | Where |
|---|---|---|
| F1 | For the ESP32-S3: `WLED_MAX_RMT_CHANNELS` is 4 and `WLED_MAX_I2S_CHANNELS` is 8. `WLED_MAX_DIGITAL_CHANNELS` is their sum, 12. `WLED_MAX_BUSSES` adds the 8 PWM channels and may not pass 32. | `wled00/const.h` |
| F2 | `PolyBus::getI()` gives an output RMT while fewer than `WLED_MAX_RMT_CHANNELS` are taken and RMT is asked for, else the parallel driver while fewer than `WLED_MAX_I2S_CHANNELS` are taken, else nothing: the output does not work. | `wled00/bus_wrapper.h` |
| F3 | `BusManager::add()` makes a placeholder for a digital output beyond `WLED_MAX_DIGITAL_CHANNELS`. | `wled00/bus_manager.cpp` |
| F4 | On the ESP32-S3 every parallel output is a `NeoPixelBus<..., X8...Method>`: the twelve `B_32_IP_*` types name the `X8` methods, and the nine `X1...Method` names of the S3 are set to the `X8` ones. | `wled00/bus_wrapper.h` |
| F5 | For the ESP32-S3 the library names `X8Ws2812xMethod` as `NeoEsp32LcdX8Ws2812xMethod` and `X16Ws2812xMethod` as `NeoEsp32LcdX16Ws2812xMethod`. All nine methods WLED uses have an `X16` form. | `src/internal/XMethods.h` of NeoPixelBus |
| F6 | The two forms are one template. `X8` keeps one byte for each sample, a bit for each of 8 lanes; `X16` keeps two bytes, a bit for each of 16 lanes, and switches the chip's LCD unit to 16 data lines. A lane is a signal `LCD_DATA_OUT0` + lane, routed to any pin. Every bit of LED data is three samples. All lanes share one buffer of DMA memory: 24 bytes (X8) or 48 bytes (X16) for each byte of the longest output, reset bytes included. The transfer starts when every lane has new data, and the method is busy until the end of the transfer clears `lcd_start`. | `src/internal/methods/NeoEsp32LcdXMethod.h` of NeoPixelBus |
| F7 | The ESP32-S3 has one LCD unit, 16 data lines wide, with the signals `LCD_DATA_OUT0` to `LCD_DATA_OUT15`; four RMT channels that can send; and four pulse counters. This build watches the idle task of processor core 0 with a time-out of 10 seconds. | `soc/soc_caps.h`, `soc/gpio_sig_map.h` and `qio_opi/include/sdkconfig.h` of the platform's Arduino core |
| F8 | A WS2812 bit takes 1,250 ns and the reset 300 us, which the library sends as 30 more bytes. An output of 180 LEDs is 570 bytes: 5.7 ms on the wire. | `src/internal/methods/NeoBits.h` of NeoPixelBus |
| F9 | `finalizeInit()` adds up an estimate of the memory of all outputs and makes a placeholder of an output that takes the sum above `MAX_LED_MEMORY`, 192 KB on the S3. For the parallel driver it counts the common buffer as 8 lanes. | `wled00/FX_fcn.cpp`, `wled00/const.h` |
| F10 | `PinManager::isPinOk()` on the S3 with this build: pins 0 to 18 pass; 19 and 20 fail, being the USB pins; 21 passes; 22 to 32 fail; 33 to 37 fail when octal PSRAM is found; 38 to 48 pass. | `wled00/pin_manager.cpp` |
| F11 | `MAX_NUM_SEGMENTS` is 64 on a board with PSRAM, and `makeAutoSegments()` makes one segment for each output. | `wled00/FX.h`, `wled00/FX_fcn.cpp` |
| F12 | The LED settings page gets the three limits from the firmware. `deserializeConfig()` reads up to `WLED_MAX_BUSSES` outputs from `cfg.json`. | `wled00/xml.cpp`, `wled00/cfg.cpp` |
| F13 | The current limiter: with WLED's maximum of 850 mA it allows the LEDs 730 mA and counts 1 mA for each LED at rest. 3,600 LEDs are 3,600 mA at rest, so it sets every LED to its lowest level, and to do so reads and writes every LED of every output once more. | `wled00/bus_manager.cpp` (`applyABL`, `applyBriLimit`) |

Read on the web:

| # | Fact | Where |
|---|---|---|
| F14 | The sixteen-lane LCD code entered NeoPixelBus with pull request 808, "ESP32S3 16-bit parallel LCD code for WLED with WS2818x", merged into its branch `Esp32S3Led` on 2024-06-30. Its author tested ten strips of 45 LEDs. In August 2024 the library's maintainer wrote there that it did not work for him: "No output other than a single pulse". Nothing found says whether that still holds for the commit WLED pins. | `github.com/Makuna/NeoPixelBus/pull/808` |
| F15 | On the ESP32-S3-DevKitC-1, whose pin rows are the ones of this board: GPIO35, 36 and 37 serve the module's octal memory and are not for other use; GPIO19 and 20 are USB; the on-board RGB LED is on GPIO48, or on GPIO38 from board version 1.1; TX and RX are GPIO43 and 44. | Espressif's user guide of the ESP32-S3-DevKitC-1 |
| F16 | GPIO0, 3, 45 and 46 are the chip's strapping pins. GPIO26 to 32 serve the flash, and GPIO33 to 37 the octal PSRAM of a chip such as this board's. GPIO19 and 20 are the USB serial and JTAG unit. The page has no note against GPIO1 to 18, 21 or 47. | Espressif's GPIO page of ESP-IDF for the ESP32-S3 |

### Where twelve comes from, and what twenty needs

Stock WLED drives twelve outputs on this chip because of F1 to F4: four RMT channels, and
a parallel driver that WLED uses in the library's eight-lane form. The chip's LCD unit has
sixteen data lines (F7), and the library has the sixteen-lane form of the same method (F5,
F6). Four and sixteen are twenty: every leg of the target has an output, with none to
spare.

### The patch

One file, `firmware/patches/010-sixteen-parallel-outputs.patch`, in the form `git diff`
writes, applied by the build as `firmware/patches/README.md` says. It changes three files
of WLED and nothing for a chip other than the ESP32-S3:

| File | Change |
|---|---|
| `wled00/const.h` | For the ESP32-S3, `WLED_MAX_I2S_CHANNELS` is 16. `WLED_MAX_DIGITAL_CHANNELS` so becomes 20 and `WLED_MAX_BUSSES` 28. |
| `wled00/bus_wrapper.h` | For the ESP32-S3, the parallel types are built on the library's `X16` methods: the nine `X1...Method` names and the twelve `B_32_IP_*` types. |
| `wled00/FX_fcn.cpp` | For the ESP32-S3, `finalizeInit()` counts the common buffer of the parallel driver as 16 lanes of two bytes: twice what it counts now. |

Everything else follows from these: `getI()` hands out sixteen lanes (F2),
`add()` accepts twenty outputs (F3), the settings page shows the new limits (F12). The
settings page's own estimate of memory, which is for people, is left as it is.

The first lines of the patch file say what it changes and why the usermod cannot do it
from outside: the limits are constants compiled into WLED, and the type of the parallel
outputs is chosen inside WLED's `PolyBus`.

`firmware/patches/README.md` loses its sentence that the folder holds no patch.
`tests/firmware/test_patches.py` checks that every tracked patch applies to WLED's files at
the pinned commit, with `git apply --check --cached` in the work folder's checkout, which
looks at the commit's files and not at what a build left in the folder.

### Why not outputs driven by the usermod

The usermod could leave WLED its twelve outputs, or only the four RMT ones, and drive the
rest itself with the same library. That needs no patch, but:

- the chip has one LCD unit, so WLED's eight lanes and sixteen lanes of the usermod's
  cannot exist together; the usermod would have to own every parallel output;
- those outputs would be outside WLED's current limiter, which seed 04 keeps active on
  every refresh, outside WLED's information and LED settings, and outside the probe
  build's report, which reads outputs through WLED;
- the usermod would send through two paths.

The patch keeps one path and every rule of seed 04. The seed itself names a patch file as
the place for a change to WLED.

### What the usermod changes

`odrig_leds.cpp` makes outputs from the core's legs and asks for RMT; with the patch WLED
gives RMT to the first four legs of the file and the parallel driver to the next sixteen:
with the target file legs 1 to 4, on pins 1 to 4, are RMT, and legs 5 to 20 are the lanes
0 to 15. The text of `summary()` gets room for twenty legs that do not work. Nothing else
in the usermod depends on the number of outputs.

### Memory

| What | Bytes | Kind of memory |
|---|---:|---|
| The common buffer of the parallel driver: 48 x 570 | 27,360 | DMA-capable internal memory; 13,680 today |
| The LED bytes of sixteen parallel outputs: 16 x 540 | 8,640 | heap |
| The LED bytes of four RMT outputs, two buffers each: 4 x 1,080 | 4,320 | heap |
| WLED's own pixel buffer: 4 for each LED | 14,400 | PSRAM |
| The core, target file, a show of one file | about 65,000 | internal, from the usermod |
| The core, target file, 100 items | 70,768 | internal, from the usermod |

WLED's estimate (F9) for twenty outputs of 180 LEDs is about 111 KB of its 192 KB: about
3,800 bytes for an RMT output, 4,400 for a parallel one, and 25,920 for the common buffer.
With ten legs the probe build reported 227,940 bytes of internal memory free. Twenty legs
take about 14 KB more for the common buffer, about 8 KB more for outputs and about 14 KB
more for the core. The spike reports the free memory it finds.

### The pins

| Pins | Legs | What was checked |
|---|---|---|
| 1 to 18 | 1 to 18 | Pass WLED's pin check (F10). General-purpose pins of the chip (F16). Pin 3 is a boot-mode pin, read at reset only; the data input of a strip does not pull it. Pins 1 to 10 made working outputs in seed 04. |
| 21 | 19 | Passes WLED's pin check. A general-purpose pin on the board's right row. |
| 47 | 20 | Passes WLED's pin check, and Espressif's GPIO page has no note against it (F16). The module's datasheet, which was not read again for this design, puts pins 47 and 48 on the supply of the memory in modules whose memory runs at 1.8 V; this board's module, N16R8, is not one of those. |

Not used, and why: 19 and 20 are USB (F10, F15, F16); 33 to 37 serve the PSRAM (F16); 0,
45 and 46 are boot-mode pins that boards pull (F16); 43 and 44 are the serial lines of the
second USB socket (F15); 48 has the on-board LED on this kind of board (F15).

No pin of the seed had to be changed. The spike proves each pin by its output working and
by the pulses counted on it; if one fails, Requirement 12 criterion 10 applies.

### What a program can prove without LEDs

One strip is wired, on pin 1, and nobody watches it. Seed 04 called an output working when
WLED made it and it held its leg's bytes. For the sixteen-lane form that is not enough:
F14 reports that this code once gave no output but a single pulse. The probe build
therefore gets two measurements of the signal itself.

- **`wire_us`**: the time from the end of a send until the outputs of the parallel driver
  can take data again, shortest and longest since the last `#probe`. It is taken in the
  usermod's loop, so it is as exact as a pass of the loop is short: seed 04 counted about
  2,300 passes a second with the bench show, under half a millisecond each. For legs of
  180 LEDs it is 5.7 ms when the driver sends the whole buffer at the right rate (F8), and
  near zero when the transfer does not run.
- **`pulses`**: for each output, the number of rising edges on its pin during one refresh.
  A WS2812 bit is one pulse, so an output of 180 LEDs gives 4,320, whatever the colours.
  The chip's pulse counter counts them: the probe build turns on the input of the pin's
  pad, which does not change what the pad puts out, connects that input to one counter,
  clears the counter before a send and reads it when the outputs can take data again. One
  output is counted at each send, in turn, so after twenty sends every output has a
  figure. An output that was not counted yet reports `null`.

Both are in the probe build only, in `odrig_probe.cpp`, inside `#ifdef ODRIG_PROBE`. The
report of twenty outputs is a line of about 2,000 characters; the text it is built in gets
that room.

### Assumed, to be verified by the spike

| # | Assumption | If it does not hold |
|---|---|---|
| A1 | The library's sixteen-lane method, at the commit WLED pins, sends correct data on all sixteen lanes. | The fallback below. |
| A2 | With the patch WLED makes four RMT and sixteen parallel outputs on pins 1 to 18, 21 and 47, and all twenty work. | A pin that fails is replaced (Requirement 12 criterion 10); a limit that was missed is added to the patch. |
| A3 | The pulse counter can count a pin an output drives without disturbing the output. | `pulses` is left out, `wire_us` stands alone, and the drift is recorded. |
| A4 | Enough internal memory is left for WLED's web server and Wi-Fi. The design takes 100 KB free as enough; about 190 KB are expected. | The finding is recorded, and the usermod asks for the core's blocks in PSRAM first, where today it asks there last. |
| A5 | A send to twenty outputs happens 49 times a second or more with a picture that does not change. | The measurements say where the time goes; see "The time of one refresh". |

### The spike

The first task. It needs nothing of the new format: twenty outputs of 180 LEDs are twenty
row legs of three rows of 60, which today's format and today's core can describe. The test
makes that mapping with `tests/board/support.legs_mapping`, on the pins of the target file.

1. Write the patch; add `wire_us` and `pulses` to the probe build; build the probe build
   and the firmware.
2. `tests/board/test_twenty.py`, with the probe build:
   - twenty row legs of three rows of 6 LEDs, a picture in which every pixel has a colour
     of its own, at brightness 40: twenty working outputs on pins 1 to 18, 21 and 47 with
     18 LEDs each, four `rmt` and sixteen `parallel`; `limited` is 0; the CRC of every
     output is that of its leg's bytes in the emulator's recording; `pulses` is 432 for
     every output;
   - twenty row legs of three rows of 60, the same kind of picture at brightness 32:
     twenty working outputs of 180 LEDs; every output holds what the limiter's lowest
     level makes of its leg's bytes; `pulses` is 4,320 for every output; `wire_us` is
     between 4,500 and 7,500; `sent` is 49 or more in each of ten seconds in a row;
     `overwritten` stays 0;
   - the same mapping with a dense 60 x 60 clip of 10 seconds, compressed and then
     uncompressed: the test prints and writes to `build/firmware/out/twenty.json` the
     refreshes sent in a second, the mean and the longest request and send, the longest
     gap, `start_ms` and `heap`. It fails only when a figure is missing.
3. The whole board suite, which still has its ten-leg tests: ten legs now use ten of the
   lanes of the sixteen-lane form.
4. Write what was found into `docs/firmware.md`, "Verified on the board", for A1 to A5.

**The fallback**, if A1 fails. The task first tells the failure apart with the two new
figures: no pulses and no wire time means the transfer does not start; pulses but a wrong
count or time means a wrong length or rate. It may change the patch where the cause is in
a file of WLED. A fault inside the library's own file is not patched in this seed: the
library is fetched by the build and is not one of WLED's files. Then:

- the patch file is removed, or reduced to what works, and the firmware keeps the largest
  number of outputs for which criteria 4 to 7 of Requirement 12 hold: twelve with stock
  limits;
- `docs/firmware.md` and the open questions of `docs/decisions.md` say what was tried and
  measured, and `docs/drifts.md` gets the entry;
- the number is named once in `tests/board/support.py`, and the board tests of the later
  tasks expect that many working outputs and the rest reported as not working;
- every other task is done as written. The core produces LED data for twenty legs
  whatever the outputs do, and `status` reports its rate.

## The time of one refresh

Seed 04 measured, on the board, with ten legs of 180 LEDs and the dense 60 x 30 clip:

| | Compressed | Uncompressed |
|---|---:|---:|
| Request for a refresh: read, decode, place 1,800 LEDs, mean | 6.6 ms | 4.7 ms |
| Send to ten outputs with the limiter dimming every LED, mean | 7.7 ms | 7.7 ms |
| The same send without the dimming | about half | about half |

The loop does the request for the next refresh while the last one is on the wire, so a
refresh costs the send and then the longer of the wire time and the request. Doubling the
LEDs doubles the request and the send:

| Estimate for 3,600 LEDs | Compressed | Uncompressed |
|---|---:|---:|
| Request | 13 ms | 9.5 ms |
| Send, with the dimming | 15 ms | 15 ms |
| One refresh | 28 ms | 25 ms |
| Refreshes a second | 35 | 40 |

These are estimates from the figures above, not measurements. They say that the loop as it
is will probably not hold 49 with a dense clip while the limiter dims, and may just hold it
without the dimming. The dimming is the state of the board on the bench, where WLED's
maximum of 850 mA is below the 3,600 mA it counts for 3,600 LEDs at rest (F13), and it is
also what a bright picture causes on a real power supply, so the firmware has to hold the
rate with it.

The spike measures the real figures. The second task acts on them:

1. **If `status` reports 49 or more** for both clips with the firmware build, the loop
   stays as it is.
2. **Otherwise the request moves to a task of its own on the chip's other processor
   core.** WLED's loop runs on core 1. A task `odrig`, pinned to core 0 with a stack of
   8,192 bytes and priority 1, does this for ever: wait until the loop has taken the last
   refresh; call `odrig_core_poll` under the lock, again after a tick while none is due;
   when a refresh was produced, mark it ready. The loop, when a refresh is ready and the
   outputs can take data: copies the legs' bytes into the outputs, which is the first half
   of today's `send()`; tells the task that the refresh was taken; and then calls
   `BusManager::show()`, the limiter and the start of the transfer. The core has one buffer
   of LED data, which is why the task waits for the copy and not for the whole send. The
   request for the next refresh then runs beside the limiter and the transfer:

   | Estimate with the task | Compressed |
   |---|---:|
   | Copy into the outputs | 4 ms |
   | Then, side by side: limiter and start of the transfer, 11 ms; request, 13 ms | 13 ms |
   | One refresh | 17 ms |

   What stays as it is: every call to the core is made under the lock, one at a time;
   every refresh the core counts is sent, because the task does not ask again before the
   last one was copied; `odrig_core_begin` runs in `setup()`; while WLED writes a new
   firmware the task does not ask. What changes with it: the port feeds the core all bytes
   of one pass under one hold of the lock, up to the end of a line, so that a command
   waits for one request at most; the probe build times the request in the task.
3. **If the rate is still below 49**, the task records the measurements and what they
   point to in `docs/firmware.md`, `docs/decisions.md` and `docs/drifts.md`, and
   Requirement 13 criterion 5 applies. It does not change the core's decoder or WLED's
   limiter.

Assumed for step 2, to be verified there: a task on core 0 can read files of `/odrig`
while WLED's loop runs; core 0, which also runs Wi-Fi, has the time; and the idle task of
core 0, which the build's watchdog expects to run every 10 seconds (F7), still runs,
since the task waits at every refresh.

**Start-up.** The core decodes every file at start: 3.1 s for the dense 60 x 30 clip of
725 KB. The dense 60 x 60 clip is 1.38 MB, so about 6 s are expected, inside the 20 seconds
`install-show` waits.

## The demo show

`shows/demo-20/show.json` has the content `shows/demo-10/show.json` has: the animations
`hello.odrg` and `dvd.odrg`, a cycle of the two with 15 seconds each, `start` on the cycle,
and brightness 128. Only this file is tracked. The sources are written into `build/`:

```
mkdir -p build/demo-20/sources
python -m odrig.generators.hello_world build/demo-20/sources/hello.json --mapping mapping/legs-20.json
python -m odrig.generators.dvd_bounce  build/demo-20/sources/dvd.json   --mapping mapping/legs-20.json
python -m odrig pack --show shows/demo-20/show.json --mapping mapping/legs-20.json \
    --sources build/demo-20/sources --out build/demo-20/show
python -m emulator build/demo-20/show
```

Measured when this was written, with the converter as it is and zlib 1.2.12:

| | Frames | JSON source | ODRG uncompressed | ODRG compressed |
|---|---:|---:|---:|---:|
| Hello world, 60 x 60, 5.1 s | 255 | 2,939,938 | 19,372 | 1,210 |
| DVD bounce, 60 x 60, 20.9 s | 116 | 1,258,994 | 2,340 | 1,052 |
| Dense, 60 x 60, 10 s | 500 | not measured | 1,462,236 | 1,383,766 |

Hello world is 53 columns wide and 6 rows high: on 60 x 60 it stands in the columns 4 to
56 and the rows 28 to 33.

The demo show has brightness 128 and is for the emulator. On the board, the tests install
it with its brightness replaced, as they do with the example show.

## Measured sizes and what fits

`docs/format.md`, "Measured sizes", gets the row

```
| Dense full-colour, 10 s | 60 x 60 | 500 | <uncompressed> | <compressed> |
```

with the two sizes the converter of this repository gives when the task measures them, and
a sentence that says so, because the rows above it come from the prototype of the frame
coder. Its sentence that decoding has not been run on the board gives way to a pointer to
the measurements of `docs/firmware.md`.

The statement of what fits is computed, in `docs/format.md` and in the same words in
`docs/decisions.md`, from three figures:

- the size of the 10-second dense 60 x 60 clip, compressed and uncompressed;
- the storage partition, 10,354,688 bytes, and the 9,001,905 bytes of animations that
  seed 04 installed and played, as the upper and the proven lower figure for what storage
  holds;
- the size of a picture that nothing predicts: a stored frame record of 10,805 bytes for
  each 20 ms.

seconds = bytes of storage / (bytes of the clip / 10). With the sizes above that is 65 to
74 seconds of the dense clip compressed, 61 to 70 uncompressed, and 16 to 19 seconds of
content that is stored frame by frame. The figure `docs/decisions.md` has for noisy 60 x 30
content came from a prototype clip that is not in this repository; it is replaced by the
stored-frame figure, which follows from the format alone.

## Testing strategy

Four suites need no board; each is selected by discovery and run from the repository root:

```
.venv/bin/python -m unittest discover -s tests/converter -t .
make -C core test
python3 -m unittest discover -s tests/emulator -t .
python3 firmware/fw.py test
```

The fifth, `python3 firmware/fw.py test-board`, needs the board and takes about half an
hour. It is run in the tasks that change what the board runs or what `tests/board/` holds,
and in the last task.

### Made-up mappings

`tests/core/support.py` gives every suite its mappings. Column-leg ones are added:

| Name | What it is |
|---|---|
| `top-start` | One leg of three columns of 7 that starts at the top. |
| `two-and-four-columns` | Legs of two and of four columns, strip length 5, one starting at the top. |
| `columns-apart` | Legs whose columns are not neighbours and not in order: `[2, 4]` and `[1, 5, 3]`. |
| `one-led-column` | `height` 1 and one leg of one column. |

Until the page reads both kinds they are given by a second function, so that the emulator's
suite, which draws every mapping of `mapping_texts()`, passes at every commit; the task of
the page joins them.

`led_pixels` and `ReferencePlayer` of that file get the column rule, written out there and
not taken from `odrig.mapping.position`.

### What each suite gains

| Suite | Tests |
|---|---|
| `tests/converter/` | `test_mapping.py`: every rule of Requirement 1 broken once for a column-leg file, each kind of mixing, the edges (255 legs, 65,534 pixels, `columns` before `first_led`), the detail of each new refusal, `position` for both kinds against the test's own rule, the target file's legs, pins and corners. `test_generators.py`, `test_import_timeline.py`, `test_show_pack.py`: the target file and 60 x 60 in place of the ten-leg file and 60 x 30. `test_mapping_page.py`: Requirement 11. `test_docs.py`: the documents name no ten-leg file and no `demo-10`. |
| `tests/core/` | `test_mapping.py`: the same broken and edge files, judged by the core as by the converter; members of a column-leg file in every order that matters to a streaming reader: `legs` before `height`, `first_led` before `columns`. `test_playback.py`: every LED shows the pixel of the rule on every mapping; Hello world, DVD bounce and the dense clip on the target file against the reference for one loop. `test_memory.py`: the target file with 100 items. `test_startup.py`, `test_cycle.py`: the target file where the ten-leg file stood. |
| `tests/emulator/` | `test_layout.py`: positions and `find` on every mapping; the parts of the LEDs view and of both arrangements of the mapping view for the target file and the made-up column files, inside the drawing and apart from each other; the cells of Requirements 8 and 9; lines from pad to first LED, made of level and upright pieces, none on another, none through the board or over an LED, no two crossing twice, 88 crossings for the target file; chains through the corners of their paths; twenty colours; everything of today for the row-leg files, unchanged. `test_demo.py`, `test_realtime.py`, `test_docs.py`, `test_board.py`: the target. `test_record.py`: with the `first_led` of one leg of the target file changed to `"top"`, every column of that leg is reversed in the recording and no LED of another leg moves. `test_tool.py`: the command tool's session against the demo show. |
| `tests/firmware/` | `test_patches.py`; `test_storage.py` with the target file; `test_usermod_files.py`: the new probe code is inside `#ifdef ODRIG_PROBE`; `test_docs.py`: the owner's checks. |
| `tests/board/` | `test_twenty.py` of the spike; then with the target file: twenty outputs, exact bytes on a column-leg file of few LEDs, the limiter's level on the target file, `pulses`, `wire_us`; `test_fps.py` with the dense 60 x 60 clip; `test_measure.py` with the rows of Requirement 13. |

### Who checks what

| Item of the seed's definition of done | Checked by |
|---|---|
| 1. All suites pass | The five commands, in the last task |
| 2. LED data of the core equals the reference on the target file | `tests/core/test_playback.py` |
| 3. Memory under 128 KB, reported | `tests/core/test_memory.py`, `docs/core.md` |
| 4. The emulator holds 49 on the demo show and the dense clip | `tests/emulator/test_realtime.py` |
| 5. The page of the mapping agrees with the files | `tests/converter/test_mapping_page.py` |
| 6. The board holds 49 with the dense clip; outputs and start-up stated | `tests/board/test_fps.py`, `test_measure.py`, `docs/firmware.md` |
| 7. The board is left with the bench show | The last step of the board suite, and `tests/board/test_autostart.py` |

## Documents

| Document | What changes |
|---|---|
| `docs/mapping.md` | Both kinds: the members, the rules, where each LED is. The five generated parts. "Legs and pins": a leg is a pin with three strips of 60; leg N on pin N, with legs 19 and 20 on pins 21 and 47. "What is confirmed": legs 1 and 2 on the hardware; the target's twenty outputs as the board tests found them; that LEDs on pins 2 to 18, 21 and 47 have not been seen. |
| `docs/reasons.md` | "Mapping files": the two reasons hold for both kinds. |
| `docs/format.md` | The row of measured sizes and the statement of what fits. |
| `docs/decisions.md` | "Canvas and coordinates": a leg, the bench build and the target with both kinds of leg. "Measurements behind the choice": what fits. "Emulator": the snake through its three strips. The open question about twenty outputs with what was measured; the one about legs 3 to 10 reworded for the target. A line in the change log. |
| `docs/core.md` | `led_count`; the memory table for the target; the benchmark's clip and its figures. |
| `docs/converter.md` | The canvas of `import` for both kinds; the dense clip with the target file and its sizes. |
| `docs/emulator.md` | The demo show and its commands; the two views for both kinds, with the arrangements and the track rules of this design; the check list by eye; what was checked. |
| `docs/firmware.md` | The outputs: twenty, four RMT and sixteen parallel, and the patch; "What the firmware changes in WLED"; the limiter with 3,600 LEDs; the probe's two new members; the measurements; the owner's checks; "Verified on the board". |
| `README.md` | The line on the mapping: a snake of rows or of columns. |
| `firmware/patches/README.md` | The patch. |

`docs/show.md`, `docs/commands.md`, `docs/wifi.md` and `docs/android-app.md` name no
target and no kind of leg and stay as they are.

**The check list by eye** of `docs/emulator.md` keeps the steps for the criteria of seed
03, with the demo show of twenty legs and the dense 60 x 60 clip in them, and gains the
steps of Requirement 18, marked `(seed 05, <requirement>.<criterion>)`. Its test in
`tests/emulator/test_docs.py` reads both sets of numbers.

**The owner's checks** of `docs/firmware.md` gain two steps. One puts the wired strip on a
lane of the parallel driver: a mapping of twenty legs of one row of 60 that lists the leg
on pin 1 last makes pin 1 the sixteenth lane, and the strip must show the first row of that
leg. The other is the demo show on twenty wired legs.

## Order of work

1. The spike on the board comes first, as the seed asks, and needs none of the rest.
2. The rate with a dense clip follows at once: both are about the board, and the
   measurements of the first decide the second.
3. The format: the document and the converter's reader, then the core, then the page. The
   target file is added with the task of the page, when every reader can read it.
4. The mapping view, then the tool for `docs/mapping.md`.
5. The board with the target file, while the ten-leg file is still there for the tests it
   replaces.
6. The ten-leg file and its demo show go, and every test moves to 60 x 60.
7. The documents, the check list by eye, and the last run of all five suites.

## Risks

1. **The sixteen-lane form may not work** (F14). The spike finds out before anything else,
   with pulses counted at the pins, and the seed gives the fallback.
2. **The rate.** The estimates say the loop as it is does not hold 49 with a dense clip.
   The task on the other core is the planned answer; it is new code that runs beside
   WLED's loop, and its three assumptions are untried.
3. **The pulse counter** on a driven pin is untried (A3).
4. **Crossing lines.** Eighty-eight crossings are a lot to look at. The rules keep them
   regular; whether the result is clear is judged by eye in the check list.
5. **The page with 3,600 LEDs** may fall below 49 with the dense clip; the remedy is named
   under "Drawing 3,600 LEDs".
6. **Time on the board.** The board suite takes half an hour and is run four times.
7. **LEDs on eighteen of the twenty pins have never been seen**, and nothing in this seed
   changes that: it stays an owner's check.
8. **DVD bounce on a square canvas** is a square on one diagonal. It is correct and dull;
   the owner may want another path.
