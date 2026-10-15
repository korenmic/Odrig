# Requirements: one converter

Seed: [`project-seeds/18-p1-one-converter/seed.md`](../../../project-seeds/18-p1-one-converter/seed.md).

The repository holds two converters: the JavaScript tool in `converter/`, which people
use, and the Python package `odrig/`, which converted first and is now the referee of the
JavaScript suite. This spec leaves one: the JavaScript converter. The Python package keeps
what the tests and the firmware tool read and write of the project's files, and stops
converting.

The seed leaves two questions to the spec. They are answered here as the owner was told
on 2026-10-14 they would be unless the owner said otherwise, which the owner did not:

1. The four generators stay in Python. They write JSON frames sources and convert
   nothing; the converter encodes what they write.
2. The Python writer of the ODRG format stays in the library, as test support: the suites
   of the core, the emulator and the firmware tool make hundreds of small animation files
   with it as they run. Stored files keep it equal to the converter's writer.

In this document "the converter" is the JavaScript tool, "the library" is what stays of
`odrig/`, and "the stored files" are the files the tests compare with in place of a second
program.

## Requirement 1: one converter

1. Importing a video or a GIF, encoding, checking and decoding an animation, and packing a
   show SHALL be done by the converter only.
2. `python -m odrig` SHALL NOT exist, and the Python code that reads media SHALL be gone,
   with its tests.
3. The bytes the converter writes SHALL NOT change: a file converted before this spec and
   after it is the same file.

## Requirement 2: the converter's suite stands alone

1. No test of the converter SHALL start Python. What it compared with the Python package
   SHALL be compared with stored files, made once from what the two tools agree on
   today.
2. The stored files SHALL be small enough to be tracked: 8 MB at most in all.
3. The converter's suite SHALL pass with no Python on the path and no `.venv`.
4. A test SHALL say which stored files exist and that every one of them is read by a test.

## Requirement 3: the library

1. The library SHALL have no command line and SHALL read no video and no GIF. It SHALL
   need nothing outside Python's standard library.
2. Its page SHALL say that it is a library for tests and tools, and what it holds.
3. Its reader and the converter's reader of the ODRG format SHALL read the stored vectors,
   valid and invalid, alike, and refuse each invalid one with the same reason. Its writer
   and the converter's writer SHALL write the same bytes for the stored sources.
4. The firmware tool SHALL keep working with the standard library and the library.

## Requirement 4: who runs converter logic

1. The emulator, the command tool, the player, the preview and the firmware tool SHALL run
   no converter logic, and a test SHALL say so.
2. The suites of the core, the emulator, the firmware tool and the board, the benchmark of
   the core and the pages for newcomers SHALL get their shows from the converter, started
   as a program, or from stored files.
3. The generators SHALL go on writing their animations as sources, which the converter
   encodes.

## Requirement 5: the setup and the documents

1. The setup of a fresh clone SHALL install no Python package for reading media.
2. The documents SHALL describe one converter, and the library as what it is. No document
   SHALL call anything a reference converter.
3. Every suite that passes on macOS today SHALL pass on macOS afterwards, and the
   walkthrough of the pages for newcomers SHALL pass.
4. The suites that pass on Windows today SHALL be run there by whoever has Windows; the
   spec cannot run them, and says so to the owner.

## Left out on purpose

- Moving the generators to JavaScript.
- Renaming the Python package. Its name is the project's, and the firmware tool, the
  suites and the pages import it by that name; its page says what it is now.
- Changing what the converter does.
