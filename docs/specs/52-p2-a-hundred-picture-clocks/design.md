# Design: a hundred picture clocks

## Overview

Three kinds of work make the 112 files:

- **Two new widgets** in the widget payload, a picture dial and a picture display. Each
  carries its base picture, an ODRG file of one frame and at most 8 colours, and the
  geometry of what the player draws over it: hands and caps, or fields of digits. The core
  decodes the picture once a turn into the pixel buffer it has and draws the hands or the
  digits into a layer in the DEFLATE window, which no other work uses while a drawn type
  plays; the LED data takes the layer where it is set and the picture elsewhere. The
  converter draws the same pixels, and makes and reads the files.
- **Frames from a still picture**: a motion of parts, level, flicker, pulse, turn and
  swing, that the converter applies to a base picture at each frame's time.
- **The making**: an inventory of the 100 tiles, read by a new subcommand `clocks`; and
  the twelve, rendered from their scripts in a headless Chrome and reduced to 8 colours.

The files, their previews, readmes and sources go into the collection's folder `clocks/`;
the previews into `thumbnails/`.

## What this design relies on

The code is `master` at `000303c`: seeds 2 to 49 and 51's documents, with seed 37's
widget payload (`core/src/clock.cpp`, `converter/lib/draw.js`, `converter/lib/odrgx.js`),
seed 44's previews (`converter/lib/thumbnail.js`, `thumbnails/`) and seed 31's bounded
decoding. Where the code differs from what this design says, the code is followed and the
difference is recorded in `docs/drifts.md`.

- The player holds a drawn payload in the window, `core.window`, 32,768 bytes, and draws
  a text or a clock into `core.pixels` as three bytes for each pixel; `fill_leds` reads
  `core.pixels` through `core.decoder.palette` when `core.decoder.colours` is not 0.
- The DEFLATE window is used by a frames file being played, by the start's header reads
  and by the mapping's diagonal; the player closes its stream before the diagonal is
  decoded, and the check after the start and the upload's check have a window of their
  own, `core.check_window`, with `core.check_pixels` and the checker's decoder.
- `drawn_read` is called in four places: the check of the start without a checker
  (`check_file`), a step of the check after the start (`check_file_step`), the upload's
  check (`upload.cpp`) and the opening of a stream (`open_stream`). The test host calls it
  for `decode` and `render`.
- The converter's `odrg.js` has `bestRecord` and `container`, from which an ODRG file with
  a given palette order is made.

## The widget payload

The widget payload of type 3, version 1, names its widget in its first byte: 1 `analog`,
2 `digital`, 3 `melting`, 4 `picture-dial`, 5 `picture-display`. Widgets 1 to 3 have the
20 bytes they have today. A picture widget has a head, its parts, and its picture:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Widget | 4 `picture-dial`, 5 `picture-display` |
| 1 | 1 | Reserved | 0 |
| 2 | 2 | Seconds | the loop, 1 to 3,600 |
| 4 | 2 | Least speed | times real time, 1 to 3,600 |
| 6 | 2 | Greatest speed | the least to 3,600 |
| 8 | 1 | Direction | 0 `forward`, 1 `backward`, 2 `random`: chosen by the seed |
| 9 | 1 | Turns | the greatest chance of a turn at a slowest point, in percent: 0 to 100, and 0 unless the direction is `random` |
| 10 | 1 | Parts | a dial's hands, 1 to 8; a display's fields, 1 to 4 |
| 11 | 1 | Caps | a dial's caps, 0 to 4; 0 for a display |
| 12 | | Parts | the hands, 10 bytes each, then the caps, 6 bytes each; or the fields, 22 bytes each |
| | | Picture | an ODRG file, to the end of the payload |

A hand:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Unit | 0 the hour, a turn in 12 hours; 1 the minute, a turn in an hour; 2 the second, a turn in a minute |
| 1 | 1 | Colour | an index into the picture's palette |
| 2 | 2 | Pivot x | half pixels from the canvas's left edge, 0 to 2 W |
| 4 | 2 | Pivot y | half pixels from the canvas's top edge, 0 to 2 H |
| 6 | 1 | Length | half pixels from the pivot to the tip, 1 to 255 |
| 7 | 1 | Tail | half pixels behind the pivot, 0 to 255 |
| 8 | 1 | Half width | half pixels to either side of the hand's line, 1 to 15 |
| 9 | 1 | Offset | whole hours added to the time, a signed byte, -12 to 12 |

A cap: x and y, 2 bytes each, as a pivot; its radius in half pixels, 1 to 255; its colour.

A field:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 2 | Left | pixels from the canvas's left edge |
| 2 | 2 | Top | pixels from the canvas's top edge |
| 4 | 2 | Width | at least 1, the box within the canvas |
| 6 | 2 | Height | at least 1, the box within the canvas |
| 8 | 1 | Font | 1 `small`, 2 `medium`, 3 `large`, 4 `tiny` |
| 9 | 1 | Digits | the colour of the digits, an index into the palette |
| 10 | 1 | Colons | the colour of the colons |
| 11 | 1 | Blink | 0 or 1: the colons are shown in the first half of each real second only |
| 12 | 1 | Offset | whole hours added to the time, a signed byte, -12 to 12 |
| 13 | 1 | Reserved | 0 |
| 14 | 8 | Pattern | 1 to 8 characters of `H`, `I`, `h`, `M`, `m`, `S`, `s`, `:` and space, then zero bytes |

The pattern's characters: `H` the tens of the hour of a 12-hour clock, 1 to 12, so `0` or
`1`; `I` the same, but nothing at all, no glyph and no advance, when it is 0; `h` the ones
of the hour; `M` and `m` the tens and ones of the minutes; `S` and `s` those of the
seconds; `:` a colon; a space the font's space. So `Ih:Mm` is `h:mm`, `Hh:Mm` is `hh:mm`,
`Ih:Mm:Ss` is `h:mm:ss`, and `Mm:Ss` is a timer's minutes and seconds.

The picture is an ODRG file of the container's canvas, of exactly one frame and a palette
of 1 to 8 colours. The duration of its frame is not used. It is compressed or not as any
ODRG file; the converter writes it compressed.

The header's loop is 1,000 times the seconds, as for every clock. The largest payload of a
widget is 32,768 bytes: the largest picture, of a canvas of 21,844 pixels, has 21,889
bytes uncompressed.

### The reasons, in their order

A widget is read front to back: the canvas (`canvas-too-large`), the widget's byte
(`unknown-widget` for 0 and above 5); for widgets 1 to 3 the payload's length, 20, then
as today; for a picture widget the head (`truncated`, `bad-settings` for a reserved byte,
seconds, speeds, a direction above 2, turns above 100 or not 0 without `random`, parts or
caps out of their counts), each hand, cap and field as it is read (`bad-settings` for a
value outside its range, a box outside the canvas or empty, a pattern with no character, a
character not of the pattern's, or a non-zero byte before a later character;
`unknown-font` for a font that is not 1 to 4), then the picture's ODRG header (the
reasons of "ODRG files"), `canvas-mismatch` for another canvas, `bad-picture` for a frame
count that is not 1 or a palette of 0 or more than 8 colours; then `bad-settings` for a
colour of a hand, a cap or a field that is not below the palette's size; then the
picture's frame record and its end (the reasons of "ODRG files"); then the payload's
length (`payload-size`), and last the loop (`loop-mismatch`). `bad-picture` is a new
reason, in the core, the converter, the Python library and [reasons.md](../../reasons.md).

The vector `unknown-widget.four` becomes `unknown-widget.six`. `payload-size.header`, a
widget 1 whose header says 21 bytes, keeps its reason: 21 is no longer above the largest
payload, but a widget 1 has 20 bytes.

### The JSON source of a picture clock

Read as strictly as every source, with exactly these members: `version` 1, `type`
`"widget"`, `width`, `height`, `widget` (`"picture-dial"` or `"picture-display"`),
`seconds`, `speed_min`, `speed_max`, `direction` (`"forward"`, `"backward"` or
`"random"`), `turns` (0 to 100, 0 unless `random`), `palette` (1 to 8 colours, as in JSON
frames, no two the same), `picture` (H strings of W characters, the top row first, each
character the digit of a palette index), and for a dial `hands` and `caps`, for a display
`fields`. A hand is an object with exactly `unit` (`"hour"`, `"minute"` or `"second"`),
`color`, `x`, `y`, `length`, `tail`, `half` and `offset`; a cap `x`, `y`, `radius` and
`color`; a field `left`, `top`, `width`, `height`, `font` (`"small"`, `"medium"`,
`"large"` or `"tiny"`), `pattern`, `digits`, `colons`, `blink` (`true` or `false`) and
`offset`. A value outside its range is `out-of-range`. `decode` writes this source back
from a file, with two spaces of indent and each picture row on a line of its own.

## The virtual time with a direction

A picture widget takes from its seed, by xorshift32 as [format.md](../../format.md) says,
the eleven values of the existing clocks in their order, start to wave, and then:

| Name | From r | What it is |
|---|---|---|
| back | r % 2 | with `random`, 1 when the turn starts backward |
| chance | r % (turns + 1) | with `random`, the chance of a turn at each slowest point, in percent |

With Φ = phi * 65,536, the way forward `t` milliseconds into the turn is

```
u(t) = b * t + floor(A * P * (c(Φ) - c(Φ + floor(2^26 * (t % P) / P))) / 102,944)
```

so that the existing clocks' time is `start + u(t)`. The speed `b + A * s(Φ + ...)` is
least where the angle `Φ + floor(2^26 * (t % P) / P)` is three quarters of a turn: first
at `t0 = floor(P * ((3 * 2^24 - Φ) mod 2^26) / 2^26)`, then every P after it. The k-th
slowest point, k from 1, is at `t0 + (k - 1) * P`.

The way D(k) after k slowest points: D(0) is +1 for `forward`, -1 for `backward`, and for
`random` -1 when back is 1 and +1 otherwise. With `random`, D(k) is -D(k-1) when
`mix(seed ^ k) % 100 < chance`, and D(k-1) otherwise; `mix` is the finalizer of
[core.md](../../core.md), "Clocks". With n the number of slowest points at or before t:

```
n = 0:  v(t) = start + D(0) * u(t)
n > 0:  v(t) = start + D(0) * u(t0) + b * P * (D(1) + ... + D(n - 1)) + D(n) * (u(t) - u(t0) - (n - 1) * b * P)
```

Over a whole period u grows by exactly b * P, so the hands go back the way they came and
never jump. A part shows `(v(t) + offset * 3,600,000) mod 12 hours`, taken at or above 0.
A refresh computes the sum of D over the slowest points so far: a turn of an hour has at
most 600 of them, as P is at least 6 seconds.

## Drawing

A pixel x, y, counted from the top left from 0, has its centre at `2x + 1`, `2y + 1` half
pixels from the canvas's top left corner.

**A picture dial** at a time t of its turn: the base picture; over it each hand in its
order, and then each cap. A hand of the hour, the minute or the second points at
`floor(2^26 * (T mod U) / U)`, with T the part's time and U 12 hours, an hour or a
minute; its direction is `(s(a), -c(a))`, as the existing clocks' strokes. A pixel with
`u = 2x + 1 - pivot x` and `w = 2y + 1 - pivot y` is the hand's when
`-tail * 16,384 <= u * s(a) - w * c(a) <= length * 16,384` and
`|u * (-c(a)) - w * s(a)| <= half * 16,384`. A pixel is a cap's when
`u * u + w * w <= radius * radius`, u and w taken from the cap's place. A later part
covers an earlier one.

**A picture display**: the base picture; over it each field in its order. The pattern
becomes glyphs of its font, `large` being `small` at twice the size; a line is as wide as
its advances less the spacing after the last, as the digital clock's. Its left is
`left + floor((width - line) / 2)` and its top `top + floor((height - ascent * scale) /
2)`, where the ascent is the font's rows above the baseline: digits have no descent. Every
lit pixel of a glyph that falls inside the box takes the digits' colour, or the colons'
for a colon; with blink, a colon is drawn only while `t % 1,000 < 500`. Nothing is drawn
outside the box.

**The font `tiny`** is `fonts/tiny.txt`: id 4, version 1, ascent 5, descent 0, the digits
3 pixels wide, the colon 1 and the space 1. `fonts/generate.mjs` writes it with the
others into `core/src/font_tables.cpp` and `converter/lib/fonttables.js`; a font file
may name its own repertoire, and `tiny`'s is the ten digits, the colon and the space. The
texts' fonts stay 1 to 3: a text that names 4 is refused with `unknown-font`, as now.

## The core

- **`core/src/clock.h/.cpp`.** `clock_read(file, header, into, picture)` takes a fourth
  argument, `Picture`: the decoder, the inflate state, the window and the pixel buffer to
  decode a base picture with. Widgets 1 to 3 do not use it. A picture widget's head and
  parts, at most 12 + 8 * 10 + 4 * 6 = 116 bytes, are read into a buffer on the stack and
  checked; then `decoder->open` on the same source reads the picture's header,
  `decoder->next` decodes its one record into the given pixels, again while it gives
  `kPendingWork`, and `decoder->finish` reads to its end; then the file's length is
  compared with the payload's, and last the loop. With `into`, the head and parts are
  copied there at the end, after the window has served the inflate.
- **`clock_overlay(payload, seed, width, height, t, layer)`** writes the layer of a
  picture widget at a time of its turn: W * H bytes, 0 where nothing is drawn and the
  palette index plus 1 where a hand, a cap or a digit is. `clock_is_picture(payload)`
  says whether a payload is a picture widget's. The virtual time with its direction is
  shared by both and by `clock_virtual_time`.
- **`core/src/container.cpp`.** The largest widget payload is 32,768. `drawn_read` passes
  the `Picture` on.
- **Play.** `open_stream` of a picture widget calls `drawn_read` with the window as `into`
  and the player's decoder, inflate, window and pixel buffer as the picture's, so the
  pixel buffer holds the picture's indices, `core.decoder.colours` its palette's size and
  `core.decoder.palette` its colours. The window then holds the head and parts at 0 and
  the layer from byte 128, at most 21,844 bytes. `show_at` of a picture widget does not
  set `core.decoder.colours` to 0, and writes the layer with `clock_overlay` instead of
  drawing into the pixel buffer. `fill_leds` takes, for each LED, the layer's index where
  it is not 0 and the pixel buffer's otherwise, through the palette. The pixel buffer is
  not written after the picture is decoded.
- **The checks.** `check_file` passes the player's decoder, inflate, window and pixel
  buffer; `check_file_step` and the upload's check those of the checker, which they use
  for frames. A picture widget is still read and checked in one step.
- **The test host.** `decode` reads a picture widget whole, as a text; `render` decodes
  its picture, writes the layer and prints the picture through the palette, the layer
  over it, three bytes for each pixel, as the LEDs show it.
- **Memory.** No block is added and the core object does not change: the layer and the
  head live in the window, the picture in the pixel buffer, and the work of reading on
  the stack. A test compares the memory a show asks for with picture widgets and without
  them.

## The Python library

`odrig/odrgx.py`: the largest widget payload is 32,768. `odrig/errors.py`: `bad-picture`.
The reference player of `tests/core/support.py` takes a picture widget's pictures from the
core's `render`, as it takes a clock's.

## The converter

- **`converter/lib/odrgx.js`.** `decodeWidget` reads a picture widget in the core's order
  into `settings` with `widget`, `seconds`, `speedMin`, `speedMax`, `direction`, `turns`,
  `palette`, `picture` (the indices in the format's pixel order), and `hands` and `caps`
  or `fields`; `loadsWidget`, `dumpsWidget` and `encodeWidget` handle the JSON source. The
  picture is written by `odrg.bestRecord` and `odrg.container` with the palette in the
  source's order, so that the parts' colours keep their indices.
- **`converter/lib/draw.js`.** `WIDGETS` gains the two names; `clockOf` gives `back` and
  `chance` after `wave`; `pictureTime(settings, clock, seed, t)` is the virtual time with
  its direction; `drawClock` draws a picture widget as the base picture through its
  palette with `overlayOf(settings, seed, t, canvas)` over it; `overlayOf` is the layer
  the core writes. `pictureAt` of `odrgx.js` gives it as for any clock, so `thumbnail`
  makes its preview with the seed 1.
- **`converter/lib/motion.js`.** `framesOf(base, motion)` makes the JSON frames of a
  motion; see below.
- **`converter/lib/inventory.js`.** `loads(bytes)` reads an inventory strictly;
  `filesOf(inventory)` gives, for each tile, its name and the bytes of its file: the
  container of its picture clock, or the ODRG file of its motion's frames, compressed.
- **`converter/cli/`**: the subcommand
  `node converter/odrig.js clocks INVENTORY.json --out DIR`, which writes the files into
  `DIR`, made when it is missing, and prints a line `<name> <kind> <bytes>` for each. An
  inventory it refuses ends with status 1 and its reason, naming the tile, and nothing is
  written.

### The inventory

A UTF-8 JSON object with exactly `version` 1, `width`, `height` and `tiles`, 1 to 256 of
them. A tile has exactly `name` (`clock-001` to `clock-100`: letters, digits and dashes),
`tile` (1 to 100), `kind` (`"dial"`, `"display"` or `"motion"`), `about` (a few words of
what the tile shows), `palette` and `picture` as in a picture clock's source, and `clock`
for a dial or a display, `motion` for a motion. `clock` has the members of a picture
clock's source other than `version`, `type`, `width`, `height`, `widget`, `palette` and
`picture`. Names are unique.

### A motion

`motion` has exactly `seconds` (10 to 600), `frame_ms` (20 to 1,000, a multiple of 10
that divides the loop) and `parts`, 1 to 8 of them, applied in order: each part works on
the picture the parts before it made, from the base picture. Every part has `kind` and
`box`, `[left, top, width, height]` within the canvas. At the time t of a frame, within
the loop L:

| Kind | Members | At t |
|---|---|---|
| `level` | `inside` (indices), `fill`, `empty`, `rests` (`"bottom"`, `"top"`, `"left"` or `"right"`), `from` and `to` (percent) | The box's pixels of an `inside` index are the content. A share of the box, from its `rests` side, `from` percent at 0 and `to` percent at L / 2 and back, a triangle, is filled: its content pixels become `fill`, the others `empty`. |
| `flicker` | `variants` (2 or 3 lists of `[from, to]` pairs), `step_ms` | Variant `floor(t / step_ms) % count` recolours the box's pixels: an index `from` becomes `to`. The loop is a multiple of `step_ms * count`. |
| `pulse` | `variants` (2 to 8 lists of pairs) | The variants are gone through and back over the loop, evenly: step `floor(t * (2n - 2) / L)`, variant the step or `2n - 2` less it. |
| `turn` | `moving` (indices), `behind`, `centre` (`[x, y]` in half pixels), `degrees` (per loop, negative counter-clockwise) | The box's pixels of a `moving` index turn about the centre by `degrees * t / L`; where they were and are no longer, `behind`. |
| `swing` | `moving`, `behind`, `centre`, `degrees` (the swing to each side), `swings` (whole swings per loop) | As a turn, by `degrees * s(2^26 * swings * t / L) / 16,384`. |

A turn takes for each pixel of the box the pixel of the picture before the part at the
place the turn brings to it, `(cx + (du * c + dv * s) / 16,384, cy + (-du * s + dv * c) /
16,384)` halved and rounded down, with the sine table of the clocks and integer division:
so the same inventory gives the same bytes everywhere. A level's filled share of a box of
size S is `floor(S * (from * L + (to - from) * (L - |2t - L|)) / (100 * L))` rows or
columns. Every motion comes back at L to its picture at 0, so a file loops without a jump
when its turns are whole turns of the shape's symmetry, which the inventory sees to.

The frames are taken at 0, `frame_ms`, ... up to L, each `frame_ms` long, and encoded as an
ODRG file with a palette: consecutive frames that are the same merge, as `encode` merges
them.

## The hundred

The tools that prepare the tiles are scripts of their own, kept with the collection in
`clocks/source/tools/` and run from `scratch/`; they are not part of the repository, as
the inventory is not.

1. **Prepare.** Each cut tile `scratch/clocks/clock-NNN.png` is scaled to 60 x 60 with
   Pillow's box filter and reduced to at most 8 colours: Pillow's median cut on the
   scaled tile, then black, when the tile has pixels darker than 24 in each channel,
   taking the place of the colour nearest to it; every pixel takes the nearest of the
   colours. The script writes the skeleton of the inventory: each tile's palette and
   picture, and a kind from the list below.
2. **The dials**, by hand with tools: for each dial the pivot, the hands of the tile
   (an hour and a minute hand, and a second hand where the tile has one; a sundial's
   shadow is a dial with one hour hand), their lengths, tails, widths and colours, and
   the caps; the hands erased from the picture by painting their pixels with the colour
   of the face around them. A dial's numerals and marks stay: they are its face.
3. **The displays**: the box of the time, the font that fits it, the pattern the tile
   shows, the colours; the digits erased by painting the box with the display's
   background colour. Labels that are not the time, `GPS`, `NTP`, a date, the names of
   cities, stay.
4. **The motions**: a kind of motion for each tile that shows no time, its boxes and
   colours.
5. **Make**: `clocks` writes the 100 files into `build/clocks/`; `check` reads each.

The settings of a clock unless its tile calls for others: 30 seconds; the speeds 60 to
600 for a dial without a second hand and for `h:mm`, and 2 to 30 for a dial with a second
hand and for a display with seconds, so that the second hand and the seconds can be seen;
the direction `random` with turns 30. A motion runs 12 seconds, its frames 50 ms apart.

The kinds, by tile, from a look at the owner's picture: dials 1 to 3 (the sundials'
shadows), 15 to 20, 31 to 50, 57 to 59, 68, 70, 76, 77, 82 and 91; displays 21 to 30,
51 to 53, 60, 64, 66, 67, 75, 81, 83 to 86, 89 and 97 to 100; motions 4 to 14, 54 to 56,
61 to 63, 65, 69, 71 to 74, 78 to 80, 87, 88, 90 and 92 to 96. The tasks that make the
inventory may move a tile to another kind when its picture asks for it, and record it.

## The twelve

`render12.mjs`, kept with the tools, starts Chrome headless with a fresh profile in a
temporary folder, which it removes, and loads a page of its own with the script:

- the original six: `references/original/animation.js` in its DOM and style, with
  `requestAnimationFrame` and `performance.now` replaced by a clock the page steps, and
  the scene chosen by its select;
- the standalone six: `references/standalone/standalone-script.js`, whose
  `TimeAnimations.draw(ctx, scene, seconds)` draws a scene at a time.

It takes the 60 x 60 canvas at 0, 50, ... ms up to the period. The colours: black, then
every colour the script names (`#rgb`, `#rrggbb`, `rgb()` without transparency) that a
pixel of the file has exactly, the most used first, up to 8 in all; every other pixel
takes the nearest of them. The frames are encoded as ODRG; a file larger than 2 MB is
rendered again at 100 ms. The sizes and the rate of each go into the drift entry.

The comparison takes each reference GIF's frames at their times, maps them to the file's
8 colours the same way, and counts the pixels that differ from the file's frame at the
same time: the largest count and the mean, for each of the twelve, go into the drift
entry and the readmes.

## Where the files go

- `E:\artifacts\odrig\collection\clocks\`: the 112 files, `X.gif` the copy of its preview
  in `thumbnails/`, and `X.md` the readme of seed 46's shape: the title, then the 16 lines,
  `Source` naming the owner's picture and its tile, or the script and its reference GIF.
- `clocks/source/`: the owner's picture, `tiles/` with the 100 cut tiles, `inventory.json`,
  `base/` with each base picture as a PNG, `tools/` with the scripts.
- `thumbnails/`: `thumbnail --catalog thumbnails` of the 112 files, committed.
- `build/clocks/contact-sheet.png`: the first picture of each of the 112, for the report.

## The app and the emulator

The emulator plays the widgets through the core and needs no change; its suite plays the
reference pictures of the new widgets with those of the clocks. The app lists a picture
widget as a widget with its preview. Its "Edit" reads the file as today; when the read
gives a picture widget, the form is not filled and the screen says "This clock is made
from a picture: it cannot be edited here." A test of `tests/app/` shows it.

## Tests

- **The converter's suite**: the picture widgets read, written, refused with each reason;
  the JSON source strict and given back by `decode`; the virtual time forward equal to the
  existing clocks', backward its mirror, `random` turning only at slowest points and as
  the seed says; the drawing of a hand, a cap and each pattern character; the tiny font;
  a motion of each kind, its loop, and the same bytes twice; `clocks` on a small
  inventory, and its refusals.
- **The vectors**: `tests/vectors/widgets/` gains valid picture widgets and one invalid
  vector for each new refusal; `tests/vectors/procedural/` the reference pictures of the
  valid ones, at several times and seeds.
- **The core's suite**: the vectors, the reference pictures drawn by `render` equal to the
  converter's, a picture widget in a show played as the reference player plays it, from
  the start, an upload and a drive; the memory with and without them.
- **The emulator's suite**: the reference pictures on its LEDs, through the existing
  test of the procedural pictures.
- **The app's suite**: "Edit" of a picture widget.
- **The onboarding suite**: the pages.

## Decisions

Recorded at the end of `docs/drifts.md` under "Seed 52" by the task that applies each:
the payload's layout and its largest size; the reason `bad-picture`; the direction and the
slowest points; the font `tiny`; the inventory, its motions and the subcommand; the
tiles' kinds, a dial's numerals kept, the clocks' settings; the twelve's colours, rates
and comparison; where the tools are kept.

## What needs the owner

The owner's look at the clocks on the LEDs, a check only a person can make. No command is
added, and no decision of `docs/decisions.md` changes but the format's extension, which
the owner approved through the seed.
