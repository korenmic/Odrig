# Making the inventory entries of picture clocks (seed 52 of the Odrig repository)

You make, for some tiles of the owner's picture of 100 timekeepers, the entry of each tile
in the inventory: its base picture with its hands or its digits erased, and the geometry
of what the player draws over it. You write only files under
`C:\Users\koren\src\Odrig\scratch\clocks52\work\` (one JSON per tile) and
`C:\Users\koren\src\Odrig\scratch\clocks52\sheets\` (your preview sheets). Never touch
anything else: no git, no change in any repository folder, no file of `scratch/clocks/`,
nothing on any other drive. Run Python with `-I`:
`C:\Users\koren\src\Odrig\.venv\Scripts\python -I`. Node is `node`.

## What exists

- `C:\Users\koren\src\Odrig\its not the time frames.png`: the owner's picture, a grid of
  10 x 10 tiles numbered 1 to 100 in reading order (tile 85 and 86 are printed 95 and 96).
- `C:\Users\koren\src\Odrig\scratch\clocks\clock-NNN.png`: each tile cut, at about 122 px.
- `C:\Users\koren\src\Odrig\scratch\clocks52\skeleton.json`: for each tile its `name`,
  `tile`, `kind`, `about`, and the tile scaled to 60 x 60 and reduced to at most 8 colours:
  `palette` (integers 0xRRGGBB, index 0 the darkest) and `picture` (60 strings of 60
  characters, the top row first, each character the digit of a palette index).
- `C:\Users\koren\src\Odrig\scratch\clocks52\reduced\clock-NNN.png`: the same as images.
- `C:\Users\koren\src\Odrig\scratch\clocks52\tools\edit.py`: helpers, documented at its
  top: `load(n)`, `grid(pic, box)` (prints the indices with coordinates: read the hands
  and digits pixel by pixel this way, it is exact), `counts`, `replace_box`,
  `replace_disc`, `set_pixels`, `fill_box`, `hand`, `hand_at`, `cap`, `cap_at`, `write`,
  and the default settings `DIAL`, `DIAL_WITH_SECONDS`.
- `C:\Users\koren\src\Odrig\scratch\clocks52\tools\tile.mjs`: `node tile.mjs check
  work/clock-NNN.json` makes the tile's file with the converter and reads it back;
  `node tile.mjs sheet OUT.png work/clock-NNN.json ... --times 0,9000,21000 --seeds 1,2`
  draws one row per tile: the reduced tile before erasing, your base picture, then the
  clock as the player draws it at each time with each seed (the seed changes the time and
  the speed). Look at the sheets with your image reading tool and correct until they are
  right. `C:\Users\koren\src\Odrig\scratch\clocks52\work\clock-015.json` is a worked
  example of a dial (tile 15); its erasing still left a speck near the numeral 2 that a
  better entry would remove.

## The entry of a tile

`work/clock-NNN.json`, as `edit.write(entry, pic, clock=...)` writes it:

```json
{"name": "clock-015", "tile": 15, "kind": "dial", "about": "a wall clock with numbers",
 "palette": [...], "picture": ["...60 strings..."],
 "clock": {"seconds": 30, "speed_min": 60, "speed_max": 600, "direction": "random", "turns": 30,
           "hands": [...], "caps": [...]}}
```

For a display, `clock` has `fields` in the place of `hands` and `caps`. Keep `palette` as the
skeleton has it (the same 8 colours or fewer, the same order); every colour you draw with is
an index into it. The picture is the skeleton's with the hands or the time erased.

**A hand** (`edit.hand(unit, color, x, y, length, half, tail, offset)` with the pivot at the
centre of pixel x, y; `edit.hand_at` with the pivot in half pixels): `unit` `"hour"`,
`"minute"` or `"second"`; `color` a palette index; `x`, `y` the pivot in half pixels from
the top left (the centre of pixel x, y is 2x+1, 2y+1; a pivot between pixels is even);
`length` from the pivot to the tip and `tail` behind the pivot, in half pixels (1 to 255
and 0 to 255); `half` the half width in half pixels, 1 to 15 (1 draws a line about 1 pixel
wide, 2 about 2 pixels); `offset` whole hours added, -12 to 12. Hands are drawn in their
order, each over the ones before; then each **cap**, a disc of `radius` half pixels and a
`color` about `x`, `y` (`edit.cap`), over the hands: use one for the pivot's boss when the
tile has one. A dial has 1 to 8 hands and 0 to 4 caps; several pivots are allowed (a chess
clock, a world map with three small clocks: each its own hands).

**A field** of a display: `left`, `top`, `width`, `height` the box in pixels (within the
canvas); `font` `"tiny"` (digits 3 x 5, the colon 1 wide, a glyph advances its width + 1),
`"small"` (digits 5 x 7, the "1" 3 wide), `"medium"` (10 rows high) or `"large"` (small at
twice the size: digits 10 x 14); `pattern` up to 8 characters: `H` the tens of the hour of
a 12-hour clock (0 or 1), `I` the same but nothing at all when it is 0, `h` the ones of the
hour, `M` `m` the tens and ones of the minutes, `S` `s` those of the seconds, `:` a colon,
space. So `Ih:Mm` is h:mm, `Hh:Mm` hh:mm, `Ih:Mm:Ss` h:mm:ss, `Mm:Ss` a timer. `digits` and
`colons` palette indices; `blink` true or false (the colons show in the first half of each
second); `offset` hours. The text is centred in its box (horizontally, and vertically by the
font's height above the baseline) and clipped to it, so choose a box and a font in which the
widest time, `12:59` or `12:59:59`, fits whole. A display has 1 to 4 fields: a flip clock
or a band whose hours and minutes are apart gets one field for `Hh` and one for `Mm`; nixie
tubes one field per tube (`H`, `h`, `M`, `m`); three cities three fields with their
offsets.

## The rules the owner set

- The tile's hands (dial) or its time (display) are erased: paint their pixels with the
  colour of the face or of the display's background around them. A dial's numerals and
  marks stay: they are the face. Labels that are not the time stay (GPS, NTP, a date, the
  names of cities, a bpm).
- The drawn hands and digits use colours of the tile's palette: the hands the colour the
  tile's hands had (often the darkest), a second hand the colour of the tile's second hand
  when it has one (else leave it out); the digits the colour the tile's digits had.
- A dial has an hour and a minute hand, and a second hand only where the tile has one; a
  sundial's shadow is a dial with one hour hand, with the shadow's colour, about the foot
  of the gnomon.
- Proportions as the tile has them: the hour hand about half the dial's radius, the minute
  hand most of it, never over the numerals' ring if it can be helped; widths that read on
  LEDs (an hour hand `half` 2, a minute and a second hand `half` 1, as the tile suggests).
- Settings: `seconds` 30; `direction` `"random"`, `turns` 30; speeds `speed_min` 60 and
  `speed_max` 600 (`edit.DIAL`), or 2 and 30 (`edit.DIAL_WITH_SECONDS`) for a dial with a
  second hand and for a display that shows seconds.
- Check every entry with `tile.mjs check`, and look at every tile on a sheet at three times
  and two seeds. A tile is done when the base picture has no trace of the old hands or
  digits and the drawn ones sit where the tile's were and read.

## What to report

For each tile: done, its hands or fields in a few words, and anything you were unsure of.
Do not change a tile's kind; if a tile seems to be of another kind (a dial that shows no
time, a display that is not a time), make it as well as you can and say so.

## Motions: the tiles that show no time

A tile that shows no time becomes frames: its base picture (the skeleton's, unchanged
unless a little cleaning helps the motion) and a `motion` that moves parts of it. The
entry has `"kind": "motion"` and `motion` in the place of `clock`:

```json
"motion": {"seconds": 12, "frame_ms": 50, "parts": [ ...1 to 8 parts, applied in order... ]}
```

`seconds` 10 to 600 (default 12); `frame_ms` 20 to 1000, a multiple of 10 that divides the
loop (default 50). Every part has `kind` and `box`, `[left, top, width, height]` in pixels
from the top left, within the canvas. Each part works on the picture the parts before it
made. At a time t of the loop L:

- `level`: `inside` (indices), `fill`, `empty`, `rests` (`"bottom"`, `"top"`, `"left"`,
  `"right"`), `start` and `half` (percent). The box's pixels whose index is in `inside` are
  the vessel; a share of the box measured from its `rests` side, `start` percent of the box
  at t = 0 and `half` percent at L/2, then back to `start` at L (a triangle, so it loops
  without a jump), is filled: its vessel pixels become `fill`, the other vessel pixels
  `empty`. An hourglass: the top chamber's level falls while the bottom chamber's rises
  (two parts), and the sand goes back up in the second half: that is the installation's
  "this is not the time". Water clocks, a candle burning down, a battery: the same.
- `flicker`: `variants` (2 or 3 lists of `[from, to]` index pairs) and `step_ms`: variant
  `floor(t / step_ms) % count` recolours the box: each pixel of index `from` becomes `to`.
  A variant may be `[]` (no change). The loop must be a multiple of `step_ms * count`.
  Flames, a lava lamp, a light bulb, a radio mast's waves, a tuning fork's hum.
- `pulse`: `variants` (2 to 8 lists of pairs), gone through and back once over the loop,
  evenly: a slow pulse of brightness (map a region's colours to the palette's next lighter
  or darker ones). For a tile no other kind fits.
- `turn`: `moving` (indices), `behind` (an index), `centre` (`[x, y]` in half pixels: the
  centre of pixel x, y is 2x+1, 2y+1), `degrees` (per loop; negative is counter-clockwise).
  The box's pixels of a `moving` index turn about the centre by `degrees * t / L`; where
  they were and are no longer, `behind`. It loops without a jump only when the shape looks
  the same after `degrees`: a gear of n teeth turns by a multiple of 360/n per loop, a
  wheel of 8 spokes by a multiple of 45, anything by 360.
- `swing`: as a turn, by `degrees * sin(2 pi * swings * t / L)` (degrees 1 to 180 to each
  side, `swings` whole swings per loop): a metronome's arm, a pendulum.

Rotating pixel art by nearest neighbour roughens it; keep turning parts compact, choose
`moving` indices that belong to the moving thing only (not the background behind it),
and prefer a box that holds the moving thing and the room it moves in. Look at the sheets
at four or more times; a motion that does not read is worse than a gentle one.

The library with motions is not yet in the worktree: run the tools with
`ODRIG_TREE=C:/Users/koren/src/Odrig/scratch/clocks52/stage` set, for example
`ODRIG_TREE=C:/Users/koren/src/Odrig/scratch/clocks52/stage node tools/tile.mjs check work/clock-005.json`.
`C:\Users\koren\src\Odrig\scratch\clocks52\trial\clock-005.json` is a worked example (an
hourglass: two levels and a flicker of the falling stream).
