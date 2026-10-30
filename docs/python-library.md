# The Python library

`odrig` is a Python package at the repository root: a library for the tests and the tools.
It reads and writes the project's files, JSON frames, the ODRG format of
[format.md](format.md) and the ODRGX containers of frames, mapping files and shows, and it
holds the generators. It converts
nothing and is no program of its own: the converter, which imports media, encodes, decodes,
checks and packs, is the JavaScript tool of [converter.md](converter.md).

The package was the project's first converter. What it answered to the converter's tests
while it still converted is stored with them, in `converter/tests/expected/`, and the
converter's suite compares with those answers ([converter.md](converter.md), "Tests").

What builds on it:

| What | Where |
|---|---|
| The [generators](#generators), which write the tracked animations and the dense test clip | `odrig/generators/` |
| The builder of the [test vectors](#test-vectors) for other ODRG readers | `tests/converter/build_vectors.py` |
| The program that writes the drawings and tables of [mapping.md](mapping.md), `python -m odrig.mapdoc`, which that page describes | `odrig/mapdoc.py` |
| The catalogs of [catalog.md](catalog.md), and the program that keeps the catalog of a card mounted on a computer, `python -m odrig.catalog`, which [microsd.md](microsd.md) describes | `odrig/catalog.py` |
| The check the firmware tool makes of a show folder before it installs it ([firmware.md](firmware.md)) | `firmware/fwtool/` |
| The decoder and the readers that the suites of the core and the emulator compare with, and the writer with which they make the small animation files they play ([core.md](core.md), [emulator.md](emulator.md)) | `tests/core/`, `tests/emulator/` |

## Setup

The package needs Python 3.10 or later and nothing outside Python's own library. The
commands of the repository run with the Python of the environment the getting-started page
makes, `.venv`, into which nothing is installed:

```
python3 -m venv .venv
```

Every command on this page is run from the repository root with that Python, written
`python` below: `.venv/bin/python` on macOS and Linux, `.venv\Scripts\python` on Windows.
Git ignores the folder.

The examples on this page write into the folder `build/`, which git ignores. Make it once:

```
mkdir build
```

The package opens no serial port and no network connection, and has no code for one
operating system only. It is verified on macOS and on Windows 11, each with Python 3.14.
Linux and the Python versions from 3.10 to 3.13 are supported by construction and not yet
verified.

## Generators

A generator is a program that writes an animation as a JSON frames file. It takes the
canvas size from a mapping file of either kind, a row-leg file or a column-leg file, and
needs only Python. The converter encodes what it writes.

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
None of them is a finished animation of the installation. A generator ends with status 0
when it wrote its file, 1 with one line `error: <reason>: <detail>` when an input was
refused, and 2 when its command line was not understood.

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
node converter/odrig.js encode build/dense.json build/dense.odrg
```

Encoded, that clip is 1,462,236 bytes uncompressed and
1,383,766 bytes compressed with zlib 1.2.12; the converter writes those bytes on every
computer.

## Test vectors

`tests/vectors/` holds small ODRG files for checking any ODRG reader against the decoder of
this library. No file is above 4,096 bytes.

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
| `encoded.pal`, `encoded.rgb` | Short animations written by the library's writer, compressed. |

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

The suite of the converter reads every vector as well, with its own decoder.

`tests/vectors/containers/` holds ODRGX containers, in `valid/` beside the JSON frames they
decode to and in `invalid/` named by their reason as above, one of "ODRGX files" or, for a
fault of a frames payload, of "ODRG files". They are made from the ODRG vectors by
`node tests/vectors/containers/build.mjs`, and the converter's suite checks that the files
are what it makes. `odrig/odrgx.py` reads them for the suites of this library and of the
core. Of a text and a clock it reads the header only: the payload is read by the
converter and the core. `tests/vectors/widgets/` holds the clocks, made the same way by
`node tests/vectors/widgets/build.mjs`.

## Tests

```
python -m unittest discover -s tests/converter -t .
```

This one command runs the whole suite of the library and the generators, and checks every
tracked document against the tools. It finds the tests by itself: every file named
`test_*.py` in `tests/converter/` is run, so a new test file needs no change anywhere else.
The suite needs no hardware, no network connection and nothing outside Python's own library.

The converter's suite, which compares the converter with the stored answers of this
package, is [converter.md](converter.md), "Tests".

## From Python

| Call | Result |
|---|---|
| `odrig.odrg.decode(data)` | The decoder: the canvas size, the palette size, whether the body is compressed, and for every frame record its duration, the picture after it and its mode byte. |
| `odrig.messageclock.decode(data)` | Strict reading of a generated message-clock container: caption text, flags, durations, static masks and digit atlas. Catalog admission also validates this payload. Conversion and rendering remain in JavaScript and the core. |
| `odrig.odrg.encode(animation, compressed=True)` | The bytes of the ODRG file of an animation, as the converter writes them; the suites use it to make small files. |
| `odrig.jsonframes.read(path)`, `loads(data)`, `dumps(animation)`, `write(path, animation)` | JSON frames files, read strictly and written in the canonical layout. |
| `odrig.mapping.read(path)` | The kind, the canvas size and the legs of a mapping file: for each leg its number, its pin, its `first_led`, its strips in chain order, and the end each strip starts at when the leg has `starts`, else `None`. |
| `odrig.mapping.position(canvas, leg, n)` | The canvas position (x, y) of LED n of a leg, by the rule of [mapping.md](mapping.md). |
| `odrig.show.read(path)` | The items of a show file. |
| `odrig.errors.status_of(action)` | The exit status of a command line's work, with its error line for a refusal. |
| `odrig.catalog.read(storage)`, `add(storage, name, data)`, `remove(storage, name)`, `rebuild(storage)`, `check(storage)`, `recover(storage)` | A storage's catalog of [catalog.md](catalog.md), and the changes a computer makes to it; `Storage(folder)` is a folder, `MemoryStorage(files)` files held in a dict. |
| `odrig.catalog.main(argv)` | The command line of `python -m odrig.catalog`, as [microsd.md](microsd.md) gives it; returns the exit status. |

A picture is `bytes` of 3 * W * H: red, green and blue for each pixel in the pixel order of
[format.md](format.md), the bottom row first. A refused input raises
`odrig.errors.Rejection`, which carries the `reason` and the `detail`.

`show.Item.ignored` is `None` when absent, otherwise the strict boolean supplied by
the show. Cycles reject this member. Packing remains the JavaScript converter's job.
