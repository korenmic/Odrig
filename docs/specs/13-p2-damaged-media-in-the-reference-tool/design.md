# Design: damaged media in the reference tool

## What is wrong, and where

All three faults are in `odrig/media.py`.

| Fault | Place | What happens today |
|---|---|---|
| A video whose first video stream has no decoder | `_video_frames`, `container.decode(stream)` | PyAV 17.1.0 lists the stream with `stream.codec_context` equal to `None` and follows it without looking: the process ends with signal 11. |
| A video with metadata that is not UTF-8 | `_video_frames`, `av.open` | `UnicodeDecodeError`, which is not one of PyAV's own errors and is not caught. |
| A GIF cut short | `_gif_frames`, `image.seek` and `image.convert` | `IndexError` or `struct.error` from Pillow, neither of which is caught. |

Small files that show each one:

- **No decoder:** the video that `tests/converter/media_fixtures.write_video` writes for
  `COLOURS` is 1,529 bytes; its first 993 bytes open as a file with one video stream and
  no decoder.
- **Metadata:** a three-frame video written with PyAV whose `title` is fifteen ASCII
  letters, with the first four of those bytes then replaced in the file by `FF FE FD FC`.
- **Cut GIF:** the GIF that `media_fixtures.write_gif` writes for four colours is 213
  bytes; cut after 78 bytes it gives `IndexError`, cut after 86 bytes `struct.error`.

## The change to `odrig/media.py`

- `_video_frames` refuses the file before decoding when
  `container.streams.video[0].codec_context is None`:
  `Rejection(UNREADABLE_MEDIA, "the video stream has no decoder")`.
- `_video_frames` catches `UnicodeDecodeError` beside `av.error.FFmpegError`, with the
  message "the video cannot be decoded: ...".
- `_gif_frames` adds `IndexError` and `struct.error` to the errors it turns into
  `unreadable-media`.

Nothing else changes. A whole file takes the same path as before, with one comparison
added per video.

## Running the tool where it may fault

`tests/converter/quiet.py` holds one function, `run_tool(arguments)`. It starts
`sys.executable -c PRELUDE` in a child process. The prelude names the C function `_exit` as
the handler of signals 10 and 11 through `ctypes`, then calls `odrig.cli.main` with the
arguments. A fault of memory in the child then ends it with status 10 or 11 and writes no
crash report. `run_tool` returns the status, the output and the error stream, and raises
`AssertionError` naming the signal when the status is 10 or 11.

On Windows `ctypes.CDLL(None)` does not exist; the prelude skips the handlers there. Windows
shows no dialog for a child that faults when the parent has set the error mode, which
`subprocess` leaves as it is; the fault is then a non-zero status and the test fails with
that status.

## Tests

In `tests/converter/test_import_damaged.py`, found by the suite's discovery:

- one test per fault, each writing its small file into a temporary folder as above and
  requiring status 1, the line `error: unreadable-media:` and no traceback;
- the test GIF cut after every number of bytes from 1 to its length less 1: status 0 with
  a JSON frames file that `check` accepts, or status 1 with `unreadable-media`; never a
  traceback;
- the whole test video and the whole test GIF give the same JSON frames bytes as a copy of
  the expected output kept from before the change.

Each fault's test is run against the unchanged `odrig/media.py` first, and what it showed
is recorded in the commit message: status 11 for the first, a traceback for the other two.

## The JavaScript converter's suite

`converter/tests/reference.py` has `_undecodable_video`, which looks at a video's streams
and declines to run the Python tool on a file without a decoder, and `_quiet_faults`, which
installs the same quiet handler. `_undecodable_video` and its use are removed.
`_quiet_faults` stays: it costs nothing and keeps a new fault from reaching the screen.

`converter/tests/import.test.js` compares the two tools on its damaged files. Where both
refuse, the reasons must be equal. Where they differ in whether they read the file at all,
the file's name must be in a table `KNOWN_DIFFERENCES` in that test file, each row with the
reason it is expected: the two tools use different decoders, and one may recover a picture
from a file the other gives up on.

## Documents

- `docs/reasons.md`, "Media files": the row for `unreadable-media` names the three cases.
- `docs/reference-converter.md`: the sentence about a damaged video ending the tool goes.
- `agent/getting-started.md` or `agent/animation-guide.md`: the warning about the fault
  goes. `AGENTS.md`: seed 13 leaves "What is coming".

## Risks

- Another build of PyAV or Pillow may fail in a way these three catches do not cover. The
  cut-GIF sweep and the quiet handler are what would show it.
- Refusing by `codec_context is None` relies on PyAV exposing a missing decoder that way.
  It does in 17.1.0, the version `requirements.txt` pins.
