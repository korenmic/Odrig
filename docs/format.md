# Animation formats

An animation exists in these formats:

| Format | File | Role |
|---|---|---|
| JSON frames | `name.json` | The tracked source of an animation of the bench or of a test. Lossless and readable. Never played by the board. |
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
| 5 | 1 | Type | The content type: 1, frames; 2, a text; 3, a widget. |
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
`static`). It is the tracked source of a text of the bench or of a test, as JSON frames
are of frames; the converter writes it with two spaces of indent.

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

### The widget payload

The payload of the type 3 is a widget: a clock that the player draws. Its first byte names
the widget: 1 `analog`, 2 `digital` and 3 `melting` have the 20 bytes of this table; 4
`picture-dial` and 5 `picture-display` carry a picture of their own, as
["Picture clocks"](#picture-clocks) says. Subtype 6 is a
[message clock](#message-clocks). A widget's payload has at most 32,768 bytes.

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Widget | 1 `analog`, 2 `digital`, 3 `melting` |
| 1 | 1 | Reserved | 0 |
| 2 | 2 | Seconds | the loop, 1 to 3,600 |
| 4 | 3 | Face | red, green, blue |
| 7 | 3 | Hands | red, green, blue |
| 10 | 3 | Rim | red, green, blue |
| 13 | 3 | Background | red, green, blue |
| 16 | 2 | Least speed | times real time, 1 to 3,600 |
| 18 | 2 | Greatest speed | the least to 3,600 |

The loop in the header is 1,000 times the seconds. The canvas's picture, 3 * W * H bytes,
is at most 65,534.

**The time a clock shows** is imaginary: no clock of the board or of a network is read.
Each turn of a clock has a seed, a 32-bit number other than 0, which the player chooses
when the turn begins: [core.md](core.md), "Clocks". From the seed, xorshift32 (x ^= x <<
13, x ^= x >> 17, x ^= x << 5, on 32 bits) gives one number after the other, r, and the
clock takes, in this order:

| Name | From r | What it is |
|---|---|---|
| start | r % 43,200,000 | the virtual time at the start of the turn, in milliseconds |
| b | least + r % (greatest - least + 1) | the base speed |
| A | floor(min(b - least, greatest - b) * (r % 101) / 102) | the swing of the speed about b |
| P | 6,000 + r % 14,001 | the period of the swing, in milliseconds |
| phi | r % 1,024 | the phase of the swing, in 1,024ths of a turn |
| tilt | 25 + r % 16 | the melting watch's tilt, in degrees |
| fold | r % 21 | where it folds, in percent of its radius below its centre |
| stretch | 130 + r % 41 | how far the hanging face stretches, in percent |
| narrow | 20 + r % 31 | how fast it narrows as it hangs, in percent |
| shear | 10 + r % 21 | how far it drifts sideways as it hangs, in percent |
| wave | 2 + r % 3 | how high the fold waves, in half pixels |

`t` milliseconds into the turn, the virtual time is

```
v(t) = start + b * t + floor(A * P * (c(phi * 65,536) - c(phi * 65,536 + floor(2^26 * (t % P) / P))) / 102,944)
```

Angles here are in 2^26ths of a turn, and `s` and `c` are the sine and the cosine of the
sine table of 1,024 entries, in units of 1/16,384, that `fonts/generate.mjs` writes: an
angle a is read at entry `floor(a / 65,536) % 1,024` and moved towards the next one by
`floor((next - entry) * (a % 65,536) / 65,536)`; `c(a)` is `s(a + 2^24)`. 102,944 is 2 pi
times 16,384, rounded. The speed of the virtual time is b plus the swing's sine, never
below the least speed and never above the greatest. The clock shows `v(t)` modulo 12
hours. Every division here rounds down.

**Drawing a clock** at a time t of its turn, with its seed. Positions are in half pixels
from the canvas's centre, with y growing downwards: a pixel x, y, counted from the top,
is at `2x + 1 - W`, `2y + 1 - H`. A dial of radius R half pixels has a rim of 4 half
pixels; inside it the pivot, the points whose squared distance from the centre is at most
16; the hour hand, to `floor(R * 55 / 100)` and 2 half pixels to either side of its line,
pointing at `v` modulo 12 hours; the minute hand, to `floor(R * 85 / 100)` and 1 half
pixel to either side, at `v` modulo an hour; twelve marks, from `R - 6 - floor(R / 7)` to
`R - 6`, 1 half pixel to either side; and the face. The rim and the face take their
colours, and the pivot, the hands and the marks take the hands' colour.

- **analog**: the background, and a dial of radius `2 * (floor(min(W, H) / 2) - 1)`.
- **digital**: the background, and `h:mm` of `v` in the font `large`, the hour 1 to 12,
  as wide as its advances less the spacing after the last, its left at `floor((W -
  width) / 2)` and its top at `floor((H - 18) / 2)`; the digits in the face's colour and
  the colon in the rim's, shown while `t % 1,000` is below 500.
- **melting**: a pocket watch, after the seed's picture in
  `project-seeds/37-p1-odrgx-text-and-clock-animations/`. Its dial has 66 percent of the
  analog clock's radius, its centre lies 6 percent of that radius left of the canvas's
  centre and 12 percent above it, and it is tilted counter-clockwise by `tilt`. Above the
  fold the dial lies flat; below it, the face hangs straight down, stretched by `stretch`,
  narrowing by `narrow` and drifting right by `shear` as it hangs, and darker the deeper
  it hangs. The fold waves by `wave` along the dial, once across it, with a period of 7
  seconds of real time. A crown and a ring of the rim's colour sit at 12 o'clock. The
  formulas are those of `core/src/clock.cpp` and `converter/lib/draw.js`, which give the
  same pixels.

### Message clocks

A `message-clock` is a generated 60 x 60 canvas with Hebrew captions above an imaginary
rolling clock and a moving white square. Its loop is the complete caption sequence,
not a fixed clock duration. All multibyte integers below are little-endian.

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Widget | 6 |
| 1 | 1 | Version | 1 |
| 2 | 1 | Sequence | 1 to 7 |
| 3 | 1 | Caption count | 1 to 24 |
| 4 | 4 | Loop | Sum of caption durations, milliseconds |
| 8 | 2 | Text bytes | 1 to 4,096 |
| 10 | 2 | Reserved | 0 |
| 12 | 4 | Mask offset | 24 + 12 * count + text bytes |
| 16 | 4 | Glyph offset | Mask offset + 900 * count |
| 20 | 4 | Payload bytes | Glyph offset + 3,968 |

The header is followed by `count` records of 12 bytes: duration u32, flags u8,
reserved zero u8, text offset u16, text length u16, reserved zero u16. Text offsets
start at zero and are contiguous. Each caption has 1 to 256 strict UTF-8 bytes,
without U+0000–001F or U+007F–009F. Then come the concatenated texts, the masks and
the glyph atlas, with no gaps or trailing bytes. The maximum payload is 29,976 bytes;
the existing 32,768-byte player window is sufficient.

Flags are countdown (1), zero subtitle (2), gradual motion stop (4), square freeze
(8), and increased random digit changes (16). Countdown and zero subtitle are
mutually exclusive and belong only to sequence 5; stop belongs only to sequence 1
and occurs at most once; freeze and increased changes belong only to sequence 6,
with at most one freeze. All other bits are zero. Countdown records last 2,000 ms;
every other record lasts 6,100 ms. Header and container loops must both equal the sum.

Each caption mask covers the upper half of the canvas, with 900 alpha4 bytes. The atlas has 62 glyphs of
8 x 16 alpha4 pixels, 64 bytes each: ten digits for each of six numeric positions,
then the two colons. Masks and glyphs are top-down, left-to-right, high nibble first.
This compiled-mask order is separate from the ordinary bottom-up RGB picture order.
Numeric origins are x = 2, 9, 23, 30, 43, 50; colon origins 16 and 36; all start at
y = 34 and are clipped to 16 rows. The square covers three columns and rows 57–59.

Rendering uses elapsed modulo the complete loop, restarting both motion and seeded
random choices. Xorshift32, with zero seed replaced by 1, chooses the initial second
of an imaginary day. Every 2,000 motion milliseconds the seconds roll forward; the
minute and hour changes are chosen with probabilities .14/.045, or .48/.25 during
the increased-changes caption. Both probability draws precede direction draws.
Digits carry modulo ten as in the source animation; subsequent random times need
not be conventional 24-hour times. A roll lasts 500 motion milliseconds with
smoothstep interpolation. No wall clock or network clock is read.

After a motion stop at S, motion time is
`S + u - floor(u^3 / 12250000) + floor(u^4 / 85750000000)`, with
`u = clamp(elapsed - S, 0, 3500)`. Before S it is elapsed. Once stopped, digit rolls
settle fully and remain lit. Freeze holds only the square at its position when the
caption begins. Its centre is the rounded `29.5 + 26.5*cos(motion*2*pi/4000)`, using
the shared interpolated sine table. Text continues independently: 600 ms fade in,
5,000 ms hold, 500 ms fade out; countdown text is steady. A blue sweep lasts 1,500 ms
every 9,000 ms, centre `1.35*phase/1500 - .15` of the width, half-width .07,
RGB 90/205/255. Values below four are black; sweep colouring requires alpha at least
eight. Remaining lit pixels are white on black.

The strict JSON source has exactly `version` (1), `type` (`"widget"`), `width` (60),
`height` (60), `widget` (`"message-clock"`), `tab` (1–7), `messages`, and `glyphs`.
Each message has exactly `text`, integer `flags`, and `mask`; masks and glyphs are
lowercase hexadecimal strings of exactly twice their byte lengths. The converter
validates the compiled payload as well as the source and round-trips it canonically.
The shared app previews and uploads these generated widgets, but its ordinary clock
form cannot edit them.

### The JSON source of a clock

A UTF-8 JSON object, read as strictly as JSON frames, with exactly the members `version`
(1), `type` (`"widget"`), `width`, `height`, `widget` (`"analog"`, `"digital"` or
`"melting"`), `seconds` (1 to 3,600), `face`, `hands`, `rim` and `background` (colours as
in JSON frames), `speed_min` (1 to 3,600) and `speed_max` (`speed_min` to 3,600).

```json
{
  "version": 1,
  "type": "widget",
  "width": 60,
  "height": 60,
  "widget": "melting",
  "seconds": 30,
  "face": 16051408,
  "hands": 2105376,
  "rim": 13934615,
  "background": 0,
  "speed_min": 60,
  "speed_max": 600
}
```

### Picture clocks

A picture dial and a picture display are clocks drawn over a picture of their own: the
picture is still, and the player draws over it, at every refresh, the hands of a dial or
the time of a display, of the virtual time of the turn. Their payload is a head, its
parts, and the picture:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Widget | 4 `picture-dial`, 5 `picture-display` |
| 1 | 1 | Reserved | 0 |
| 2 | 2 | Seconds | the loop, 1 to 3,600 |
| 4 | 2 | Least speed | times real time, 1 to 3,600 |
| 6 | 2 | Greatest speed | the least to 3,600 |
| 8 | 1 | Direction | 0 `forward`, 1 `backward`, 2 `random`: chosen by the seed of the turn |
| 9 | 1 | Turns | 0 to 100: the greatest chance of a turn at a slowest point, in percent; 0 unless the direction is `random` |
| 10 | 1 | Parts | a dial's hands, 1 to 8; a display's fields, 1 to 4 |
| 11 | 1 | Caps | a dial's caps, 0 to 4; a display's 0 |
| 12 | | Parts | a dial's hands, 10 bytes each, then its caps, 6 bytes each; a display's fields, 22 bytes each |
| | | Picture | an ODRG file, to the end of the payload |

A hand:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 1 | Unit | 0 the hour, a turn in 12 hours; 1 the minute, a turn in an hour; 2 the second, a turn in a minute |
| 1 | 1 | Colour | an index into the picture's palette |
| 2 | 2 | Pivot x | half pixels from the canvas's left edge, 0 to 2 W |
| 4 | 2 | Pivot y | half pixels from the canvas's top edge, 0 to 2 H |
| 6 | 1 | Length | half pixels from the pivot to the tip, 1 to 255 |
| 7 | 1 | Tail | half pixels behind the pivot, 0 to 255 |
| 8 | 1 | Half width | half pixels to either side of the hand's line, 1 to 15 |
| 9 | 1 | Offset | whole hours added to the time, a signed byte, -12 to 12 |

A cap is a disc: x and y, 2 bytes each, as a pivot's; its radius in half pixels, 1 to 255;
its colour, an index into the palette.

A field:

| Offset | Size | Field | Values |
|---:|---:|---|---|
| 0 | 2 | Left | pixels from the canvas's left edge |
| 2 | 2 | Top | pixels from the canvas's top edge |
| 4 | 2 | Width | at least 1; the box lies within the canvas |
| 6 | 2 | Height | at least 1 |
| 8 | 1 | Font | 1 `small`, 2 `medium`, 3 `large`, 4 `tiny` |
| 9 | 1 | Digits | the colour of the digits, an index into the palette |
| 10 | 1 | Colons | the colour of the colons, an index into the palette |
| 11 | 1 | Blink | 0, or 1: the colons are shown in the first half of each real second only |
| 12 | 1 | Offset | whole hours added to the time, a signed byte, -12 to 12 |
| 13 | 1 | Reserved | 0 |
| 14 | 8 | Pattern | 1 to 8 characters of the pattern, then zero bytes |

The characters of a pattern: `H` the tens of the hour of a 12-hour clock, 1 to 12, so `0`
or `1`; `I` the same, but nothing at all, no glyph and no advance, when it is 0; `h` the
ones of the hour; `M` and `m` the tens and ones of the minutes; `S` and `s` those of the
seconds; `:` a colon; and the space. So `Ih:Mm` is `h:mm`, `Hh:Mm` is `hh:mm`, `Ih:Mm:Ss`
is `h:mm:ss`, and `Mm:Ss` is a timer's minutes and seconds.

**The picture** is an ODRG file of the container's canvas, of exactly one frame and a
palette of 1 to 8 colours; the duration of its frame is not used. Every colour of a hand, a
cap or a field is one of the palette's. The loop in the header is 1,000 times the seconds,
and the canvas's picture, 3 * W * H bytes, is at most 65,534, as for every clock.

**The font `tiny`** is the ten digits, the colon and the space, 5 rows high with nothing
below the baseline: the digits 3 pixels wide, the colon and the space 1. Its glyphs are
those of `fonts/tiny.txt`. A text cannot name it.

**The time a picture clock shows.** Its seed gives, by xorshift32, the eleven values of the
table of "The widget payload", start to wave, in their order, and then:

| Name | From r | What it is |
|---|---|---|
| back | r % 2 | with `random`, 1 when the turn starts backward |
| chance | r % (turns + 1) | with `random`, the chance of a turn at each slowest point, in percent |

With Φ = phi * 65,536, the way forward `t` milliseconds into the turn is

```
u(t) = b * t + floor(A * P * (c(Φ) - c(Φ + floor(2^26 * (t % P) / P))) / 102,944)
```

so that the time of the other clocks is `start + u(t)`. The speed is least where the
angle `Φ + floor(2^26 * (t % P) / P)` is three quarters of a turn: first at
`t0 = floor(P * ((3 * 2^24 - Φ) mod 2^26) / 2^26)`, and then every P after it, so that the
k-th slowest point, k from 1, is at `t0 + (k - 1) * P`. The way after k slowest points,
D(k), is +1 or -1: D(0) is +1 for `forward`, -1 for `backward`, and for `random` -1 when
back is 1 and +1 otherwise. With `random`, D(k) is -D(k - 1) when `mix(seed ^ k) % 100`
is below chance, and D(k - 1) otherwise; `mix` is MurmurHash3's finalizer of
[core.md](core.md), "Clocks". With n the number of slowest points at or before t:

```
n = 0:  v(t) = start + D(0) * u(t)
n > 0:  v(t) = start + D(0) * u(t0) + b * P * (D(1) + ... + D(n - 1)) + D(n) * (u(t) - u(t0) - (n - 1) * b * P)
```

Over a whole period u grows by exactly b * P, so the hands turn back the way they came,
and nothing jumps. A part shows `(v(t) + offset * 3,600,000) mod 12 hours`, taken at or
above 0. Every division rounds down.

**Drawing a picture clock** at a time t of its turn, with its seed. A pixel x, y, counted
from the top left from 0, has its centre at `2x + 1`, `2y + 1` half pixels from the
canvas's top left corner. The picture is drawn through its palette, and over it:

- **picture-dial**: each hand in its order, then each cap; a later one covers an earlier
  one. A hand of the hour, the minute or the second points at the angle
  `a = floor(2^26 * (T mod U) / U)`, with T the part's time and U 12 hours, an hour or a
  minute. With `u = 2x + 1 - pivot x` and `w = 2y + 1 - pivot y`, a pixel is the hand's
  when `-tail * 16,384 <= u * s(a) - w * c(a) <= length * 16,384` and
  `|u * c(a) + w * s(a)| <= half * 16,384`; it is a cap's when `u * u + w * w` is at most
  the square of its radius, u and w taken from the cap's place.
- **picture-display**: each field in its order. The pattern becomes glyphs of its font,
  `large` being `small` at twice the size; the line is as wide as its advances less the
  spacing after the last, as the digital clock's. Its left is
  `left + floor((width - line) / 2)` and its top `top + floor((height - ascent * scale) /
  2)`, where the ascent is the font's rows above its baseline, which the digits fill.
  Every lit pixel of a glyph inside the box takes the colour of the digits, or of the
  colons for a colon; with blink, a colon is drawn only while `t % 1,000` is below 500.
  Nothing is drawn outside the box.

### The JSON source of a picture clock

A UTF-8 JSON object, read as strictly as JSON frames, with exactly the members `version`
(1), `type` (`"widget"`), `width`, `height`, `widget` (`"picture-dial"` or
`"picture-display"`), `seconds` (1 to 3,600), `speed_min` and `speed_max` as a clock's,
`direction` (`"forward"`, `"backward"` or `"random"`), `turns` (0 to 100, and 0 unless
`random`), `palette` (1 to 8 colours as in JSON frames, no two the same), `picture` (H
strings of W characters, the top row first, each character the digit of an index into the
palette), and for a dial `hands` (1 to 8) and `caps` (0 to 4), for a display `fields` (1
to 4). A hand is an object with exactly `unit` (`"hour"`, `"minute"` or `"second"`),
`color`, `x`, `y`, `length`, `tail`, `half` and `offset`; a cap `x`, `y`, `radius` and
`color`; a field `left`, `top`, `width`, `height`, `font` (`"small"`, `"medium"`,
`"large"` or `"tiny"`), `pattern`, `digits`, `colons`, `blink` (`true` or `false`) and
`offset`, each with the values of its bytes above. The converter writes the picture as an
ODRG file with the palette in the source's order, compressed.

```json
{
  "version": 1,
  "type": "widget",
  "width": 60,
  "height": 60,
  "widget": "picture-display",
  "seconds": 30,
  "speed_min": 60,
  "speed_max": 600,
  "direction": "random",
  "turns": 30,
  "palette": [0, 16777215],
  "picture": ["000 ... 60 characters", "... 60 rows"],
  "fields": [
    {"left": 10, "top": 25, "width": 40, "height": 9, "font": "small", "pattern": "Ih:Mm",
     "digits": 1, "colons": 1, "blink": true, "offset": 0}
  ]
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
