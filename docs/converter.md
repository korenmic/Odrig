# The converter

`odrig` is the command-line tool that works with the animation formats of
[format.md](format.md). It is a Python package at the repository root, started as
`python -m odrig <subcommand>`.

## Setup

The tool needs Python 3.10 or later. Create a virtual environment inside the repository
once:

```
python3 -m venv .venv
```

Every command on this page is run from the repository root with the Python of that
environment, written `python` below: `.venv/bin/python` on macOS and Linux,
`.venv\Scripts\python` on Windows. Nothing is installed outside the `.venv` folder, and git
ignores it.

## Exit statuses

| Status | Meaning |
|---:|---|
| 0 | The subcommand did its work. |
| 1 | An input was rejected. One line `error: <reason>: <detail>` is written to standard error and no output is left behind. The reasons are listed in [reasons.md](reasons.md). |
| 2 | The command line was not understood. A usage message is written to standard error and nothing else is written. |

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
python -m odrig encode clip.json clip.odrg
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
python -m odrig decode clip.odrg clip.json
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
python -m odrig check clip.odrg
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

## Generators

A generator is a program that writes an animation as a JSON frames file. It takes the
canvas size from a mapping file and needs only Python.

```
python -m odrig.generators.hello_world OUT.json --mapping MAPPING
python -m odrig.generators.dvd_bounce OUT.json --mapping MAPPING
```

| Generator | Animation |
|---|---|
| `hello_world` | The words HELLO WORLD, six rows high and 53 columns wide, centred on the canvas, with a rainbow that flows through the letters from left to right. 255 frames of 20 ms; after the last frame the rainbow is where it started. |
| `dvd_bounce` | A 2 x 2 square that starts in the top-left corner, moves one pixel diagonally every 180 ms and turns back at every edge. Each of its pixels has the colour that a rainbow fixed to the canvas gives to that place. On the 60 x 6 canvas the loop has 232 frames. |

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

## Tests

```
python -m unittest discover -s tests/converter -t .
```

This one command runs the whole suite of the tool. It finds the tests by itself: every file
named `test_*.py` in `tests/converter/` is run, so a new test file needs no change anywhere
else. The suite needs no hardware and no network connection.
