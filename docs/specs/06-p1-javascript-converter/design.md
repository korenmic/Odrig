# Design: JavaScript converter (seed 06)

## Overview

The JavaScript converter is a port of the Python package `odrig`, module by module, into
the folder `converter/`:

- **the library**, `converter/lib/`: plain JavaScript modules with no dependency and no
  file access. It reads and writes JSON frames, decodes and encodes ODRG, reads mapping
  and show files, packs a show from bytes, fits pictures and builds the 50
  frames-per-second timeline. It brings its own DEFLATE decoder and its own DEFLATE
  compressor, so that it gives the same bytes in Node.js and in every web view.
- **the command line part**, `converter/odrig.js` and `converter/cli/`: arguments, files
  and folders, and two readers of media: the ffmpeg program of the npm package
  `ffmpeg-static` for mp4 and mov, and the GIF reader of the npm package `omggif`.

It is started as `node converter/odrig.js <subcommand> ...`. Nothing is built.

The Python tool stays as it is. The suite of the JavaScript tool,
`npm test --prefix converter`, runs both tools on the same inputs and compares them, and
loads the library in the Chrome that is installed.

Decisions taken where the seed left a point open are in `docs/drifts.md` under "Seed 06".

## What this design relies on

Read for this design: the Python tool and its suite, the core's DEFLATE decoder, the test
vectors, and the spec of seed 05. A task that finds one of these different follows the code
and records the difference in `docs/drifts.md`.

| Where | What is there |
|---|---|
| `odrig/cli.py` | Five subcommands built with `argparse`; `status_of` turns a `Rejection` into the error line and status 1, with white space in the detail collapsed. |
| `odrig/errors.py` | 42 reason names, `Rejection(reason, detail)`, `naming(path)`. |
| `odrig/files.py` | `read(path, missing)` and `write(path, data)` through `<path>.part`; the operating system's message as the detail. |
| `odrig/strictjson.py` | `loads` on Python's `json` with hooks; `members`, `integer`, `array`. An integer text of more than 30 characters becomes plus or minus 10 to the power 30. |
| `odrig/jsonframes.py` | `loads`, `dumps`, `merged`, `colours`, `colour_count`; the canonical layout. |
| `odrig/odrg.py` | `decode`; `encode` with `palette_for`, `_hue_order`, `to_buffer`, `best_record`, `_data_sizes`, `coded_record`, `stored_record`, `container`; compression with `zlib.compressobj(9, zlib.DEFLATED, -15)`. |
| `odrig/mapping.py` | The reader of mapping files. **After seed 05** it reads both kinds, with the order of checks and the details that the design of seed 05 gives under "The reader", and has `kind`, `strips`, `strip_length`, `led_count` and `position`. Today's file reads row legs only. |
| `odrig/show.py` | The reader of show files, `files(show)`, the three passes over the ids. |
| `odrig/pack.py` | `pack` and `_write_folder`, which builds `<out>.part` and moves it into place. |
| `odrig/media.py` | `import_media`, `tick_pictures`, `tick_count`, `source_rect`, `resample`, `_shares`, `_over_black`, `_gif_frames` on Pillow, `_video_frames` on PyAV. Times are `Fraction`s; the mean is computed with 64-bit integers of numpy. |
| `odrig/generators/`, `odrig/mapdoc.py` | The generators of the tracked animations and of the dense clip, and, after seed 05, the tool that writes `docs/mapping.md`. They are not ported. |
| `core/src/inflate.cpp` | A DEFLATE decoder that judges each part of a stream at the point where zlib does; see "Seed 02: At which bit the DEFLATE decoder finds a defect" in `docs/drifts.md`. |
| `tests/vectors/` | 22 valid vectors with their frames and 34 invalid ones named by their reason. |
| `tests/converter/media_fixtures.py` | `write_gif`, `save_gif` and `write_video`, which build the test media with Pillow and PyAV. |
| `mapping/`, `shows/` **after seed 05** | `mapping/legs-2.json` (60 x 6), `mapping/legs-20.json` (60 x 60, column legs), `shows/example/show.json`, `shows/demo-20/show.json`. `mapping/legs-10.json` and `shows/demo-10/` are gone. |

On this Mac: Node.js 26.5.0, npm 12.0.2 with `ignore-scripts` false, Google Chrome in
`/Applications`, Python 3.14.6 with zlib 1.2.12, and Node.js 20.18.0 in the firmware tool's
work folder, `build/firmware/venv/bin/node`, when seed 04's setup has run.

## Repository layout

```
converter/
  odrig.js              the command line: node converter/odrig.js <subcommand> ...
  package.json          private, "type": "module", Node.js 20 or later, two packages
  package-lock.json     tracked
  ffmpeg.sha256         the checksum of the decoder program, for each platform verified
  lib/                  the library
    index.js            every name the library offers
    errors.js           reason names, Rejection, naming
    whole.js            whole numbers of any size, and exact fractions
    strictjson.js       strict JSON from bytes
    jsonframes.js       JSON frames: read strictly, written in the canonical layout
    inflate.js          raw DEFLATE, decoded
    deflate.js          raw DEFLATE, compressed
    odrg.js             the ODRG decoder and encoder, palettes
    mapping.js          mapping files of both kinds
    show.js             show files
    pack.js             a show packed from bytes
    fit.js              the rectangle of a fit, the area mean, pictures over black
    timeline.js         the 20 ms ticks; the timing rules of video and GIF; import
  cli/
    main.js             subcommands, exit statuses, the error line
    arguments.js        the argument parser and the usage texts
    files.js            an input read whole, an output written through .part
    folder.js           pack: sources from a folder, the output folder
    video.js            mp4 and mov through the decoder program
    gif.js              GIF through omggif, and the pictures of its frames
  tests/
    support.js          both tools run, temporary folders, data from seeds
    reference.py        the Python side: media, clips and expected values
    page/               the page of the Chrome test
    *.test.js           the suite
docs/
  converter.md              rewritten: the JavaScript tool
  reference-converter.md    new: the Python tool
```

Also changed: `.gitignore` gains `/converter/node_modules/`; `README.md`,
`docs/emulator.md`, `docs/firmware.md`, `docs/reasons.md`, `docs/decisions.md`;
`tests/converter/test_docs.py`, `tests/emulator/test_docs.py` and
`tests/firmware/test_docs.py`, where they read a command or a page that changes.

No file of `odrig/`, `core/`, `emulator/`, `odrigctl/` or `firmware/` changes.

## How it is run

```
node converter/odrig.js import MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                               [--start SECONDS] [--duration SECONDS]
node converter/odrig.js encode IN.json OUT.odrg [--uncompressed]
node converter/odrig.js decode IN.odrg OUT.json
node converter/odrig.js check FILE [--format json|odrg]
node converter/odrig.js pack --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]
```

`converter/package.json` says `"type": "module"`, so every `.js` file under `converter/`
is an ECMAScript module for Node.js, and a web view loads the same files with
`<script type="module">` or `import`. `converter/odrig.js` checks the version of Node.js,
imports `cli/main.js`, and exits with the status it returns.

`encode`, `decode`, `check` and `pack` need Node.js alone. `import` needs the two packages:

```
npm ci --prefix converter
```

## The library

### Shapes

| Thing | In JavaScript |
|---|---|
| Bytes of a file | `Uint8Array`. A `Buffer` of Node.js is one. |
| A picture | `Uint8Array` of 3 * W * H. |
| A frame | `{ms, picture}`. |
| An animation | `{width, height, frames}`. |
| A source picture | `{width, height, rgba}`, `rgba` a `Uint8Array` or `Uint8ClampedArray` of 4 * width * height, rows from the top. |
| A rejection | `Rejection`, an `Error` with `reason` and `detail`. |
| A whole number | A `Number` while it is a safe integer, else a `BigInt`. |
| A fraction | `{n, d}`, two `BigInt`s, `d` above 0, in lowest terms. |

Nothing in the library is asynchronous except `timeline.importFrames`, which waits for the
frames it is given.

### The port, module by module

| Python | JavaScript | What must be the same |
|---|---|---|
| `errors.py` | `errors.js` | The 42 names, `canvas-too-small` of the generators among them, so that the two lists can be compared. `naming(label, action)` puts the label in front of the detail. |
| `strictjson.py` | `strictjson.js` | Which texts are refused, and the details of `members`, `integer` and `array`. |
| `jsonframes.py` | `jsonframes.js` | `loads`: the order of the checks and every detail. `dumps`: every byte. |
| `odrg.py`, `decode` | `odrg.js`, `inflate.js` | The order of the checks, every reason and every detail but zlib's. |
| `odrg.py`, `encode` | `odrg.js` | Every byte of an uncompressed file. |
| `zlib.compressobj` | `deflate.js` | The method. Not the bytes. |
| `mapping.py` | `mapping.js` | The order of the checks and every detail, for both kinds of file. |
| `show.py` | `show.js` | The same. |
| `pack.py` | `pack.js`, `cli/folder.js` | The order of the checks, every detail, the file set. |
| `media.py` | `fit.js`, `timeline.js`, `cli/video.js`, `cli/gif.js` | Every tick and every byte of every canvas picture for the same decoded frames. |
| `files.py`, `cli.py` | `cli/files.js`, `cli/main.js`, `cli/arguments.js` | Statuses, the error line, what is left behind. |

A detail is ported by copying the text of the Python source. Where Python formats a value,
the port formats it the same way: a whole number in decimal digits, `0x{value:02x}` as two
lower-case hexadecimal digits, `magic.hex(' ')` as lower-case pairs with a space between
them, and `{float:.6g}` by the rule under "Whole numbers and fractions".

### Whole numbers and fractions (`whole.js`)

Python's integers have no size and its `Fraction` is exact. JavaScript's `Number` is exact
only up to 2 to the power 53. The library never lets a result depend on that:

- **Whole numbers from a file.** `strictjson` gives an integer as a `Number` when it is a
  safe integer and as a `BigInt` otherwise, and `-0` as 0. Sums and products of values
  from a file (`width * height`, the sum of the durations, the number of frame records)
  are computed as `BigInt` whenever an operand or the result is not a safe integer. They
  are printed in decimal digits either way.
- **Fractions.** A fraction is two `BigInt`s. `whole.js` has `fraction(n, d)`, `add`,
  `sub`, `mul`, `div`, `compare`, `floor` and `fromDecimal(text, scale)`. Floor division
  rounds toward minus infinity, as Python's `//` does; `BigInt` division rounds toward
  zero, so `floor` corrects a negative quotient that is not whole.
- **Seconds.** `--start` and `--duration` are read from their digits:
  `fromDecimal(text, 1000)` gives milliseconds as a fraction, and it is rounded half away
  from zero, which is `ROUND_HALF_UP` of Python's `decimal`.
- **`{float:.6g}`.** The Python tool prints the end of the media in a `bad-range` detail
  as a float with six significant digits. `whole.js` has `sixDigits(fraction)`: the
  fraction as a `Number`, `toPrecision(6)`, zeros at the end of the fraction part removed,
  and the exponent form of Python (`1e+06`, at least two digits of exponent) when the
  exponent is below -4 or at least 6.

### strictjson

A reader written for this library, over the bytes of the text. JavaScript's `JSON.parse`
cannot be used: it cannot tell `1.0` from `1`, does not report a member named twice, and
loses digits of a long integer.

1. The bytes are decoded with `new TextDecoder("utf-8", {fatal: true, ignoreBOM: true})`.
   A failure is `bad-json` with the detail `not UTF-8`. `ignoreBOM` keeps a byte-order
   mark in the text, so that step 2 sees it.
2. A text that begins with U+FEFF is `bad-json`, `starts with a byte-order mark`.
3. One value is read by the grammar of RFC 8259, which is the grammar Python's `json`
   reads with its default settings: white space is space, tab, line feed and carriage
   return; a string has no control character and only the escapes of JSON; a number is
   `-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?`. Python also reads `NaN`, `Infinity`
   and `-Infinity` and the Python tool then refuses them; the reader refuses them with the
   Python tool's detail, `<word> is not a JSON value`.
4. An object is a `Map` from member name to value, in the order of the text. A name that
   is already there is `bad-json`, `member "<name>" appears twice in one object`.
5. A number without a fraction and without an exponent is a whole number: a `Number` or a
   `BigInt`, and plus or minus 10 to the power 30 when its text is longer than 30
   characters. Any other number is the value `NOT_AN_INTEGER`, which no check accepts.
6. Anything after the value but white space is `bad-json`.
7. Arrays and objects may be nested 512 deep. Deeper is `bad-json`,
   `nested too deeply`. The reader keeps its own stack and does not call itself, so the
   depth of the text cannot exhaust the stack of the engine.

The detail of a text that is not JSON is `line <l>, column <c>: <what>`, with the reader's
own words for `<what>`. Python's words there are its JSON module's, and they changed with
Python 3.13, so they are not copied.

`members(map, required, optional, what)`, `integer(value, low, high, what)` and
`array(value, what)` are the Python functions with their details.

### jsonframes

`loads(bytes)` follows `odrig/jsonframes.py` line by line. A picture is built from the
`pixels` array in one pass; when an entry is not a whole number from 0 to 16,777,215, the
entries are gone through in order to find the first one that fails and its reason:
`bad-type` or `out-of-range`.

`dumps(animation, {merge = true})` writes:

```
{
  "version": 1,
  "width": <W>,
  "height": <H>,
  "frames": [
    {"ms": <ms>, "pixels": [<c>, <c>, <c>]},
    {"ms": <ms>, "pixels": [<c>, <c>, <c>]}
  ]
}
```

with a line feed after every line, the last one included, a comma and a space between
colours, and each colour as `red * 65536 + green * 256 + blue` in decimal digits. The text
is built in pieces and encoded once; a file of 20 MB is one `Uint8Array`.

`merged(frames)`, `colours(picture)` and `colourCount(frames)` are as in Python.

### The ODRG decoder (`odrg.js`, `decode`)

`decode(bytes)` gives `{width, height, paletteSize, compressed, records, modes}`. It is the
Python function, step for step:

1. Fewer than 16 bytes: `truncated`.
2. The header in the order of its offsets: magic, version, flags, width and height,
   palette size, N, frame count.
3. A compressed body is inflated whole by `inflate.js`: `bad-deflate`, `truncated`, or
   `trailing-bytes` for bytes after the stream.
4. The palette, then each frame record: its five bytes, the duration, L, the mode byte,
   the length of a stored frame, the data bytes, the bits, and last the palette indexes of
   the picture.
5. Bytes after the last record: `trailing-bytes`.

The bits of a coded frame are read from the data bytes with a position counted in bits;
the Python tool's string of `0` and `1` is not copied. `rice(k)` counts one-bits up to a
zero-bit or up to eight; `gamma()` counts zero-bits up to the first one-bit and then reads
as many bits again plus one. A code cut off by the end of the data is `out-of-bits`; the
value is judged after the whole code is read.

### inflate

`inflateRaw(bytes)` gives `{data, used}`, the output and the number of input bytes the
stream took, or throws a `Rejection` with `bad-deflate` or `truncated`.

It is the method of `core/src/inflate.cpp` on a whole input: the two tables for each of
the two codes of a block, canonical codes decoded bit by bit, and each defect judged where
zlib judges it: the counts of a dynamic block when its 14 bits are read; the code-length
code when all its lengths are read; a repeat when its extra bits are read; the two codes
when all their lengths are read, the missing end-of-block code first; a bit pattern that is
no code once as many bits are read as the longest code has; a length or distance symbol
that does not exist when it is decoded; a distance beyond the output when its extra bits
are read. An input that ends before any of these is `truncated`. The output grows in a
`Uint8Array` that doubles.

The Python tool reports what zlib finds first. The suite compares the verdict of
`inflateRaw` with zlib's for every stream it has, as the core's suite does.

### The encoder (`odrg.js`, `encode`)

`encode(animation, {compressed = true})`:

1. `merged(frames)`.
2. `paletteFor(frames)`: the set of colours of all pictures; `null` when there are more
   than 256; else the colours sorted by `hueOrder`.
3. N = W * H * bpp. Above 65,534: `canvas-too-large`.
4. The number of records, the sum over the frames of `ceil(ms / 65535)`. Above
   4,294,967,295: `too-many-frames`.
5. For each frame: its pixel buffer, the picture itself or one palette index for each
   pixel; then one record for each piece of at most 65,535 ms, `bestRecord(old, new, W,
   bpp, duration)`.
6. `container`: the 16-byte header, the palette, the records, through `deflateRaw` when
   compressed.

**The palette order.** `hueOrder(colour)` is `(h, s, mx)` with mx the largest and mn the
smallest of the three channels and d = mx - mn:

- h = 0 when d is 0; `((g - b) / d) mod 6` when mx is red; `(b - r) / d + 2` when mx is
  green and not red; `(r - g) / d + 4` otherwise. The first case that applies is taken, in
  this order, as in the Python tool.
- s = d / mx, and 0 when mx is 0.

All of it is in fractions with the denominator d or mx. Two colours are compared by
cross-multiplying: `h1.n * h2.d` against `h2.n * h1.d`, then the same for s, then mx. Every
product is below 400,000, so `Number`s are exact. Two different colours never have the
same three values: mx and s give mn, and h gives which channel is largest and the value of
the third. The order therefore does not depend on the order in which the colours were
met, and a sort that is not stable gives the same palette.

**The search.** `bestRecord` goes through predictors 0 to 3 and, for each, through plain
mode with k from 0 to 7 and then run mode with k from 0 to 7. It keeps a form only when its
number of data bytes is strictly below the best so far. So among equal sizes the lowest
predictor wins, then plain mode, then the lowest k. When the best size is N or more the
record is stored.

`codes(old, new, width, bpp, predictor)` gives the N codes of a predictor: the residuals
`new - old`, `change - nb(change)`, `new - nb(new)` or `new`, each modulo 256, turned into
codes by `2r` for r below 128 and `2 * (256 - r) - 1` otherwise.

`dataSizes(codes)` gives the 16 sizes without writing a bit, from the histogram of the
codes and the lengths of the runs of zero codes:

- plain mode: the sum over the codes of the length of Rice(k) of the code, in bits,
  rounded up to bytes;
- run mode: for each run of z zero codes, a Gamma code of z + 1, `2 * bits(z + 1) - 1`
  bits; for each code that is not zero and has no zero run before it, one bit, the Gamma
  code of 1; for each code c that is not zero, the length of Rice(k) of c - 1; rounded up
  to bytes. A run of zero codes at the end of the buffer has its Gamma code and no Rice
  code after it.

The length of Rice(k) of v is `(v >> k) + 1 + k` when `v >> k` is below 8, and 16
otherwise.

`codedRecord` writes the bits most significant first into bytes and pads the last byte
with zero bits. `storedRecord` is the five bytes of the record start with mode `0x40` and
the N bytes.

### The DEFLATE compressor (`deflate.js`)

`deflateRaw(bytes)` gives one raw DEFLATE stream.

**Why a compressor of our own.** The library may have no dependency and must give the same
bytes wherever it runs. Node's `zlib` module does not exist in a web view. The compression
streams that Node.js and browsers offer are asynchronous, take no level, and give the
bytes of whatever zlib the platform has: Chrome's and Node's differ, so a file encoded in
the app would not be the file encoded on the command line, and the test of Requirement 16
could not hold. A compressor of about 300 lines in the library removes all of this, as the
core's own decoder did for the board.

**The method** is zlib's at level 9, which is what the Python tool uses, written from
RFC 1951 and from the description of zlib's algorithm:

- A hash of three bytes, `((b0 << 10) ^ (b1 << 5) ^ b2) & 0x7fff`, with a chain of earlier
  positions for each value. A match is at most 258 bytes long and at most 32,506 bytes
  back.
- The longest match is looked for along at most 4,096 positions of the chain, a quarter of
  that when the match before is 32 bytes or longer, and the search stops at a match of 258.
  A match of 3 bytes more than 4,096 back is not used.
- Lazy matching: a match is written only when the match at the next position is not
  longer; otherwise a literal is written and the next match is looked at in turn.
- A block ends after 16,383 symbols. Each block is written in the smallest of three
  forms: stored, with the fixed codes, or with codes made for the block.
- The codes of a block are Huffman codes of at most 15 bits, and of at most 7 bits for
  the code lengths, with the run-length symbols 16, 17 and 18 as zlib uses them.

**What "within 5 percent" is measured against.** The size of the whole file the Python
tool writes for the same source, with the zlib of the Python that runs the test, 1.2.12 on
this Mac. The JavaScript file may be at most 5 percent larger. A smaller one passes.

**Tried for this design.** A sketch of this method, 250 lines of JavaScript, was run on six
bodies made by the Python tool and compared with zlib 1.2.12 at level 9. Every stream was
inflated back by zlib to the body.

| Body | Bytes | zlib, level 9 | The sketch |
|---|---:|---:|---:|
| Hello world, 60 x 6 | 17,715 | 1,122 | 1,122, the same bytes |
| DVD bounce, 60 x 6 | 3,783 | 1,596 | 1,596 |
| Dense, 60 x 6, 2 s | 34,462 | 32,826 | 32,825 |
| Hello world, 60 x 60 | 19,356 | 1,194 | 1,194 |
| DVD bounce, 60 x 60 | 2,324 | 1,036 | 1,037 |
| Dense, 60 x 60, 1 s | 146,717 | 140,856 | 140,857 |

The largest difference is 0.1 percent. The bytes differ where two Huffman codes of the
same cost exist; identical bytes are not a requirement. The dense 60 x 60 body took 9 ms.

The sketch is not project code. The task writes `deflate.js` for the library, with typed
arrays for the chains and the symbols, and without the `node:` modules the sketch used to
check itself.

### mapping

`loads(bytes)` gives `{kind, width, height, legs}`, `kind` being `"rows"` or `"columns"`
and each leg `{leg, pin, firstLed, strips}`; `stripLength(mapping)` and
`ledCount(mapping, leg)` as the Python reader has them after seed 05. The checks are the
nine steps of the design of seed 05, "The reader", in that order, with its details. Every
rejection leaves `loads` as `mapping-malformed`, with the reason and the detail of an
inner rejection in the detail, as `odrig/mapping.py` does. The task ports the reader from
the Python file as seed 05 left it, not from this paragraph.

`position` is not ported: nothing in the JavaScript tool places an LED.

### show

`loads(bytes)` gives `{brightness, items, start}`, an item being `{id, file}` or
`{id, cycle, seconds}`; `files(show)` gives the different file names in the order of first
use. The format is checked first, every failure wrapped as `show-malformed` with the inner
reason in the detail; then the ids in three passes. The task ports `odrig/show.py` as it
is on the day: seed 07 changes what a show file may hold, and whichever of the two seeds
is implemented second brings both readers to the same rule.

### pack

```js
const plan = pack.begin(mappingBytes, showBytes, {mapping: label, show: label});
// plan.canvas, plan.show, plan.names
const bytes = pack.encodeSource(plan, name, sourceBytes, sourceLabel, {compressed});
const files = pack.pack({mapping, show, sources}, {compressed});   // a Map of name to bytes
```

`begin` reads and checks the mapping and then the show, each named by its label in a
detail. `encodeSource` does what the Python tool does for one source: a `null` source is
`file-missing`; a source that is no JSON frames file is `file-malformed` with the inner
reason in the detail; another canvas size is `size-mismatch`; then it is encoded.
`pack` is `begin`, then `encodeSource` for every name of `plan.names`, and gives
`mapping.json`, `show.json` and the `.odrg` files in that order. It is the form a web view
uses, with `sources` a `Map` or an object from `X.json` to bytes.

The command line needs the two steps apart, because the Python tool looks at the output
folder between the show and the first source.

### fit

`sourceRect(sw, sh, w, h, fit)` gives `{left, top, width, height}` as fractions, by the
Python rule: with `wider` true when `sw * h >= sh * w`, `stretch` is the whole picture;
when `(fit == "fill") == wider` the rectangle is as high as the picture and
`sh * w / h` wide, centred; otherwise it is as wide as the picture and `sw * h / w` high,
centred.

`overBlack(source)` gives the three colour bytes of each pixel, `(v * alpha + 127) div 255`
when its alpha is below 255.

`resample(rgb, columns, rows, rect, w, h)` gives the canvas picture. Every length is
counted in units of 1 / (2 * w * h) of a source pixel, as in Python:

1. `unit = 2 * w * h`. `x0 = left * unit`, `y0 = top * unit`, `dx = width * unit / w`,
   `dy = height * unit / h`, each a whole number, computed as `BigInt`. `area = dx * dy`.
2. `511 * area >= 2^63`: `unreadable-media`, with the Python tool's detail.
3. For each canvas column c, `shares(x0 + c * dx, dx, columns, unit)`: the first source
   column the slice covers and, for it and each one after it, the length they share. The
   same for each canvas row r with `y0 + r * dy`, `dy` and `rows`. The first index is
   `max(0, floor(start / unit))` and the last `min(count, ceil(end / unit))`, with the
   floor and the ceiling of `whole.js`: a slice that begins left of the picture has a
   negative start.
4. For canvas row r: `down[column][channel]`, the sum over the source rows of the row's
   share times the channel value; then for canvas column c
   `sum = sum over the source columns of the column's share times down`.
5. The value is `(2 * sum + area) div (2 * area)`.
6. The rows are put out bottom row first: the top row of the source lands on row H.

**Exact in `Number`s where it can be.** No intermediate value is above `511 * area`. When
`511 * area` is below 2 to the power 53, steps 3 to 5 run in `Number`s, in `Float64Array`s,
and every value is a whole number that a `Number` holds exactly. The division of step 5 is
`(a - a % b) / b`, which is exact, and not `Math.floor(a / b)`, whose quotient is rounded.
A picture of 3,840 x 2,160 on a canvas of 60 x 60 has an area of 1.2 * 10^11 units and is
far inside this. Between 2^53 and 2^63 the same steps run in `BigInt`s, slowly and
exactly. The suite has a case on each side of the border.

### timeline

`tickCount(length)` is `max(1, floor((2 * length + 20) / 40))` on a fraction.

`tickPictures(frames, startMs, durationMs, place)` is the Python function on an iteration
of `{start, end, picture}` with `start` and `end` fractions of milliseconds: the two checks
of the signs first; then, for each frame, ticks are added while there are fewer than
wanted and `startMs + 20 * ticks < end`, the frame fitted with `place` at its first tick;
the iteration is left when `end >= stop`; then no frame at all is `unreadable-media`, and
the two checks against the length are `bad-range` with the Python details.

`videoFrames(timed)` turns frames with a presentation time into frames with a start and an
end: the first time is time zero; a frame ends where the next begins; the last one lasts
`start / (count - 1)`, or 20 ms when it is alone; a frame without a time and a time below
the one before are `unreadable-media`.

`gifFrames(delayed)` does the same for frames with a delay: a delay of 10 ms or less is
100 ms, and each frame begins where the one before ends.

### How the library is given frames

```js
const animation = await timeline.importFrames(source, {width: 60, height: 60},
                                              {fit: "fill", startMs: 0, durationMs: null});
```

`source` is `{kind, frames}`:

- `kind` is `"video"` or `"gif"`.
- `frames` is a synchronous or an asynchronous iterable. `importFrames` takes one frame at
  a time with `for await`, and stops asking when the part is covered; an iterable with a
  `return` method is so told to stop decoding.
- A frame of a video is `{width, height, rgba, time}`: `time` is the presentation time in
  milliseconds from any starting point, a whole number or a fraction given as `[n, d]`,
  each a safe integer or a `BigInt`.
- A frame of a GIF is `{width, height, rgba, delayMs}`: the picture as it is on screen,
  with every earlier frame applied, and the delay the file records in whole milliseconds.

`importFrames` builds the timing with `videoFrames` or `gifFrames`, fits each frame that is
on screen at a tick with `overBlack`, `sourceRect` and `resample`, and gives the animation
with one frame of 20 ms for each tick. `jsonframes.dumps` then merges equal neighbours.

This is the whole surface a web view needs. With WebCodecs a video frame has a `timestamp`
in microseconds, so its `time` is `[timestamp, 1000]`; with an image decoder a GIF frame
has a `duration` in microseconds. Reading pixels out of a video frame and choosing a
decoder are the app's work, in seed 09.

## The command line part

### Arguments (`cli/arguments.js`)

A parser written for the five subcommands, about 80 lines. Node's `util.parseArgs` is not
used: it takes `--start -1` for a missing value, where the Python tool reads the start
`-1` and then refuses it as `bad-range` with status 1.

- The first argument is the subcommand, or `--help`.
- `--name value` and `--name=value`. After an option that takes a value, the next argument
  is the value unless it begins with `-` and is not a minus sign followed by digits with
  an optional fraction.
- `--` ends the options.
- A flag (`--uncompressed`, `--help`) takes no value.
- An option given twice takes its last value, as `argparse` has it.
- An unknown option, an option without its value, a wrong number of positional arguments
  and a missing required option are usage errors.

Shortened option names, which `argparse` accepts when they are unambiguous, are not
accepted: no document shows one.

The usage texts are fixed texts in this file, one for the tool and one for each
subcommand.

### Statuses and the error line (`cli/main.js`)

`main(argv, streams)` returns the status. It parses, runs the subcommand and catches
`Rejection`: one line `error: <reason>: <detail>` with every run of white space in the
detail made one space, status 1. A usage error is status 2. Any other error is thrown on.

`check` prints its lines with one `write`, after everything was read and decoded.

### Files (`cli/files.js`)

`read(path, missing = "not-found")` reads a file whole; a failure is a rejection with the
detail `<path>: <words>`. `write(path, bytes)` writes `<path>.part` and renames it over
`path`; on a failure it removes the part file and rejects with `cannot-write`.

The words are Python's `strerror` for the error codes that matter:

| Code | Words |
|---|---|
| `ENOENT` | `No such file or directory` |
| `EISDIR` | `Is a directory` |
| `ENOTDIR` | `Not a directory` |
| `EACCES` | `Permission denied` |
| `EEXIST` | `File exists` |
| `ENOTEMPTY` | `Directory not empty` |
| any other | the code itself |

A path is used as it was given. Where the Python tool joins a folder and a name with
`os.path.join`, the port joins them the same way: the folder, the separator of the system
unless the folder already ends in one, and the name. Node's `path.join` is not used for a
path that appears in a detail, because it rewrites `./a` as `a`.

### pack on folders (`cli/folder.js`)

1. The mapping file is read, missing as `mapping-missing`; the show file, missing as
   `show-missing`; `pack.begin`.
2. The output path exists and is no folder, or is a folder that is not empty:
   `output-not-empty`.
3. For each name of the plan: the source `<sources>/<X>.json` is read, missing as
   `file-missing`, and `pack.encodeSource`.
4. The files are written into `<out>.part`, made with the folders above it, and that
   folder takes the place of the output folder. On a failure the part folder is removed, an
   output folder that existed and was removed is made again, and the rejection is
   `cannot-write` with the path the system named.

### Video (`cli/video.js`)

**The package.** `ffmpeg-static` 5.3.0. Read on npm's registry and in the package's files:

| # | Fact |
|---|---|
| V1 | Licence GPL-3.0-or-later. It needs Node.js 16 or later and has four dependencies, all for its install script. |
| V2 | Its install script fetches one program, ffmpeg 6.1.1 built for the platform, from the release `b6.1.1` of the package's GitHub repository, into the package's own folder, and makes it executable. Platforms: macOS on Intel and on Apple Silicon, Linux on four processors, Windows on two. |
| V3 | The script checks no checksum. It keeps a copy of the download in the user's cache folder, `~/Library/Caches/ffmpeg-static-nodejs` on macOS. |
| V4 | The package's one export is the path of the program, or `null` on a platform it has none for. It gives the value of the environment variable `FFMPEG_BIN` in place of its own path when that is set. |
| V5 | ffmpeg 6.1's filter `showinfo` logs, at the level `info`, one line `config in time_base: <n>/<d>, frame_rate: ...` and for each frame a line with `n:`, `pts:`, `pts_time:`, `duration:`, `fmt:`, `s:<w>x<h>`; its option `checksum=0` leaves the checksums out. Read in `libavfilter/vf_showinfo.c` of FFmpeg's branch `release/6.1`. |

It is a program that the tool starts. It is not loaded into Node.js, is not part of the
library, and is not copied into the repository: `converter/node_modules/` is ignored. The
operators' app does not use it.

Other packages were looked at and not chosen: `node-av`, bindings to FFmpeg's libraries
with the API closest to PyAV, needs Node.js 22.18 or later; `@ffmpeg-installer/ffmpeg`
carries its programs inside npm packages, without a download, but they are builds of 2018
to 2021 that nobody maintains; `@ffmpeg/ffmpeg` no longer runs in Node.js; `libav.js`
publishes no build with the H.264 and HEVC decoders that phone videos need.

**The call.** One process for one file:

```
ffmpeg -hide_banner -nostdin -nostats -loglevel info -noautorotate -i <path>
       -map 0:v:0 -an -sn -dn
       -vf showinfo=checksum=0,scale=flags=bilinear,format=rgba
       -fps_mode passthrough -f rawvideo pipe:1
```

- Standard output carries the frames, each `4 * w * h` bytes of red, green, blue and
  alpha, rows from the top. Standard error carries the log.
- For each frame the reader takes from the log its `pts` and its size, and from the
  `config in` line the time base n/d. The presentation time of a frame is
  `pts * n * 1000 / d` milliseconds, given to the library as the fraction
  `[pts * n * 1000, d]`. A `pts` of `NOPTS` is given as no time, which the library refuses.
- `-noautorotate` keeps ffmpeg from turning a picture by the rotation the file records,
  which the Python tool does not apply either. `-fps_mode passthrough` keeps every decoded
  frame, neither dropped nor repeated. `flags=bilinear` is the scaler setting PyAV uses
  when it turns a frame into RGBA.
- The format is not forced: like PyAV, ffmpeg tells it from the content.
- Both pipes are read all the time, so that neither fills while the other is waited for.
- When the library stops asking for frames, the process is ended.
- A process that ends with another status than 0 before the part is covered, a frame cut
  short, and no frame at all are `unreadable-media`. The detail is
  `the video cannot be decoded: ` and the last line ffmpeg wrote that is not a frame line.

The program's path comes from the package, V4. `cli/video.js` and `cli/gif.js` load their
package with `import()` when the first file of their kind is read, so nothing else needs
`converter/node_modules/`. When the package is not installed, or the program's file is not
there, the tool ends with `error: decoder-missing: ...` and status 1.
`decoder-missing` is a failure of the setup, not a rejection of an input: it is a word of
`cli/video.js`, is listed in `docs/converter.md`, and is not in `docs/reasons.md`.

**Assumed, to be verified by the task that adds `import`:**

| # | Assumption | If it does not hold |
|---|---|---|
| A1 | The program of V2 installs under npm 12 on this Mac and runs. | `@ffmpeg-installer/ffmpeg` in its place, and the drift recorded. |
| A2 | The log lines of V5 come out as read, with the `pts` in the time base of the `config in` line, and that time base is the stream's. | The times are taken from a second output of the same run in ffmpeg's `framecrc` form, which is made for programs to read. |
| A3 | A file with transparency (`qtrle` in a mov, as the Python suite makes) comes out with its alpha. | The pixel format is named on the input side for that codec, and the drift recorded. |
| A4 | For the suite's mp4 and mov no colour value differs from PyAV's by more than 3. PyAV 17 carries FFmpeg 8 and the package ffmpeg 6.1.1. | The scaler flags are set to what the comparison shows PyAV uses. |
| A5 | A file that is not a video, an empty file and a file cut short make ffmpeg end with a status that is not 0, or with no frame. | `-xerror` is added. |

### GIF (`cli/gif.js`)

**The package.** `omggif` 1.0.10: licence MIT, one file of plain JavaScript, no
dependency, no install script. Its `GifReader` gives the size of the logical screen, the
number of frames, and for each frame its rectangle, its palette, its transparent index,
its delay in hundredths of a second, its disposal, and `decodeAndBlitFrameRGBA`, which
writes the frame's pixels that are not transparent into a picture of the screen's size.

**GIF pictures.** The package draws one frame; the pictures are built here:

1. The canvas has the size of the logical screen, four bytes for each pixel, all zero:
   every pixel transparent.
2. Before frame k is drawn, the disposal of frame k - 1 is applied to the rectangle of
   frame k - 1: 0 and 1 leave it; 2 makes it transparent; 3 gives it back what it held
   before frame k - 1 was drawn. For disposal 3 a copy of the rectangle is kept.
3. Frame k is drawn into its rectangle: a pixel whose index is the frame's transparent
   index is left as it is, every other pixel gets the colour of the frame's palette and
   the alpha 255.
4. The source picture of frame k is a copy of the canvas. Its delay is the frame's, times
   10, in milliseconds.

A frame whose rectangle reaches beyond the logical screen, a file the package refuses,
and a frame for which the package reports that the data is shorter or longer than the
frame, are `unreadable-media`. The package reports the last by writing a warning; the
reader watches for it while it decodes.

These are the rules of the GIF format as browsers apply them. The web view of seed 09 will
decode GIFs itself, by these rules, so the two ways through the library agree. Pillow,
which the Python tool uses, differs in three corners, read in its `GifImagePlugin.py`,
version 12.3.0: after a frame with disposal 2 that has no transparent index it paints the
background colour where this reader makes the pixels transparent; it keeps the disposal
of the frame before for a frame that names none; and where the first frame does not cover
the screen it paints the background colour. The suite's GIFs do not go there, and the
documentation says so.

**Assumed, to be verified by the same task:** A6, for the GIFs the Python suite makes and
for GIFs built with Pillow that stay out of the three corners, one with a transparent
index, one with later frames smaller than the screen, and one for each disposal with a
transparent index on every frame and a disposal named on every frame, the pictures equal
Pillow's. If the package fails on a GIF that Pillow reads, the decoder program reads GIFs
too, with `-f gif` in front of `-i`, and the drift is recorded.

## The page of the Chrome test

`converter/tests/browser.test.js`:

1. Starts an HTTP server on `127.0.0.1` on a free port. It serves `converter/lib/` at
   `/lib/`, `converter/tests/page/` at `/`, `animations/hello.json` at `/hello.json`, and
   takes one `POST /result`.
2. Starts Chrome: the program the environment variable `ODRIG_CHROME` names, or
   `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, or `google-chrome`,
   `chromium` or `chrome.exe` in the usual places of Linux and Windows. The arguments are
   `--headless=new --no-first-run --no-default-browser-check --disable-extensions
   --disable-background-networking --disable-sync --disable-component-update
   --user-data-dir=<a new temporary folder>` and the address of the page.
3. `page/index.html` holds one `<script type="module" src="page.js">`. `page.js` imports
   `/lib/index.js`, fetches `/hello.json`, reads it with `jsonframes.loads`, encodes it
   compressed and uncompressed, decodes both, imports three source pictures it fills from
   a fixed rule with each fit, and posts the results as JSON with the bytes in base64. An
   error is posted as its text.
4. The test waits up to 60 seconds for the post, ends Chrome, removes the profile folder,
   and compares: the two files with what `node converter/odrig.js encode` writes, the
   decoded frames with the source, and the canvas pictures with what the same calls give
   in Node.js.

Module scripts do not load from a `file:` address, which is why there is a server.
Without a Chrome the test is skipped and says where it looked.

## Testing strategy

One command, from the repository root:

```
npm test --prefix converter
```

`converter/package.json` has `"scripts": {"test": "node --test"}`. npm starts it in
`converter/`, and the test runner finds every file there whose name ends in `.test.js`.
Tried for this design: Node.js 20.18 takes a folder as an argument of `--test` and no
pattern, and Node.js 26.5 takes a pattern and no folder; without an argument both find the
files of the folder they are started in. `converter/node_modules/` is skipped by both.

**The Python side.** `tests/support.js` runs the Python tool as a child process:
`.venv/bin/python` of the repository (`.venv\Scripts\python.exe` on Windows), or the
program `ODRIG_PYTHON` names, with the repository root as the working folder.
`tests/reference.py` is what the tests ask for things only Python has:

| Request | Gives |
|---|---|
| `gif`, `video` | A test GIF, mp4 or mov, made by `tests/converter/media_fixtures.py`. |
| `dense` | The dense clip for a mapping file and a number of seconds, from `odrig.generators.dense`. |
| `resample` | For source pictures and rectangles read from standard input, the canvas pictures of `odrig.media.resample`. |
| `ticks` | For frames with times read from standard input, the ticks of `odrig.media.tick_pictures`, or its rejection. |
| `inflate` | For streams read from standard input, zlib's verdict on each. |
| `encode` | For animations read from standard input, the uncompressed and the compressed file of `odrig.odrg.encode`. |

Data from seeds is made in JavaScript, by a small generator in `tests/support.js`, and
given to Python as data, so both sides work on the same bytes.

**What each test file holds:**

| File | Tests |
|---|---|
| `cli.test.js` | Statuses 0, 1 and 2; the error line; nothing on standard output and nothing left behind after a rejection; `--help`; every usage error of Requirement 2; the same status as the Python tool for a table of command lines, `--start -1` among them; an old Node.js refused, with the version check given a version. |
| `library.test.js` | Every file of `lib/` imports only `./<name>.js`; none names `node:`, `require`, `process`, `Buffer`, `fetch`, `document`, `window`, `CompressionStream`, `Date` or `Math.random`; `index.js` offers every module; the reason names are those of `odrig/errors.py`, read from that file. |
| `strictjson.test.js` | A table of texts, each read by both tools through `check --format json`: the same reason; integers at and beyond 2 to the power 53 and of 31 characters; a member named twice by an escape; depth 512 and 513. |
| `jsonframes.test.js` | Every rule of the format broken once, with the Python tool's error line; `dumps` byte for byte for the tracked sources and for animations from seeds; a file of 20 MB in under 10 seconds. |
| `inflate.test.js` | The three `deflate-*` vectors; streams from zlib at every level; each damaged in every byte and cut at every length up to a limit of cases: the verdict of zlib. |
| `decode.test.js` | Every valid vector, record by record; every invalid vector, by its reason; `decode` and `check` through the command line against the Python tool, standard output and error line; damaged and cut copies of valid files. |
| `encode.test.js` | Uncompressed files identical for Hello world, DVD bounce, the dense clip and 200 animations from seeds; the palette order for colours of equal hue; the search on records where several forms have the same size; `canvas-too-large` and `too-many-frames`; a duration above 65,535 ms. |
| `deflate.test.js` | Requirement 8: frames identical, sizes within 5 percent, zlib accepts every stream, two runs identical, the time limit. |
| `mapping.test.js` | Every file of `mapping/`; the made-up mappings of `tests/core/support.py`, given by `reference.py`; and mappings written out in the test that break every rule of the design of seed 05 once, for each kind of file, and mix the two kinds. Each is read by both tools through `import`: the same canvas, or the same error line. |
| `pack.test.js` | The example show, the demo show and a show of one dense clip, compressed and uncompressed, against the Python tool's folder; shows that break every rule of `docs/show.md` and meet every reason of `docs/reasons.md`, "Shows", once, with the Python tool's error line; the output folder cases; `pack.pack` from bytes gives the files the command line writes. |
| `fit.test.js` | The rectangles of the three fits as fractions; 300 pictures from seeds against `resample` of the Python tool; a slice left of the picture; the border at 2 to the power 53, on both sides; `unreadable-media` at 2 to the power 63. |
| `timeline.test.js` | Frames with times from seeds against `tick_pictures`: 25, 29.97 and 60 frames a second, one frame, start and duration at every edge, each `bad-range`; the GIF delays 30, 50, 70 and 0. |
| `import.test.js` | Requirement 14: the GIFs byte for byte, the mp4 and the mov within 3, the order of the checks, each reason, `decoder-missing` and a working `encode` in a copy of `converter/` without `node_modules`, the checksum of the decoder program, and that its path lies in `converter/node_modules/`. |
| `browser.test.js` | Requirement 16. |
| `docs.test.js` | Requirement 19: the pages name each subcommand with an example, the test command, the packages with their versions and licences, and what is verified. |

**Who checks what** of the seed's definition of done:

| Item | Checked by |
|---|---|
| 1. Both tools on the same inputs | `encode.test.js`, `deflate.test.js`, `decode.test.js`, `pack.test.js` |
| 2. The test GIF identical, the test mp4 within 3 | `import.test.js` |
| 3. The library in Chrome | `browser.test.js` |
| 4. One command, passing on macOS | `npm test --prefix converter`, in the last task |
| 5. The Python suites still pass | The four commands, in every task |

## What is tracked and what is ignored

| Path | |
|---|---|
| `converter/package.json`, `converter/package-lock.json` | Tracked. `.gitattributes` already keeps git from changing the bytes of a `.json` file. |
| `converter/ffmpeg.sha256` | Tracked: one line for each platform the program was verified on, `<sha256>  <platform>-<processor>`. |
| `converter/node_modules/` | Ignored. |
| What the tests write | Temporary folders of the system, removed by the tests. |
| npm's cache, the cache of `ffmpeg-static` | Outside the repository, in the user's folders. The documentation names both. |

`package.json`:

```json
{
  "name": "odrig-converter",
  "private": true,
  "type": "module",
  "engines": {"node": ">=20"},
  "scripts": {"test": "node --test"},
  "dependencies": {"ffmpeg-static": "5.3.0", "omggif": "1.0.10"}
}
```

## Documents

| Document | What it becomes |
|---|---|
| `docs/converter.md` | The JavaScript tool: what it is; setup with Node.js 20 or later and `npm ci --prefix converter`; the two packages with versions and licences, and what their install fetches and leaves; exit statuses; `import`, `encode`, `decode`, `check` and `pack`, each with its usage line and an example, with the texts on the timeline, the fits, the palette and the search taken over from today's page; `decoder-missing`; GIF pictures and where they differ from the reference; the library, how a page loads it and how it is given frames; the tests; what is verified. |
| `docs/reference-converter.md` | The Python tool: that it is the independent check the tests compare with, and what else uses it: the generators, the vector builder, `odrig.mapdoc`, the firmware tool and the suites of the core and the emulator; its setup; the usage line of each subcommand; the sections "Generators", "Test vectors", "Tests" and "From Python" of today's page. |
| `README.md` | The paragraph on the converter names both pages. |
| `docs/emulator.md`, `docs/firmware.md` | Where they pack a show, the command is `node converter/odrig.js pack ...`. |
| `docs/reasons.md` | The opening says that both converters write this line and use these names. |
| `docs/decisions.md` | "Conversion": the converter is `converter/`, checked against the Python tool. A line in the change log. |

`tests/converter/test_docs.py` reads `docs/reference-converter.md` for what moved there and
`docs/converter.md` for the subcommand sections, with `node converter/odrig.js` in the
commands. `tests/emulator/test_docs.py` counts pack commands in their new form.

## Order of work

1. The frame of the tool: the package file, errors, the argument parser, statuses, files,
   and the test command with the checks on the library.
2. Strict JSON and JSON frames; `check` of a JSON frames file.
3. The DEFLATE decoder and the ODRG decoder; `decode` and `check`.
4. The compressor, checked against zlib by itself.
5. The encoder; `encode`, with and without compression.
6. Mapping files, show files and `pack`.
7. Fitting and the timeline, in the library, on frames the tests supply.
8. Media on the command line: the two packages, `import`.
9. The library in Chrome.
10. The documents and the last run of every suite.

Each step leaves the tool working for what it has: a subcommand that is not there yet is
answered as an unknown subcommand until its task.

## Risks

1. **The decoder program.** It is fetched by an install script from GitHub, without a
   checksum, under the GPL, and it leaves a copy in the user's cache folder. The tracked
   checksum covers the platforms it was verified on. If the owner does not want it,
   `import` of video needs another package, and A1 names one.
2. **Parsing ffmpeg's log** for the times (A2). The form was read in the source of the
   version the package carries; another version of the package can change it. The package
   is pinned.
3. **Colours of a video** depend on two versions of FFmpeg agreeing within 3 (A4). The
   test media are flat colours, which hides differences in how colour is spread between
   pixels; a real video can differ by more at a sharp edge.
4. **GIF pictures** follow browsers, not Pillow, in three corners. The two tools then give
   different JSON for such a GIF.
5. **Details that hold library text** are not compared. A script that reads the detail of
   `bad-json` gets other words from the two tools.
6. **The size of the port.** Every detail of every rejection is compared with the Python
   tool, also for inputs nobody writes, such as a width of 40 digits. That is what keeps
   the two tools one, and it is where the time of the tasks goes.
7. **Seed 05 and seed 07 change readers this seed ports.** The tasks port the Python files
   as they are on the day, and the comparison tests show any difference.
