# Design: ODRGX text and clock animations

## Overview

The core learns a second kind of file beside ODRG: the container ODRGX, whose header names
its payload. A frames payload is an ODRG file and plays through the decoder of today. A
text payload holds the text, its settings and its layout, made by the converter; a widget
payload holds a clock's settings. For those two the core holds the payload in memory while
it plays and draws the picture of the time at each refresh into the pixel buffer, from
which the LED data is made as for a frames file. The converter's library has the same
drawing rules in JavaScript, and the app's preview uses them. Reference pictures in
`tests/vectors/procedural/` hold the two to the same pixels.

```
JSON source (text / widget / frames)
        |  converter: layout (bidi, wrapping), pass length, encode
        v
   X.odrgx  ----upload / pack / card---->  core: check, hold, draw at each refresh
        |                                        |
        +--> app preview: converter library draws the same pixels
```

## What this design relies on

From the sources of this branch, which holds seeds 28 to 31 (task 1) and 38:

- `core/src/core.cpp`: the start reads the header of each file (`open_file`), or the whole
  file for a host that cannot change its storage (`check_file`); the check after the start
  and a drive's check take one step a refresh through `check_file_step`: the header, one
  frame record, the end.
- `core/src/upload.cpp`: the check of an uploaded file takes the same steps.
- `core/src/player.cpp`: `open_stream` opens an animation's file for one turn and one
  loop, `show_at` brings the pixel buffer to the picture of a time, `turn_ms` gives the
  length of a turn, `advance` finds the turn of the playlist or of a cycle, `fill_leds`
  makes the LED data from the pixel buffer, through the decoder's palette when it has one.
- `core/src/core_state.h`: `FileInfo` of 48 bytes, with 3 bytes of padding after the name;
  `DriveEntry` of 16 bytes with one byte free; the core object, at most 4,096 bytes, now
  3,384; the decoder's window of 32,768 bytes, `core.window`, which only a compressed
  frames file uses.
- The memory of the core is 124,629 bytes of the 131,072 it may use for the target file,
  128,725 with a drive (`docs/core.md`, "Memory"): there is no room for a new block of a
  few kilobytes.
- `converter/lib/`: `odrg.js` encodes and decodes ODRG; `show.js` checks a show and its
  names; `pack.js` packs a show from sources; `index.js` is what the app imports, beside
  its own web code, as `converter/`.
- `app/www/screens/storage.js`: the storage screen, which makes an animation from a video
  and uploads it with `upload.js`, as a new item with the lowest free id.
- The shared contract of the run of 2026-10-24: `list` items gain `type`, one of
  `"frames"`, `"text"`, `"widget"`; a missing `type` counts as `"frames"`.

## The container

All numbers little-endian.

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | `4F 44 52 58`, "ODRX" |
| 4 | 1 | Container version | 1 |
| 5 | 1 | Type | 1 frames, 2 text, 3 widget |
| 6 | 1 | Type version | 1 for each of the three |
| 7 | 1 | Reserved | 0 |
| 8 | 2 | Width | W, at least 1 |
| 10 | 2 | Height | H, at least 1 |
| 12 | 4 | Loop | milliseconds of one loop, 1 to 4,294,967,295 |
| 16 | 4 | Payload | P, the bytes after the header |

The file is 20 + P bytes. The loop is the sum of the frame durations of a frames payload,
the length of a pass of a text, and the seconds of a clock times 1,000. The start reads
the header only, as it reads the 16 bytes of an ODRG file today, and so knows the type and
the length of every file at once; the check after the start reads the payload and refuses
a loop that is not the payload's.

The reasons, beside those of ODRG files: `bad-container` (container version or reserved
byte), `unknown-type`, `unknown-type-version`, `payload-size` (P is not the rest of the
file, or above the type's limit), `bad-settings` (a setting out of its range),
`bad-text` (the text is not UTF-8 or not 1 to 512 bytes), `unknown-font`, `bad-glyph` (a
glyph outside the font or outside the block), `unknown-widget`, `does-not-fit`,
`loop-mismatch`, and `canvas-too-large` (a text or a clock on a canvas of more than
65,534 bytes). A frames payload with a fault has the reason of ODRG files.

## Payload: frames

An ODRG file of `format.md` as it is, whose width and height are those of the container.
The decoder of today reads it, from byte 20 of the file on.

## Payload: text, version 1

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Font | 1 `small`, 2 `medium`, 3 `large` |
| 1 | 1 | Font version | the version the layout was made with |
| 2 | 1 | Effect | 0 `static`, 1 `marquee`, 2 `slide`, 3 `pan` |
| 3 | 1 | Motion | 0 `left`, 1 `right`, 2 `up`, 3 `down` |
| 4 | 1 | Align | 0 `left`, 1 `center`, 2 `right` |
| 5 | 1 | Vertical align | 0 `top`, 1 `middle`, 2 `bottom` |
| 6 | 1 | Direction | 0 `auto`, 1 `ltr`, 2 `rtl` |
| 7 | 1 | Wrap | 0 or 1 |
| 8 | 3 | Colour | red, green, blue |
| 11 | 3 | Background | red, green, blue |
| 14 | 2 | Speed | pixels a second, 1 to 240 |
| 16 | 2 | Pause | milliseconds, 0 to 65,535; at least 20 for `static` |
| 18 | 2 | Text bytes | T, 1 to 512 |
| 20 | 2 | Glyphs | G, 0 to 512 |
| 22 | 2 | Block width | BW, 1 to 65,535 |
| 24 | 2 | Block height | BH, 1 to 65,535 |
| 26 | 2 | Reserved | 0 |
| 28 | T | Text | UTF-8, as written |
| 28 + T | 6 G | Glyphs | each: glyph index, x, y, three 16-bit numbers |

P is 28 + T + 6 G, at most 3,612. Direction and wrap are kept for editing: the layout is
already made. A glyph's index is a place in its font's table; x and y are the place of its
cell's top left corner in the block, in pixels, with y growing downwards; its cell lies
inside the block. Spaces have no glyph.

### The fonts

| Font | Id | Table | Ascent | Descent | Pitch | Scale |
|---|---:|---|---:|---:|---:|---:|
| `small` | 1 | small | 7 | 2 | 10 | 1 |
| `medium` | 2 | medium | 10 | 3 | 14 | 1 |
| `large` | 3 | small | 7 | 2 | 10 | 2 |

A glyph is a cell of `ascent + descent` rows and its own width in columns; its advance is
its width and one column of spacing. The space is a dark glyph, 2 columns wide in `small`
and 3 in `medium`. Lines are a pitch apart, times the scale. Each table has the
95 printable ASCII characters and the 27 Hebrew letters from U+05D0 to U+05EA, 122 glyphs,
in the order of their code points, and version 1.

The sources are `fonts/small.txt` and `fonts/medium.txt`: a header of `name`, `id`,
`version`, `ascent` and `descent`, then for each glyph a line
`glyph U+XXXX` and its rows, `#` for a lit pixel and `.` for a dark one. `node
fonts/generate.mjs` writes `core/src/font_tables.cpp` and `converter/lib/fonttables.js`
from them, with the sine table of the clocks; a test of the converter's suite fails when
either is not what the sources give.

### The layout, in the converter

1. Every character is one of the repertoire, else `unsupported-character`, naming it and
   its code point.
2. The text is split at line feeds into paragraphs.
3. Each paragraph gets its levels by the Unicode Bidirectional Algorithm, UAX #9, for these
   classes: `L` for `A`-`Z` and `a`-`z`; `R` for the Hebrew letters; `EN` for the digits;
   `ES` for `+` and `-`; `ET` for `#`, `$` and `%`; `CS` for `,`, `.`, `/` and `:`; `WS`
   for the space; `ON` for the other printable ASCII characters. With no explicit
   embeddings these are the rules P2 and P3 (unless the direction is forced), W4 to W7, N1,
   N2, I1 and I2.
4. With wrapping, a paragraph is broken greedily at spaces into lines whose width is at
   most W; a word wider than W is broken between characters. Spaces at the end of a
   wrapped line are dropped. Without wrapping a paragraph is one line.
5. Each line is reordered by L1 and L2, and in a run of an odd level `(`, `)`, `<`, `>`,
   `[`, `]`, `{` and `}` take their mirror's glyph (L4).
6. Glyphs are placed from x 0 in visual order; a line's width is the sum of its advances
   less the last spacing. BW is the widest line, at least 1; a line is placed in the block
   at 0, `(BW - width) / 2` or `BW - width`, by the alignment. Line i lies at
   `y = i * pitch * scale`; BH is `lines * pitch * scale - scale`.

### The pass and the place of the block

Let `X0` be 0, `(W - BW) / 2` or `W - BW` by the alignment, and `Y0` be 0,
`(H - BH) / 2` or `H - BH` by the vertical alignment, divisions rounded down, and
`steps(d) = ceil(d * 1000 / speed)`, the milliseconds `d` pixels take. At a time t of the
pass, `moved(t) = floor(t * speed / 1000)`. Horizontal motions place the block at `Y0`,
vertical ones at `X0`.

| Effect | Fits | Pass | The block's x (left, right) or y (up, down) at t |
|---|---|---|---|
| `static` | BW <= W, BH <= H | pause | X0, Y0 |
| `marquee` left | BH <= H | steps(W + BW) | W - moved(t) |
| `marquee` right | BH <= H | steps(W + BW) | -BW + moved(t) |
| `marquee` up | BW <= W | steps(H + BH) | H - moved(t) |
| `marquee` down | BW <= W | steps(H + BH) | -BH + moved(t) |
| `slide` left | BW <= W, BH <= H | in + pause + out, in = steps(W - X0), out = steps(X0 + BW) | max(X0, W - moved(t)); then X0; then X0 - moved(t - in - pause) |
| `slide` right | the same | in = steps(X0 + BW), out = steps(W - X0) | min(X0, -BW + moved(t)); X0; X0 + moved(t - in - pause) |
| `pan` left | BH <= H | 2 pause + 2 steps(T), T = max(0, BW - W) | from S = 0 (X0 when T is 0): S during the first pause, S - moved, S - T during the second pause, then S - T + moved |
| `pan` right | BH <= H | the same | from S = W - BW (X0 when T is 0) the other way |

`slide` and `pan` up and down are the same in y, with H, BH, `Y0` in place of W, BW,
`X0`. A `pan` that moves nothing still holds for both pauses, at least 20 milliseconds in
all. Every value is a whole number; the core and the converter compute them in 64-bit
integers.

### Drawing a text

The pixel buffer is filled with the background. For each glyph whose cell, at the block's
place, meets the canvas, each lit pixel of its rows becomes `scale x scale` pixels of the
colour. Rows of the canvas are counted from the top here: canvas row r is the format's
row `H - r`. Glyphs that lie wholly outside are passed over by comparing their cell with
the canvas, so the work is bounded by the 512 glyphs and the canvas.

## Payload: widget, version 1

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Widget | 1 `analog`, 2 `digital`, 3 `melting` |
| 1 | 1 | Reserved | 0 |
| 2 | 2 | Seconds | 1 to 3,600 |
| 4 | 3 | Face | red, green, blue |
| 7 | 3 | Hands | red, green, blue |
| 10 | 3 | Rim | red, green, blue |
| 13 | 3 | Background | red, green, blue |
| 16 | 2 | Least speed | 1 to 3,600, times real time |
| 18 | 2 | Greatest speed | the least to 3,600 |

### The seed

The core keeps a 32-bit `noise`, which takes in the timestamp of every `odrig_core_poll`
with MurmurHash3's finalizer, `mix`. When a clock's turn begins, its seed is
`mix(noise ^ mix(item id ^ turn's start))`, or 1 when that is 0; a turn begins at a new
start time of the turn, so `play` always gives a new seed and a loop within the turn does
not. The host gives no randomness: the timing of the refreshes does. With the same
timestamps the core gives the same seeds, which keeps it repeatable for the tests.

### The virtual time

From the seed, xorshift32 gives in turn: the start, `seed % 43,200,000`; the base speed
`b = least + r % (greatest - least + 1)`; the swing `A = min(b - least, greatest - b) *
(r % 101) / 100`; the period `P = 6,000 + r % 14,001` ms; the phase `phi = r % 1,024`. At t
milliseconds into the turn:

```
v(t) = start + b * t + floor(A * P * (c(phi) - c(phi + 1024 * t / P)) / 102,944)
```

where `c` is the cosine of a sine table of 1,024 entries in units of 1/16,384, read
between its entries by linear interpolation in steps of 1/65,536 of an entry, and 102,944
is 2 pi times 16,384. Its rate of change is `b - A sin(...)`, which is never below the least
speed. The dial's hour hand is at `v mod 43,200,000` of a turn, the minute hand at
`v mod 3,600,000`, and the digital clock shows the hour from 1 to 12 and the minutes of `v`.

### Drawing a clock

All three draw in half pixels about the canvas's centre, with the sine table for every
angle and 64-bit integers for every product.

- **Analog**: the background; a disc of radius R = min(W, H) / 2 - 1 of the face's colour
  with a rim of 2 pixels; twelve marks; the hour hand to 55 % of R and 2 pixels wide, the
  minute hand to 85 % and 1 pixel; a pivot of the hands' colour.
- **Digital**: the background, and `h:mm` in `large`, centred, in the face's colour, the
  colon in the rim's colour and shown in the first half of every real second.
- **Melting**: each canvas pixel is taken back into the plane of an analog dial through
  the fold: a tilt chosen by the seed between 25 and 40 degrees, a fold line below which
  the face hangs down and narrows towards a drip, and a slow wave along the fold whose
  phase moves with the real time of the turn. The point in the dial's plane is drawn as
  the analog clock draws it, shaded darker the deeper it hangs, with a crown and a ring at
  the top of the rim. Pixels that land outside the watch are the background.

## The core

New sources, each compiled by every host:

- `core/src/container.h/.cpp`: `ContentHeader` (type, loop, payload, width, height,
  whether it is a container) and `content_open`, which reads the first bytes of a file
  through a `FileSource`: an ODRG file's decoder is opened on it from its first byte, a
  container's header is checked, and a frames container's decoder is opened at byte 20.
  `FileSource` gains `rewind`, which goes back to the first byte while the first block
  read is still in its buffer, so the magic can be looked at first.
- `core/src/text.h/.cpp`: the text payload's check, reading from a `FileSource` byte by
  byte without holding it; its pass; its drawing from the payload in memory.
- `core/src/clock.h/.cpp`: the widget payload's check; the seed's mixing, xorshift32, the
  virtual time; the three drawings.
- `core/src/font_tables.cpp`, generated, and `core/src/fonts.h`: the two tables and the
  sine table, in read-only data.

Changes to what is there:

- `FileInfo` gains `type`, in its padding; `DriveEntry` gains `type`, in its free byte.
  The core object gains the noise, the seed and its turn, and whether the open stream is
  drawn. No block is added.
- The start reads a container's header (`content_open`); its loop is the file's length
  from then on. A host that cannot change its storage checks the whole payload there.
- `check_file_step`, used by the check after the start and a drive's check, and the
  upload's check: the header step opens with `content_open`; a text or a widget is checked
  in one step, its payload of at most 3,612 bytes; the last step finds the end of the file,
  which must be at 20 + P bytes. A loop that differs is `loop-mismatch`.
- `open_stream`: a text's or a clock's payload is read into `core.window`, whole, and the
  decoder's palette is set to none, so that `fill_leds` takes the pixel buffer as colours.
- `show_at`: a drawn stream draws the picture of `in_turn` modulo the loop for a text, and
  of `in_turn` for a clock, whose seed belongs to the turn.
- `turn_ms` and `advance`: a text's longest time is rounded up to whole passes; a cycle's
  turns are walked one by one, each `seconds` long and a text's rounded up to whole passes,
  with whole rounds of the cycle taken off by division as the playlist does.
- `list` writes `type`; `status` writes `seed`; `read` and `upload expect` are new.
- The show's file names may end in `.odrgx`.

## Commands

`read <id> <offset>`: the reply is `{"ok":true,"bytes":<size>,"data":"<base64>"}` with up
to 600 bytes of the file from the offset, read with the host's `read_at`; at the end of the
file `data` is empty. It is refused with `bad-argument` for an offset above the size,
`show-invalid`, `busy` while the check after the start runs, `unknown-id` for an id that is
no animation of the show or of a drive, and `storage-error` when the host cannot read.

`upload expect <crc32>`, after `upload begin` and before `upload end`: the core reads the
file of the upload's item through `read_at` and compares its CRC-32. It is refused with
`no-upload` when no upload is open, `stale`, and the upload discarded, when the id has no
animation item or its file has another CRC-32, `bad-argument` when that file is longer than
16,384 bytes, and `storage-error` when it cannot be read. `stale` stands after
`mapping-conflict` in the order of the codes.

`list`: every animation item gets `"type":"frames"`, `"text"` or `"widget"`, as its last
member. `status`: `"seed":<n>` or `"seed":null`, as its last member.

## The converter

- `converter/lib/fonttables.js`, generated; `converter/lib/bidi.js`, the algorithm of the
  layout's step 3 and 5; `converter/lib/textlayout.js`, the layout; `converter/lib/draw.js`,
  the pass, the place of the block, the drawing of a text and of the three clocks, the
  seed's mixing and the virtual time, with the same integer rules as the core;
  `converter/lib/odrgx.js`, the container, the two descriptors and their JSON sources.
- The JSON source of a text: `version` 1, `type` `"text"`, `width`, `height`, `text`,
  `font`, `color`, `background`, `align`, `valign`, `direction`, `wrap`, `effect`,
  `motion`, `speed`, `pause_ms`; of a clock: `version`, `type` `"widget"`, `width`,
  `height`, `widget`, `seconds`, `face`, `hands`, `rim`, `background`, `speed_min`,
  `speed_max`. Colours are the integers of the JSON frames. Every member is required, and
  no other is allowed.
- `encode IN.json OUT.odrgx` makes a container of a text, a clock or JSON frames;
  `decode IN.odrgx OUT.json` gives the JSON source of a text or a clock, or the JSON frames;
  `check FILE --width W --height H` checks either kind; `pack` takes `X.json` as the source
  of `X.odrgx`.
- `index.js` exports the new modules, so the app has them.

The Python library gains `odrig/odrgx.py`, which splits a container's header from its
payload, for the tests' reference player, and `odrig/show.py` takes `.odrgx` names.

## The app

On today's storage screen, under "Add an animation", two buttons beside the choice of a
video: "Make a text" and "Make a clock". Each opens a form:

- The text's form: a field for the text, the font, the two colours, the alignments, the
  direction, wrapping, the effect, the motion, the speed and the pause; a canvas of the
  target's size, drawn larger, that plays the pass again and again with `draw.js`; a line
  with the pass's length, or why the text cannot be made.
- The clock's form: the kind, the seconds, the four colours, the two speeds; the canvas,
  and a button for a new seed.
- "Upload" makes the `.odrgx` file with `odrgx.js` and uploads it as a new item, with the
  lowest free id and a file name from the text's first letters that fit the naming rule,
  or `clock-<kind>`, made unique as a video's is.

Editing: a row of the installed list whose `type` is `text` or `widget` has "Edit". It reads
the file with `read`, decodes it with `odrgx.js` and opens its form with "Save" and
"Cancel". Saving uploads to the item's id under its file name with `upload expect` and the
CRC-32 of the bytes that were read; `stale` gives the message that another controller
changed the animation, and the form stays open with the edits. A drive's animation has no
"Edit", as it has no "Remove".

## The emulator and the firmware

- `emulator/host.py` takes a drive's `.odrgx` names; `preview` names a single `.odrgx`
  file `preview.odrgx`.
- `firmware/usermod/odrig_drive.cpp` takes the card's and the stick's `.odrgx` names.
- The emulator's suite plays a show of the reference texts and clocks and compares the
  LEDs at chosen times with the reference pictures, which are kept as PNG files so that a
  person can look at them.
- `python3 firmware/fw.py build` builds the firmware with the new sources; the font tables'
  bytes are those `generate.mjs` prints, and the image's growth is recorded.

## Tests

- `converter/tests/`: the fonts' sources against the generated tables; every glyph of the
  repertoire in both fonts; the layout of the golden cases; the bidi cases of UAX #9 for
  the classes above; the pass of every effect and motion; the reference pictures; the JSON
  sources strict; encode, decode and check of every type; refusals with their reasons.
- `tests/core/`: legacy vectors and the demo show unchanged; frames containers play as
  their ODRG file; the reference pictures through the test host; every refusal of the
  container and the payloads at the start, in the check after it, in an upload and from a
  drive; the turn of a text in the playlist, in a cycle and with `max_seconds`; `play` and
  `off` at once; a seed for each turn, kept through the turn and in `status`; the virtual
  time at irregular refreshes; `list` with `type`; `read` and `upload expect`.
- `tests/emulator/`: the reference pictures through the emulator; a drive's `.odrgx`.
- `tests/app/`: making, previewing, uploading and editing a text and a clock, a stale
  edit, an unsupported character, a block that does not fit, a cancelled upload, and a
  drive's animation without "Edit".
- `tests/firmware/`: the drive's `.odrgx` names.

## Memory

No new block. A text's payload, at most 3,612 bytes, and a clock's 20 bytes are held in
the decoder's window while they play, since the stream is either a frames file or a drawn
one. The check reads a payload byte by byte through its source. The tables are read-only
data: 122 glyphs of each font, 1,464 bytes for `small` and 1,952 for `medium` with their
code points and widths, and 2,048 bytes of sine table.

## Decisions

- The runtime format is ODRG and ODRGX; the sources of a text and a clock are typed JSON,
  not JSON frames, and the core draws them at runtime from validated settings with fonts
  and widgets that are built in. No file brings code, fonts or a network to the player.
- Fonts live in the firmware and in the converter, generated from one source; a text file
  names a font and its version and holds no glyph pictures.
- The layout is made by the converter and stored; the core checks its bounds and draws it.
- A clock's randomness comes from the timing of the refreshes, mixed with the turn.
- New commands and reply members: `read`, `upload expect`, `stale`, `type` of `list` and
  `seed` of `status`, approved by the owner in advance on 2026-10-24.

## What needs the owner

The look of Hebrew and of the clocks on the LEDs, the melting clock's moving hands, the
rate on the board, and the app on a phone: task 13.
