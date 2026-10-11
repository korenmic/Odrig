# The converter

`odrig` is the command-line tool that works with the animation formats of
[format.md](format.md). It is a Python package at the repository root, started as
`python -m odrig <subcommand>`.

| Subcommand | What it does |
|---|---|
| [`import`](#import) | Turns a video or a GIF into a JSON frames file for the canvas of a mapping file. |
| [`encode`](#encode) | Turns a JSON frames file into an ODRG file, the file the player reads. |
| [`decode`](#decode) | Turns an ODRG file back into a JSON frames file. |
| [`check`](#check) | Says whether a JSON frames or ODRG file is valid and what it holds. |
| [`pack`](#pack) | Builds the folder that is installed for a show. |

The page also covers the [generators](#generators) of the tracked animations, the
[test vectors](#test-vectors) for other ODRG readers, the [tests](#tests), and how to use
the reference decoder [from Python](#from-python).

The package holds one more program, `python -m odrig.mapdoc`, which writes the drawings and
tables of [mapping.md](mapping.md) from the mapping files. It is not a subcommand of the
tool, and that page describes it.

## Setup

The tool needs Python 3.10 or later. Create a virtual environment inside the repository
once, and install the libraries of `requirements.txt` into it:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Every command on this page is run from the repository root with the Python of that
environment, written `python` below: `.venv/bin/python` on macOS and Linux,
`.venv\Scripts\python` on Windows. Nothing is installed outside the `.venv` folder, and git
ignores it.

The libraries are needed only to turn media files into JSON frames. `encode`, `decode`,
`check`, `pack` and the generators run with Python alone, and so does the reference decoder
when another program uses it. The test suite needs the libraries.

| Library | Version | Used for |
|---|---|---|
| numpy | 2.4.6 (2.2.6 on Python 3.10) | The arithmetic that fits a picture to the canvas. |
| Pillow | 12.3.0 | Reading GIF files. |
| av (PyAV) | 17.1.0 | Reading mp4 and mov files. It carries its own FFmpeg libraries; no ffmpeg program is needed. |

The examples on this page write into the folder `build/`, which git ignores. Make it once:

```
mkdir build
```

The tool opens no serial port and no network connection, and has no code for one operating
system only. It is verified on macOS with Python 3.14. Windows, Linux and the Python
versions from 3.10 to 3.13 are supported by construction and not yet verified.

## Exit statuses

| Status | Meaning |
|---:|---|
| 0 | The subcommand did its work. |
| 1 | An input was rejected. One line `error: <reason>: <detail>` is written to standard error and no output is left behind. The reasons are listed in [reasons.md](reasons.md). |
| 2 | The command line was not understood. A usage message is written to standard error and nothing else is written. |

## import

```
python -m odrig import MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                       [--start SECONDS] [--duration SECONDS]
```

Turns a video or a GIF into a JSON frames file for the canvas of a mapping file. The media
file's name ends in `.mp4`, `.mov` or `.gif`, in any letter case. The canvas is the one
the mapping file describes: with a row-leg file it is as wide as the mapping's `width` and
as high as the number of rows the mapping lists, and with a column-leg file it is as wide as
the number of columns the mapping lists and as high as the mapping's `height`
(see [mapping.md](mapping.md)).

```
python -m odrig import clip.mp4 build/clip.json --mapping mapping/legs-2.json
```

**Timeline.** The output is built on the 50 frames-per-second timeline. Ticks are 20 ms
apart, the first at the start time, and each tick takes the source frame that is on screen
at that moment: the last frame that starts no later. Ticks that follow each other with the
same picture are written as one frame, so every `ms` is a multiple of 20.

- In a video, the first video stream is used and time is counted from its first frame. A
  frame is on screen until the next one starts; the last one stays for the mean interval
  between the frames. Sound is ignored.
- In a GIF, each frame is on screen for the delay the file records. A delay of 10 ms or
  less counts as 100 ms, as in web browsers. The frames are gone through once.
- Transparent pixels are black.

**Part of a file.** `--start` and `--duration` are decimal numbers of seconds. Without
`--start` the part starts at 0; without `--duration` it runs to the end of the media. The
number of ticks is the length of the part divided by 20 ms, rounded to the nearest, and at
least one, so the output is within 20 ms of the length asked for. A part that is not inside
the media is refused with `bad-range`; it is never shortened.

```
python -m odrig import clip.mp4 build/clip.json --mapping mapping/legs-2.json \
    --start 12.5 --duration 4 --fit fit
```

**Fitting.** Canvas pixels are square, so the canvas has the shape of its width to its
height. `--fit` says how a picture of another shape is put on it:

| Fit | Result |
|---|---|
| `fill` | The default. The picture is scaled by one factor until it covers the whole canvas; what overflows is cut off equally on the two opposite sides. |
| `fit` | The picture is scaled by one factor until all of it lies inside the canvas, centred; the rest of the canvas is black. |
| `stretch` | The picture is scaled to the whole canvas, by a different factor in each direction when the shapes differ. |

The colour of a canvas pixel is the mean of the source area it covers, each source pixel
weighted by the area they share, rounded to the nearest whole number with halves up. Area
outside the picture counts as black, so the edge of a bar that falls inside a pixel is
blended. The same rule is used when the picture is enlarged. The mean is computed in whole
numbers, so the same decoded picture gives the same canvas picture on every computer.

The top row of the picture lands on the top row of the canvas, row H.

A rotation that a file records for display, pixels that are not square and colour profiles
are not applied: the picture is used as the library decodes it. A video filmed upright on a
phone has to be turned before it is imported.

`import` checks the mapping file first, then the name of the media file, then that it
exists. Its reasons are under "Media files" in [reasons.md](reasons.md).

## encode

```
python -m odrig encode IN.json OUT.odrg [--uncompressed]
```

Reads a JSON frames file and writes the ODRG file that shows the same picture at every
millisecond. It follows the converter guidance of [format.md](format.md):

- Frames that follow each other with the same pixels become one frame record, and a frame
  longer than 65,535 ms becomes several records with the same picture.
- An animation with at most 256 colours gets a palette of exactly those colours, ordered by
  hue, then saturation, then brightness, with black and the greys first. An animation with
  more colours is written without a palette.
- Every frame record is written with the predictor, mode and k that give the fewest bytes
  of data. Among equally small ones the lowest predictor is taken, then plain mode before
  run mode, then the lowest k. When no coded form is smaller than the picture itself, the
  frame is stored as it is.
- The body is compressed with DEFLATE, with a window of 32,768 bytes. `--uncompressed`
  writes the body as it is.

```
python -m odrig encode animations/hello.json build/hello.odrg
```

An existing output file is replaced. The same source and options always give the same
bytes. A compressed file comes from the zlib library of the Python installation, so its
bytes are the same wherever zlib is the same; an uncompressed file is the same everywhere.

A source that breaks the JSON frames format is rejected with its reason from "JSON frames
files" in [reasons.md](reasons.md). A valid source that does not fit an ODRG file is
rejected with `canvas-too-large` or `too-many-frames`.

## decode

```
python -m odrig decode IN.odrg OUT.json
```

Reads an ODRG file with the reference decoder and writes its frames as a JSON frames file
in the canonical layout. Frame records that follow each other with the same picture are
written as one frame, so the JSON file shows the same picture at every millisecond as the
ODRG file. An existing output file is replaced.

```
python -m odrig decode build/hello.odrg build/hello-again.json
```

A file that breaks the format is rejected with one of the reasons under "ODRG files" in
[reasons.md](reasons.md), and no output is written.

A source in which no two frames that follow each other have the same pixels comes back from
`encode` and `decode` with the same frames, byte for byte.

## check

```
python -m odrig check FILE [--format json|odrg]
```

Says whether a file is valid and what it holds. A name ending in `.json` is read as JSON
frames and one ending in `.odrg` as ODRG, in any letter case. `--format` overrides the name
and is needed for any other name; without it such a name is a usage error (status 2).

```
python -m odrig check build/hello.odrg
```

For a valid file these lines are printed, and nothing else:

```
format: odrg
canvas: 60x6
frames: 255
duration_ms: 5100
colours: 256
file_bytes: 1138
palette: 256
compressed: yes
```

| Line | Value |
|---|---|
| `format` | `json-frames` or `odrg`. |
| `canvas` | W and H. |
| `frames` | The number of frames the file lists: frame objects in a JSON frames file, frame records in an ODRG file. |
| `duration_ms` | The sum of all durations. |
| `colours` | The number of different colours that appear in the pictures. |
| `file_bytes` | The size of the file. |
| `palette` | ODRG only: the palette size C, 0 for a file without a palette. |
| `compressed` | ODRG only: `yes` or `no`. |

An invalid file is rejected with its reason and nothing is printed to standard output.

## pack

```
python -m odrig pack --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]
```

Builds the folder that is installed on the board and run by the emulator (see
[show.md](show.md)). The output folder then holds exactly:

- `mapping.json`, a byte-for-byte copy of the mapping file;
- `show.json`, a byte-for-byte copy of the show file;
- for every different `X.odrg` the show names, the file `X.odrg`, encoded from `X.json` in
  the sources folder as `encode` does. `--uncompressed` writes every one of them without
  compression.

The example show plays Hello world and DVD bounce in turn, 15 seconds each. It is packed
with the two-leg mapping:

```
python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
```

`build/example-show` then holds `mapping.json`, `show.json`, `hello.odrg` and `dvd.odrg`.

The output folder must be new or empty; otherwise `pack` refuses with `output-not-empty`.
`pack` makes the folder, and the folders above it when they do not exist.
`pack` checks everything before it writes anything: the mapping file, then the show file
and its ids, then the output folder, then each source in the order the show names them. A
source must have the canvas size of the mapping. The first thing that is wrong is reported,
with a reason from "Shows" in [reasons.md](reasons.md), and the output folder and the
folder around it are left as they were.

## Generators

A generator is a program that writes an animation as a JSON frames file. It takes the
canvas size from a mapping file and needs only Python.

```
python -m odrig.generators.hello_world OUT.json --mapping MAPPING
python -m odrig.generators.dvd_bounce OUT.json --mapping MAPPING
python -m odrig.generators.dense OUT.json --mapping MAPPING [--seconds N]
```

| Generator | Animation |
|---|---|
| `hello_world` | The words HELLO WORLD, six rows high and 53 columns wide, centred on the canvas, with a rainbow that flows through the letters from left to right. 255 frames of 20 ms; after the last frame the rainbow is where it started. |
| `dvd_bounce` | A 2 x 2 square that starts in the top-left corner, moves one pixel diagonally every 180 ms and turns back at every edge. Each of its pixels has the colour that a rainbow fixed to the canvas gives to that place. On the 60 x 6 canvas the loop has 232 frames. |
| `dense` | A full-colour test clip: every pixel is lit and changes at every 20 ms tick, and there are far more than 256 colours. `--seconds` gives its length in whole seconds, 10 by default. |

The two tracked sources are the output of these generators for the two-leg mapping, byte
for byte:

```
python -m odrig.generators.hello_world animations/hello.json --mapping mapping/legs-2.json
python -m odrig.generators.dvd_bounce animations/dvd.json --mapping mapping/legs-2.json
```

A canvas below 53 x 6 for Hello world, or below 3 x 3 for DVD bounce, is rejected with
`canvas-too-small`.

Encoded, `hello.json` is 17,731 bytes uncompressed and `dvd.json` 3,799 bytes, the figures
of [format.md](format.md). Compressed they are 1,138 and 1,612 bytes with zlib 1.2.12,
within 2 percent of the 1,134 and 1,594 bytes measured there.

The dense clip is the worst case for the codec and is used by tests. It is written when it
is needed and is not tracked: ten seconds for the ten-leg mapping are 8 MB of JSON.

```
python -m odrig.generators.dense build/dense.json --mapping mapping/legs-10.json
```

Encoded, that clip is 765,984 bytes uncompressed and about 725,000 bytes compressed.

## Test vectors

`tests/vectors/` holds small ODRG files for checking any ODRG reader against the reference
decoder. No file is above 4,096 bytes.

`tests/vectors/valid/` holds pairs: `NAME.odrg` and `NAME.json`. The JSON frames file has
one frame for every frame record of the ODRG file, in order and without merging: the
duration of the record and the picture after it. A reader is right when it gives exactly
those frames.

| Name | Content |
|---|---|
| `rgb-modes` | 4 x 3 without a palette: one coded record for each of the 64 combinations of predictor, mode and k. |
| `pal-modes` | 5 x 4 with a palette of 7: the same 64 combinations on index bytes. |
| `escape` | Plain-mode and run-mode records, for k from 0 to 4, with Rice values on both sides of the long form (eight one-bits and the value) and the largest value. No other vector uses the long form. |
| `stored.rgb`, `stored.pal` | Stored records: first in the file, after a coded record and after a stored one. |
| `run-to-end` | Run-mode records that end in a zero run, and records whose codes are all zero. |
| `run-last-nonzero` | Run-mode records whose last code is not zero. |
| `long-run` | A 20 x 16 palette canvas with zero runs longer than 255 codes. |
| `durations` | Records of 1 ms and of 65,535 ms. |
| `pal-256`, `pal-1` | A 16 x 16 file that uses all 256 palette entries; a file with a palette of one colour. |
| `one-wide.rgb`, `one-wide.pal` | A canvas of 1 x 5, where every pixel starts a row. |
| `one-high.rgb`, `one-high.pal` | A canvas of 5 x 1. |
| `one-pixel.rgb`, `one-pixel.pal` | A canvas of 1 x 1. |
| `deflate-stored`, `deflate-fixed`, `deflate-dynamic` | One body in a DEFLATE stream of one stored block, one fixed-code block and one dynamic-code block. |
| `encoded.pal`, `encoded.rgb` | Short animations written by `encode`, compressed. |

`tests/vectors/invalid/` holds files that a reader must reject. A file is named
`REASON.odrg` or `REASON.CASE.odrg`: the part before the first dot is the reason, one of
those under "ODRG files" in [reasons.md](reasons.md). Each file is a small valid file with
exactly one defect, and a reader is right when it rejects it for that reason.

| Reason | Cases |
|---|---|
| `truncated` | `header`, `palette`, `record-start` and `record-data`: the file is cut off there. `deflate`: the DEFLATE stream is cut off. `deflate-body`: the stream is complete and its output ends inside a record. |
| `bad-magic`, `bad-version`, `bad-palette-size`, `no-frames` | One file each: that header field is wrong. |
| `reserved-bits` | `flag`: flag bit 1 is set. `mode-bit-7`: bit 7 of a mode byte is set. `stored-mode`: a stored frame's mode byte is `0x41`. |
| `zero-size` | `width`, `height`. |
| `canvas-too-large` | `palette`: 65,535 x 1 with a palette. `rgb`: 21,845 x 1 without one. |
| `bad-deflate` | `block-type`: the block type is 3. `stored-length`: a stored block's length and its complement disagree. |
| `zero-duration`, `bad-stored-length`, `run-past-end`, `too-much-padding` | One file each. |
| `bad-length` | `below-2`: L is 1. `above-n-plus-1`: L is N + 2. |
| `out-of-bits` | `plain`: the data of a plain-mode record lacks its last byte. `gamma`: a Gamma code is cut off by the end of the data. |
| `bad-code` | `plain`: the Rice value 256 with k = 6. `run`: the Rice value 255 in run mode. |
| `bad-palette-index` | `coded`, `stored`: in a coded frame and in a stored frame. |
| `trailing-bytes` | `body`: a byte after the last record of an uncompressed body. `deflate-body`: the same inside a compressed body. `after-deflate`: a byte in the file after the DEFLATE stream. |

None of the invalid files is made with zlib; their compressed bodies are DEFLATE streams of
one stored block.

The vectors are the output of a tracked program, which makes them from fixed data:

```
python -m tests.converter.build_vectors
```

It makes each folder hold exactly its set. The suite checks that the tracked files are what
the program gives, byte for byte. The compressed files (`deflate-*` and `encoded.*`) are
left out of that comparison, because another zlib may compress the same body to other
bytes; they are checked by decoding them.

## Tests

```
python -m unittest discover -s tests/converter -t .
```

This one command runs the whole suite of the tool. It finds the tests by itself: every file
named `test_*.py` in `tests/converter/` is run, so a new test file needs no change anywhere
else. The suite needs no hardware and no network connection. It builds the media files it
imports while it runs; none is tracked.

## From Python

The modules that other programs and tests build on need only the Python standard library:

| Call | Result |
|---|---|
| `odrig.odrg.decode(data)` | The reference decoder: the canvas size, the palette size, whether the body is compressed, and for every frame record its duration, the picture after it and its mode byte. |
| `odrig.odrg.encode(animation, compressed=True)` | The bytes of the ODRG file of an animation. |
| `odrig.jsonframes.read(path)`, `loads(data)`, `dumps(animation)`, `write(path, animation)` | JSON frames files, read strictly and written in the canonical layout. |
| `odrig.mapping.read(path)` | The kind, the canvas size and the legs of a mapping file: for each leg its number, its pin, its `first_led` and its strips in chain order. |
| `odrig.mapping.position(canvas, leg, n)` | The canvas position (x, y) of LED n of a leg, by the rule of [mapping.md](mapping.md). |
| `odrig.show.read(path)` | The items of a show file. |
| `odrig.pack.pack(show, mapping, sources, out, compressed=True)` | What the `pack` subcommand does. |

A picture is `bytes` of 3 * W * H: red, green and blue for each pixel in the pixel order of
[format.md](format.md), the bottom row first. A refused input raises
`odrig.errors.Rejection`, which carries the `reason` and the `detail`.
