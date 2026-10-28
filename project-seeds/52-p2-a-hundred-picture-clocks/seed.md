# A hundred picture clocks

## Summary

The owner's picture of 100 timekeepers, a grid of 10 by 10 pixel-art tiles from sundials
to holographic clocks, becomes 100 animation files of 60 x 60, one for each tile, each of
at most 8 colours. A tile with a dial or a display becomes a widget: a still base picture
from the tile, its painted hands, numbers or digits erased, over which the player draws
the hands or the digits as the time ticks, at a random speed, with random changes of
speed and in a random direction, as the three clocks of seed 37 do. A tile that shows no
time becomes a frames animation that moves as the tile suggests; it loses the random
direction, as the owner allows.

Twelve more animations come with them, the owner's ideas of time that is not the time:
the six demos of the owner's ChatGPT conversation "רעיונות לאנימציות זמן" and six that
another tool authored after the same six descriptions. Each becomes a frames animation of
60 x 60 and at most 8 colours, rendered from its own script. In all, 112 files.

## Priority

- `P2`

## Depends On

- Seed 37, the ODRGX container and its clocks: the widget payload, the seed of a turn,
  the virtual time and its speeds, the fonts.
- Seed 18, one converter: the files are made by the JavaScript converter.
- Seed 44, the previews, and seed 46, the collection: where the files, their previews,
  their source and their readmes are kept.

## Product Context

The source is the owner's picture `its not the time frames.png`, 1280 x 1229, which the
owner put in the root of the checkout on the Windows computer on 2026-10-27, untracked.
Its tiles are numbered 1 to 100 in reading order; the numbers of the fifth and sixth
tiles of the ninth row are printed `95` and `96` by mistake, and are 85 and 86. The tiles
were cut on 2026-10-28, each at its own size of about 122 x 122 and with its printed
number painted out, into `scratch/clocks/clock-001.png` to `clock-100.png` of that
checkout, named by their place in the grid.

About 45 tiles have a dial with hands: watches, wall, pocket, alarm, mantel, tower and
station clocks, a stopwatch, a chess clock. About 25 show digits: alarm clocks, watches, a
nixie tube, a flip clock, GPS and NTP receivers, timers. About 30 show no time: sundials,
hourglasses, candles, water clocks, an incense spiral, a lava lamp, moon phases, a
metronome, a tuning fork, gears, a water wheel, a light bulb.

The owner wants the clocks to tick in random directions, with random accelerations and
random speeds, as the existing clock widgets tick, and chose on 2026-10-28 that every
clock has at most 8 colours: the LEDs show far fewer distinct colours than the 24 bits the
board sends, and 8 well-chosen colours read better on them than a picture's many shades.

The twelve. On 2026-10-28 the owner asked an assistant for animations of the
installation's name, "זה לא הזמן", and got six ideas with a working demo of each on a 60 x
60 grid: two second hands that part and meet, a countdown that never reaches zero, sand
that climbs back up an hourglass, a dot that rewinds and leaves an echo, a clock cut into
bands each in its own time, and a clock that melts while its hands go on. The demos run
only for a logged-in reader of the share,
https://chatgpt.com/share/6ae1379a-9dc8-83ed-8fee-9aca58017cc7; their script was taken out
of the owner's logged-in browser by a read-only extraction. Another tool wrote a
standalone page with its own six of the same ideas, its own script and a GIF of each. The
references of all twelve are in `references/` beside this seed:

- `references/original/`: the extraction as it was made, `animation.js` the demos' own
  script, with its style, its DOM, its readme, its provenance and its hashes; and a GIF
  of each demo, `original-1-two-times.gif` to `original-6-the-clock-melts.gif`, rendered
  frame by frame from that script at 100 ms a frame, for one period of the demo: 18, 16,
  16, 10, 144 and 90 seconds.
- `references/standalone/`: the standalone page's script, `standalone-script.js`, and its
  six GIFs, `standalone-1-two-times.gif` to `standalone-6-melting-clock.gif`, 18 seconds
  each, as the page held them.
- `references/conversation.txt`: the text of the conversation.

## Technical Constraints

- **One file for each tile, 100 in all**, named by the tile's place: `clock-001` to
  `clock-100`, with `.odrgx` for a widget and `.odrg` for frames. Every file is 60 x 60,
  checks clean with `node converter/odrig.js check`, and plays in the emulator.
- **At most 8 colours in each file**, black among them when the clock has black, chosen
  for each clock from its scaled tile; the hands, the marks and the digits are colours of
  the 8. The base picture is the tile scaled to 60 x 60 and reduced to those colours.
- **Two new widgets in the widget payload of [format.md](../../docs/format.md)**, beside
  `analog`, `digital` and `melting`: a picture dial and a picture display. Each carries
  its base picture as indices into a palette of at most 8 colours, compressed as the
  format compresses a picture, and its geometry: for the dial, the pivot in half pixels,
  the length and the width of each hand it has (the hour, the minute, and a second hand
  where the tile has one; a sundial's shadow is a dial with one hand), and the colour of
  each; for the display, the box the time is drawn in, the font that fits it, and the
  colours of the digits and the colon, and whether it shows `h:mm` or `h:mm:ss` or minutes
  and seconds as a timer does. The spec writes the bytes.
- **A random direction.** The two new widgets take the speeds of the existing clocks, the
  least and the greatest, and a direction: forward, backward, or chosen by the seed of the
  turn; a direction chosen by the seed may also turn at the swing's slowest point, at a
  chance the seed fixes. The existing widgets do not change.
- **No more memory.** The core's memory is nearly all used. The base picture is decoded
  once a turn into the pixel buffer the player has, and the hands or the digits are drawn
  over it as the LED data is made at each refresh, without writing into the buffer: the
  core asks for no new block, and the memory table of `docs/core.md` stays as it is.
- **The tiles that show no time** become frames animations of 60 x 60 and 8 colours, at
  least 10 seconds and looping without a jump, with a motion of one of these kinds, chosen
  for each tile by the spec: a level that falls or rises in a region (an hourglass, a
  water clock, a candle burning down, a battery); a flicker that alternates two or three
  variants of a region (flames, a lava lamp, a light bulb, a radio mast's waves); a turn
  of a region about a point (gears, a water wheel, a ship's wheel, a moon's phase); a
  swing about a point (a metronome, a tuning fork). A tile that none of these fits is a
  still picture with a slow pulse of brightness of one region.
- **The erasing and the geometry are made once and kept.** For each of the 100 tiles the
  base picture without its hands, numbers or digits, its kind, its geometry or its motion,
  and its 8 colours are written in one inventory, a JSON file the converter reads to make
  the 100 files. The erasing may be done by a tool and corrected by hand; the inventory is
  what counts. The inventory and the base pictures are kept with the collection, not in
  git, as the sources of seed 46 are.
- **The converter makes the files.** A subcommand of the JavaScript converter, or one of
  its library's functions called from a small script in `scratch/`, reads the inventory
  and the base pictures and writes the 100 files; nothing else converts. The core and the
  emulator draw the two new widgets; the operators' app shows them as it shows a clock,
  without making or editing them.
- **Where the files go.** The 100 files, each with its preview and a readme that names the
  source picture and its tile, go into the collection of seed 46, in a folder `clocks/`,
  and onto the share with it; their previews into `thumbnails/` as seed 44 keeps them.
- **The source is kept.** The owner's picture and the 100 cut tiles go into the collection
  beside the files, as their source.
- **The twelve are frames animations**, not widgets: each is a demo written to show one
  scripted turn of strangeness, the same every time, and its own script already draws it
  exactly. Each is rendered from its script, not from its reference GIF: the original six
  from `references/original/animation.js`, the standalone six from
  `references/standalone/standalone-script.js`, by calling the script's drawing at each
  frame's time on a 60 x 60 canvas, in a headless Chrome with a profile of its own.
- **Their loops.** A file holds whole periods, so that its last frame leads into its
  first: the original two times 18 seconds, never zero 16, sand 16, we were here 10, every
  row 720 (the least time after which its three motions, of 16, 18 and 90 seconds, come
  back together), the clock that melts 90; every standalone one 18. In the original sand
  the falling grains' own period, 38/11 of a second, does not divide 16: the grains may
  jump at the loop, and nothing else does.
- **Their frames** are 50 ms apart, 20 a second. A file that would be larger than 2 MB at
  that rate has its frames 100 ms apart; the spec measures which.
- **Their colours.** Each file has at most 8 colours: black, then the colours its script
  draws with, most used first, and every other pixel, a blend of the canvas's soft edges,
  takes the nearest of them.
- **Their names.** `time-original-1-two-times.odrg` to
  `time-original-6-the-clock-melts.odrg` and `time-standalone-1-two-times.odrg` to
  `time-standalone-6-melting-clock.odrg`; they go into the collection's folder `clocks/`
  with the 100, each with its preview and a readme that names its script and its reference
  GIF.
- **The references stay beside the seed**, tracked, about 5 MB: they are what the owner
  chose, and the spec and the tests compare against them.
- **The approval.** The two new widgets extend the format of `docs/decisions.md`; the
  owner approved them on 2026-10-28 by asking for this seed, and the spec writes the
  change log entry.

## Required Behavior

1. All 112 files exist, one for each tile and one for each of the twelve, each 60 x 60 and
   of at most 8 colours, and each checks clean.
2. A picture dial shows its tile's dial with its hands drawn by the player, turning with
   the virtual time of its turn; a picture display shows its tile's display with the time
   in it. Both run at a random speed between their least and greatest speeds, change speed
   as the existing clocks do, and run forward or backward as their direction says.
3. Two turns of the same clock differ, by their seeds, as the existing clocks' turns do.
4. A tile that shows no time plays its motion and loops without a jump.
5. Each of the twelve plays as its reference GIF shows it, frame for frame at the same
   times but for its 8 colours, and loops without a jump but for the grains of the
   original sand.
6. The core's memory with the new widgets is what it is without them.
7. Every file is in the collection's folder `clocks/` with its preview and its readme, the
   previews in `thumbnails/`, the source picture and the tiles beside them.

## Definition Of Done

1. The 112 files play in the emulator, one after the other: each of the 100 looks like
   its tile, and each of the twelve like its reference GIF.
2. Every suite that needs no board passes on macOS, and those of Windows pass there.
3. The owner has looked at a selection of the clocks on the LEDs and said they read.
4. `docs/format.md`, `docs/core.md`, `docs/reasons.md`, `docs/decisions.md` and
   `docs/android-app.md` say what exists.

## Open Questions

None.
