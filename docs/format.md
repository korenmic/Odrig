# Animation formats

An animation exists in these formats:

| Format | File | Role |
|---|---|---|
| JSON frames | `name.json` | The tracked source of the animation. Lossless and readable. Never played by the board. |
| ODRG | `name.odrg` | The runtime format, produced from the JSON source by the converter. This is what the player reads, on the board and in the emulator. |
| ODRGX | `name.odrgx` | The container of the runtime: a header that names what its payload is, and the payload. A payload of frames is an ODRG file as it is. |

A reader tells ODRG and ODRGX apart by the first four bytes of a file, never by its name.

Both describe the same thing: a list of full-canvas pictures, each shown for a number of
milliseconds. Converting JSON to ODRG loses nothing: the two files show the same picture at
every millisecond.

## Rules common to both formats

**Canvas.** The canvas is W columns by H rows. A pixel is addressed as (x, y), both starting
at 1, with (1,1) at the bottom-left, x growing to the right and y growing upward.

**Pixel order.** Wherever pixels are listed, pixel (x, y) is at position

    p = (y - 1) * W + (x - 1)

so the bottom row comes first, and each row runs left to right.

**Colour.** A colour is three values, red, green and blue, each 0 to 255. They are the values
the LED is given before the board's global brightness is applied.

**Frame.** A frame is the colour of every pixel plus a duration in whole milliseconds, at
least 1.

**Playback.** Frames play in order and the animation loops: after the last frame comes the
first. Frame 1 starts at time 0 and every other frame starts when the one before it ends. At
each LED refresh the player shows the frame whose time span contains the current time. Our
tools build animations on a 50 frames-per-second timeline, so every duration they write is a
multiple of 20 ms.

**Canvas size.** A file carries its own W and H. The player does not play a file whose size
differs from the canvas described by the mapping file.

## JSON frames

A UTF-8 JSON object with exactly these members:

| Member | Type | Meaning |
|---|---|---|
| `version` | integer | Format version. This document describes version 1. |
| `width` | integer | W, at least 1. |
| `height` | integer | H, at least 1. |
| `frames` | array | One or more frames, in playback order. |

Each frame is an object with exactly these members:

| Member | Type | Meaning |
|---|---|---|
| `ms` | integer | Duration in milliseconds, at least 1. |
| `pixels` | array of W * H integers | One colour per pixel, in pixel order. A colour is the integer `red * 65536 + green * 256 + blue`, so 0 is off and 16777215 is full white. |

The file is read strictly. It is UTF-8 without a byte-order mark and holds exactly one JSON
value, and no object names a member twice. An integer is a JSON number written without a
fraction and without an exponent, so `1.0`, `1e3` and `true` are not integers.

A reader rejects a file that breaks these rules, and a file with a different version, a
missing member, any other member, a value of the wrong type, no frames, a wrong number of
pixels, or a value out of range. It checks `version` first.

Consecutive frames with identical pixels should be written as one frame with the durations
added together.

Example, a 3 x 2 canvas showing red at (1,1) and blue at (3,2) for half a second, then green
at (2,2) for half a second:

```json
{
  "version": 1,
  "width": 3,
  "height": 2,
  "frames": [
    {"ms": 500, "pixels": [16711680, 0, 0,  0, 0, 255]},
    {"ms": 500, "pixels": [0, 0, 0,  0, 65280, 0]}
  ]
}
```

## ODRG

A binary file: a 16-byte header followed by the body. All multi-byte integers are
little-endian.

### Header

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | The bytes `4F 44 52 47` ("ODRG"). |
| 4 | 1 | Version | 1. |
| 5 | 1 | Flags | Bit 0: the body is compressed. Bits 1 to 7 are zero. |
| 6 | 2 | Width | W, at least 1. |
| 8 | 2 | Height | H, at least 1. |
| 10 | 2 | Palette size | C: 0, or 1 to 256. |
| 12 | 4 | Frame count | F, at least 1. |

**Pixel units.** When C is 0, a pixel is 3 bytes: red, green, blue. When C is 1 to 256, a
pixel is 1 byte: an index into the palette, less than C. The number of bytes per pixel is
called bpp below (3 or 1).

**Limit.** N = W * H * bpp is the size of one picture in bytes. N is at most 65,534.

### Body

The body is the palette followed by F frame records.

- **Palette:** C entries of 3 bytes each (red, green, blue). Absent when C is 0.
- **Compression:** when flag bit 0 is set, the bytes after the header are a single raw
  DEFLATE stream (RFC 1951, no zlib or gzip wrapper) with a window of at most 32,768 bytes.
  Its output is the body. When the flag is clear, the body follows the header as it is.

Nothing follows the last frame record.

### Pixel buffer

The decoder keeps one pixel buffer of N bytes. Pixel p occupies bytes `p * bpp` to
`p * bpp + bpp - 1`. The buffer is all zero before the first frame, and is reset to zero
whenever playback loops back to the first frame. Each frame record turns the buffer from the
previous picture into the new one.

### Frame record

| Size | Field | Value |
|---:|---|---|
| 2 | Duration | Milliseconds, 1 to 65,535. |
| 2 | Length | L: the number of bytes that follow in this record, 2 to N + 1. |
| 1 | Mode | See below. |
| L - 1 | Data | Depends on the mode. |

Mode byte:

| Bits | Name | Meaning |
|---|---|---|
| 0 to 2 | k | Rice parameter, 0 to 7. |
| 3 | run | 0: plain mode. 1: run mode. |
| 4 to 5 | predictor | 0 to 3, see below. |
| 6 | stored | 1: the data is the new pixel buffer as it is. |
| 7 | | Zero. |

**Stored frame.** The mode byte is `0x40`, L is N + 1, and the data is the N bytes of the new
pixel buffer.

**Coded frame.** The data is a string of bits. Bits fill each byte from the most significant
bit down, and the last byte is padded with fewer than 8 zero bits. Decoding has three steps:

1. Read N codes `u[0]` to `u[N-1]`, each 0 to 255, in plain mode or run mode.
2. Turn each code into a residual byte `r[i]`: when `u` is even the signed value is `u / 2`,
   when `u` is odd it is `-(u + 1) / 2`; `r[i]` is that value modulo 256. So codes
   0, 1, 2, 3, 4 mean 0, -1, +1, -2, +2, and code 255 means -128.
3. Apply the predictor to get the new pixel buffer.

### Bit codes

**Rice(k)** writes a value v from 0 to 255. Let `q = v >> k`.

- When q is less than 8: q one-bits, then a zero-bit, then the k low bits of v, most
  significant first.
- When q is 8 or more: eight one-bits, then v as 8 bits.

To read it, count one-bits. If a zero-bit arrives after q ones (q less than 8), the value is
`(q << k)` plus the next k bits. If eight one-bits arrive, the value is the next 8 bits.

Example with k = 1: the value 5 is written `1101` (q = 2, then the zero-bit, then the low bit
1).

**Gamma** writes a value g of 1 or more. If g takes b bits in binary, write b - 1 zero-bits
followed by those b bits. So 1 is `1`, 2 is `010`, and 5 is `00101`.

### Plain mode

`u[i]` is read as Rice(k), for i from 0 to N - 1.

### Run mode

Run mode stores runs of zero codes compactly. Start with i = 0 and all of `u` zero, then
repeat while i is less than N:

1. Read g as Gamma. The next g - 1 codes are zero: add g - 1 to i.
2. If i equals N, stop.
3. Read v as Rice(k). Set `u[i]` to v + 1 and add 1 to i.

When the last code in the buffer is non-zero, nothing follows it. A run never extends past N.

### Predictors

Let `stride = W * bpp`. For a byte array `a` and position i, the neighbour `nb(a, i)` is:

- `a[i - bpp]` when `i mod stride` is at least bpp: the same channel of the pixel to the left;
- otherwise `a[i - stride]` when i is at least stride: the same channel of the first pixel of
  the row before it in pixel order;
- otherwise 0.

With `old` the pixel buffer before the frame and `new` the buffer after it, processed in
increasing i:

| Predictor | Name | Rule |
|---:|---|---|
| 0 | Previous frame | `new[i] = (old[i] + r[i]) mod 256` |
| 1 | Previous frame, then left | `d[i] = (r[i] + nb(d, i)) mod 256`, then `new[i] = (old[i] + d[i]) mod 256` |
| 2 | Left | `new[i] = (r[i] + nb(new, i)) mod 256` |
| 3 | None | `new[i] = r[i]` |

In palette files the same arithmetic is applied to the index bytes. Every resulting index is
less than C.

### What a reader rejects

A file that ends before the header, the palette or a frame record is complete, a wrong magic
or version, non-zero reserved bits, a width or height of zero, C above 256, N above 65,534, a
frame count of zero, a compressed body that is not a valid DEFLATE stream or whose stream
ends before its last block is complete, a duration of zero, a length below 2 or above N + 1,
a mode byte with bit 6 set that is not `0x40`, a stored frame whose length is not N + 1, a
coded frame that runs out of bits or has 8 or more padding bits, a run that passes N, a code
above 255, a palette index of C or more, and any bytes after the last frame record: in the
body, or in the file after the end of the DEFLATE stream.

A reader does not examine the values of the padding bits.

The bit codes can spell a code above 255. With k of 6 or 7, fewer than eight one-bits
followed by the k low bits give a Rice value of up to 1,023, and in run mode the Rice value
255 gives the code 256. A reader reads the whole Rice code and then rejects it.

Every rejection has a fixed name. The names are listed in [reasons.md](reasons.md).

### Decoder memory

A decoder needs the N-byte pixel buffer and, for predictor 1, two pixels' worth of running
values. It can read the file front to back without holding a whole frame record in memory.
A compressed file adds the DEFLATE window (up to 32,768 bytes) and the inflate state.

## ODRGX

A binary file: a header of 20 bytes and the payload, nothing after it. All multi-byte
integers are little-endian.

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | Magic | The bytes `4F 44 52 58` ("ODRX"). |
| 4 | 1 | Container version | 1. |
| 5 | 1 | Type | The content type: 1, frames; 2, a text. |
| 6 | 1 | Type version | The version of the content type: 1. |
| 7 | 1 | Reserved | 0. |
| 8 | 2 | Width | W, at least 1. |
| 10 | 2 | Height | H, at least 1. |
| 12 | 4 | Loop | The length of one loop in milliseconds, 1 to 4,294,967,295. |
| 16 | 4 | Payload | P, the number of bytes after the header. |

The container's version, the content type and the type's version are three numbers of
their own: a new version of one type changes neither the others nor the container. The
loop is in the header so that a reader that reads the headers only knows how long every
file plays; a reader that reads the payload refuses a loop that is not the payload's.

### The frames payload

The payload of the type 1 is an ODRG file, as "ODRG" above describes it, for the canvas
of the container. Its loop is the sum of the durations of its frames. It plays exactly as
the ODRG file plays by itself.

### The text payload

The payload of the type 2 is a text: its settings, the text as it was written, and its
layout, the glyphs and their places, which the converter made. The player draws the glyphs
where the settings move them; it lays out nothing itself.

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Font | 1 `small`, 2 `medium`, 3 `large` |
| 1 | 1 | Font version | the version of the font the layout was made with: 1 |
| 2 | 1 | Effect | 0 `static`, 1 `marquee`, 2 `slide`, 3 `pan` |
| 3 | 1 | Motion | 0 `left`, 1 `right`, 2 `up`, 3 `down` |
| 4 | 1 | Align | 0 `left`, 1 `center`, 2 `right` |
| 5 | 1 | Vertical align | 0 `top`, 1 `middle`, 2 `bottom` |
| 6 | 1 | Direction | 0 `auto`, 1 `ltr`, 2 `rtl` |
| 7 | 1 | Wrap | 0 or 1 |
| 8 | 3 | Colour | red, green, blue |
| 11 | 3 | Background | red, green, blue |
| 14 | 2 | Speed | pixels a second, 1 to 240 |
| 16 | 2 | Pause | milliseconds, 0 to 65,535, and at least 20 for `static` |
| 18 | 2 | Text bytes | T, 1 to 512 |
| 20 | 2 | Glyphs | G, 0 to 512 |
| 22 | 2 | Block width | BW, at least 1 |
| 24 | 2 | Block height | BH, at least 1 |
| 26 | 2 | Reserved | 0 |
| 28 | T | Text | the text, UTF-8 |
| 28 + T | 6 G | Glyphs | each three 16-bit numbers: the glyph's place in its font's table, and x and y of the top left corner of its cell in the block, y growing downwards |

P is 28 + T + 6 G, at most 3,612. The canvas's picture, 3 * W * H bytes, is at most 65,534.
The direction and wrapping are kept so that the text can be edited; the layout already
follows them.

**The fonts.** `small` has 7 rows above the baseline and 2 below, `medium` 10 and 3, and
`large` is `small` at twice the size: every pixel a square of 2 x 2. Each has a glyph for
the 95 printable ASCII characters and the 27 Hebrew letters from U+05D0 to U+05EA. A glyph's
cell is its rows by its width; it advances by its width and one column, times the scale,
and the space is a dark glyph. Lines are a cell and one row apart. The glyphs are those of
`fonts/` in the repository.

**The layout** is made by the converter: the text split at line feeds into paragraphs; each
paragraph put in order by the Unicode Bidirectional Algorithm, UAX #9, its direction that
of its first strong letter unless forced; with wrapping, broken at spaces into lines no
wider than the canvas, and a word wider than the canvas between its characters; each line
reordered, brackets in right-to-left runs mirrored, and its glyphs placed from x 0; the
block as wide as its widest line, each line aligned in it, and as high as its lines.

**The pass.** Where the block rests: x is 0, (W - BW) / 2 or W - BW by the alignment, and y
0, (H - BH) / 2 or H - BH by the vertical one, rounded down. `steps(d)` is the
milliseconds of d pixels at the speed, `ceil(d * 1000 / speed)`, and `moved(t)` the pixels
after t milliseconds, `floor(t * speed / 1000)`. A motion left or right moves x, one up
or down moves y, and the block rests across it.

| Effect | Must fit | Pass | Where the block is at t |
|---|---|---|---|
| `static` | the canvas | the pause | at rest |
| `marquee` | the canvas across the motion | `steps(size + length)` | it enters at one side and leaves at the other: left from W, right from -BW, up from H, down from -BH, `moved(t)` on |
| `slide` | the canvas | in + pause + out | it moves in from the side the motion comes from to its rest, holds the pause, and moves out at the other side |
| `pan` | the canvas across the motion | 2 pauses + 2 `steps(T)`, at least 20 | it holds at one end, moves to the other, holds and moves back; T is the length beyond the canvas, 0 when it fits, and then it rests |

Here size and length are W and BW across a horizontal motion and H and BH across a
vertical one. A pan left starts with the block's left end at the canvas's left side, one
right with its right end at the right side, and so for up and down.

**Drawing** at a time t of the pass: the canvas takes the background, and every lit pixel of
every glyph whose cell meets the canvas at the block's place becomes the colour, a square
of the scale. Rows are counted from the top here: a canvas row r is the format's row
H - r.

### The JSON source of a text

A UTF-8 JSON object, read as strictly as JSON frames, with exactly the members `version`
(1), `type` (`"text"`), `width`, `height`, `text` (1 to 512 bytes of UTF-8), `font`
(`"small"`, `"medium"` or `"large"`), `color` and `background` (colours as in JSON
frames), `align` (`"left"`, `"center"` or `"right"`), `valign` (`"top"`, `"middle"` or
`"bottom"`), `direction` (`"auto"`, `"ltr"` or `"rtl"`), `wrap` (`true` or `false`),
`effect`, `motion`, `speed` (1 to 240) and `pause_ms` (0 to 65,535, at least 20 for
`static`). It is the tracked source of a text, as JSON frames are of frames; the converter
writes it with two spaces of indent.

```json
{
  "version": 1,
  "type": "text",
  "width": 60,
  "height": 60,
  "text": "שלום world",
  "font": "small",
  "color": 16766016,
  "background": 0,
  "align": "center",
  "valign": "middle",
  "direction": "auto",
  "wrap": false,
  "effect": "marquee",
  "motion": "left",
  "speed": 20,
  "pause_ms": 1000
}
```

### What a reader rejects

A file that ends inside the header, a wrong magic, a container version that is not 1, a
reserved byte that is not 0, a type or a type version the reader does not know, a width or
height of zero, a payload longer than its type allows, a payload that the rules of its type
reject, a frames payload of another canvas, a payload whose length is not P, and a loop
that is not the payload's. The names are listed in [reasons.md](reasons.md), "ODRGX
files".

## Guidance for the converter

This section is advice, not part of the format. Any file that follows the rules above is
valid.

- Merge consecutive identical frames into one. Split a frame longer than 65,535 ms into
  several.
- For each frame, try every predictor, both modes and every k, and keep the smallest result.
  Write a stored frame when nothing coded is smaller.
- Use a palette when the animation has at most 256 colours, and order the palette by hue.
  The order does not affect correctness but it affects size: when colours shift gradually,
  hue order turns the shift into small index steps. For the Hello world animation,
  compressed, an arbitrary palette order gives 11,277 bytes and hue order gives 1,134.
- Compress the body unless the board proves too slow at decompressing.

## Measured sizes

File sizes in bytes for this exact format, with the guidance above applied. The row of
60 x 30 is a size the target had before the target became twenty upright legs; the last
row is the target of today, 60 x 60.

| Animation | Canvas | Stored frames | Uncompressed | Compressed |
|---|---|---:|---:|---:|
| DVD bounce, 41.8 s | 60 x 6 | 232 | 3,799 | 1,594 |
| Hello world, 5.1 s | 60 x 6 | 255 | 17,731 | 1,134 |
| Square ping-pong, 3.4 s | 60 x 3 | 114 | 2,985 | 1,403 |
| Dense full-colour, 10 s | 60 x 6 | 500 | 163,188 | 156,344 |
| Dense full-colour, 10 s | 60 x 30 | 500 | 765,984 | 725,162 |
| Dense full-colour, 10 s | 60 x 60 | 500 | 1,462,236 | 1,383,766 |

The dense clips are synthetic. The rows above the last were measured with the prototype of
the frame coder; each of those files was decoded with a decoder written from this text
alone, and every pixel of every frame matched the source. The converter of this repository
writes DVD bounce, Hello world and the dense clips of 60 x 6 and 60 x 30 at the same
uncompressed sizes. Its compressed files differ a little: 1,612 and 1,138 bytes for DVD
bounce and Hello world. Among frame records of equal size in bytes it chooses by a fixed
rule where the prototype kept the one with the fewest bits, so DEFLATE sees slightly
different bytes.

The last row was measured with the converter of this repository, with zlib 1.2.12: it is
the clip the generator `dense` writes for the target file `mapping/legs-20.json`, see
[python-library.md](python-library.md), "Generators". The decoder of the Python library
gives back every frame of both files, and the suite of the core plays the clip on the target file
and compares every LED of every refresh with the reference.

Decoding has been run and timed on the board: see [firmware.md](firmware.md), "Measurements
on the board" and "Verified on the board".

**What fits.** The board's storage partition has 10,354,688 bytes, and 9,001,905 bytes of
animations have been installed in it and played. A dense 60 x 60 clip takes 138,377 bytes
for a second compressed and 146,224 uncompressed, so storage holds 65 to 74 seconds of it
compressed and 61 to 70 seconds uncompressed: the first figure of each pair is what has
been shown to fit, the second what the whole partition would hold. A picture that nothing
predicts is written as a stored frame record, 10,805 bytes for each 20 ms on a 60 x 60
canvas, which makes 16 to 19 seconds of content stored frame by frame. Content that
changes less takes less: the two animations of the demo show are 1,210 and 1,052 bytes. On the bigger layout of [firmware.md](firmware.md), "The regions of the flash", the storage
has 13,500,416 bytes, which hold 97 seconds of the clip compressed, 92 uncompressed and 24
stored frame by frame.
