# Requirements: Converter and reference codec (seed 01)

Source seed: `project-seeds/01-p0-converter-and-reference-codec/seed.md`.

`docs/format.md`, `docs/mapping.md` and `docs/show.md` define the formats, the mapping and
shows. These requirements say what the tool does with them. Where those documents leave a
point open, the answer used here is recorded in `docs/drifts.md`.

Terms:

- **the tool**: the command-line program started as `python -m odrig`.
- **reject**: stop with one named reason, as Requirement 2 defines.
- **picture**: the colour of every canvas pixel, in the pixel order of `docs/format.md`.
- **W**, **H**, **N**, **bpp**, **C**, **F**, **L**, **k**: as in `docs/format.md`.
- **reference decoder**: the ODRG reader in this tool, against which every other ODRG reader
  is checked.

## Requirement 1: One command-line tool

**User Story:** As someone who makes animations, I want one tool with a small set of
subcommands, so that every conversion is done the same way every time.

### Acceptance Criteria

1. The tool SHALL be started from the repository root as `python -m odrig <subcommand>` and
   SHALL offer exactly these subcommands: `import`, `encode`, `decode`, `check`, `pack`.
2. WHEN a subcommand finishes its work THEN the tool SHALL exit with status 0.
3. IF an input is rejected THEN the tool SHALL write exactly one line
   `error: <reason>: <detail>` to standard error, SHALL exit with status 1, and SHALL leave
   neither a partly written output file nor a partly written output folder.
4. IF the command line is not understood THEN the tool SHALL print a usage message, SHALL
   exit with status 2 and SHALL write no output file.
5. WHEN the output file of `import`, `encode` or `decode` already exists THEN the tool SHALL
   replace it.
6. WHEN the tool is run twice with the same input files and the same options THEN the output
   files of the two runs SHALL be byte-identical.
7. The tool SHALL NOT open a serial port or a network connection.

## Requirement 2: Every rejection names its reason

**User Story:** As a person or a test that receives a rejection, I want a fixed name for what
is wrong, so that the same defect is reported the same way by the tool, by the test vectors
and by every other implementation.

### Acceptance Criteria

1. Every rejection SHALL carry exactly one reason, taken from the reason tables in
   Requirements 3, 6, 7, 10, 11, 13, 14 and 15 or from criteria 3 and 5 below.
2. A reason SHALL be a fixed name made of lower-case letters, digits and hyphens. The detail
   that follows it SHALL be free text for people and SHALL name the file concerned.
3. IF an input path given on the command line does not exist or cannot be read, and no more
   specific reason applies, THEN the tool SHALL reject with `not-found`.
4. WHEN a file has more than one defect THEN the tool SHALL report the reason of the defect
   it meets first when reading the file from front to back.
5. IF an output file or folder cannot be written THEN the tool SHALL reject with
   `cannot-write`.

## Requirement 3: JSON frames files are read strictly

**User Story:** As a maintainer of tracked animation sources, I want a source that breaks the
format to be refused, so that a wrong file never reaches the board.

### Acceptance Criteria

1. WHEN a file follows the JSON frames rules of `docs/format.md` THEN the tool SHALL accept
   it and SHALL obtain W, H and, for every frame, its duration and its picture.
2. The tool SHALL accept a file in which consecutive frames have identical pixels.
3. IF a file breaks a rule THEN the tool SHALL reject it with the reason in this table:

   | Reason | Condition |
   |---|---|
   | `bad-json` | The file is not UTF-8, starts with a byte-order mark, is not one JSON value, uses a member name twice in one object, or its top level is not an object. |
   | `missing-member` | A member that `docs/format.md` lists is absent, at the top level or in a frame. |
   | `bad-type` | A member, or an entry of `pixels`, is not of the listed type. An integer is a JSON number written without a fraction and without an exponent; `true` and `false` are not integers. |
   | `bad-version` | `version` is not 1. |
   | `unknown-member` | A member that `docs/format.md` does not list is present, at the top level or in a frame. |
   | `out-of-range` | `width` or `height` is below 1, `ms` is below 1, or a colour is below 0 or above 16,777,215. |
   | `no-frames` | `frames` is empty. |
   | `bad-pixel-count` | A frame's `pixels` does not have exactly W * H entries. |

4. The tool SHALL check `version` before it checks any other member, so that a file of
   another version is reported as `bad-version`.

## Requirement 4: JSON frames files are written in one canonical form

**User Story:** As a maintainer who reviews changes to tracked sources, I want every JSON
frames file the tool writes to have the same layout, so that a change in a file is a change
in the animation.

### Acceptance Criteria

1. Every JSON frames file the tool or a generator writes SHALL be UTF-8 without a byte-order
   mark, SHALL end lines with a line feed, SHALL list the members in the order of
   `docs/format.md`, and SHALL put each frame on its own line.
2. WHEN consecutive frames have identical pixels THEN the writer SHALL write them as one
   frame whose `ms` is the sum of their durations.
3. WHEN the tool reads a file it wrote THEN it SHALL obtain the same W, H, durations and
   pictures it was given, after the merge of criterion 2.
4. WHEN the same frames are written twice THEN the two files SHALL be byte-identical.

## Requirement 5: The reference decoder reads ODRG exactly as specified

**User Story:** As the author of another ODRG reader, I want a decoder that follows
`docs/format.md` to the letter, so that I can check my own against it.

### Acceptance Criteria

1. WHEN an ODRG file follows `docs/format.md` THEN the reference decoder SHALL yield W, H, C,
   whether the body is compressed, and for every frame record, in order, its duration and
   the picture the pixel buffer holds after that record.
2. The decoder SHALL start from a pixel buffer of N zero bytes and SHALL apply each record
   to the buffer the previous record left.
3. WHEN C is 1 to 256 THEN the colour of a pixel SHALL be the palette entry its buffer byte
   selects. WHEN C is 0 THEN it SHALL be the pixel's three buffer bytes.
4. WHEN flag bit 0 is set THEN the decoder SHALL take the bytes after the header as one raw
   DEFLATE stream and SHALL use its output as the body.
5. The decoder SHALL NOT examine the values of the padding bits at the end of a coded
   frame's data.

## Requirement 6: The reference decoder rejects every invalid ODRG file

**User Story:** As the author of another ODRG reader, I want every way a file can be wrong
to have one name, so that my reader can be checked for refusing the same files for the same
reasons.

### Acceptance Criteria

1. IF an ODRG file breaks a rule THEN the reference decoder SHALL reject it with the reason
   in this table:

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

2. The decoder SHALL check the header fields in the order of their offsets, and within a
   frame record SHALL check the duration, then L, then the mode byte, then the data, then
   the palette indexes of the resulting picture.
3. WHEN a Gamma code or a Rice code is read THEN the decoder SHALL read the whole code
   before judging its value, so that a code cut off by the end of the data is `out-of-bits`.

## Requirement 7: `encode` writes small, lossless ODRG files

**User Story:** As someone who installs shows, I want each source converted into the
smallest runtime file the converter guidance gives, without losing anything, so that as
many animations as possible fit on the board.

### Acceptance Criteria

1. WHEN `encode` is given a valid JSON frames file THEN it SHALL write an ODRG file that the
   reference decoder accepts and that shows the same picture as the source at every
   millisecond of the animation.
2. `encode` SHALL write consecutive frames with identical pixels as one frame whose duration
   is the sum.
3. WHEN a frame lasts longer than 65,535 ms THEN `encode` SHALL write it as frame records of
   65,535 ms followed by one frame record for the remainder, all with the same picture.
4. WHEN the animation has at most 256 different colours THEN `encode` SHALL write a palette
   file whose palette holds exactly those colours, ordered by hue, then by saturation, then
   by brightness, with colours that have no hue first.
5. WHEN the animation has more than 256 different colours THEN `encode` SHALL write a file
   with C equal to 0.
6. For each frame record `encode` SHALL consider every predictor, both modes and every k,
   and SHALL write the combination whose data is the fewest bytes. WHEN several are equally
   small THEN it SHALL choose the lowest predictor number, then plain mode before run mode,
   then the lowest k.
7. WHEN no coded combination has fewer than N bytes of data THEN `encode` SHALL write a
   stored frame.
8. `encode` SHALL compress the body, with a DEFLATE window of at most 32,768 bytes, unless
   the option `--uncompressed` is given. WHEN `--uncompressed` is given THEN it SHALL write
   the body as it is and SHALL leave flag bit 0 clear.
9. IF the source is invalid THEN `encode` SHALL reject it with the reason of Requirement 3.
   IF a valid source cannot be written as ODRG THEN `encode` SHALL reject it with the reason
   in this table:

   | Reason | Condition |
   |---|---|
   | `canvas-too-large` | N would be above 65,534: W * H with a palette, 3 * W * H without one. |
   | `too-many-frames` | More than 4,294,967,295 frame records would be needed. |

10. WHEN the tracked Hello world and DVD bounce sources are encoded THEN each file size SHALL
    be within 2 percent of the figure in `docs/format.md`: 17,731 and 3,799 bytes
    uncompressed, 1,134 and 1,594 bytes compressed.
11. WHEN Hello world, DVD bounce or the dense 60 x 30 test clip is encoded and the result is
    decoded THEN the frames SHALL be identical to the source frames, for the compressed and
    for the uncompressed file.

## Requirement 8: `decode` turns an ODRG file back into a source

**User Story:** As someone who has only a runtime file, I want to get its frames back in
the source format, so that I can inspect or edit the animation.

### Acceptance Criteria

1. WHEN `decode` is given a valid ODRG file THEN it SHALL write a JSON frames file, in the
   canonical form of Requirement 4, with the same W and H and the same picture at every
   millisecond.
2. WHEN a JSON frames file in which no two consecutive frames have identical pixels is
   encoded and the result is decoded THEN the decoded file SHALL have the same frames, with
   the same durations and pictures, as the source.
3. IF the ODRG file is invalid THEN `decode` SHALL reject it with the reason of
   Requirement 6.

## Requirement 9: `check` validates and summarises a file

**User Story:** As someone handling animation files, I want one command that says whether a
file is valid and what it contains, so that I can trust a file before using it.

### Acceptance Criteria

1. WHEN the file name ends in `.json` THEN `check` SHALL treat the file as JSON frames, and
   WHEN it ends in `.odrg` THEN as ODRG. The option `--format json` or `--format odrg` SHALL
   override the file name. IF neither tells the format THEN the tool SHALL exit with
   status 2.
2. WHEN the file is valid THEN `check` SHALL print these lines to standard output, in this
   order, and nothing else:
   - `format: json-frames` or `format: odrg`
   - `canvas: <W>x<H>`
   - `frames: <number of frames in the file>`
   - `duration_ms: <sum of all durations>`
   - `colours: <number of different colours that appear in the pictures>`
   - `file_bytes: <size of the file>`
   - for ODRG only, `palette: <C>` and `compressed: yes` or `compressed: no`.
3. IF the file is invalid THEN `check` SHALL reject it with the reason of Requirement 3 or
   Requirement 6 and SHALL print nothing to standard output.

## Requirement 10: The canvas comes from a mapping file

**User Story:** As the owner of the installation, I want the canvas size to come only from
the mapping file, so that changing the build never means changing code.

### Acceptance Criteria

1. WHEN a subcommand or a generator needs a canvas size THEN it SHALL take W from the
   mapping file's `width` and H from the total number of rows the file lists. No canvas size
   SHALL be written in the code of `import`, `pack` or a generator.
2. The tool SHALL accept a mapping file WHEN all of these hold:
   - it is strict JSON as in Requirement 3, with exactly the members `version`, `width` and
     `legs` at the top level;
   - `version` is 1 and `width` is an integer from 1 to 65,535;
   - `legs` is an array of one or more objects, each with exactly the members `leg`, `pin`,
     `first_led` and `rows`;
   - every `leg` is an integer from 1 to 255 and no two legs have the same number;
   - every `pin` is an integer from 0 to 255 and no two legs have the same pin;
   - every `first_led` is `"left"` or `"right"`;
   - every `rows` is an array of one or more integers, and the rows of all legs together
     hold every y from 1 to H exactly once;
   - W * H is at most 65,534.
3. IF the mapping file is not acceptable THEN the tool SHALL reject with the reason in this
   table:

   | Reason | Condition |
   |---|---|
   | `mapping-missing` | The mapping file does not exist. |
   | `mapping-malformed` | The mapping file breaks a rule of criterion 2. |

## Requirement 11: `import` samples media onto the 50 frames-per-second timeline

**User Story:** As someone who makes animations, I want to turn a video or a GIF into a
source for the canvas, so that I do not edit numbers by hand.

### Acceptance Criteria

1. WHEN `import` is given a media file whose name ends in `.mp4`, `.mov` or `.gif`, in any
   letter case, and a mapping file THEN it SHALL write a JSON frames file whose `width` and
   `height` are the mapping's canvas size.
2. `import` SHALL place ticks 20 ms apart, the first at the start time, and SHALL give each
   tick the source frame that is on screen at the tick's time: the last frame whose
   presentation time is not later than the tick.
3. For `.mp4` and `.mov`, `import` SHALL use the first video stream, SHALL count time from
   the presentation time of its first frame, and SHALL treat the last frame as on screen
   for the mean interval between frames, or for 20 ms when the stream has one frame.
4. For `.gif`, `import` SHALL treat each frame as on screen for the delay the file records,
   SHALL count a delay of 10 ms or less as 100 ms, and SHALL go through the frames once.
5. `import` SHALL treat transparent pixels as black and SHALL ignore sound.
6. `import` SHALL place the top row of the picture on canvas row H and the bottom row on
   canvas row 1.
7. Each tick SHALL become 20 ms of the output, and `import` SHALL merge consecutive ticks
   with identical pictures, so that every `ms` it writes is a multiple of 20.
8. IF the media cannot be imported THEN `import` SHALL reject with the reason in this table:

   | Reason | Condition |
   |---|---|
   | `unsupported-media` | The file name does not end in `.mp4`, `.mov` or `.gif`. |
   | `unreadable-media` | The file cannot be decoded, or it holds no picture. |

9. WHEN a short mp4 file and a GIF file are imported THEN each output SHALL have the
   mapping's canvas size, every `ms` SHALL be a multiple of 20, and the sum of all `ms`
   SHALL be within 20 ms of the requested length.

## Requirement 12: `import` fits the picture to the canvas

**User Story:** As someone who makes animations, I want to choose how a picture of another
shape is put on the canvas, so that the result looks the way I intend.

### Acceptance Criteria

1. WHEN no fit option is given, or `--fit fill` is given, THEN `import` SHALL scale the
   picture by one factor so that it covers the whole canvas and SHALL cut off the overflow
   equally on the two opposite sides.
2. WHEN `--fit fit` is given THEN `import` SHALL scale the picture by one factor so that all
   of it lies inside the canvas, centred, and SHALL make the rest of the canvas black.
3. WHEN `--fit stretch` is given THEN `import` SHALL scale the picture to the whole canvas,
   with a different factor in each direction when the shapes differ.
4. `import` SHALL treat canvas pixels as square, so the shape of the canvas is W to H.
5. The colour of a canvas pixel SHALL be the mean of the source area that the pixel covers,
   each part weighted by its area, for each colour channel, rounded to the nearest whole
   number with halves rounded up. Area outside the picture SHALL count as black.
6. `import` SHALL compute the mean of criterion 5 in whole-number arithmetic, so that the
   same decoded picture gives the same canvas picture on every machine.

## Requirement 13: `import` converts part of a file

**User Story:** As someone who makes animations, I want to convert only a section of a
media file, so that I can cut an animation out of a longer recording.

### Acceptance Criteria

1. `import` SHALL accept `--start <seconds>` and `--duration <seconds>`, each a decimal
   number. WHEN `--start` is absent THEN the start SHALL be 0. WHEN `--duration` is absent
   THEN the requested length SHALL run from the start to the end of the media.
2. The number of ticks SHALL be the requested length in milliseconds divided by 20, rounded
   to the nearest whole number with halves rounded up, and at least 1.
3. IF the start is negative, the duration is not above 0, the start is not before the end of
   the media, or the start plus the duration is after the end of the media THEN `import`
   SHALL reject with `bad-range`.

## Requirement 14: `pack` builds the installed file set

**User Story:** As someone who installs shows, I want one command that builds the folder
the board and the emulator run, so that the installed files always come from tracked
sources in the same way.

### Acceptance Criteria

1. `pack` SHALL take a show file (`--show`), a mapping file (`--mapping`), a folder of JSON
   frames sources (`--sources`) and an output folder (`--out`).
2. WHEN the show is valid THEN the output folder SHALL hold exactly: `mapping.json`, a
   byte-for-byte copy of the mapping file; `show.json`, a byte-for-byte copy of the show
   file; and, for every different `X.odrg` the show names, the file `X.odrg` encoded from
   `X.json` in the sources folder as Requirement 7 defines.
3. WHEN `--uncompressed` is given THEN `pack` SHALL encode every file without compression.
4. `pack` SHALL accept a show file only WHEN it follows `docs/show.md`: strict JSON as in
   Requirement 3; exactly the listed members; `version` 1; `brightness` from 0 to 255; one
   or more items, each either an animation item or a cycle item with exactly that kind's
   members; every `id` from 1 to 65,535; every `file` name within the naming rule; every
   `seconds` from 1 to 65,535; every `cycle` a list of one or more integers; and `start`,
   when present, an integer.
5. IF the show is invalid in a way `docs/show.md` lists THEN `pack` SHALL refuse it with the
   reason in this table, checking in the order of the table:

   | Reason | Condition |
   |---|---|
   | `mapping-missing`, `mapping-malformed` | As in Requirement 10. |
   | `show-missing` | The show file does not exist. |
   | `show-malformed` | The show file breaks a rule of criterion 4. |
   | `duplicate-id` | Two items have the same `id`. |
   | `undefined-id` | A cycle, or `start`, names an id that no item has. |
   | `nested-cycle` | A cycle names an item that is a cycle. |
   | `file-missing` | The source `X.json` of a named `X.odrg` is not in the sources folder. |
   | `file-malformed` | A source is rejected under Requirement 3. The detail gives that reason too. |
   | `size-mismatch` | A source's canvas size differs from the mapping's. |

6. IF a source cannot be written as ODRG THEN `pack` SHALL refuse with the reason of
   Requirement 7 criterion 9.
7. IF the output folder exists and is not empty THEN `pack` SHALL refuse with
   `output-not-empty`.
8. WHEN `pack` refuses THEN the output folder SHALL be as it was before the command.
9. WHEN the example show of Requirement 17 is packed THEN every `.odrg` file in the output
   folder SHALL pass `check` and SHALL decode to the frames of its source.

## Requirement 15: Hello world and DVD bounce exist as tracked sources

**User Story:** As the owner of the installation, I want the two proof-of-concept animations
to exist as JSON frames in the current coordinate convention, so that they can be converted,
packed and played like any other animation.

### Acceptance Criteria

1. A generator started as `python -m odrig.generators.hello_world` SHALL write the Hello
   world animation as a JSON frames file, and one started as
   `python -m odrig.generators.dvd_bounce` SHALL write the DVD bounce animation. Each SHALL
   take the canvas size from a mapping file and SHALL use only the Python standard library.
2. For the two-leg mapping, Hello world SHALL be 255 frames of 20 ms on a 60 x 6 canvas. In
   every frame the same 122 pixels SHALL be lit, forming the words HELLO WORLD upright, read
   from left to right, with the tops of the letters on row 6 and the text spanning columns
   4 to 56. The rainbow SHALL move through the letters from left to right and SHALL return
   to its first state after the last frame.
3. For the two-leg mapping, DVD bounce SHALL be 232 frames of 180 ms on a 60 x 6 canvas. In
   every frame exactly a 2 x 2 square of pixels SHALL be lit; it SHALL start in the top-left
   corner, move one pixel diagonally per frame, and turn back at every edge of the canvas.
   Each lit pixel SHALL have the colour that the fixed rainbow gives to its coordinates.
4. `animations/hello.json` and `animations/dvd.json` SHALL be tracked and SHALL be
   byte-identical to what the two generators write for `mapping/legs-2.json`.
5. IF the canvas is too small for the animation THEN the generator SHALL reject with
   `canvas-too-small`.

## Requirement 16: A dense test clip can be generated

**User Story:** As a tester of the codec, the core, the emulator and the firmware, I want a
full-colour clip in which every pixel changes all the time, so that the worst case can be
tried on any canvas.

### Acceptance Criteria

1. A generator started as `python -m odrig.generators.dense` SHALL write a JSON frames file
   for the canvas of a mapping file and a length in whole seconds, 10 by default, with one
   frame per 20 ms tick.
2. For the ten-leg mapping the clip SHALL be 60 x 30, SHALL have more than 256 different
   colours, and SHALL light every pixel in every frame.
3. The generated clip SHALL NOT be tracked.

## Requirement 17: A tracked example show

**User Story:** As someone trying the emulator or the board, I want a ready show that uses
the two animations, so that there is something known to install and watch.

### Acceptance Criteria

1. `shows/example/show.json` SHALL be tracked and SHALL hold: item 1, the animation
   `hello.odrg`; item 2, the animation `dvd.odrg`; item 3, a cycle of items 1 and 2 with
   `seconds` 15; `start` 3; and `brightness` 128.
2. WHEN `pack` is run with that show, `mapping/legs-2.json` and the folder `animations` THEN
   it SHALL succeed.

## Requirement 18: Valid test vectors

**User Story:** As the author of another ODRG reader, I want small known-good files with
their expected pictures, so that I can prove my reader decodes every feature of the format.

### Acceptance Criteria

1. `tests/vectors/valid/` SHALL be tracked and SHALL hold pairs of files: `NAME.odrg` and
   `NAME.json`. `NAME.json` SHALL be a JSON frames file with one frame for every frame
   record of `NAME.odrg`, in order and without merging, giving that record's duration and
   the picture after it.
2. Every `.odrg` file in the set SHALL be at most 4,096 bytes.
3. Together the files SHALL cover: palette files and files without a palette; compressed
   and uncompressed bodies; every predictor; plain mode and run mode; every k, in each
   mode; stored frames; the escape code; a zero run that reaches the end of the buffer; a
   non-zero last code in run mode; the duration 65,535; a palette of 256 colours and a
   palette of 1 colour; a canvas one pixel wide and a canvas one pixel high; and compressed
   bodies made of stored blocks, of fixed-code blocks and of dynamic-code blocks.
4. WHEN the reference decoder decodes `NAME.odrg` THEN the result SHALL equal `NAME.json`.
5. A tracked program SHALL build the whole set, and the set SHALL be the output of that
   program.

## Requirement 19: Invalid test vectors

**User Story:** As the author of another ODRG reader, I want one wrong file for each reason
a reader rejects, so that I can prove my reader refuses each of them for the right reason.

### Acceptance Criteria

1. `tests/vectors/invalid/` SHALL be tracked. Each file SHALL be named `REASON.odrg` or
   `REASON.CASE.odrg`, where REASON is the reason of Requirement 6 the file must be rejected
   with.
2. The set SHALL hold at least one file for every reason in the table of Requirement 6, and
   separate files for each of these cases: a reserved flag bit, mode bit 7, and a stored
   mode byte other than `0x40`; a file cut off in the header, in the palette, in a record's
   first five bytes and in a record's data; a DEFLATE stream cut off, and a complete DEFLATE
   stream whose output ends inside a record; L below 2 and L above N + 1; a code above 255
   in plain mode and in run mode; a bad palette index in a coded frame and in a stored
   frame; bytes after the last record in an uncompressed body, in a compressed body, and in
   the file after the DEFLATE stream.
3. Each file SHALL have exactly one defect: with that defect removed it would be valid.
4. WHEN the reference decoder reads a file of the set THEN it SHALL reject it with the
   reason in the file's name.

## Requirement 20: Runs wherever Python runs, with pip-only dependencies

**User Story:** As a contributor on any computer, I want to set the tool up with Python and
pip alone, so that nothing has to be installed system-wide.

### Acceptance Criteria

1. The tool SHALL run on Python 3.10 and later.
2. Every third-party library SHALL be declared in the one file `requirements.txt` at the
   repository root, SHALL install with pip alone on macOS, Windows and Linux, and SHALL need
   no separately installed program such as ffmpeg.
3. `encode`, `decode`, `check`, `pack`, the generators and the reference decoder SHALL work
   with the Python standard library alone. Only `import` SHALL need third-party libraries.
4. The tool SHALL contain no code that is specific to one operating system. Windows and
   Linux are supported by this construction; this seed verifies macOS only.

## Requirement 21: One test command

**User Story:** As a contributor, I want one command that runs every test of this seed, so
that a test added later can never be left out.

### Acceptance Criteria

1. The command `python -m unittest discover -s tests/converter -t .`, run from the
   repository root, SHALL run the whole suite of this seed.
2. The command SHALL select tests by discovery in that folder. WHEN a test file is added to
   the folder THEN it SHALL be run without a change to any command, script or list.
3. The suite SHALL need no hardware and no network connection.
4. The suite SHALL pass on macOS.
5. The suite SHALL contain tests for every acceptance criterion of Requirements 1 to 20 that
   states a behaviour.

## Requirement 22: The tool is documented

**User Story:** As a newcomer, I want to read how to set up and use the tool, so that I can
convert an animation without reading the code.

### Acceptance Criteria

1. `docs/converter.md` SHALL describe how to set up the tool, every subcommand with an
   example, the three ways to fit a picture, the generators, how to pack the example show,
   the test command, and the layout of the test vectors.
2. `docs/reasons.md` SHALL list every reason of these requirements with its condition.
3. `README.md` SHALL point to `docs/converter.md`.
4. WHEN implementing shows that `docs/format.md`, `docs/mapping.md` or `docs/show.md` is
   ambiguous on a point this tool depends on THEN the document SHALL be made exact in the
   same change, in line with the answer recorded in `docs/drifts.md`.
