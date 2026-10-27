# Reasons

When a converter refuses an input it writes one line to standard error,

```
error: <reason>: <detail>
```

and exits with status 1. This holds for the converter of [converter.md](converter.md) and
for the programs of the Python library of [python-library.md](python-library.md), its
generators and its writer of the mapping page: they write this line and use the names of
this page. The reason is a fixed name made of lower-case letters, digits and hyphens;
every implementation that reads the same files uses the same names. The detail is free
text for people and names the file concerned.

When a file has more than one defect, the reason is that of the defect met first when the
file is read from front to back.

## Any input

| Reason | Condition |
|---|---|
| `not-found` | An input path given on the command line does not exist or cannot be read, and no more specific reason applies. |

## JSON frames files

Rules: [format.md](format.md), "JSON frames". `version` is checked before any other member,
so a file of another version is always `bad-version`.

| Reason | Condition |
|---|---|
| `bad-json` | The file is not UTF-8, starts with a byte-order mark, is not one JSON value, uses a member name twice in one object, or its top level is not an object. |
| `missing-member` | A member that the format lists is absent, at the top level or in a frame. |
| `bad-type` | A member, or an entry of `pixels`, is not of the listed type. An integer is a JSON number written without a fraction and without an exponent; `true` and `false` are not integers. |
| `bad-version` | `version` is not 1. |
| `unknown-member` | A member that the format does not list is present, at the top level or in a frame. |
| `out-of-range` | `width` or `height` is below 1, `ms` is below 1, or a colour is below 0 or above 16,777,215. |
| `no-frames` | `frames` is empty. |
| `bad-pixel-count` | A frame's `pixels` does not have exactly W * H entries. |

The checks run in this order: the top level, `version`, the other top-level members (a
missing one before an unknown one), `width`, `height`, `frames`, then each frame in order:
its members, `ms`, the number of pixels, and each pixel in order.

## ODRG files

Rules: [format.md](format.md), "ODRG".

| Reason | Condition |
|---|---|
| `truncated` | The file ends before the 16-byte header, the palette or a frame record is complete, or a compressed body's DEFLATE stream ends before its last block is complete. |
| `bad-magic` | Bytes 0 to 3 are not `4F 44 52 47`. |
| `bad-version` | The version byte is not 1. |
| `reserved-bits` | A flag bit from 1 to 7 is set; bit 7 of a mode byte is set; or a mode byte has bit 6 set and is not `0x40`. |
| `zero-size` | Width or height is 0. |
| `bad-palette-size` | C is above 256. |
| `canvas-too-large` | N is above 65,534. |
| `no-frames` | F is 0. |
| `bad-deflate` | The compressed body is not a valid DEFLATE stream. |
| `zero-duration` | A frame record's duration is 0. |
| `bad-length` | L is below 2 or above N + 1. |
| `bad-stored-length` | A stored frame's L is not N + 1. |
| `out-of-bits` | A coded frame needs a bit after the last bit of its data. |
| `run-past-end` | In run mode, a run of g - 1 zero codes would pass N. |
| `bad-code` | A code of a coded frame is above 255: a Rice value above 255 in plain mode, or above 254 in run mode. |
| `too-much-padding` | After the N codes of a coded frame, 8 or more bits of its data are unread. |
| `bad-palette-index` | In a palette file, a pixel of a decoded picture is C or more. |
| `trailing-bytes` | Bytes follow the last frame record: in the body, or in the file after the end of the DEFLATE stream. |

The checks run in this order. A file shorter than 16 bytes is `truncated`. The header fields
are checked in the order of their offsets: magic, version, flags, width and height, palette
size, N, frame count. A compressed body is inflated whole, which gives `bad-deflate`,
`truncated` or the `trailing-bytes` of bytes after the stream. Then come the palette and the
frame records in order. Within a frame record: its first five bytes are present, the
duration, L, the mode byte, the length of a stored frame, the data bytes are present, the
bits of the data, and last the palette indexes of the picture. A Gamma code or a Rice code is
read whole before its value is judged, so a code cut off by the end of the data is
`out-of-bits`. Bytes after the last frame record are found last.

## Sources that `encode` cannot write as ODRG

| Reason | Condition |
|---|---|
| `canvas-too-large` | N would be above 65,534: W * H with a palette, 3 * W * H without one. |
| `too-many-frames` | More than 4,294,967,295 frame records would be needed. |

The canvas is judged before the number of frame records.

## ODRGX files

Rules: [format.md](format.md), "ODRGX".

| Reason | Condition |
|---|---|
| `truncated` | The file ends before the 20-byte header is complete. |
| `bad-magic` | Bytes 0 to 3 are neither `4F 44 52 58` nor, for an ODRG file, `4F 44 52 47`. |
| `bad-container` | The container's version is not 1, or its reserved byte is not 0. |
| `unknown-type` | The content type is not one the reader knows: 1, frames, 2, a text, or 3, a widget. |
| `unknown-type-version` | The version of the content type is not the one the reader knows: 1. |
| `zero-size` | Width or height is 0. |
| `payload-size` | The payload's length is above the most its type may have, 3,612 bytes for a text and 20 for a widget, or, once the payload was read, not the number of bytes after the header. |
| `canvas-mismatch` | The canvas of a frames payload differs from the container's. |
| `loop-mismatch` | The loop the header gives differs from the payload's: for frames, the sum of the durations; for a text, its pass; for a widget, its seconds. |

The checks run in this order: the header's length, its fields in the order of their
offsets, then the payload, whose faults are those of its type, a frames payload's those of
"ODRG files", a text's those of "Texts in ODRGX" and a widget's those of "Widgets in
ODRGX", then the canvas of a frames payload,
the payload's length, and last the loop.

## Texts in ODRGX

Rules: [format.md](format.md), "The text payload".

| Reason | Condition |
|---|---|
| `canvas-too-large` | The text is for a canvas whose picture, 3 * W * H bytes, is above 65,534. |
| `truncated` | The payload ends before its settings, its text or a glyph is complete. |
| `unknown-font` | The text names a font, or a version of it, that the reader does not have. |
| `bad-settings` | A setting is outside its values: the effect, the motion, the alignments, the direction, wrapping, a speed that is not 1 to 240, a `static` text shown for less than 20 ms, more than 512 glyphs, a block of no width or height, or reserved bytes that are not 0. |
| `bad-text` | The text has not 1 to 512 bytes, or they are not UTF-8. |
| `payload-size` | The payload's length in the header is not 28 bytes, the text and 6 bytes for each glyph. |
| `does-not-fit` | The block cannot be seen whole: a `static` or `slide` block larger than the canvas, or a moving one larger than the canvas across its motion. |
| `bad-glyph` | A glyph is not in its font, or its cell is not in the block. |
| `trailing-bytes` | Bytes follow the last glyph. |
| `loop-mismatch` | The loop the header gives is not the pass of the text. |

The payload is checked as it is read: the canvas, the settings in the order of their
offsets, the payload's length against them, whether the block fits, the text, each glyph,
the end, and last the loop.

## Widgets in ODRGX

Rules: [format.md](format.md), "The widget payload".

| Reason | Condition |
|---|---|
| `canvas-too-large` | The clock is for a canvas whose picture, 3 * W * H bytes, is above 65,534. |
| `payload-size` | The payload's length in the header is not 20 bytes. |
| `truncated` | The file ends before the 20 bytes of the payload. |
| `unknown-widget` | The widget is not one the reader has: 1 `analog`, 2 `digital` or 3 `melting`. |
| `bad-settings` | The reserved byte is not 0, the seconds are not 1 to 3,600, the least speed is not 1 to 3,600, or the greatest is below the least or above 3,600. |
| `trailing-bytes` | Bytes follow the payload. |
| `loop-mismatch` | The loop the header gives is not 1,000 times the seconds. |

The payload is checked as it is read: the canvas, the payload's length, the widget, the
other settings in the order of their offsets, the end, and last the loop.

## Sources that `encode` cannot write as ODRGX

| Reason | Condition |
|---|---|
| `canvas-too-large`, `too-many-frames` | The frames cannot be written as ODRG, as above; or a text or a clock is for a canvas above 65,534 bytes. |
| `loop-mismatch` | The loop would be longer than 4,294,967,295 milliseconds. |
| `unsupported-character` | A text holds a character that no font has: anything but the printable ASCII characters, the 27 Hebrew letters and the line feed. The detail names each, with its code point. |
| `does-not-fit` | A text's block cannot be seen whole with its effect and motion; the detail names the effects that show it. |

## JSON sources of texts

Rules: [format.md](format.md), "The JSON source of a text". A source is told from JSON
frames by its member `type`.

| Reason | Condition |
|---|---|
| `bad-json`, `missing-member`, `bad-type`, `bad-version`, `unknown-member` | As for JSON frames files. |
| `unknown-type` | `type` is not `"text"` or `"widget"`. |
| `out-of-range` | A number or a name is outside its values: the canvas, `text` of not 1 to 512 bytes of UTF-8, a colour, the font, an alignment, the direction, the effect, the motion, `speed` not 1 to 240, `pause_ms` not 0 to 65,535, or below 20 for a `static` text. |

## JSON sources of clocks

Rules: [format.md](format.md), "The JSON source of a clock".

| Reason | Condition |
|---|---|
| `bad-json`, `missing-member`, `bad-type`, `bad-version`, `unknown-member` | As for JSON frames files. |
| `out-of-range` | A number or a name is outside its values: the canvas, the widget, `seconds` not 1 to 3,600, a colour, `speed_min` not 1 to 3,600, or `speed_max` below `speed_min` or above 3,600. |

## Mapping files

Rules: [mapping.md](mapping.md), "Rules". The two reasons hold for both kinds of mapping
file, the row-leg file and the column-leg file. A file that is of neither kind, or that
mixes the two, breaks a rule.

| Reason | Condition |
|---|---|
| `mapping-missing` | The mapping file does not exist. |
| `mapping-malformed` | The mapping file breaks a rule. The detail says which. |

## Shows

Rules: [show.md](show.md). `pack` checks in the order of this table and reports the first
reason that applies.

| Reason | Condition |
|---|---|
| `mapping-missing`, `mapping-malformed` | As under "Mapping files". |
| `show-missing` | The show file does not exist. |
| `show-malformed` | The show file breaks its format: it is not strict JSON; a member is missing, unknown or of the wrong type; `version` is not 1; `brightness` is not 0 to 255; an item is neither an animation item nor a cycle item; an `id` is not 1 to 65,535; a `file` name is outside the naming rule; `seconds` is not 1 to 65,535; or a `cycle` is empty. The detail says which. |
| `duplicate-id` | Two items have the same `id`. |
| `undefined-id` | A cycle, or `start`, names an id that no item has. |
| `nested-cycle` | A cycle names an item that is a cycle. |
| `output-not-empty` | The output folder of `pack` exists and is not empty. |
| `file-missing` | The source `X.json` of a named `X.odrg` or `X.odrgx` is not in the sources folder. |
| `file-malformed` | A source is rejected as a JSON frames file. The detail gives that reason too. |
| `size-mismatch` | A source's canvas size differs from the mapping's. |
| `canvas-too-large`, `too-many-frames` | A source cannot be written as ODRG, as under `encode`. |

The ids are checked in three passes over the items in file order: every repeated id, then
every id that a cycle or `start` names and no item has, then every cycle that names a
cycle.

## Media files

`import` reads the mapping file first; its reasons are under "Mapping files".

| Reason | Condition |
|---|---|
| `unsupported-media` | The file name does not end in `.mp4`, `.mov` or `.gif`. |
| `unreadable-media` | The file cannot be decoded, or it holds no picture. This includes a video whose first video stream has no decoder, a video whose metadata cannot be read, and a GIF that is cut short. |
| `bad-range` | The start is negative, the duration is not above 0, the start is not before the end of the media, or the start plus the duration is after the end of the media. |

## Generators

| Reason | Condition |
|---|---|
| `canvas-too-small` | The canvas of the mapping file is too small for the animation: below 53 x 6 for Hello world, below 3 x 3 for DVD bounce. |

## Any output

| Reason | Condition |
|---|---|
| `cannot-write` | An output file or folder cannot be written, for example because its folder does not exist. |

## The core

The core is the library that plays an installed show, on the board and in the emulator; see
[core.md](core.md). It writes no error line. When it refuses a show it holds the reason as a
text that begins with a reason name, and the `status` command reports that text.

It names an invalid show as "Shows" does, from `mapping-missing` to `nested-cycle`, and a
rejected `.odrg` file as "ODRG files" does, and a rejected container as "ODRGX files"
does. A fault of one `.odrg` or `.odrgx` file, `file-missing`, `size-mismatch`, `read-error`
or a reason of "ODRG files" or "ODRGX files", does not make the show invalid:
the file is quarantined, the log says `file <name> unavailable: <reason>`, and `list` gives
the reason's name as the animation's `fault`. It adds three reasons that only a running
player can meet:

| Reason | Condition |
|---|---|
| `read-error` | The host reports a failure while a file is read. |
| `out-of-memory` | The host cannot supply the memory the core asks for when it starts. |
| `too-many-folders` | A file of a drive's catalog lies in a folder that would be the 33rd sub-folder of the drive's folder, which only a catalog can name: the file is left out, the log says `drive file <path> left out: too-many-folders`, and the show plays on. |

The text is the reason name, followed for most reasons by what it is about:

| Text | Condition |
|---|---|
| `mapping-missing` | `mapping.json` does not exist. |
| `mapping-malformed` | `mapping.json` breaks a rule. |
| `show-missing` | `show.json` does not exist. |
| `show-malformed` | `show.json` breaks its format. |
| `duplicate-id <id>` | Two items have that id. |
| `undefined-id <id>` | A cycle, or `start`, names that id and no item has it. |
| `nested-cycle <id>` | The cycle item with that id names an item that is a cycle. |
| `read-error <name>` | The host reports a failure while `mapping.json` or `show.json` is read. |
| `out-of-memory` | The host cannot supply the memory the core asks for. |

The checks of the first seven rows are made in the order of the table and the first one
that fails decides. The last two rows are reported at the point where they happen.

The files of the show are taken in the order in which `show.json` first names them, and
each by its header, then its size, then its body. A file that does not exist is
`file-missing`, one whose canvas differs from the mapping's `size-mismatch`, one the host
cannot read `read-error`, and one rejected as an ODRG file has that reason of "ODRG
files". Each quarantines the file and is not a text of an invalid show.

Inside the core, work that is not finished yet gives the internal result `pending`: the
decoder settling a defect in slices, or the player catching up over several refreshes;
see [core.md](core.md#bounded-work). `pending` is no reason. It is never reported, in a
reply, a log line or a reason text, and a file's reason is the same whatever the slices.

`<id>` is a decimal number. For `undefined-id` it is the number as the file writes it, which
need not be an id at all, such as `0`, `-5` or `70000`; a number beyond 32 bits is given as
`4294967295`, with its sign. `<name>` is the file name as `show.json` has it, or
`mapping.json` or `show.json` for `read-error`. `<reason>` is the reason the reference
decoder of the converter gives for the same file. The whole text is made of lower-case
letters, digits, `.`, `-`, `_` and spaces, so it stands in a JSON string as it is.

A file that is gone, cannot be read, or no longer follows the format while the show plays
does not make the show invalid: the file is quarantined, as above.
