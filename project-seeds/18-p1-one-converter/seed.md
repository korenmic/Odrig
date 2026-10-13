# One converter

## Summary

Leave one implementation of the converter in the repository, the JavaScript one. Take the
converting out of the Python package, make the JavaScript converter's tests stand without
it, and keep of Python only a small library that reads and writes the project's files for
the tests and for the firmware tool.

## Priority

- `P1`

## Depends On

- Seed 06, which wrote the JavaScript converter and made it the one people use.
- Seed 11, for Windows: every suite that passes there has to pass there afterwards.
- Seed 13 mended the Python tool's reading of damaged media. That code goes with this seed.

## Product Context

The repository holds two programs that turn a video or a GIF into an animation: the
Python package `odrig/`, written first, and the JavaScript tool in `converter/`, written
to run inside the operators' app as well. Since seed 06 the JavaScript tool is the
converter, and the Python package is called the reference: the tests compare the two.

On 2026-10-13 the owner ruled: there is to be a single implementation, a single source of
truth. A converter runs in two places and nowhere else: on a computer, from the command
line, and inside the operators' app. Nothing else is to run converter logic.

Who uses which today:

| Consumer | Python `odrig/` | JavaScript `converter/` |
|---|---|---|
| People converting from the command line, as the documents tell them | no | yes |
| The operators' app, in its second part, seed 17 | no | yes |
| The emulator, the command tool, the player | no | no |
| The firmware tool, which reads show, mapping and settings files | yes | no |
| The four animation generators | yes | no |
| The builder of the mapping page for the documents | yes | no |
| The tests of the player, of the emulator, of the firmware tool, and of the pages for newcomers | yes | no |
| The JavaScript converter's own tests, which compare it with Python | yes | yes |

So nobody converts with Python any more. What still uses the Python package uses it as a
library for the project's files: it reads a show or a mapping file, and it writes and
reads animation files for tests. The one place where both converters run is the JavaScript
converter's own suite, where Python is the referee: about 1,300 tests lean on it.

Two things follow from that. The duplicate can go without anyone losing a tool. And the
JavaScript suite must be given another referee first, or removing Python removes its
tests' meaning.

## Technical Constraints

- The bytes the JavaScript converter writes do not change: an animation converted before
  this seed and after it is the same file.
- No test of the JavaScript converter starts Python. What it compared with Python is
  compared with files stored in the repository, made once from what the two tools agree
  on today, and small enough to be tracked.
- What stays of Python is a library and not a tool: it has no command line, reads no
  video and no GIF, and its name and its page say that it is for tests and tools. It
  needs nothing outside the standard library, so the Python packages that were installed
  only to read media go from the setup.
- The player's tests keep their independent reference: a second reader of the animation
  format, apart from the player's own, is what they compare the player with. That is a
  reader for checking and not a converter.
- The two readers that remain, the JavaScript converter's and the Python library's, are
  kept in step by one set of stored files, valid and invalid, that both must read, or
  refuse with the same reason.
- The firmware tool keeps working with the standard library and the library that stays.
- Every suite that passes on macOS and on Windows today passes on both afterwards.
- A page changes with the code it describes. The documents stop calling anything a
  reference converter.

## Required Behavior

1. A video or a GIF is turned into an animation, an animation is encoded, checked and
   decoded, and a show is packed, by the JavaScript converter only.
2. `python -m odrig` with a command that converts, checks or packs no longer exists, and
   the Python code that reads media is gone, with its tests.
3. The JavaScript converter's suite passes on a computer on which its tests cannot start
   Python.
4. The emulator, the command tool, the player and the firmware tool run no converter
   logic, and a test says so.
5. The tests of the player, of the emulator and of the firmware tool, and the firmware
   tool itself, get the files they need from the library that stays or from stored
   files, and pass.
6. The generators go on writing their animations as sources, which the converter then
   encodes.
7. The documents describe one converter, and the library that stays as what it is.

## Definition Of Done

1. Every suite that needs no board passes on macOS, and those of Windows pass there.
2. The JavaScript converter's suite passes with Python taken off its path.
3. A search of the repository finds one implementation of importing media and one command
   line that converts.
4. The setup of a fresh clone installs no Python package for reading media, and the
   walk-through of the pages for newcomers passes.
5. The documents, the entry file for agents and the decisions page say what exists.

## Open Questions

1. Do the four generators stay in Python? They write sources and convert nothing, so
   this seed leaves them where they are. Moving them to JavaScript would make one
   language of everything that makes an animation; it is a seed of its own if the owner
   wants it.
2. The tests make hundreds of small animation files as they run, with the Python
   library's writer of the format. The spec decides whether that writer stays in the
   library, as test support, or whether the tests take those files from the converter.
   The first keeps a second writer of the format beside the converter's; the second
   makes the suites start the converter. The stored files of the constraints keep the
   two writers equal in the first case.
