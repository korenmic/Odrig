# The reference converter

`odrig` is a second converter, a Python package at the repository root, started as
`python -m odrig <subcommand>`. It was the first converter of the project. The converter
people use is now the JavaScript tool of [converter.md](converter.md), and the Python tool
is kept as its reference: an independent implementation of the same formats, which the
suite of the JavaScript tool runs on the same inputs and compares with, result by result.
To convert or to pack, use the tool of that page.

The package is also what the rest of the repository builds on:

| What | Where |
|---|---|
| The [generators](#generators), which write the tracked animations and the dense test clip | `odrig/generators/` |
| The builder of the [test vectors](#test-vectors) for other ODRG readers | `tests/converter/build_vectors.py` |
| The program that writes the drawings and tables of [mapping.md](mapping.md), `python -m odrig.mapdoc`. It is not a subcommand of the tool, and that page describes it. | `odrig/mapdoc.py` |
| The check the firmware tool makes of a show folder before it installs it ([firmware.md](firmware.md)) | `firmware/fwtool/` |
| The reference decoder and the readers that the suites of the core and the emulator compare with ([core.md](core.md), [emulator.md](emulator.md)) | `tests/core/`, `tests/emulator/` |

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
when another program uses it. The test suite needs the libraries, and so does the suite of
the JavaScript tool, which compares imports.

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
system only. It is verified on macOS and on Windows 11, each with Python 3.14. Linux and the
Python versions from 3.10 to 3.13 are supported by construction and not yet verified.

## Command line

The subcommands, their arguments and their options are those of the JavaScript tool, and
[converter.md](converter.md) describes what each one does:

```
python -m odrig import MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                       [--start SECONDS] [--duration SECONDS]
python -m odrig encode IN.json OUT.odrg [--uncompressed]
python -m odrig decode IN.odrg OUT.json
python -m odrig check FILE [--format json|odrg]
python -m odrig pack --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]
```

| Status | Meaning |
|---:|---|
| 0 | The subcommand did its work. |
| 1 | An input was rejected. One line `error: <reason>: <detail>` is written to standard error and no output is left behind. The reasons are listed in [reasons.md](reasons.md). |
| 2 | The command line was not understood. A usage message is written to standard error and nothing else is written. |

For the same input the two tools end with the same status, the same reason and the same
output. Where they are known to differ:

- **Compressed files.** The Python tool compresses with the zlib library of the Python
  installation, so the bytes of a compressed ODRG file are the same wherever zlib is the
  same. With zlib 1.2.12 they are the bytes the JavaScript tool writes everywhere. An
  uncompressed file is the same from both tools, always.
- **GIF pictures.** The Python tool takes the picture of each frame from Pillow, which
  differs from web browsers and from the JavaScript tool in three corners;
  [converter.md](converter.md), "import", names them.
- **Words of a library in a detail.** The place and the fault in a `bad-json` detail are
  those of Python's JSON module, the fault in a `bad-deflate` detail is zlib's, and what
  cannot be decoded in an `unreadable-media` detail is said by Pillow or PyAV.
- **The command line.** The Python tool also reads an option shortened to its first
  letters, and numbers of seconds in spellings the JavaScript tool refuses, such as
  `1_0`. It has no status 70 and no `decoder-missing`: without its libraries `import` ends
  with Python's own report of the missing module.
- **Damaged media.** The two tools need not judge a damaged or cut media file alike: they
  decode with different builds of FFmpeg, and one may recover a picture where the other
  gives up. Both refuse a file they cannot decode as `unreadable-media`. For the Python
  tool that includes a video whose first video stream has no decoder, as happens with an
  mp4 cut inside its header, a video whose metadata is not UTF-8, and a GIF that is cut
  short. Of the 160 cut and damaged videos the suite gives both tools, one is read by the
  JavaScript tool and refused by the Python tool.

## Generators

A generator is a program that writes an animation as a JSON frames file. It takes the
canvas size from a mapping file of either kind, a row-leg file or a column-leg file, and
needs only Python. The generators exist in Python only.

```
python -m odrig.generators.hello_world OUT.json --mapping MAPPING
python -m odrig.generators.dvd_bounce OUT.json --mapping MAPPING
python -m odrig.generators.dense OUT.json --mapping MAPPING [--seconds N]
```

| Generator | Animation |
|---|---|
| `hello_world` | The words HELLO WORLD, six rows high and 53 columns wide, centred on the canvas, with a rainbow that flows through the letters from left to right. 255 frames of 20 ms; after the last frame the rainbow is where it started. |
| `dvd_bounce` | A 2 x 2 square that starts in the top-left corner, moves one pixel diagonally every 180 ms and turns back at every edge. Each of its pixels has the colour that a rainbow fixed to the canvas gives to that place. On the 60 x 6 canvas the loop has 232 frames. On a canvas as wide as it is high, such as the 60 x 60 of the target file, the square meets two edges at once and runs to and fro along one diagonal: 116 frames. |
| `dense` | A full-colour test clip: every pixel is lit and changes at every 20 ms tick, and there are far more than 256 colours. `--seconds` gives its length in whole seconds, 10 by default. |

All three write test content: animations made to try the tools, the player and the board.
None of them is a finished animation of the installation.

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
is needed and is not tracked: ten seconds for the target file, 60 x 60, are 16 MB of JSON.

```
python -m odrig.generators.dense build/dense.json --mapping mapping/legs-20.json
```

Encoded, that clip is 1,462,236 bytes uncompressed and
1,383,766 bytes compressed with zlib 1.2.12.

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

The suite of the JavaScript tool reads every vector as well, with its own decoder.

## Tests

```
python -m unittest discover -s tests/converter -t .
```

This one command runs the whole suite of the Python tool. It finds the tests by itself:
every file named `test_*.py` in `tests/converter/` is run, so a new test file needs no
change anywhere else. The suite needs no hardware and no network connection. It builds the
media files it imports while it runs; none is tracked.

The comparison of the two converters is not in this suite: it is in the suite of the
JavaScript tool, [converter.md](converter.md), "Tests".

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
