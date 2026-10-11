# Design: Converter and reference codec (seed 01)

## Overview

The tool is a Python package named `odrig` at the repository root, run as
`python -m odrig`. Everything except `import` uses only the Python standard library, so the
reference decoder, the encoder, `pack` and the generators can be used by the tests of later
seeds without installing anything. `import` alone uses three third-party libraries.

The package has one direction of dependency: `cli` calls the subcommand modules, the
subcommand modules call the format modules (`jsonframes`, `odrg`, `mapping`, `show`), and
those call `strictjson`, `files` and `errors`. No format module imports a subcommand module.

Decisions taken where the seed and the documents left a point open are listed in
`docs/drifts.md` under "Seed 01".

## Repository layout

```
requirements.txt                 third-party libraries, needed by import only
.gitignore                       /.venv/, /build/, /.codex/, __pycache__/
odrig/
  __init__.py
  __main__.py                    runs cli.main()
  cli.py                         arguments, exit statuses, the error line
  errors.py                      Rejection and the reason names
  files.py                       reading an input file and writing an output file whole
  strictjson.py                  strict JSON loading shared by every reader
  jsonframes.py                  JSON frames: read, canonical write, merge
  odrg.py                        ODRG reference decoder and encoder
  mapping.py                     mapping file reader
  show.py                        show file reader
  pack.py                        pack
  media.py                       import: readers, timeline, fitting (third-party libraries)
  generators/
    __init__.py
    rainbow.py                   the rainbow colours shared by Hello world and DVD bounce
    hello_world.py
    dvd_bounce.py
    dense.py
animations/
  hello.json                     written by the Hello world generator, tracked
  dvd.json                       written by the DVD bounce generator, tracked
shows/
  example/
    show.json                    the example show
tests/
  __init__.py
  converter/
    __init__.py
    test_*.py                    the suite of this seed
    support.py                   runs the tool for the tests
    media_fixtures.py            builds the short GIF, mp4 and mov inputs at run time
    build_vectors.py             writes tests/vectors; run by hand
  vectors/
    valid/NAME.odrg, NAME.json
    invalid/REASON.odrg, REASON.CASE.odrg
docs/
  converter.md                   how to set up and use the tool
  reasons.md                     every reason and its condition
```

The folders `animations/` and `tools/` already hold untracked proof-of-concept files. The
new tracked files use names that none of those files have, and no task moves, edits or
deletes an untracked file.

## Data structures

A **picture** is a `bytes` object of 3 * W * H bytes: red, green, blue for each pixel, in
pixel order (bottom row first, left to right). A **frame** is a pair `(ms, picture)`.

```python
# odrig/jsonframes.py
@dataclass(frozen=True)
class Animation:
    width: int
    height: int
    frames: tuple[tuple[int, bytes], ...]

# odrig/odrg.py
@dataclass(frozen=True)
class Decoded:
    width: int
    height: int
    palette_size: int                       # C
    compressed: bool
    records: tuple[tuple[int, bytes], ...]  # one (duration, picture) per frame record
    modes: tuple[int, ...]                  # the mode byte of each frame record

# odrig/mapping.py
@dataclass(frozen=True)
class Leg:
    leg: int
    pin: int
    first_led: str                          # "left" or "right"
    rows: tuple[int, ...]

@dataclass(frozen=True)
class Mapping:
    width: int
    height: int                             # total number of rows
    legs: tuple[Leg, ...]

# odrig/show.py
@dataclass(frozen=True)
class Item:
    id: int
    file: str | None                        # animation item
    cycle: tuple[int, ...] | None           # cycle item
    seconds: int | None

@dataclass(frozen=True)
class Show:
    brightness: int
    items: tuple[Item, ...]
    start: int | None
```

## Components and interfaces

### `errors`

```python
class Rejection(Exception):
    reason: str      # one of the names below
    detail: str      # free text; names the file
```

Every reason of the requirements is a module constant, for example
`BAD_MAGIC = "bad-magic"`. No other module writes a reason as a string literal.

### `strictjson`

`loads(data: bytes) -> object` raises `Rejection("bad-json", ...)` when the bytes are not
UTF-8, start with U+FEFF, are not one JSON value, or hold an object with a repeated member
name. It calls `json.loads` with an `object_pairs_hook` that refuses repeated names, a
`parse_constant` that refuses `NaN` and the infinities, and a `parse_float` that returns a
value of a private class, so that a number written with a fraction or an exponent can never
pass an integer check.

Helpers used by all readers:

- `members(obj, required, optional=())` checks that `obj` is a `dict`, then reports
  `missing-member` or `unknown-member`.
- `integer(value, low, high)` reports `bad-type` unless `type(value) is int`, then
  `out-of-range` outside `low..high`.

### `jsonframes`

```python
def loads(data: bytes) -> Animation      # Requirement 3
def read(path) -> Animation
def merged(frames) -> list[tuple[int, bytes]]   # joins consecutive identical pictures
def dumps(animation: Animation, merge=True) -> bytes
                                          # Requirement 4; applies merged() unless merge is
                                          # False, which only the vector builder passes
def write(path, animation: Animation) -> None
def colour_count(frames) -> int
```

`loads` checks in this order: top level is an object (`bad-json`); `version` present
(`missing-member`), an integer (`bad-type`), equal to 1 (`bad-version`); the other top-level
members; `width` and `height`; `frames` is a non-empty array (`bad-type`, `no-frames`); then
each frame in order: its members, `ms`, the number of pixels, each pixel.

The canonical layout written by `dumps`, shown for the example of `docs/format.md`:

```
{
  "version": 1,
  "width": 3,
  "height": 2,
  "frames": [
    {"ms": 500, "pixels": [16711680, 0, 0, 0, 0, 255]},
    {"ms": 500, "pixels": [0, 0, 0, 0, 65280, 0]}
  ]
}
```

Two spaces before each top-level member, four before each frame, `", "` between entries,
`": "` after a name, one line feed after the closing brace. The file is written in binary
mode, so no platform changes the line ends.

### `odrg`

```python
def decode(data: bytes) -> Decoded                                   # Requirements 5 and 6
def encode(animation: Animation, compressed: bool = True) -> bytes   # Requirement 7

# Building blocks. encode() is made of them; the vector builder uses them to force choices.
def palette_for(frames) -> list[bytes] | None        # hue order, or None above 256 colours
def to_buffer(picture: bytes, palette) -> bytes      # picture -> the N buffer bytes
def codes(old: bytes, new: bytes, width: int, bpp: int, predictor: int) -> bytes
                                                     # the N codes of one predictor
def coded_record(old: bytes, new: bytes, width: int, bpp: int, duration: int,
                 predictor: int, run: bool, k: int) -> bytes
def stored_record(new: bytes, duration: int) -> bytes
def best_record(old: bytes, new: bytes, width: int, bpp: int, duration: int) -> bytes
def container(width: int, height: int, palette, records: list[bytes],
              deflate=None) -> bytes                 # deflate: bytes -> bytes, or None
```

### `mapping`

`read(path) -> Mapping` applies the rules of Requirement 10. A missing file is
`mapping-missing`. Any rejection raised while reading the content is turned into
`mapping-malformed`, with the inner reason and the place in the detail.

### `show`

`read(path) -> Show` applies Requirement 14 criterion 4 (`show-missing`, `show-malformed`),
then checks ids in three passes, in the order of the requirement's table: `duplicate-id`,
scanning items in file order; `undefined-id`, over every entry of every cycle in file order
and then `start`; `nested-cycle`, over every entry of every cycle in file order.
`files(show) -> list[str]` gives the different file names in the order of first use.

The file name rule is the regular expression `[a-z0-9._-]{1,32}` matching the whole name,
and the name ending in `.odrg`.

### `pack`

`pack(show_path, mapping_path, sources_dir, out_dir, compressed=True)`:

1. Read the mapping, then the show.
2. Refuse `output-not-empty` when `out_dir` exists and holds any entry.
3. For each name `X.odrg` of `show.files()`: `file-missing` when `sources_dir/X.json` does
   not exist; read it (`file-malformed`); compare its size with the mapping
   (`size-mismatch`); encode it.
4. Write `mapping.json`, `show.json` and the encoded files into a new temporary folder next
   to `out_dir`, then move that folder into place. The two JSON files are copied as bytes.

### `media`

Used by `import` only. It imports numpy, Pillow and PyAV inside its functions, so importing
`odrig.cli` never loads them.

```python
def source_frames(path) -> Iterator[tuple[Fraction, Fraction, ndarray]]
    # (start_ms, end_ms, picture) for each source frame; picture is rows x columns x 3, uint8
def tick_pictures(frames, start_ms: int, duration_ms: int | None,
                  resample) -> list[bytes]          # one canvas picture per tick
def source_rect(sw: int, sh: int, w: int, h: int, fit: str) -> tuple[Fraction, ...]
def resample(picture: ndarray, rect, w: int, h: int) -> bytes   # canvas picture, pixel order
def import_media(path, mapping: Mapping, fit: str, start_ms: int,
                 duration_ms: int | None) -> Animation
```

### `generators`

Each generator module has `frames(width: int, height: int) -> list[tuple[int, bytes]]` and a
`main()` with the arguments `OUT --mapping MAPPING`; `dense` also takes `--seconds`. They
write through `jsonframes.write`.

### `cli`

```
python -m odrig import  MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                        [--start SECONDS] [--duration SECONDS]
python -m odrig encode  IN.json OUT.odrg [--uncompressed]
python -m odrig decode  IN.odrg OUT.json
python -m odrig check   FILE [--format json|odrg]
python -m odrig pack    --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]
```

`main(argv)` parses with `argparse` (usage errors exit with status 2), calls the subcommand,
and turns a `Rejection` into `error: <reason>: <detail>` on standard error with status 1. A
path that does not exist is turned into `not-found` unless the subcommand has a more specific
reason. `--start` and `--duration` are parsed with `decimal.Decimal` and converted to whole
milliseconds, rounded to the nearest.

`decode` writes the records of `odrg.decode` through `jsonframes.write`, which merges equal
neighbours. `check` reads the file with `jsonframes.read` or `odrg.decode` and prints the
lines of Requirement 9: `frames` is the number of frame objects of a JSON frames file and F
for an ODRG file; `colours` is counted over the pictures of all frames. `import` chooses its
reader from the file name's ending in lower case; any other ending is `unsupported-media`.

Output files are written to `<name>.part` in the destination folder and moved into place
with `os.replace` once complete; a failure removes the `.part` file.

Output is a function of the input bytes and the options only: no time, no random value and
no environment setting enters a file. Uncompressed files are therefore the same on every
machine. Compressed bytes come from the zlib library of the Python installation; they are
the same from run to run, and the same on every installation whose zlib produces the same
stream.

## Algorithms

### Reference decoder

`decode` follows `docs/format.md` step by step and favours clarity over speed.

1. Fewer than 16 bytes: `truncated`. Then, in offset order: `bad-magic`, `bad-version`,
   `reserved-bits` (flags above bit 0), `zero-size`, `bad-palette-size`, `canvas-too-large`,
   `no-frames`.
2. Body. Uncompressed: the bytes after the header. Compressed: feed them to
   `zlib.decompressobj(wbits=-15)`; `zlib.error` is `bad-deflate`; a stream that has not
   reached its end (`eof` false) is `truncated`; bytes in `unused_data` are
   `trailing-bytes`.
3. Palette: C * 3 bytes of the body, or `truncated`.
4. Buffer of N zero bytes. For each of the F records: five bytes (`truncated`), duration
   (`zero-duration`), L (`bad-length`), mode (`reserved-bits` for bit 7, or for bit 6 with
   any other bit), stored and L not N + 1 (`bad-stored-length`), L - 1 data bytes
   (`truncated`).
5. Stored: the data becomes the buffer.
6. Coded: read the N codes from the data with a bit reader that raises `out-of-bits` past
   the last bit. Plain mode reads N Rice codes. Run mode follows the three steps of the
   document; a Gamma code is read completely, then `i + g - 1 > N` is `run-past-end`. A
   Rice code is read completely, then a code above 255 is `bad-code`. After the last code,
   `8 * (L - 1) - bits_read >= 8` is `too-much-padding`. Then the residuals and the
   predictor.
7. In a palette file, any buffer byte of C or more is `bad-palette-index`.
8. Record the mode byte, the duration and the picture (through the palette when C is not 0).
9. After the last record, any body byte left is `trailing-bytes`.

### Encoder

1. **Frames.** Merge consecutive identical pictures. Split a frame longer than 65,535 ms
   into records of 65,535 ms and a last record with the remainder. More than 4,294,967,295
   records: `too-many-frames`.
2. **Palette.** Collect the different colours. At most 256: the palette is those colours
   sorted by the key `(h, s, v)` below, and bpp is 1. Otherwise there is no palette and bpp
   is 3. N above 65,534: `canvas-too-large`.

   For a colour (r, g, b), with `mx` the largest channel, `mn` the smallest and
   `d = mx - mn`:

   - `h` is 0 when d is 0; `((g - b) / d) mod 6` when mx is r; `(b - r) / d + 2` when mx is
     g; `(r - g) / d + 4` otherwise;
   - `s` is 0 when mx is 0, otherwise `d / mx`;
   - `v` is mx.

   `h` and `s` are exact fractions (`fractions.Fraction`), so the order does not depend on
   floating-point rounding. With this key the proof-of-concept animations encode to exactly
   the uncompressed sizes in `docs/format.md` (17,731 and 3,799 bytes). Compressed they are
   1,138 and 1,612 bytes with zlib 1.2.12, against 1,134 and 1,594 in the document, because
   of the tie-break of step 3.
3. **Each record.** With `old` the buffer before the record and `new` the buffer after it,
   and `nb` the neighbour rule of the document, the four residual arrays are:

   | Predictor | Residual `r[i]` |
   |---:|---|
   | 0 | `(new[i] - old[i]) mod 256` |
   | 1 | `(t[i] - nb(t, i)) mod 256`, where `t[i] = (new[i] - old[i]) mod 256` |
   | 2 | `(new[i] - nb(new, i)) mod 256` |
   | 3 | `new[i]` |

   Each residual becomes a code `u`: with `s` the residual read as a signed byte, `u = 2s`
   when s is 0 or more and `u = -2s - 1` otherwise.

   The size of every combination comes from the histogram of the codes and the lengths of
   the zero runs, without writing any bits:

   - `rice_bits(k, v)` is `(v >> k) + 1 + k` when `v >> k` is below 8, otherwise 16;
   - `gamma_bits(g)` is `2 * bit_length(g) - 1`;
   - plain mode: the sum of `rice_bits(k, u[i])` over all i;
   - run mode: `gamma_bits(z + 1)` for the z zero codes before each non-zero code, plus
     `rice_bits(k, u - 1)` for each non-zero code, plus `gamma_bits(z + 1)` for a last run
     of z zero codes when z is not 0.

   The data size is the bit count rounded up to whole bytes. The encoder evaluates the 64
   combinations in the order predictor 0 to 3, plain then run, k 0 to 7, and keeps a
   combination only when it is strictly smaller than the best so far, which gives the
   tie-break of Requirement 7. When the best is not below N bytes it writes a stored record.
4. **Bits.** `coded_record` writes the chosen combination: bits fill each byte from the most
   significant bit and the last byte is padded with zero bits.
5. **Container.** Header, palette and records. With compression the bytes after the header
   pass through `zlib.compressobj(9, zlib.DEFLATED, -15)`, a raw stream with a 32,768-byte
   window.

Speed: the residuals use `bytes.translate` and generator expressions, the histogram
`collections.Counter`, and the zero runs a regular expression over the code bytes. A
60 x 30 full-colour clip of 500 frames encodes and decodes in a few seconds.

### Import timeline

`source_frames` yields the frames in presentation order with exact times in milliseconds as
`Fraction` values.

- **GIF** (Pillow): `Image.open`, then for each index up to `n_frames`: `seek`, the delay
  from `info["duration"]` (10 or less becomes 100), and the composed frame from
  `convert("RGBA")`, laid over black. Start times are the running sum of the delays.
- **mp4 and mov** (PyAV): `av.open`, the first entry of `container.streams.video`, then
  `container.decode(stream)`. A frame's time is `(pts - first_pts) * stream.time_base`, and
  its picture `frame.to_ndarray(format="rgb24")`. Each frame ends where the next begins. The
  last frame lasts the mean interval `(last_time - first_time) / (count - 1)`, or 20 ms when
  there is one frame.

The end of the last frame is the length of the media. The requested length is the given
duration, or the length of the media minus the start. The number of ticks is
`max(1, floor((length_ms + 10) / 20))`; tick n is at `start + 20 * n` ms. `tick_pictures`
walks the frames once, resamples each source frame that is on screen at one or more ticks
exactly once, and returns one canvas picture per tick. When no duration is given, the tick
count is known only once the last frame has been read: ticks are collected up to the end of
the last frame and the list is then cut to the count. `import_media` turns each tick into a
20 ms frame; `jsonframes.dumps` merges equal neighbours.

`bad-range` is raised when the start is negative, the duration is zero or negative, the
start is at or after the length of the media, or the start plus the duration is after it.

The rotation a file may record for display, the shape of non-square source pixels and colour
profiles are not applied; the picture is used as the library decodes it.

### Fitting and the area mean

`source_rect` gives the rectangle of source space, in source pixels, that the canvas shows.
For a source of Sw by Sh pixels and a canvas of W by H:

| Fit | When `Sw * H >= Sh * W` (source is wider) | Otherwise |
|---|---|---|
| `stretch` | the whole source | the whole source |
| `fill` | full height; width `Sh * W / H`, centred | full width; height `Sw * H / W`, centred |
| `fit` | full width; height `Sw * H / W`, centred, reaching beyond the picture | full height; width `Sh * W / H`, centred, reaching beyond the picture |

Canvas column c, counted from the left from 0, covers the c-th of W equal slices of the
rectangle's width; canvas row r, counted from the top from 0, the r-th of H equal slices of
its height. Row r is canvas row `y = H - r`.

`resample` computes, for each canvas pixel, the sum over source pixels of
`overlap_x * overlap_y * value`, divided by the area of the pixel's slice, where the overlaps
are the lengths shared by the slice and the source pixel. All lengths are multiplied by
`2 * W * H`, which makes them whole numbers, so the sum and the rounding
`(2 * sum + area) // (2 * area)` are exact. The same rule applies whether the picture
shrinks or grows. Area of the rectangle outside the source adds nothing to the sum, which is
how the bars of `fit` are black and their inner edge is blended.

The work is done per canvas row with numpy `int64` arrays: the source rows a canvas row
overlaps are combined with their weights, then the columns. `resample` rejects
`unreadable-media` when `511 * area`, the largest value of `2 * sum + area`, would not fit
in 63 bits.

### Generators

**Rainbow** (`generators/rainbow.py`). `COLOURS[i]`, for i from 0 to 254, is
`colorsys.hsv_to_rgb(i / 255, 1, 1)` with each channel multiplied by 255 and rounded with
`round`. For a canvas pixel (x, y) and a shift:

```python
hue = ((x - 1) / width + (height - y) / (4 * height)) % 1.0
colour = COLOURS[(int(hue * 255) + shift) % 255]
```

These are the expressions of the proof-of-concept scripts, written for coordinates that
start at 1 with y growing upward, so the pictures are the same as on the board today.

**Hello world.** The text `HELLO WORLD` in this font, six rows high, top row first:

```
H: X..X  E: XXXX  L: X...  O: .XX.  W: X...X  R: XXX.  D: XXX.
   X..X     X...     X...     X..X     X...X     X..X     X..X
   XXXX     XXX.     X...     X..X     X...X     X..X     X..X
   X..X     X...     X...     X..X     X.X.X     XXX.     X..X
   X..X     X...     X...     X..X     XX.XX     X.X.     X..X
   X..X     XXXX     XXXX     .XX.     X...X     X..X     XXX.
```

Letters are one column apart and the two words four columns apart, which makes the text 53
columns wide. It is centred: `(width - 53) // 2` dark columns on the left and
`(height - 6) // 2` dark rows above. A canvas below 53 by 6 is `canvas-too-small`. Frame s,
for s from 0 to 254, lasts 20 ms and gives each lit pixel the rainbow colour of its own
coordinates with shift `(255 - s) % 255`.

**DVD bounce.** A canvas below 3 by 3 is `canvas-too-small`. With `span_x = width - 2` and
`span_y = height - 2`, the animation has `lcm(2 * span_x, 2 * span_y)` frames of 180 ms. In
frame j the square's left column is `1 + bounce(j, span_x)` and its top row is
`height - bounce(j, span_y)`, where `bounce(j, span)` is `m = j mod (2 * span)`, then `m`
when m is at most span and `2 * span - m` otherwise. The four pixels of the square have the
rainbow colour of their own coordinates with shift 0.

**Dense.** For tick n, with `t = n / 50`, `u = x - 1` and `w = height - y`:

```python
ax = 30 + 22 * sin(t * 0.61)
ay = 15 + 11 * cos(t * 0.47)
v1 = sin(u * 0.115 + t * 1.3)
v2 = sin(u * 0.061 + w * 0.173 - t * 0.9)
d = hypot(u - ax, (w - ay) * 1.6)
v3 = sin(d * 0.21 - t * 2.1)
hue = (0.5 + 0.22 * v1 + 0.22 * v2 + 0.11 * v3 + t * 0.07) % 1.0
sat = 0.78 + 0.22 * sin(u * 0.047 - w * 0.091 + t * 0.7)
val = 0.62 + 0.38 * sin(d * 0.13 + v2 * 1.1 + t * 1.6)
```

The colour is `colorsys.hsv_to_rgb(hue, sat, val)` with each channel multiplied by 255 and
rounded. This is the clip the sizes in `docs/format.md` were measured with.

## Example show

`shows/example/show.json`:

```json
{
  "version": 1,
  "brightness": 128,
  "items": [
    {"id": 1, "file": "hello.odrg"},
    {"id": 2, "file": "dvd.odrg"},
    {"id": 3, "cycle": [1, 2], "seconds": 15}
  ],
  "start": 3
}
```

It is packed with the two-leg mapping:

```
python -m odrig pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
```

## Test vectors

`tests/converter/build_vectors.py`, run as `python -m tests.converter.build_vectors`, writes
both sets from fixed data and a seeded `random.Random`, of which it uses only `random()`.
It uses `coded_record`, `stored_record` and `container` to force each choice, and writes
each expected `NAME.json` from the pictures it started with, not from the decoder. A coded
record holds at most N bytes of data, so a forced combination cannot code every picture:
the builder grows each picture byte by byte from codes that the combination writes in at
most N bytes, and checks them against `codes`. It exposes the cases as data
(`valid_cases()`, `invalid_cases()`), each with its name, its bytes, whether zlib made any
of them and, for an invalid case, the valid bytes it was changed from, so the tests can
compare the tracked folders with it.

Valid set:

| Name | Content |
|---|---|
| `rgb-modes` | 4 x 3, no palette: one coded record for each of the 64 combinations of predictor, mode and k. |
| `pal-modes` | 5 x 4, palette of 7: the same 64 combinations on index bytes. |
| `escape` | Plain-mode and run-mode records, for k from 0 to 4, whose codes include `8 << k`, `(8 << k) - 1` and 255. |
| `stored` | Stored records, first in the file and after a coded record, with and without a palette. |
| `run-to-end` | Run-mode records ending in a zero run, and a record whose codes are all zero. |
| `run-last-nonzero` | Run-mode records whose last code is not zero. |
| `long-run` | 20 x 16 palette canvas with zero runs longer than 255 codes. |
| `durations` | Records of 1 ms and of 65,535 ms. |
| `pal-256`, `pal-1` | A 16 x 16 file using all 256 palette entries; a file with a palette of one colour. |
| `one-wide`, `one-high`, `one-pixel` | Canvases 1 x 5, 5 x 1 and 1 x 1, with and without a palette, with predictors 1 and 2. |
| `deflate-stored`, `deflate-fixed`, `deflate-dynamic` | One body compressed with zlib level 0, with strategy `Z_FIXED`, and with level 9. |
| `encoded` | A short animation written by `encode()`, with and without a palette, compressed. |

Names that cover two kinds of file carry a suffix, for example `stored.rgb` and
`stored.pal`.

Invalid set: each file is a small valid file with one change, named as Requirement 19
states. The builder writes the cases listed there and one file for every other reason.

## Error handling

- Every refusal is a `Rejection`. Nothing else is caught and turned into a rejection, except
  `zlib.error` in the decoder and the decoding errors of Pillow and PyAV in `media`
  (`unreadable-media`). A programming error ends the tool with a traceback.
- Readers reject on the first defect they meet and do not try to continue.
- `pack` writes nothing before every source has been read, checked and encoded.

## Third-party libraries

| Library | Used for | Licence |
|---|---|---|
| numpy | arrays in the area mean | BSD 3-Clause |
| Pillow | reading GIF files | MIT-CMU (HPND) |
| av (PyAV) | reading mp4 and mov files | BSD 3-Clause; its wheels carry FFmpeg libraries under LGPL and GPL terms |

All three publish binary wheels for macOS, Windows and Linux and install with pip alone.
They are installed, not copied into the repository. `requirements.txt` names an exact
version of each, chosen when the import task is done as the newest release with wheels for
Python 3.10 and later on the three systems. numpy has no such release: the file names
numpy 2.2.6 for Python below 3.11 and numpy 2.4.6 from Python 3.11 on. The PyAV names used above (`av.open`,
`streams.video`, `decode`, `pts`, `time_base`, `to_ndarray`) are confirmed against that
version in the same task.

Setup, from the repository root:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Testing strategy

The suite is `unittest`, in `tests/converter/`, run with

```
python -m unittest discover -s tests/converter -t .
```

from the repository root. Discovery picks up every `test_*.py` in the folder; no script and
no document lists test files.

| File | What it proves |
|---|---|
| `test_cli.py` | Exit statuses, the error line, no partial output, replacing an output, two runs giving identical bytes. |
| `test_jsonframes.py` | One accepted and one rejected case per rule of Requirement 3; the canonical layout byte for byte; merging; read-after-write. |
| `test_odrg_decode.py` | Files assembled by hand from the examples of `docs/format.md` (the Rice code of 5 with k = 1, the Gamma codes of 1, 2 and 5, each predictor on a tiny canvas), and every reason of Requirement 6. |
| `test_odrg_encode.py` | Seeded random animations decode to their source; the chosen record is never larger than any of the 64 forced records; ties; stored frames on noise; merging; splitting of long frames; palette order; the two encode reasons; the compression flag. |
| `test_check.py` | The printed lines for both formats; rejections. |
| `test_mapping.py` | Both tracked mapping files; one case per rule of Requirement 10. |
| `test_show_pack.py` | Every reason of Requirement 14; the content of the output folder; nothing left behind on refusal. |
| `test_generators.py` | The facts of Requirement 15; tracked files equal to generator output; sizes within 2 percent; round trips of Hello world, DVD bounce and the dense 60 x 30 clip, compressed and uncompressed. |
| `test_vectors.py` | Every valid vector decodes to its expected file; the coverage of Requirement 18, read from the mode bytes and headers of the tracked files; every invalid vector is rejected with the reason in its name; every reason of Requirement 6 has a file; each invalid case of the builder is valid before its one change; the tracked folders hold exactly the names the builder produces, with identical bytes for every file made without zlib. |
| `test_import_timeline.py` | A GIF with unequal delays gives the hand-computed tick pictures; mp4 and mov inputs give the canvas size, multiples of 20 ms and the requested length. |
| `test_import_fit.py` | `source_rect` and `resample` on small arrays with hand-computed results, for the three fits, shrinking and growing. |
| `test_import_range.py` | Start, duration, rounding of the tick count, `bad-range`. |
| `test_stdlib_only.py` | A fresh interpreter that runs `encode`, `decode`, `check`, `pack` and the generators has not imported numpy, PIL or av. |
| `test_docs.py` | Every reason in `odrig/errors.py` appears in `docs/reasons.md`; `docs/converter.md` names every subcommand. |
| `test_scope.py` | No module of `odrig/` imports a network or serial module, and none branches on the operating system. |

`media_fixtures.py` builds the inputs in a temporary folder: a GIF with Pillow, and an mp4
and a mov with PyAV's built-in `mpeg4` encoder, 64 x 36 pixels, 25 frames per second, each
frame one flat colour from a fixed list so that a decoded frame is recognised by its nearest
list colour. No media file is tracked.

The vector tests list the two vector folders at run time; no test names a vector file.

## Documentation

- `docs/converter.md`: setup, the five subcommands with one example each, the three fits,
  the generators, packing the example show into `build/example-show`, the test command, the
  vector layout and how to rebuild the vectors.
- `docs/reasons.md`: one table per kind of file, with every reason and its condition.
- `README.md`: one sentence pointing to `docs/converter.md`.
- `docs/format.md`, section "What a reader rejects": the rejections the text implies but
  does not list (a file that ends early, an invalid DEFLATE stream, a width or height of
  zero, a stored mode byte other than `0x40`, bytes after the DEFLATE stream), and the
  sentence that a reader does not examine padding bits.
- `docs/mapping.md`: the rules a mapping file must meet, as in Requirement 10, and the LED
  formula written with the file's `width` and the leg's number of rows in place of 60 and
  180.

## What later seeds take from this one

- `odrig.odrg.decode` and `odrig.jsonframes` as the reference for decoded pictures.
- `odrig.mapping.read` for the canvas size and the legs.
- `tests/vectors/` for every other ODRG reader.
- `pack`, the example show and the generators for installed file sets; the generators take
  the canvas size from a mapping file, which the ten-leg demo show of seed 03 needs.
- `docs/reasons.md` as the one list of reason names.
