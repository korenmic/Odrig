# The converter

The converter is the tool that works with the animation formats of [format.md](format.md).
It is written in JavaScript, lives in the folder `converter/`, and has two parts:

- the command line, started as `node converter/odrig.js <subcommand>`;
- [the library](#the-library), `converter/lib/`, which does all the work on bytes. It runs
  as it is in Node.js and in a web page, so that an app can convert with the same code.

| Subcommand | What it does |
|---|---|
| [`import`](#import) | Turns a video or a GIF into a JSON frames file for the canvas of a mapping file. |
| [`encode`](#encode) | Turns a JSON frames file into an ODRG file, the file the player reads. |
| [`decode`](#decode) | Turns an ODRG file back into a JSON frames file. |
| [`check`](#check) | Says whether a JSON frames or ODRG file is valid and what it holds. |
| [`pack`](#pack) | Builds the folder that is installed for a show. |

A second converter, written in Python, is kept as the reference: the [tests](#tests) of
this tool run both on the same inputs and compare what they give. The Python package also
holds the generators that write the tracked animations, and builds the test vectors for
other ODRG readers. All of that is on its own page,
[reference-converter.md](reference-converter.md). To convert and to pack, use the tool of
this page.

## Setup

The tool needs Node.js 20 or later. `encode`, `decode`, `check` and `pack` need Node.js alone:
there is nothing to install and nothing to build. `import` needs two packages, which one
command puts into the project folder:

```
npm ci --prefix converter
```

| Package | Version | Licence | Used for |
|---|---|---|---|
| `ffmpeg-static` | 5.3.0 | GPL-3.0-or-later | Reading mp4 and mov files. It carries a decoder program, an ffmpeg built for the computer's system and processor; no ffmpeg of the computer is needed, and none is used. |
| `omggif` | 1.0.10 | MIT | Reading GIF files. One file of JavaScript. |

What that command does, and what it leaves:

- It installs 21 packages into `converter/node_modules/`, 45 MB, which git ignores: the two
  of the table and what `ffmpeg-static` needs to install itself.
  `converter/package-lock.json` fixes the version of every one of them.
- The install script of `ffmpeg-static` fetches the decoder program from the releases of
  the package's repository on GitHub. This needs a network connection, once. The script
  checks no checksum, so `converter/ffmpeg.sha256` holds the SHA-256 of the program for
  every platform it was verified on, and the suite compares the installed program with
  it.
- npm 12 runs the install script of a package only when `package.json` allows it. The
  member `allowScripts` of `converter/package.json` allows the script of `ffmpeg-static`
  5.3.0 and no other. An older npm does not know the member and runs the script.
- Outside the project folder it leaves two things. The package keeps a copy of what it
  fetched in the user's cache folder, `~/Library/Caches/ffmpeg-static-nodejs` on macOS,
  19 MB. npm keeps its own cache and its logs in `~/.npm`. Both may be removed at any
  time; the next install fetches again.

The tool starts the decoder program as a program of its own and reads what it writes.
Nothing of it is loaded into the tool, is part of the library or is tracked. It is always
the program in `converter/node_modules/`.

Every command on this page is run from the repository root. The examples write into the
folder `build/`, which git ignores. Make it once:

```
mkdir build
```

The tool opens no serial port and no network connection, and has no code for one operating
system only.

## Exit statuses

| Status | Meaning |
|---:|---|
| 0 | The subcommand did its work. |
| 1 | An input was rejected. One line `error: <reason>: <detail>` is written to standard error and no output is left behind. The reasons are listed in [reasons.md](reasons.md). |
| 2 | The command line was not understood, or Node.js is older than 20. A usage message, or one line that names the version of Node.js, is written to standard error and nothing else is written. |
| 70 | The tool itself failed: an error that is no rejection of an input. The error is written to standard error as Node.js prints it. It is a defect of the tool. |

One reason is not in [reasons.md](reasons.md), because it is a fault of the setup and not
of an input: `decoder-missing`. `import` ends with status 1 and
`error: decoder-missing: <detail>` when the package that reads the media file is not
installed. The detail names the package and the command that installs it.

The statuses, the reasons and the error line are those of the reference converter. The
detail is the same as well, character for character, wherever the tools word it
themselves. Where a detail holds the words of a library, each tool has its own: the place
and the fault in a `bad-json` detail, the fault of the stream in a `bad-deflate` detail,
and what the decoder says in an `unreadable-media` detail.

## import

```
node converter/odrig.js import MEDIA OUT.json --mapping MAPPING [--fit fill|fit|stretch]
                               [--start SECONDS] [--duration SECONDS]
```

Turns a video or a GIF into a JSON frames file for the canvas of a mapping file. The media
file's name ends in `.mp4`, `.mov` or `.gif`, in any letter case. The canvas is the one
the mapping file describes: with a row-leg file it is as wide as the mapping's `width` and
as high as the number of rows the mapping lists, and with a column-leg file it is as wide as
the number of columns the mapping lists and as high as the mapping's `height`
(see [mapping.md](mapping.md)).

```
node converter/odrig.js import clip.mp4 build/clip.json --mapping mapping/legs-2.json
```

**Timeline.** The output is built on the 50 frames-per-second timeline. Ticks are 20 ms
apart, the first at the start time, and each tick takes the source frame that is on screen
at that moment: the last frame that starts no later. Ticks that follow each other with the
same picture are written as one frame, so every `ms` is a multiple of 20.

- In a video, the first video stream is used and time is counted from its first frame. A
  frame is on screen until the next one starts; the last one stays for the mean interval
  between the frames. Sound is ignored.
- In a GIF, each frame is on screen for the delay the file records. A delay of 10 ms or
  less counts as 100 ms, as in web browsers. The frames are gone through once.
- Transparent pixels are black.

**Part of a file.** `--start` and `--duration` are decimal numbers of seconds. Without
`--start` the part starts at 0; without `--duration` it runs to the end of the media. The
number of ticks is the length of the part divided by 20 ms, rounded to the nearest, and at
least one, so the output is within 20 ms of the length asked for. A part that is not inside
the media is refused with `bad-range`; it is never shortened.

```
node converter/odrig.js import clip.mp4 build/clip.json --mapping mapping/legs-2.json \
    --start 12.5 --duration 4 --fit fit
```

**Fitting.** Canvas pixels are square, so the canvas has the shape of its width to its
height. `--fit` says how a picture of another shape is put on it:

| Fit | Result |
|---|---|
| `fill` | The default. The picture is scaled by one factor until it covers the whole canvas; what overflows is cut off equally on the two opposite sides. |
| `fit` | The picture is scaled by one factor until all of it lies inside the canvas, centred; the rest of the canvas is black. |
| `stretch` | The picture is scaled to the whole canvas, by a different factor in each direction when the shapes differ. |

The colour of a canvas pixel is the mean of the source area it covers, each source pixel
weighted by the area they share, rounded to the nearest whole number with halves up. Area
outside the picture counts as black, so the edge of a bar that falls inside a pixel is
blended. The same rule is used when the picture is enlarged. The mean is computed in whole
numbers, so the same decoded picture gives the same canvas picture on every computer, in
Node.js and in a web page.

The top row of the picture lands on the top row of the canvas, row H.

A rotation that a file records for display, pixels that are not square and colour profiles
are not applied: the picture is used as the decoder gives it. A video filmed upright on a
phone has to be turned before it is imported.

**GIF pictures.** A frame of a GIF may cover a part of the screen only, and may leave
pixels of the frames before it showing through. The tool builds the picture of each frame
by the rules of the GIF format as web browsers apply them. The screen starts transparent.
Before a frame is drawn, the disposal of the frame before it is applied to that frame's
rectangle: disposal 0 and 1 leave it, 2 makes it transparent, and 3 gives it back what it
held before that frame was drawn. A pixel that has the frame's transparent index is left
as it is.

For the GIFs most programs write, these are the pictures the reference converter gets
from its library, Pillow, and the two tools write the same file. In three corners Pillow
has rules of its own, and the files differ: after a frame with disposal 2 that has no
transparent index, Pillow paints the background colour where this tool makes the pixels
transparent, and so black; for a frame that names no disposal, Pillow keeps the disposal
of the frame before; and where the first frame does not cover the screen, Pillow paints
the background colour.

**Videos.** The decoder program of this tool is ffmpeg 6.0, and the reference converter
decodes with the FFmpeg 8 libraries of its own library. For the videos of the suite the
two tools write the same file, byte for byte. Two decoders may give colours that differ
by a little for another video, and the two tools need not judge a damaged file alike.

`import` checks the mapping file first, then the name of the media file, then that it
exists, then that the package that reads it is installed, then the start and the duration.
Its reasons are under "Media files" in [reasons.md](reasons.md).

## encode

```
node converter/odrig.js encode IN.json OUT.odrg [--uncompressed]
```

Reads a JSON frames file and writes the ODRG file that shows the same picture at every
millisecond. It follows the converter guidance of [format.md](format.md):

- Frames that follow each other with the same pixels become one frame record, and a frame
  longer than 65,535 ms becomes several records with the same picture.
- An animation with at most 256 colours gets a palette of exactly those colours, ordered by
  hue, then saturation, then brightness, with black and the greys first. An animation with
  more colours is written without a palette.
- Every frame record is written with the predictor, mode and k that give the fewest bytes
  of data. Among equally small ones the lowest predictor is taken, then plain mode before
  run mode, then the lowest k. When no coded form is smaller than the picture itself, the
  frame is stored as it is.
- The body is compressed with DEFLATE, with a window of 32,768 bytes. `--uncompressed`
  writes the body as it is.

```
node converter/odrig.js encode animations/hello.json build/hello.odrg
```

An existing output file is replaced. The same source and options always give the same
bytes, compressed or not, on every computer and in a web page: the compressor is part of
the library, and no file depends on a library of the computer.

`animations/hello.json` and `animations/dvd.json`, the two tracked sources, are test
content: Hello world and DVD bounce exist to try the tools and the board, and are not
finished animations of the installation. Encoded, `hello.json` is 17,731 bytes
uncompressed and 1,138 bytes compressed, and `dvd.json` 3,799 and 1,612 bytes. The
reference converter writes the same uncompressed files, and with zlib 1.2.12 the same
compressed files as well.

A source that breaks the JSON frames format is rejected with its reason from "JSON frames
files" in [reasons.md](reasons.md). A valid source that does not fit an ODRG file is
rejected with `canvas-too-large` or `too-many-frames`.

## decode

```
node converter/odrig.js decode IN.odrg OUT.json
```

Reads an ODRG file and writes its frames as a JSON frames file in the canonical layout.
Frame records that follow each other with the same picture are written as one frame, so
the JSON file shows the same picture at every millisecond as the ODRG file. An existing
output file is replaced.

```
node converter/odrig.js decode build/hello.odrg build/hello-again.json
```

A file that breaks the format is rejected with one of the reasons under "ODRG files" in
[reasons.md](reasons.md), and no output is written.

A source in which no two frames that follow each other have the same pixels comes back from
`encode` and `decode` with the same frames, byte for byte.

## check

```
node converter/odrig.js check FILE [--format json|odrg]
```

Says whether a file is valid and what it holds. A name ending in `.json` is read as JSON
frames and one ending in `.odrg` as ODRG, in any letter case. `--format` overrides the name
and is needed for any other name; without it such a name is a usage error (status 2).

```
node converter/odrig.js check build/hello.odrg
```

For a valid file these lines are printed, and nothing else:

```
format: odrg
canvas: 60x6
frames: 255
duration_ms: 5100
colours: 256
file_bytes: 1138
palette: 256
compressed: yes
```

| Line | Value |
|---|---|
| `format` | `json-frames` or `odrg`. |
| `canvas` | W and H. |
| `frames` | The number of frames the file lists: frame objects in a JSON frames file, frame records in an ODRG file. |
| `duration_ms` | The sum of all durations. |
| `colours` | The number of different colours that appear in the pictures. |
| `file_bytes` | The size of the file. |
| `palette` | ODRG only: the palette size C, 0 for a file without a palette. |
| `compressed` | ODRG only: `yes` or `no`. |

An invalid file is rejected with its reason and nothing is printed to standard output.

## pack

```
node converter/odrig.js pack --show SHOW --mapping MAPPING --sources DIR --out DIR [--uncompressed]
```

Builds the folder that is installed on the board and run by the emulator (see
[show.md](show.md)). The output folder then holds exactly:

- `mapping.json`, a byte-for-byte copy of the mapping file;
- `show.json`, a byte-for-byte copy of the show file;
- for every different `X.odrg` the show names, the file `X.odrg`, encoded from `X.json` in
  the sources folder as `encode` does. `--uncompressed` writes every one of them without
  compression.

The example show plays the two tracked test animations, Hello world and DVD bounce, in
turn, 15 seconds each. It is for today's build and is packed with the two-leg mapping:

```
node converter/odrig.js pack --show shows/example/show.json --mapping mapping/legs-2.json \
    --sources animations --out build/example-show
```

`build/example-show` then holds `mapping.json`, `show.json`, `hello.odrg` and `dvd.odrg`.
The show for the target build of twenty legs, 60 x 60, is the demo show
`shows/demo-20/show.json`; its sources are written by the generators, and
[emulator.md](emulator.md), "Two shows to run", gives the commands.

The output folder must be new or empty; otherwise `pack` refuses with `output-not-empty`.
`pack` makes the folder, and the folders above it when they do not exist.
`pack` checks everything before it writes anything: the mapping file, then the show file
and its ids, then the output folder, then each source in the order the show names them. A
source must have the canvas size of the mapping. The first thing that is wrong is reported,
with a reason from "Shows" in [reasons.md](reasons.md), and the output folder and the
folder around it are left as they were.

## The library

`converter/lib/` is the converter without files and without a command line: it is given
bytes and gives bytes. Every file of it is a plain ECMAScript module. It uses no package
and nothing that only Node.js or only a browser has: the language of ECMAScript 2020 with
`BigInt` and typed arrays, and `TextEncoder` and `TextDecoder`, which both have. It reads
no file, no clock and no random number. Nothing is built, bundled or compiled: Node.js and
a web page load the same files.

| File | What it holds |
|---|---|
| `index.js` | Every name of the library, one namespace for each of the files below, and `Rejection`. |
| `errors.js` | The reasons, and `Rejection`, the error of a refused input. |
| `whole.js` | Whole numbers and fractions beyond the exact range of a JavaScript number. |
| `strictjson.js` | The strict reader of JSON. |
| `jsonframes.js` | JSON frames files: `loads` reads one, `dumps` writes the canonical layout. |
| `inflate.js` | The DEFLATE decoder. |
| `deflate.js` | The DEFLATE compressor. |
| `odrg.js` | ODRG files: `decode` and `encode`. |
| `mapping.js` | Mapping files: `loads`. |
| `show.js` | Show files: `loads`. |
| `pack.js` | The installed file set of a show from the bytes of its files: `pack`. |
| `fit.js` | Fitting a picture to a canvas: `place`. |
| `timeline.js` | The 50 frames-per-second timeline of decoded frames: `importFrames`. |

**Loading it in a page.** A page loads `converter/lib/index.js` as a module, and the
browser fetches the other files of the folder from beside it. The folder is served as it
is, from an `http` or `https` address: Chrome loads no module from a file address.

```html
<script type="module">
  import {jsonframes, odrg, Rejection} from "./lib/index.js";

  const source = new Uint8Array(await (await fetch("hello.json")).arrayBuffer());
  try {
    const file = odrg.encode(jsonframes.loads(source));
    console.log(file.length);
  } catch (error) {
    if (!(error instanceof Rejection)) {
      throw error;
    }
    console.log(error.reason, error.detail);
  }
</script>
```

In Node.js the same line imports it, with the path of the file.

**What goes in and what comes out.**

| Thing | In JavaScript |
|---|---|
| The bytes of a file | A `Uint8Array`. |
| A picture | A `Uint8Array` of 3 * W * H: red, green and blue for each pixel in the pixel order of [format.md](format.md), the bottom row first. |
| A frame | `{ms, picture}`. |
| An animation | `{width, height, frames}`. |
| A source picture | `{width, height, rgba}`: `rgba` is a `Uint8Array` or a `Uint8ClampedArray` of 4 * width * height, red, green, blue and alpha for each pixel, the top row first. The `data` of a canvas's `ImageData` is one. |
| A refused input | A `Rejection` is thrown: an `Error` with the `reason` and the `detail`. |

| Call | Result |
|---|---|
| `jsonframes.loads(bytes)` | The animation of a JSON frames file. |
| `jsonframes.dumps(animation)` | The bytes of the JSON frames file of an animation, in the canonical layout. |
| `odrg.encode(animation, {compressed})` | The bytes of the ODRG file of an animation. |
| `odrg.decode(bytes)` | `{width, height, paletteSize, compressed, records, modes}`: for every frame record its duration and the picture after it, and its mode byte. |
| `mapping.loads(bytes)` | `{kind, width, height, legs}` of a mapping file. |
| `show.loads(bytes)` | `{brightness, items, start}` of a show file. |
| `pack.pack({mapping, show, sources}, {compressed})` | A `Map` from file name to bytes: the installed file set. `sources` holds the bytes of each JSON frames source by its name. |
| `fit.place(source, w, h, fit)` | The canvas picture of one source picture. |
| `timeline.importFrames(source, canvas, options)` | The animation of decoded frames. It is the only call that is asynchronous. |

**Giving it frames.** The library decodes no video and no GIF: whoever calls it decodes,
and hands the frames to `importFrames`, which fits them and builds the timeline as
`import` does. The command line hands it the frames of the decoder program and of the GIF
package; an app hands it the frames its web view decodes.

```js
const animation = await timeline.importFrames(source, {width: 60, height: 60},
                                              {fit: "fill", startMs: 0, durationMs: null});
const bytes = jsonframes.dumps(animation);
```

`source` is `{kind, frames}`:

- `kind` is `"video"` or `"gif"`.
- `frames` is anything a `for await` loop goes through: an array, a generator, or an
  asynchronous generator that decodes as it is asked. `importFrames` takes one frame at a
  time and asks for none after the part is covered; it then leaves the loop, so a
  generator is told to stop.
- A frame of a video is a source picture with a `time`: `{width, height, rgba, time}`.
  `time` is the presentation time in milliseconds, counted from any starting point: a
  whole number, or a fraction given as `[n, d]`. A time that is not whole is given as a
  fraction and never as a number with decimals: for a timestamp in microseconds,
  `[timestamp, 1000]`.
- A frame of a GIF is a source picture with a `delayMs`: `{width, height, rgba, delayMs}`.
  The picture is the screen as it is while the frame shows, built by the rules under
  [import](#import), and `delayMs` is the delay the file records, in whole milliseconds.

The options are those of `import`: `fit`, `startMs` and `durationMs`, in whole
milliseconds; `durationMs` is `null` for "to the end". A frame of a video is complete when
the next one has come, so `importFrames` asks for one frame more than the part shows. An
input that `import` would refuse is refused with the same `Rejection`. A call that is
wrong in itself, such as a fit that does not exist or a time with decimals, throws a
`RangeError`.

## Tests

```
npm test --prefix converter
```

This one command runs the whole suite of the tool, with the test runner that is part of
Node.js. It finds the tests by itself: every file of `converter/tests/` whose name ends in
`.test.js` is run, so a new test file needs no change anywhere else. The suite needs no
hardware, and no network connection once the packages are installed.

The suite compares with the reference converter, so it needs that tool set up as
[reference-converter.md](reference-converter.md), "Setup", describes: it takes the Python
of `.venv/` in the repository, or, when there is none, the program that the environment
variable `ODRIG_PYTHON` names. Without either, every test that compares fails with a
message that says how to set it up. The suite builds the media files it imports while it
runs; none is tracked.

One test loads the library in Chrome, without a window and with a profile folder of its
own that it removes, on a page it serves from `127.0.0.1`, and compares what the page
computes with what Node.js computes, byte for byte. It looks for Chrome where it is
usually installed; the environment variable `ODRIG_CHROME` names another place. Where
there is no Chrome the test is reported as skipped and says where it looked.

## What is verified

Everything on this page was run on one Mac, with:

| What | Version |
|---|---|
| macOS | macOS 26.5, on Apple Silicon |
| Node.js | Node.js 26.5.0, and the whole suite once more with Node.js 20.18.0 |
| npm | npm 12.0.2 |
| Chrome | Chrome 154.0.8037.98 |
| The decoder program | ffmpeg 6.0, the program `ffmpeg-static` 5.3.0 fetches for macOS on Apple Silicon |
| The reference converter | Python 3.14.6 with zlib 1.2.12 |

With these the suite passes. Wherever it gives the same whole input to both converters,
they write the same file, byte for byte: compressed files and imported videos and GIFs
included.

Windows and Linux are supported by construction and not verified: nothing has been run
there. Not run either: a Node.js other than the two named, an npm older than 12, and a
browser other than Chrome. Of `import`, three things are not verified: a video with a
rotation recorded for display, a video from a real camera or phone, and the decoder
program that `ffmpeg-static` fetches for any other system or processor, for which
`converter/ffmpeg.sha256` has no line.
