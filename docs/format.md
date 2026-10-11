# Animation formats

An animation exists in two formats:

| Format | File | Role |
|---|---|---|
| JSON frames | `name.json` | The tracked source of the animation. Lossless and readable. Never played by the board. |
| ODRG | `name.odrg` | The runtime format, produced from the JSON source by the converter. This is what the player reads, on the board and in the emulator. |

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

File sizes in bytes for this exact format, with the guidance above applied:

| Animation | Canvas | Stored frames | Uncompressed | Compressed |
|---|---|---:|---:|---:|
| DVD bounce, 41.8 s | 60 x 6 | 232 | 3,799 | 1,594 |
| Hello world, 5.1 s | 60 x 6 | 255 | 17,731 | 1,134 |
| Square ping-pong, 3.4 s | 60 x 3 | 114 | 2,985 | 1,403 |
| Dense full-colour, 10 s | 60 x 6 | 500 | 163,188 | 156,344 |
| Dense full-colour, 10 s | 60 x 30 | 500 | 765,984 | 725,162 |

Each of these files was decoded with a decoder written from this text alone, and every pixel
of every frame matched the source. The dense clips are synthetic. Decoding has not yet been
run or timed on the board.

The table was measured with the prototype of the frame coder. The converter of this
repository writes DVD bounce, Hello world and the two dense clips at the same uncompressed
sizes. Its compressed files differ a little: 1,612 and 1,138 bytes for DVD bounce and Hello
world. Among frame records of equal size in bytes it chooses by a fixed rule where the
prototype kept the one with the fewest bits, so DEFLATE sees slightly different bytes.
