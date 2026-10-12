# Requirements: damaged media in the reference tool

Seed: [`project-seeds/13-p2-damaged-media-in-the-reference-tool/seed.md`](../../../project-seeds/13-p2-damaged-media-in-the-reference-tool/seed.md).

The Python tool, `python -m odrig`, is the reference the suites compare the JavaScript
converter with. Its `import` reads `.mp4` and `.mov` files with PyAV and `.gif` files with
Pillow (`odrig/media.py`). For three kinds of damaged file it does not refuse the file with
a reason: it ends the Python process with a fault of memory, or ends with a traceback.

In this document "refused" means what `docs/reasons.md` means: the tool prints one line
`error: REASON: ...` on the error stream and ends with status 1.

## Requirement 1: a video stream without a decoder

**User story.** As someone who runs the reference tool, I want a video it cannot decode to
be refused, so that the tool never takes the whole Python process down.

1. WHEN `import` is given a video whose first video stream has no decoder THEN the tool
   SHALL refuse it with the reason `unreadable-media`.
2. WHEN `import` is given such a video THEN the Python process SHALL end by itself with
   status 1, without a fault of memory.
3. WHEN `import` is given a whole video THEN its result SHALL be the same bytes as before
   this change.

## Requirement 2: metadata that is not UTF-8

**User story.** As someone who runs the reference tool, I want a video with unreadable
metadata to be refused with a reason, so that I am told what is wrong with the file.

1. WHEN opening a video raises `UnicodeDecodeError` THEN the tool SHALL refuse the file
   with the reason `unreadable-media`.
2. WHEN `import` is given such a video THEN no traceback SHALL be printed.

## Requirement 3: a GIF cut short

**User story.** As someone who runs the reference tool, I want a GIF that was cut short to
be refused with a reason, whatever place it was cut at.

1. WHEN decoding a GIF raises `IndexError` or `struct.error` THEN the tool SHALL refuse the
   file with the reason `unreadable-media`.
2. WHEN `import` is given the test GIF cut after any number of its bytes THEN the tool SHALL
   either write a JSON frames file and end with status 0, or refuse the file with
   `unreadable-media`, and SHALL print no traceback.

## Requirement 4: the tests cause no crash report

**User story.** As whoever runs the suite, I want no crash dialog on my screen, including
when a test is run against the tool as it was before this change.

1. WHEN a test gives the tool a file that may end the process with a fault of memory THEN
   the test SHALL run the tool in a child process in which such a fault ends the process
   quietly with the number of the signal as its status.
2. WHEN that child process ends with the number of a signal THEN the test SHALL fail and
   say which signal it was.
3. WHEN the whole converter suite is run on macOS THEN no crash report of Python SHALL be
   written.

## Requirement 5: the two tools compared

**User story.** As a maintainer, I want the suites to compare the two tools on damaged
files again, so that the faults cannot come back unseen.

1. WHEN the JavaScript converter's suite compares the two tools on a cut or damaged video
   THEN it SHALL run the Python tool on that file, without first looking whether the file
   has a decoder.
2. WHEN both tools refuse a damaged file THEN the test SHALL require the same reason of
   both.
3. WHEN one tool reads a damaged file that the other refuses THEN the test SHALL record
   that file by name in a table of known differences, and SHALL fail for a difference that
   is not in the table.

## Requirement 6: the documents

1. `docs/reasons.md` SHALL say, under "Media files", that a video without a decoder, a video
   whose metadata cannot be read and a GIF that is cut short are `unreadable-media`.
2. `docs/reference-converter.md` SHALL no longer describe a damaged video as able to end the
   tool, and the pages for newcomers SHALL no longer warn of it.
3. The seed's `state.json` SHALL say `completed`, and `AGENTS.md` SHALL no longer list this
   seed under what is coming.
