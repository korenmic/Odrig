# Design: one converter

## Overview

The work goes in this order, so that no suite loses its meaning on the way:

1. While both converters still exist, a maker writes the stored files once: what the
   Python package computes for every comparison the JavaScript suite makes today, in
   compact form, and the small media files the import tests use.
2. The JavaScript suite reads the stored files instead of starting Python, one group of
   test files at a time, and at the end cannot start Python at all.
3. The converting parts of the Python package go, with their tests, and the suites that
   packed shows with it start the converter.
4. The setup, the pages and the decisions say what exists.

## What this design relies on

From a survey of the repository on 2026-10-14:

- `converter/tests/support.js` starts Python in four ways: `python -m odrig` and its
  generators (`runPython`, `runBoth`, `generated`), and `converter/tests/reference.py`,
  which answers 18 kinds of request (`check`, `run`, `encode`, `decode`, `forms`,
  `dumps`, `milliseconds`, `sixdigits`, `inflate`, `deflate`, `rects`, `resample`,
  `ticks`, `timeline`, `media`, `mappings`, `read_mappings`, `read_shows`).
- About 1,000 of the converter's 1,314 tests lean on those answers, in 15 test files.
  `docs.test.js`, `library.test.js` and `browser.test.js` start no Python.
- `odrig/` holds `errors`, `files`, `strictjson`, `jsonframes`, `odrg` (reader and
  writer), `mapping`, `show`, `pack`, `cli` with `__main__`, `media`, `mapdoc` and the
  generators. Only `media` needs numpy, Pillow and PyAV.
- Outside the package: the firmware tool reads with `show`, `mapping`, `odrg`, `errors`
  and `strictjson`; the suites of the core, the emulator, the firmware tool and the board
  write animations with `odrg` and pack shows with `pack`; the onboarding suite checks the
  pages' commands with `odrig.cli`; the core's benchmark runs `python -m odrig encode`.
  The emulator, the command tool, the preview and the app import nothing of it.
- `tests/converter/` has 645 tests; those of the media import, the command line and
  `pack` go with the code, those of the reader, the writer, the vectors, JSON frames, the
  mapping, the show reader and the generators stay.

## The stored files

They live in `converter/tests/expected/`, one JSON file for each kind of request, and in
`converter/tests/media/`, the GIFs and videos the import tests read. A large table is
kept as what the comparison needs and nothing more: a reason, or a SHA-256 of a result,
for each case, and a SHA-256 of the whole table where a test compares a table at once.
Paths of temporary files in error lines are written as a placeholder that the test fills
in.

`tests/converter/make_expected.py` writes them, with the Python package as it is before
its converting parts go. It is run once, in the first task; its output is checked by the
JavaScript suite in the same task, still against Python, so that what is stored is what
the two agree on. When the converting parts go, the maker goes with them: the stored
files are the record from then on, and a change of the converter's output is a change of
a stored file, made on purpose and reviewed.

The two tests that forbid tracked media in `converter/` allow `converter/tests/media/`,
with its size checked.

## The JavaScript suite

`support.js` gets `expected(kind)`, which reads a stored file, and loses `python`,
`runPython`, `runBoth`, `reference` and `generated`. Each test file is changed to read
what it compared with: the ODRG codec and its streams first, then the media import, then
the readers and the command line. `reference.py` goes in the last of these tasks, and a
test then runs the suite's helpers with `PATH` holding no Python and finds that nothing
starts one.

The video import is compared within 3 of each colour value today; the stored file keeps
the frames the Python import gave, compressed, for the few videos, and the hashes for the
GIFs, which are compared byte for byte.

## The library

What stays of `odrig/`: `errors`, `files`, `strictjson`, `jsonframes`, `odrg`, `mapping`,
`show`, `mapdoc` and `generators`. `cli`, `__main__`, `media` and `pack` go. The one
helper of `cli` that the generators and `mapdoc` use, the exit status of a refusal, moves
to `errors`. The package's docstring and its page, `docs/python-library.md`, which takes
the place of `docs/reference-converter.md`, say that it is a library for tests and tools.

The suites that packed with `pack.pack` call a helper of their own support that runs
`node converter/odrig.js pack`. The core's benchmark encodes with the converter. The
walkthrough's GIF is a stored file, not one Pillow draws.

`requirements.txt` goes, and the setup has no `pip install`. A test of the onboarding
suite says that no page installs a Python package.

## Who runs converter logic

`tests/converter/test_scope.py`, or a test beside it, reads the imports of `emulator/`,
`odrigctl/`, `preview/`, `firmware/fwtool/` and the core's host programs: none imports a
module of the converter's or the library's converting, and none starts `odrig.js` but the
preview, which runs `check` and `pack` as programs.

## Documents

`docs/python-library.md`; `docs/converter.md`, `docs/format.md`, `docs/reasons.md`,
`docs/mapping.md`, `docs/core.md`, `docs/emulator.md`, `docs/decisions.md`, `agent/`,
`AGENTS.md` and `README.md` wherever they name the reference converter or its setup.

## Risks

- **The size of the stored files.** The large tables are kept as hashes; the 60 x 60
  generator outputs are stored uncompressed ODRG, not JSON. The limit of Requirement 2
  is checked by a test.
- **Windows.** The converter's suite fails on Windows today for reasons of its own. This
  spec does not make it pass there; it must not make more of it fail. The contributor on
  Windows runs it.
- **The length of the work.** About 1,000 tests change. Each task leaves every suite
  passing, so the work can stop between tasks.
