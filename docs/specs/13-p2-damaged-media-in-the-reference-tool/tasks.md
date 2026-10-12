# Tasks: damaged media in the reference tool

Each task is one commit that also ticks its checkbox. A test for a fault is run against
the unchanged tool first and what it showed goes into the commit message. The suite is run
with `.venv/bin/python -m unittest discover -s tests/converter -t .`.

- [x] 1. A video stream without a decoder is refused
  - Add `tests/converter/quiet.py` with `run_tool`, as the design describes.
  - Add `tests/converter/test_import_damaged.py` with the test of the 993-byte video.
    Run it against the unchanged tool: the child ends with status 11.
  - `odrig/media.py`: refuse a first video stream whose `codec_context` is `None`.
  - Set the seed's `state.json` to `in_progress`.
  - Requirements 1 and 4.

- [x] 2. Metadata that is not UTF-8 is refused
  - Add the test with the damaged `title`. Against the unchanged tool: a traceback ending
    in `UnicodeDecodeError`, status 1.
  - `odrig/media.py`: catch `UnicodeDecodeError` in `_video_frames`.
  - Requirement 2.

- [x] 3. A GIF cut short is refused
  - Add the tests of the GIF cut after 78 and after 86 bytes, and the sweep over every
    length. Against the unchanged tool: `IndexError` and `struct.error`.
  - `odrig/media.py`: catch `IndexError` and `struct.error` in `_gif_frames`.
  - Add the test that a whole video and a whole GIF give the bytes they gave before.
  - Requirements 1.3 and 3.

- [x] 4. The two tools are compared on damaged files again
  - `converter/tests/reference.py`: remove `_undecodable_video` and its use.
  - `converter/tests/import.test.js`: equal reasons where both refuse, and the table of
    known differences.
  - Run `npm test --prefix converter` and confirm no crash report of Python was written.
  - Requirement 5 and Requirement 4.3.

- [ ] 5. The documents, and the seed's state
  - `docs/reasons.md`, `docs/reference-converter.md`, the page for newcomers that warns of
    the fault, and `AGENTS.md`.
  - Run every suite that needs no board.
  - Set the seed's `state.json` to `completed`.
  - Requirement 6.
