# Converter and reference codec

## Summary

A cross-platform Python tool that turns video and GIF files into JSON frames sources, turns
JSON frames sources into ODRG runtime files, and packs a show into the folder that gets
installed. It contains the reference ODRG encoder and decoder, and produces the test vectors
that every other implementation is checked against.

## Priority

- `P0`

## Product Context

Animations exist in two formats, both specified in `docs/format.md`: JSON frames, the tracked
source, and ODRG, the runtime file the player reads. Nothing in the repository can produce or
read either format yet.

People who make animations need to turn ordinary media into animations for the canvas without
editing numbers by hand, and need the tracked source to be converted into the runtime file the
same way every time.

A show is installed as one folder: `mapping.json`, `show.json` and the `.odrg` files it names
(`docs/show.md`). Something has to build that folder from tracked sources.

The two proof-of-concept animations that run on the board today, Hello world and DVD bounce,
exist only as scripts that write GIF files in the old coordinate convention. They should
exist as JSON frames sources.

The shared runtime core (seed 02), the emulator (seed 03) and the firmware build (seed 04)
need known-good ODRG files and their expected decoded frames. This seed supplies them.

## Technical Constraints

- Python 3.10 or later. Uses only libraries available for macOS, Windows and Linux.
- Every dependency installs with pip alone: no system-wide ffmpeg or other manual install.
  Dependencies are declared in one requirements file.
- `docs/format.md`, `docs/mapping.md` and `docs/show.md` are the authority. Code that
  disagrees with them is wrong; if a document turns out to be ambiguous, it is fixed in the
  same change.
- The canvas size for imported media comes from a mapping file: its `width`, and its total
  number of rows as the height. It is never hard-coded.
- Converting JSON frames to ODRG is lossless: decoding the ODRG file gives the same picture
  at every millisecond.
- The same input and options give byte-identical output.
- The test command selects its suite by directory or discovery, never by a list of files.
- No hardware is needed and nothing here talks to the board.

## Required Behavior

1. One command-line tool with these subcommands:
   - `import`: a media file (mp4, mov, gif) plus a mapping file gives a JSON frames file.
   - `encode`: a JSON frames file gives an ODRG file, compressed unless asked otherwise.
   - `decode`: an ODRG file gives a JSON frames file.
   - `check`: validates a JSON frames or ODRG file and prints its canvas size, frame count,
     duration, colour count and file size.
   - `pack`: a `show.json`, a mapping file and a folder of JSON frames sources give the
     installed file set: `mapping.json`, `show.json` unchanged, and each `X.odrg` that
     `show.json` names, encoded from `X.json`.
2. `import` works on a 50 frames-per-second timeline: at every 20 ms tick it takes the source
   frame that is on screen at that time. Consecutive identical frames are merged.
3. `import` fits the picture to the canvas in one of three ways: fill the canvas and crop the
   overflow around the centre (the default), fit inside the canvas with black bars, or stretch.
   Shrinking uses area averaging.
4. `import` accepts a start time and a duration, so part of a file can be converted.
5. `encode` follows the converter guidance in `docs/format.md`: a hue-ordered palette when
   the animation has at most 256 colours, the smallest predictor, mode and k for each frame,
   stored frames when nothing coded is smaller, merged identical frames, and long frames
   split at 65,535 ms.
6. `decode` and `check` reject every file that `docs/format.md` says a reader rejects, and
   name the reason.
7. `pack` refuses a show that `docs/show.md` calls invalid, and names the reason.
8. Hello world and DVD bounce are re-created as generators that write JSON frames in the
   current coordinate convention for the 60 x 6 canvas. The generated JSON files are tracked.
9. A tracked example show uses those two animations in a cycle that alternates every 15
   seconds and starts at power-on, with the two-leg mapping.
10. A tracked set of test vectors: small ODRG files, each with its expected decoded frames.
    Together they cover palette and RGB files, compressed and uncompressed bodies, every
    predictor, plain and run mode, every k, stored frames, the escape code, a zero run that
    reaches the end of the buffer, a non-zero last code, and the longest duration. A second
    set holds one invalid file for each reason a reader rejects.

## Definition Of Done

1. For Hello world, DVD bounce and a dense full-colour 60 x 30 test clip, JSON to ODRG to JSON
   gives identical frames, compressed and uncompressed.
2. The encoded sizes of Hello world and DVD bounce are within 2 percent of the figures in the
   table in `docs/format.md`.
3. Importing a short mp4 and a GIF gives JSON frames of the mapping's canvas size, with every
   duration a multiple of 20 ms and the total within 20 ms of the requested length.
4. Every invalid test vector is rejected with its own reason.
5. `pack` on the example show produces a folder whose files pass `check`.
6. The whole test suite runs with one documented command on macOS and passes. Windows and
   Linux are supported by construction and are not verified in this seed.
7. The tool's use is documented.

## Open Questions

None. Use the resolved behavior in this seed.
