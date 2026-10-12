# Making an animation

How to make an animation and try it without the board, in a clone that is set up as
[getting-started.md](getting-started.md) says, on Windows with the commands as its section [On Windows](getting-started.md#on-windows) writes them. The project's words are explained in
[vocabulary.md](vocabulary.md). The commands make everything for the target, by naming its
mapping file, `mapping/legs-20.json`. For the bench build name `mapping/legs-2.json`.

## Two ways to make an animation

An animation is kept as a source: a JSON frames file that lists every frame with its time
in milliseconds and the colour of every place of the canvas. A source is made for one
canvas, whose size is always taken from a mapping file. Refreshes are 20 milliseconds
apart, so every frame gets a time that is a multiple of 20 milliseconds. There are two
ways to get a source:

- **A generator**: a short Python program works out the frames. This suits text, shapes
  and patterns, and the result is exact and small.
- **An import**: the converter turns a video or a GIF into a source. This suits anything
  filmed or drawn.

## A generator

A generator is a module in `odrig/generators/`. It is given the width and the height of
the canvas and gives back the frames, each a time in milliseconds and a picture. This one
is complete: it moves a white dot along the bottom row, one place every 100 milliseconds.

```python
"""Dot: one white dot that runs along the bottom row of the canvas."""

import sys

from . import picture, run

WHITE = bytes((255, 255, 255))


def frames(width, height):
    return [(100, picture(width, height, {(x, 1): WHITE})) for x in range(1, width + 1)]


def main(argv=None):
    return run("dot", "Writes the dot animation.", lambda width, height, _: frames(width, height), argv)


if __name__ == "__main__":
    sys.exit(main())
```

`picture` makes a black picture and sets the places it is given: a place is (x, y), and a
colour is three bytes, red, green and blue. `run` reads the mapping file, calls `frames`
and writes the source. Saved as `odrig/generators/dot.py`, the module is started like the
generators that are there, and its tests go into `tests/converter/test_generators.py`. The
generators that are there write proof-of-concept animations: test content, not examples of
finished work. `odrig/generators/dvd_bounce.py` is the shortest to read for how one is
built. This writes its bouncing square for the target:

```sh
mkdir -p build/try/sources
.venv/bin/python -m odrig.generators.dvd_bounce build/try/sources/dvd.json --mapping mapping/legs-20.json
```

## An import

Put the video or the GIF under `build/`, where git does not see it. Its name ends in
`.mp4`, `.mov` or `.gif`. The commands below take it from `build/try/clip.gif`:

```sh
.venv/bin/python -m odrig import build/try/clip.gif build/try/sources/clip.json --mapping mapping/legs-20.json
```

The picture is scaled to the canvas. `--fit` says what happens when its shape is not the
shape of the canvas: `fill`, the default, covers the canvas and cuts off what overflows,
`fit` puts all of the picture on the canvas and leaves the rest black, and `stretch`
distorts it. `--start` and `--duration` take a part of the file: with
`--start 12.5 --duration 4`, four seconds from 12.5 seconds on. Sound is ignored, and a
video that was filmed upright on a phone has to be turned before it is imported.
[converter.md](../docs/converter.md#import) has the rest.

## Check a source

```sh
.venv/bin/python -m odrig check build/try/sources/clip.json
```

For a GIF of one second with ten pictures this prints:

```text
format: json-frames
canvas: 60x60
frames: 10
duration_ms: 1000
colours: 10
file_bytes: 306358
```

`canvas` has to be the canvas of the mapping file and `duration_ms` the length you meant.
`file_bytes` is the size of the source: see [How large sources get](#how-large-sources-get).

## Pack it into a show

A show file names each animation by the file it is played from, and `pack` makes
`clip.odrg` from the source `build/try/sources/clip.json`. This writes a show with the two
animations made above, the first of which plays from power-on, and packs it:

```sh
printf '{"version": 1, "brightness": 128, "items": [{"id": 1, "file": "clip.odrg"}, {"id": 2, "file": "dvd.odrg"}], "start": 1}\n' > build/try/show.json
.venv/bin/python -m odrig pack --show build/try/show.json --mapping mapping/legs-20.json \
    --sources build/try/sources --out build/try/show
```

`build/try/show` is then an installed file set. `pack` refuses a source made for another
canvas, and a folder that is not empty: remove `build/try/show` before you pack again.
[show.md](../docs/show.md) describes show files, with more items and with cycles.

## Look at it in the emulator

```sh
.venv/bin/python -m emulator build/try/show
```

Open the address it prints, as in getting started, and look for these:

- **The picture is the right way up** and not mirrored.
- **It covers the canvas as you meant.** With `fill` the edges of a picture of another
  shape are cut off; with `fit` there are black bars.
- **The colours.** The page lifts dark colours the way LEDs do, so judge them on the page
  and not in a video player.
- **The join.** An animation starts again from its first frame when it ends.
- **The header.** `core` and `page` stay near 50, and no red band appears. A red band
  gives the reason a show is not valid.

Stop the emulator with Ctrl-C. It plays everything at 50 refreshes a second. The board
does not: see [Dense animations on the board](#dense-animations-on-the-board).

## Check it without a screen

```sh
printf '1000 status\n' > build/try/ask.txt
.venv/bin/python -m emulator build/try/show --record build/try/check.odrr --seconds 2 --script build/try/ask.txt
```

It prints one line that begins with `reply 1000`, as in getting started. In it,
`"error":null` says the show is valid, and `"playing":1` that item 1 is playing.

## Where things go

| What | Where | Committed |
|---|---|---|
| A generator | `odrig/generators/`, its tests in `tests/converter/` | Yes. |
| A source made by an import | `animations/NAME.json` | Yes, up to 50 MB; see the next section. |
| A source a generator writes for the target | `build/`, written again whenever a show is packed | No. The generator is. |
| A show file | `shows/NAME/show.json` | Yes. |
| A mapping file | `mapping/` | Yes. It changes only when the LEDs are wired another way, which is the owner's to say. |
| The video or GIF you imported, installed file sets, ODRG files, record files, everything you try | `build/` | No. Git ignores the folder. |

`pack` makes `NAME.odrg` from `NAME.json`, so name a source in lower-case letters, digits,
`-` and `_`, at most 27 characters. The two tracked sources, `animations/hello.json` and
`animations/dvd.json`, are test content: what two generators write for the bench build.
Commit on your own branch and by named paths, as [working-rules.md](working-rules.md) says.

## How large sources get

A source spells out every colour of every frame as a number, so it is far larger than the
file that is played. On the canvas of 60 x 60 a frame is 3,600 numbers: about 11 KB when
most of the canvas is dark, and about 33 KB when every place has a colour of its own.

| Source | Canvas | Length | Frames | Bytes of JSON |
|---|---|---:|---:|---:|
| `animations/dvd.json` | 60 x 6 | 41.8 s | 232 | 262,637 |
| `animations/hello.json` | 60 x 6 | 5.1 s | 255 | 461,337 |
| DVD bounce, as the demo show has it | 60 x 60 | 20.9 s | 116 | 1,258,994 |
| Hello world, as the demo show has it | 60 x 60 | 5.1 s | 255 | 2,939,938 |
| An imported GIF with 255 pictures, partly dark | 60 x 60 | 5.1 s | 255 | 3,786,708 |
| An imported video, 25 pictures a second, every place changing | 60 x 60 | 5.0 s | 125 | 4,161,666 |
| The same video at 30 pictures a second | 60 x 60 | 5.0 s | 150 | 4,994,025 |
| The clip of the generator `dense`, every place changing at every refresh | 60 x 60 | 10.0 s | 500 | 16,405,608 |

So a second of video on the target is about 0.8 MB of JSON at 25 pictures a second, 1.0 MB
at 30, and at most 1.6 MB. The files that are played are far smaller: Hello world of the
demo show is 1,210 bytes, and the dense clip 1.4 MB.

The large hosting services for git refuse a single file above 100 MB and warn above 50 MB.
Keep every source at 50 MB or less, which is a minute of video at 25 pictures a second,
and cut a longer piece into several animations with `--start` and `--duration`. Whether
sources of such sizes are tracked at all is an [open question](../docs/decisions.md#open-questions)
for the owner.

## Dense animations on the board

An animation is dense when most LEDs are lit and change at every frame, as in most video.
The board plays it faster from a file that is not compressed. Measured on the board with a
dense clip of 60 x 60: 45 to 47 refreshes a second uncompressed, 36 to 42 compressed. The
uncompressed file is 5 percent larger, and the board's storage holds a little over a minute
of such content in either form. Both rates are acceptable by the rule in
[working-rules.md](working-rules.md#the-frame-rate); the uncompressed form is the smoother.
To pack a show that way, give `pack` the option `--uncompressed`: it then writes every
animation of the show without compression. Animations that are not dense, such as those of
the demo show, play at 50 refreshes a second in either form and are far smaller compressed,
which is what `pack` does without the option. The figures are in
[firmware.md](../docs/firmware.md#verified-on-the-board) and [format.md](../docs/format.md#measured-sizes).
