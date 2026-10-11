# JavaScript converter

## Summary

One converter written in plain JavaScript. It runs from the command line with Node.js with
no build step, and the same code loads unchanged inside the Capacitor and Tauri apps. It has
the features of the Python tool: import, encode, decode, check and pack. The Python tool
stays as the independent check that tests compare it against.

## Priority

- `P1`

## Depends On

- Seed 01, for the Python tool, the test vectors and the documents it is checked against.

## Product Context

Converting media into animations is heavy work. It runs on phones and PCs, never on the
board and never in the emulator.

The operators' app is built with Capacitor, and a PC app with Tauri is intended. Both run
web code. Neither can run the Python converter, and the owner wants one converter, not one
per place it runs.

The owner also needs to run the converter from a command line on any PC or laptop at any
moment, the way a Python script runs, with nothing to compile.

Plain JavaScript meets all three: web views run it as it is, and Node.js runs it from the
command line.

## Technical Constraints

- Plain JavaScript modules. No transpiling, bundling or other build step is needed to run
  the tool or to load the library.
- Two parts:
  - a library that uses only what both Node.js and web views provide, with no file access
    and no dependencies: JSON frames, the ODRG encoder and decoder, palettes, fitting a
    picture to the canvas, the 50 frames-per-second timeline, checking mappings and shows,
    and packing a show from files held in memory;
  - a command-line part for Node.js: arguments, files, and reading media files.
- Node.js 20 or later.
- Dependencies install with npm alone into the project folder, from a package file with a
  lock file. Reading mp4, mov and gif files on the command line uses a package that brings
  its own decoder; no system-wide ffmpeg.
- `docs/format.md`, `docs/mapping.md`, `docs/show.md` and `docs/reasons.md` are the
  authority, and the reason names are the same as the Python tool's.
- The same input and options give the same output on every run.
- The Python package keeps its behaviour. Tests use it as the reference.
- The test command selects its suite by directory or discovery, never by a list of files.

## Required Behavior

1. A command-line tool with the subcommands `import`, `encode`, `decode`, `check` and `pack`,
   taking the same options and giving the same results and messages as the Python tool.
2. `encode` without compression gives files byte-identical to the Python tool's.
3. `encode` with compression gives files that decode to identical frames. Their size is
   within 5 percent of the Python tool's.
4. `decode` and `check` accept every valid test vector and reject every invalid one for the
   reason the vector set names.
5. `import` follows the same rules as the Python tool: the 50 frames-per-second timeline, the
   three ways of fitting, area averaging, and the start time and duration.
6. `pack` produces the same installed file set as the Python tool, byte-identical when
   uncompressed, and refuses the same invalid shows for the same reasons.
7. The library can be loaded in a web page as it is, and encodes and decodes there.
8. The tool documentation presents the JavaScript tool as the converter and the Python tool
   as the reference used by tests.

## Definition Of Done

1. Tests run the JavaScript tool and the Python tool on the same inputs and compare the
   results: Hello world, DVD bounce and a dense clip for encode, decode and pack; every test
   vector for decode and check.
2. Importing the test GIF gives JSON frames identical to the Python tool's. Importing the
   test mp4 gives the same number of frames and the same durations, with no colour value
   differing by more than 3.
3. A test loads the library in headless Chrome, encodes an animation there and gets the
   same bytes as on the command line.
4. The whole suite runs with one documented command on macOS and passes. Windows and Linux
   are supported by construction and not verified in this seed.
5. The Python suites still pass.

## Open Questions

None. Use the resolved behavior in this seed.
