# Requirements: JavaScript converter (seed 06)

Source seed: `project-seeds/06-p1-javascript-converter/seed.md`. It depends on seed 01, for
the Python package `odrig`, the test vectors in `tests/vectors/` and the documents the two
tools are checked against, and on seed 05, which changes the mapping file format. Seed 05
is being implemented while this spec is written: these requirements rely on the repository
as seed 05 leaves it, and take the design of seed 05,
`docs/specs/05-p0-canvas-60-by-60/design.md`, as the description of that state. Where the
code then differs from that design, the code is what counts.

`docs/format.md`, `docs/mapping.md`, `docs/show.md` and `docs/reasons.md` define the
formats and the reason names. The Python tool defines everything those documents leave
open: the options, the texts, the order of the checks and the bytes of every output. Where
the seed leaves a point open, the answer used here is recorded in `docs/drifts.md` under
"Seed 06".

Terms:

- **the JavaScript tool**: the converter this seed adds, in the folder `converter/`.
- **the library**: the part of the JavaScript tool in `converter/lib/`. It runs unchanged
  in Node.js and in a web view.
- **the command line part**: the part in `converter/odrig.js` and `converter/cli/`. It runs
  in Node.js only.
- **the Python tool**, **the reference**: the package `odrig`, started as
  `python -m odrig`.
- **a web view**: the browser engine inside the Capacitor and Tauri apps, and a web page in
  a browser.
- **reason**, **detail**, **error line**: as in `docs/reasons.md`: the line
  `error: <reason>: <detail>` on standard error.
- **library text**: a part of a detail that the Python tool does not word itself: the
  message of Python's JSON module, of zlib, of the operating system, of Pillow or of PyAV.
- **picture**: the colours of every canvas pixel, three bytes for each, in the pixel order
  of `docs/format.md`.
- **source picture**: a decoded picture of a media file: rows from the top, four bytes for
  each pixel, red, green, blue and alpha.
- **the decoder program**: the ffmpeg program that the package `ffmpeg-static` installs
  into `converter/node_modules/`.
- **Chrome**: the Google Chrome that is installed on the Mac.

## Requirement 1: One converter in plain JavaScript, in two parts

**User Story:** As the owner, I want one converter that runs from a command line on any
computer and inside the apps, so that there is one piece of conversion code and not one for
each place it runs.

### Acceptance Criteria

1. The JavaScript tool SHALL live in the folder `converter/` at the repository root: the
   library in `converter/lib/`, the command line part in `converter/odrig.js` and
   `converter/cli/`, and its tests in `converter/tests/`.
2. Every file of the JavaScript tool SHALL be a JavaScript module that Node.js and a web
   view load as it is. No step SHALL transpile, bundle, minify or generate a file before
   the tool is run or the library is loaded.
3. The library SHALL import nothing but its own files, by relative paths that end in
   `.js`. It SHALL name no module of Node.js and no package, and SHALL read no file, no
   clock, no environment variable and no random number.
4. The library SHALL use only what both Node.js 20 and a web view provide: the language of
   ECMAScript 2020 with `BigInt`, typed arrays, `Map`, `Set`, `TextEncoder` and
   `TextDecoder`. It SHALL NOT use `Buffer`, `process`, `require`, `fetch`, the DOM, a
   worker, or a compression stream of the platform.
5. The library SHALL hold: reasons and rejections; strict JSON; JSON frames, read and
   written; the ODRG decoder and encoder with palettes; the DEFLATE decoder and
   compressor; mapping files of both kinds; show files; packing a show from files held in
   memory; fitting a picture to the canvas; and the 50 frames-per-second timeline.
6. The command line part SHALL hold: arguments, exit statuses and the error line; reading
   and writing files and folders; and reading media files with the decoder program and
   the GIF reader.
7. The command line part SHALL use the library for everything the library holds. It SHALL
   NOT decode, encode, check or fit anything by itself.
8. The JavaScript tool SHALL run with Node.js 20 and every later version. WHEN it is
   started with an older Node.js THEN it SHALL write one line that says so to standard
   error and exit with status 2.
9. The library SHALL give the same result for the same input in Node.js and in a web view,
   byte for byte, for every function it has.

## Requirement 2: The command line

**User Story:** As someone at a laptop, I want to run the converter like a script, with the
subcommands and options I know from the Python tool, so that I need not learn a second
tool.

### Acceptance Criteria

1. The tool SHALL be started as `node converter/odrig.js <subcommand> ...`, from any
   folder, with paths taken as the shell gives them.
2. It SHALL have exactly the subcommands `import`, `encode`, `decode`, `check` and `pack`,
   with these arguments and options, which are those of the Python tool:

   | Subcommand | Arguments and options |
   |---|---|
   | `import` | `MEDIA OUT.json --mapping MAPPING [--fit fill\|fit\|stretch] [--start SECONDS] [--duration SECONDS]` |
   | `encode` | `IN.json OUT.odrg [--uncompressed]` |
   | `decode` | `IN.odrg OUT.json` |
   | `check` | `FILE [--format json\|odrg]` |
   | `pack` | `--show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]` |

3. An option SHALL be accepted before, between and after the positional arguments, as
   `--name value` and as `--name=value`. A value that follows an option and is a minus
   sign followed by a number without an exponent, such as `-1` or `-0.5`, SHALL be taken
   as the value.
4. The exit status SHALL be 0 when the subcommand did its work, 1 when an input was
   rejected, and 2 when the command line was not understood.
5. WHEN an input is rejected THEN the tool SHALL write exactly one line,
   `error: <reason>: <detail>`, to standard error, with every run of white space in the
   detail written as one space, SHALL write nothing to standard output, and SHALL leave no
   output and no `.part` file behind. An output that existed before SHALL be as it was.
6. WHEN the command line is not understood THEN the tool SHALL write a message that
   begins with `usage:` to standard error and nothing to standard output, and SHALL write
   no file. These are not understood: no subcommand, an unknown subcommand, an unknown
   option, a missing or an extra positional argument, a required option that is missing,
   an option without its value, a `--fit` or `--format` that is not one of the listed
   values, a `--start` or `--duration` that is not a number of seconds, and a `check` of a
   file whose name does not tell its format without `--format`. An option given twice
   SHALL take its last value, as in the Python tool.
7. `--help`, alone or after a subcommand, SHALL write a usage text that names the
   subcommands, or the arguments and options of the subcommand, to standard output and
   exit with status 0.
8. `--start` and `--duration` SHALL be decimal numbers of seconds: an optional sign,
   digits with an optional fraction, and an optional exponent. The value SHALL be rounded
   to whole milliseconds, halves away from zero, computed on the digits and not in
   floating point.
9. For every command line the Python tool understands in the forms of criteria 2, 3 and
   8, the JavaScript tool SHALL end with the same exit status as the Python tool.
10. An error that is not a rejection SHALL NOT be reported as one: the tool SHALL let it
    end the program with Node's own message and a status that is neither 0, 1 nor 2.
11. The same input files and the same options SHALL give the same output, byte for byte,
    on every run.

## Requirement 3: The same reasons and the same messages

**User Story:** As a maintainer, I want the two tools to say the same thing about the same
file, so that a test can compare them and a person can read either.

### Acceptance Criteria

1. The library SHALL have exactly the 42 reason names of `odrig/errors.py`, and no other.
2. For every input the Python tool rejects, the JavaScript tool SHALL reject it with the
   same reason, and for every input the Python tool accepts, the JavaScript tool SHALL
   accept it.
3. The detail SHALL be the detail of the Python tool, character for character, wherever
   the Python tool words it itself, with the file named as the command line names it.
4. Where the detail of the Python tool holds library text, the JavaScript tool SHALL give
   the same reason and a detail of its own that names the same file. These are: the
   position and message of a text that is not JSON (`bad-json`); zlib's message
   (`bad-deflate`); the operating system's message for a file or folder that cannot be
   read or written (`not-found`, `cannot-write`, and the reasons that stand for a missing
   file); and the decoder's message for a media file (`unreadable-media`).
5. For a file or folder that does not exist, is a folder where a file is expected, or may
   not be read or written, the JavaScript tool SHALL write the words the Python tool
   writes on macOS and Linux: `No such file or directory`, `Is a directory`,
   `Not a directory`, `Permission denied`, `File exists`, `Directory not empty`.
6. Everything a successful run writes to standard output SHALL be what the Python tool
   writes, byte for byte.
7. The usage text SHALL be the JavaScript tool's own. It SHALL name the tool as
   `node converter/odrig.js`.

## Requirement 4: Strict JSON and JSON frames

**User Story:** As a maintainer, I want the JavaScript tool to read a JSON frames file as
strictly as the Python tool and to write it in the same layout, so that a source file is
the same whichever tool wrote it.

### Acceptance Criteria

1. The library SHALL read a JSON text from bytes with a reader of its own. It SHALL refuse
   as `bad-json`: bytes that are not UTF-8, a byte-order mark at the start, a text that is
   not exactly one JSON value, a member named twice in one object, the words `NaN`,
   `Infinity` and `-Infinity`, and a text nested deeper than 512 levels.
2. An integer SHALL be a JSON number written without a fraction and without an exponent.
   A number with either SHALL pass no integer check. An integer of any length SHALL be
   read without losing a digit when it has 30 characters or fewer, and SHALL count as
   beyond every range when it has more.
3. The JSON frames reader SHALL apply the rules of `docs/format.md` in the order of
   `docs/reasons.md`, "JSON frames files": the top level, `version`, the other top-level
   members with a missing one before an unknown one, `width`, `height`, `frames`, then
   each frame in order: its members, `ms`, the number of pixels, and each pixel in order.
4. The JSON frames writer SHALL write the canonical layout of the Python tool: the bytes
   of `odrig.jsonframes.dumps` for the same animation, with consecutive identical
   pictures written as one frame.
5. A JSON frames file of 20 MB SHALL be read in under 10 seconds on the Mac.

## Requirement 5: The ODRG decoder

**User Story:** As a maintainer, I want a second decoder that agrees with the reference on
every file, so that either can check an ODRG file.

### Acceptance Criteria

1. The library's decoder SHALL give, for an ODRG file: W, H, the palette size, whether the
   body is compressed, and for every frame record in order its duration, the picture
   after it and its mode byte.
2. For every file in `tests/vectors/valid/` the decoder SHALL give exactly the frames of
   the vector's JSON file, record by record.
3. For every file in `tests/vectors/invalid/` the decoder SHALL reject the file with the
   reason its name gives.
4. The checks SHALL run in the order of `docs/reasons.md`, "ODRG files", so that a file
   with more than one defect gets the reason the reference gives.
5. The decoder SHALL NOT examine the values of padding bits, and SHALL read a Rice code
   and a Gamma code whole before it judges its value.
6. For every file the suite makes by changing one byte of a valid file, by cutting a
   valid file short at every length, and by adding a byte to it, the decoder SHALL give
   the reason the reference gives, or accept the file with the same frames.

## Requirement 6: Reading a compressed body

**User Story:** As a maintainer, I want the JavaScript tool to judge a DEFLATE stream as
zlib does, so that `bad-deflate`, `truncated` and `trailing-bytes` mean the same in both
tools.

### Acceptance Criteria

1. The library SHALL decode a raw DEFLATE stream (RFC 1951) with a decoder of its own,
   with stored, fixed and dynamic blocks and distances up to 32,768.
2. The decoder SHALL give the output of the stream and the number of input bytes after its
   last byte, or reject the stream as `bad-deflate` when it is not valid, or as
   `truncated` when the input ends before the last block is complete.
3. For every stream the suite has, whole, damaged in one byte, or cut at any length, the
   verdict SHALL be the one Python's zlib gives: the same output and the same number of
   bytes left, or `bad-deflate`, or `truncated`.
4. A compressed ODRG file whose stream is followed by a byte SHALL be rejected as
   `trailing-bytes`, with the number of bytes in the detail as the Python tool gives it.

## Requirement 7: The encoder writes the bytes of the Python tool

**User Story:** As the owner, I want an animation encoded on a phone to be the file the
Python tool would have written, so that it does not matter where a file was made.

### Acceptance Criteria

1. `encode --uncompressed` SHALL write, for every JSON frames source, the file the Python
   tool writes with `--uncompressed`, byte for byte.
2. Frames that follow each other with identical pixels SHALL become one frame record, and
   a frame longer than 65,535 ms SHALL become several records with the same picture, the
   first ones of 65,535 ms.
3. An animation with at most 256 different colours SHALL get a palette of exactly those
   colours, ordered by hue, then saturation, then the largest channel, each compared as an
   exact fraction, with a colour without hue counted as hue 0. An animation with more
   colours SHALL be written without a palette.
4. Each frame record SHALL be the one with the fewest bytes of data among the 64 coded
   forms: predictors 0 to 3, plain mode and run mode, k from 0 to 7. Among forms of the
   same number of bytes the lowest predictor SHALL be taken, then plain mode before run
   mode, then the lowest k.
5. WHEN no coded form has fewer bytes of data than N THEN the record SHALL be a stored
   frame.
6. A source whose picture would be larger than 65,534 bytes SHALL be rejected as
   `canvas-too-large`, and one that would need more than 4,294,967,295 frame records as
   `too-many-frames`, the canvas judged first.
7. For Hello world, DVD bounce, a dense clip, and 200 small animations the suite makes
   from fixed seeds, with canvases from 1 x 1 to 40 x 30, with and without a palette, the
   uncompressed files of the two tools SHALL be identical.

## Requirement 8: Compression

**User Story:** As the owner, I want compressed files from the JavaScript tool to be as
small as the Python tool's, so that the board's storage holds as much.

### Acceptance Criteria

1. `encode` without `--uncompressed` SHALL write the body as one raw DEFLATE stream with a
   window of at most 32,768 bytes, made by a compressor that is part of the library.
2. The compressed file SHALL decode, with the reference decoder and with the library's
   own, to exactly the frame records of the uncompressed file of the same source.
3. The compressed file SHALL be at most 5 percent larger than the file the Python tool
   writes for the same source with the zlib of the Python that runs the test. This SHALL
   hold for Hello world and DVD bounce on the bench canvas and on 60 x 60, for a dense
   clip of 2 seconds on 60 x 60, and for the two `encoded.*` test vectors' sources. A
   smaller file is never a failure.
4. The compressor SHALL compress anyway when the result is larger than its input: only
   `--uncompressed` turns compression off.
5. The same body SHALL give the same stream on every run, on every computer and in every
   web view: the compressor uses whole-number arithmetic only and nothing of the platform.
6. Every stream the compressor writes SHALL be accepted by Python's zlib with nothing left
   over, for the bodies above and for inputs the suite makes from fixed seeds: empty, one
   byte, 70,000 equal bytes, 200,000 bytes without a pattern, and text that repeats at
   distances up to 32,768.
7. Compressing the body of a dense 60 x 60 clip of 10 seconds SHALL take under 20 seconds
   on the Mac.

## Requirement 9: decode and check

**User Story:** As a maintainer, I want `decode` and `check` to print and write what the
Python tool prints and writes, so that scripts work with either.

### Acceptance Criteria

1. `decode IN.odrg OUT.json` SHALL write the JSON frames file the Python tool writes for
   the same input, byte for byte: the canonical layout, with frame records that follow
   each other with the same picture written as one frame.
2. `check FILE` SHALL read a name ending in `.json` as JSON frames and one ending in
   `.odrg` as ODRG, in any letter case, and `--format` SHALL override the name.
3. For a valid file `check` SHALL print the lines of the Python tool, byte for byte:
   `format`, `canvas`, `frames`, `duration_ms`, `colours`, `file_bytes`, and for an ODRG
   file `palette` and `compressed`.
4. `decode` and `check` SHALL accept every valid test vector and SHALL reject every
   invalid one with the reason the vector's name gives, with exit status 1.
5. `encode` followed by `decode` SHALL give back a source in which no two frames that
   follow each other have the same pixels, byte for byte.

## Requirement 10: Mapping files of both kinds

**User Story:** As the owner of an installation with upright strips, I want the JavaScript
tool to read the mapping files the board reads, of both kinds.

### Acceptance Criteria

1. The library SHALL read a row-leg file and a column-leg file as `docs/mapping.md`
   defines them after seed 05, and give: the kind, W, H, and for each leg its number, its
   pin, its `first_led`, its strips in chain order and its number of LEDs.
2. A file that breaks a rule SHALL be `mapping-malformed`, and a file that does not exist
   `mapping-missing`.
3. The checks SHALL run in the order the design of seed 05 gives for the Python reader,
   and the detail SHALL be the Python reader's.
4. `mapping/legs-2.json` SHALL give a canvas of 60 x 6 and `mapping/legs-20.json` one of
   60 x 60.
5. For every mapping file of `mapping/`, every mapping the suites of the core make up, and
   mappings that break each rule of `docs/mapping.md` once, for each kind of file, the
   two tools SHALL agree: the same canvas, or the same error line.

## Requirement 11: Shows and pack

**User Story:** As someone who installs a show, I want `pack` of the JavaScript tool to
build the folder the Python tool builds, so that the board gets the same files.

### Acceptance Criteria

1. The library SHALL read a show file under the rules of `docs/show.md` as the Python
   reader does when this seed is implemented: its format first, then repeated ids, then
   ids that no item has, then cycles that name a cycle, each over the items in file order.
2. The library SHALL pack a show from bytes held in memory: given the bytes of a mapping
   file, of a show file and of the sources by name, it SHALL give the installed file set
   by name: `mapping.json` and `show.json`, each the bytes it was given, and for every
   different `X.odrg` the show names, in the order of first use, the file encoded from the
   source `X.json`.
3. `pack` on the command line SHALL check in the order of the Python tool: the mapping
   file, the show file and its ids, the output folder, then each source in the order the
   show names them: present, valid, of the mapping's canvas size, encodable. The first
   failure SHALL decide, with the reasons of `docs/reasons.md`, "Shows".
4. The output folder SHALL be new or empty, else `output-not-empty`. `pack` SHALL make it
   and the folders above it, SHALL write nothing before every check has passed, and on a
   failure SHALL leave the output folder and the folder around it as they were.
5. With `--uncompressed` the output folder SHALL hold the files the Python tool writes,
   with the same names and the same bytes.
6. Without `--uncompressed` the output folder SHALL hold files of the same names;
   `mapping.json` and `show.json` SHALL have the same bytes, and every `.odrg` file SHALL
   decode to the frame records of the Python tool's file and meet Requirement 8
   criterion 3.
7. This SHALL hold for the example show with `mapping/legs-2.json`, for the demo show
   with `mapping/legs-20.json`, and for a show of one dense clip of 2 seconds on 60 x 60.
   A show that breaks a rule of `docs/show.md`, or meets a reason of `docs/reasons.md`,
   "Shows", SHALL be refused by both tools with the same error line, for every rule and
   every reason.

## Requirement 12: The 50 frames-per-second timeline

**User Story:** As someone who converts a video, I want the JavaScript tool to pick the
same pictures at the same moments as the Python tool.

### Acceptance Criteria

1. The output SHALL have one frame of 20 ms for each tick. The first tick SHALL be at the
   start time, and each tick SHALL show the source frame that is on screen at its time:
   the last frame that starts no later.
2. The number of ticks SHALL be the length of the part divided by 20 ms, rounded to the
   nearest with halves up, and at least 1. Without a duration the part SHALL run to the
   end of the media.
3. Times SHALL be exact fractions of milliseconds. No time SHALL pass through a
   floating-point number before it is compared.
4. In a video, time SHALL be counted from the first frame. A frame SHALL be on screen
   until the next one starts, and the last one for the mean interval between the frames,
   or for 20 ms when it is the only one.
5. In a GIF, each frame SHALL be on screen for the delay the file records, with a delay of
   10 ms or less counted as 100 ms, and the frames gone through once.
6. A part that is not inside the media SHALL be refused as `bad-range`, in the four cases
   and with the details of the Python tool. A media file without a picture SHALL be
   `unreadable-media`.
7. A source frame that is on screen at no tick SHALL NOT be fitted, and one that is on
   screen at several SHALL be fitted once.
8. Reading SHALL stop when the part that was asked for is covered.

## Requirement 13: Fitting a picture to the canvas

**User Story:** As someone who converts a video, I want every canvas pixel to have the
value the Python tool computes, exactly.

### Acceptance Criteria

1. `fill`, `fit` and `stretch` SHALL choose the rectangle of the source that the canvas
   shows as the Python tool does, as exact fractions: canvas pixels are square; `fill`
   covers the canvas and cuts the overflow equally on two opposite sides; `fit` shows the
   whole picture with black bars; `stretch` shows the whole picture whatever its shape.
2. The colour of a canvas pixel SHALL be the mean of the source area it covers, each
   source pixel weighted by the area they share, for each channel, rounded to the nearest
   whole number with halves up. Area outside the picture SHALL count as black. The top row
   of the picture SHALL land on canvas row H.
3. A source pixel with an alpha below 255 SHALL be laid over black first: each channel v
   becomes `(v * alpha + 127) div 255`.
4. The mean SHALL be computed in whole numbers and SHALL equal the result of the Python
   tool for the same source picture, byte for byte, for every source picture and canvas
   the Python tool accepts.
5. A picture so large that `511 * area` is 2 to the power 63 or more, in the units of the
   Python tool, SHALL be refused as `unreadable-media`, as the Python tool does.
6. For 300 source pictures the suite makes from fixed seeds, of sizes from 1 x 1 to
   200 x 150 and canvases from 1 x 1 to 60 x 60, with each fit, the canvas pictures of the
   two tools SHALL be identical.

## Requirement 14: Reading media on the command line

**User Story:** As someone at a laptop, I want `import` to read my mp4, mov and GIF files
without installing ffmpeg, so that the tool works after one `npm` command.

### Acceptance Criteria

1. `import` SHALL read a file whose name ends in `.mp4`, `.mov` or `.gif`, in any letter
   case. Another ending SHALL be `unsupported-media`.
2. `import` SHALL check in this order: the mapping file; the name of the media file; that
   it exists, else `not-found`; a negative start and a duration that is not above 0; then
   the content; and last the part against the length of the media.
3. An mp4 or a mov SHALL be decoded by the decoder program, which npm installs into
   `converter/node_modules/`. The tool SHALL NOT use an ffmpeg of the system, and SHALL
   NOT look one up on `PATH`.
4. The tool SHALL take from the decoder program, for the first video stream: every
   decoded frame in the order it is shown, as a source picture, and for each frame its
   presentation time as a whole number of units of the stream's time base. Sound SHALL be
   ignored. A rotation the file records for display SHALL NOT be applied.
5. A GIF SHALL be read by the GIF reader of the package `omggif`, and by nothing else: a
   file of another kind under the name `.gif` SHALL be `unreadable-media`.
6. The pictures of a GIF SHALL be built by the rules of the design, "GIF pictures": the
   logical screen, each frame's rectangle, its palette, its transparent index and its
   disposal. Pixels nothing was drawn on SHALL be transparent, and so black.
7. A file that cannot be decoded, a video without a video stream, a frame without a
   presentation time, and frames whose times go backwards SHALL be `unreadable-media`.
8. WHEN the package that reads the kind of file is not installed THEN `import` SHALL end
   with status 1 and the line `error: decoder-missing: <detail>`, which names the command
   that installs it. `import` of a GIF SHALL NOT need the decoder program.
9. `encode`, `decode`, `check` and `pack` SHALL run where `converter/node_modules/` does
   not exist.
10. Importing the suite's test GIFs SHALL give the JSON frames file the Python tool gives,
    byte for byte.
11. Importing the suite's test mp4 and mov SHALL give the same number of frames with the
    same durations as the Python tool, and no colour value SHALL differ by more than 3.

## Requirement 15: The library takes decoded frames from whoever has them

**User Story:** As the developer of the operators' app, I want to hand the library frames
that the phone's web view decoded, so that the app converts without a decoder of its own.

### Acceptance Criteria

1. The library SHALL import media through one function that takes the frames of a source,
   a canvas size and the options of `import`, and gives the animation. It SHALL NOT read a
   media file itself.
2. A frame SHALL be given as its width, its height, its source picture as a `Uint8Array`
   or a `Uint8ClampedArray`, and its time: for a video the presentation time, for a GIF
   the delay.
3. The frames SHALL be taken from a synchronous or an asynchronous iteration, one at a
   time, so that a source of many frames is never held whole.
4. The rules of Requirement 12 criteria 4 and 5 SHALL be in the library, so that a web
   view that supplies times and delays gets the timeline of the command line.
5. A time SHALL be given as a whole number of milliseconds, or as an exact fraction of
   two whole numbers, each a `Number` that is a safe integer or a `BigInt`.
6. The command line part SHALL use this same function for `import`.

## Requirement 16: The library runs in a web page

**User Story:** As the owner, I want proof that the library loads in a browser engine as
it is, so that the app can rely on it.

### Acceptance Criteria

1. A test SHALL start Chrome without a window on a page that loads
   `converter/lib/index.js` as a module from a server on the loopback address, with no
   other script and no change to any file of the library.
2. In that page the library SHALL encode Hello world, compressed and uncompressed, and the
   bytes SHALL be those `node converter/odrig.js encode` writes for the same source.
3. In that page the library SHALL decode both files to the frames of the source, and
   SHALL import three source pictures the page makes, with each fit, to the canvas
   pictures Node.js gives.
4. The test SHALL use the Chrome that is installed. It SHALL install no browser and no
   package, SHALL give Chrome a profile folder of its own in a temporary folder, and SHALL
   remove that folder and end Chrome when it is done.
5. WHEN no Chrome is found THEN the test SHALL be reported as skipped with the place it
   looked. On the Mac of this project it SHALL run.

## Requirement 17: Dependencies, and what is tracked

**User Story:** As someone who sets the tool up, I want one `npm` command that puts
everything into the project folder, and a lock file that fixes what it fetches.

### Acceptance Criteria

1. `converter/package.json` SHALL name the packages the command line part needs, each at
   one exact version, and SHALL be marked private. `converter/package-lock.json` SHALL be
   tracked.
2. `npm ci --prefix converter` SHALL install everything into `converter/node_modules/`,
   which git SHALL ignore.
3. The packages SHALL be `ffmpeg-static` and `omggif`, and no other.
4. The library SHALL need no package. The suite SHALL prove it by reading every file of
   `converter/lib/`.
5. `converter/ffmpeg.sha256` SHALL hold the SHA-256 of the decoder program for every
   platform it was verified on. The suite SHALL compare the installed program with the
   entry of its platform when there is one.
6. The documentation SHALL say what an installation leaves outside the project folder:
   npm's own cache, and the copy of the download that `ffmpeg-static` keeps in the user's
   cache folder.

## Requirement 18: Tests

**User Story:** As a maintainer, I want one command that runs every test of the
JavaScript tool and compares it with the Python tool.

### Acceptance Criteria

1. `npm test --prefix converter` SHALL run the whole suite with the test runner that is
   built into Node.js, and SHALL pass on the Mac.
2. The command SHALL find the tests by discovery: every file of `converter/tests/` whose
   name ends in `.test.js`. No command, script or document SHALL list test files.
3. The suite SHALL run both tools on the same inputs and compare, as the criteria of
   Requirements 3 to 14 state: Hello world, DVD bounce and a dense clip for `encode`,
   `decode` and `pack`; every test vector for `decode` and `check`; the test GIFs and the
   test mp4 for `import`.
4. The suite SHALL take the Python tool from `.venv/bin/python` of the repository, or
   from the program the environment variable `ODRIG_PYTHON` names. WHEN it is not there
   THEN every test that needs it SHALL fail with a message that says how to set it up.
5. The suite SHALL build its media files and its dense clip while it runs. It SHALL track
   no media file and no generated source.
6. The suite SHALL need no hardware and no network connection once `npm ci` has run.
7. The four suites that need no board SHALL still pass:
   `.venv/bin/python -m unittest discover -s tests/converter -t .`, `make -C core test`,
   `python3 -m unittest discover -s tests/emulator -t .` and `python3 firmware/fw.py test`.
8. The Python package `odrig` SHALL keep its behaviour: no file of `odrig/` SHALL change
   in this seed.

## Requirement 19: Documentation

**User Story:** As a newcomer, I want the documentation to show me the converter I will
use, and to say what the Python tool is for.

### Acceptance Criteria

1. `docs/converter.md` SHALL present the JavaScript tool as the converter: its setup, its
   exit statuses, a section with an example for each subcommand, the library and how a
   page loads it, how frames are given to it, and the test command.
2. `docs/reference-converter.md` SHALL present the Python tool as the reference the tests
   compare with: its setup, its command line, the generators, the test vectors, the tool
   that writes `docs/mapping.md`, and its use from Python.
3. Every document that shows how to convert or pack SHALL show the JavaScript tool:
   `README.md`, `docs/emulator.md` and `docs/firmware.md`. The generators SHALL be shown
   as the Python programs they are.
4. `docs/reasons.md` SHALL say that both tools use its names.
5. `docs/decisions.md` SHALL state the converter as it is, with a line in its change log.
6. The documents SHALL say what is verified: macOS, with the versions of Node.js, npm,
   Chrome and the decoder program that were used; and that Windows and Linux are
   supported by construction and not verified.
7. The tests of the Python suite that read `docs/converter.md` SHALL read the page that
   now holds what they check, and SHALL pass.
