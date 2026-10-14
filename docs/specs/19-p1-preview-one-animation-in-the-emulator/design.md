# Design: preview one animation in the emulator

## Overview

`python -m emulator.preview FILE` is a small program in `emulator/preview.py`. It checks
what it needs, has the converter pack a show without items under `build/preview/`,
starts the emulator on that folder as a child process, uploads the file into it as item
1 with the command tool's upload, prints the address of the page, opens it, and waits.
Ctrl-C stops the emulator and removes the folder. Every judgement of the file is made by
the core of the emulator, which is the core of the board.

## What this design relies on

- `node converter/odrig.js pack` builds an installed show from a show source, a mapping
  and a folder of sources, and takes a show without items; `check FILE` prints the
  canvas of an ODRG file as `canvas: WxH`, or refuses it with a reason.
- `python -m emulator SHOW_DIR --port N --serial-link PATH --tcp-port N --core PATH`
  prints `page:`, on a Mac `serial:`, and with a line port `tcp:`; a port that is taken
  ends it with status 1 and `error: address-in-use: ...` on standard error (see
  [emulator.md](../../emulator.md), "Exit statuses").
- After its start the core of an empty show has nothing to check: `upload begin` is
  answered at once. An upload is checked by the core, and `upload end` answers `bad-file`
  with the reason, `size-mismatch` among them.
- `odrigctl.content.upload` sends a file over a `client.Session`, and `client.Session`
  reaches the emulator over HTTP.
- With one animation installed, the playlist is that animation, from its first frame, in
  loops.

## The command

```
python -m emulator.preview FILE [--mapping FILE] [--no-browser] [--core PATH]
```

Run from anywhere; paths are taken as given, relative to the folder the command is run in.
`--core` is the emulator's option of that name, passed on.

The steps, in this order:

1. **The file.** It must be there and be a file. Otherwise: `preview: <path>: there is
   no file there`, status 1.
2. **What it needs.** The core's library at the path the emulator would load, and `node`
   on the path. Otherwise one line that names the step of the getting-started page:
   `preview: the core's library is not built: <path>; see "Build the core" in
   agent/getting-started.md`, or `preview: Node.js is not there; see "What the computer
   needs" in agent/getting-started.md`. Status 1.
3. **The canvas.** `node converter/odrig.js check FILE --format odrg` is run. A refusal
   ends the command with the converter's reason: `preview: <path> is refused: <reason>`.
   The canvas it prints is kept for the message of step 6.
4. **The show.** A folder `build/preview/<process id>/` is made. The converter packs
   `shows/preview/show.json`, a show without items at brightness 255, with the mapping
   and an empty folder of sources, into its folder `show`.
5. **The emulator.** `python -m emulator <folder>/show` is started as a child, in a
   process group of its own, with `--port 8600`, `--serial-link <folder>/serial` on a Mac
   and `--tcp-port 0` elsewhere. When it ends with `address-in-use`, it is started
   again with `--port 0`, and the command says `preview: port 8600 is taken; the page is
   on <port>`. The lines it prints are read until `page:`.
6. **The upload.** The file's bytes go to the emulator as item 1 named `preview.odrg`,
   over HTTP, with `odrigctl.content.upload`. The name is the preview's own, so that any
   file name works; the bytes are the file's. A reply that is no success ends the
   command: `bad-file` with `size-mismatch` as `preview: <path> is <W> x <H>, and the
   mapping <mapping> is <W> x <H>`, any other as `preview: <path> is refused: <reason>`.
   The emulator is stopped first.
7. **The page.** `page: <address>` is printed, and the address is opened with Python's
   `webbrowser` unless `--no-browser` was given. Then the command waits for the
   emulator.
8. **The end.** Ctrl-C, or the termination of the command, stops the emulator as its
   tests stop it: an interrupt to its group, and after 10 seconds a kill. Then the
   folder is removed, and the command ends with 0. When the emulator ends by itself, the
   command ends with its status.

The canvas of the mapping for the message of step 6 is read from the mapping file as
[mapping.md](../../mapping.md) defines it: a file of rows has `width` and as many rows as
its legs name, and a file of columns has `height` and as many columns as its legs name.
That is the one thing the command reads of a file, and only for a message.

## What it leaves

Nothing of the folder `build/preview/<process id>/` stays. The file is opened for
reading only. The emulator child is in a group of its own, so that an interrupt reaches
it whether the command was stopped from its terminal or by a signal.

## Tests

`tests/emulator/test_preview.py`, against the real emulator, with `--no-browser`:

- a file of the example's canvas on `mapping/legs-2.json`: the command prints the page
  address; the emulator lists one item, `preview.odrg`, with the bytes of the file, and
  plays it; its refreshes are those of the reference player for that show; after an
  interrupt the command ends with 0, the emulator is gone, the port is free, and
  `build/preview/` holds nothing of it; the file is unchanged.
- a relative path and an absolute one; a file whose name breaks the naming rule.
- the default mapping, with a 60 x 60 clip.
- a path with nothing there, and a folder: status 1, one line, nothing started.
- a file of random bytes: `bad-magic`, status 1, nothing left running.
- a file of another canvas: the line names `60 x 6` and `60 x 60`.
- port 8600 taken by the test: the line that names the port taken, and the page on
  another.
- a core library path with nothing there, and a path without `node`: the line that names
  the step, and nothing started.
- the scope: `emulator/preview.py` imports no module of `odrig/` and none of
  `converter/`, runs the converter only as `node converter/odrig.js`, and names no
  `show.json`, `mapping.json` or `.part` file it writes.

## Documents

`docs/emulator.md`: a section "Previewing one animation". `agent/getting-started.md`:
the command, in the place where the demo show is run. `shows/preview/show.json` is named
in the page of the shows if there is one. `AGENTS.md`: the seed leaves "What is coming".
`docs/decisions.md`: a line in the change log.

## Risks

- **Windows.** The command is written for both systems, as the emulator is, but this Mac
  cannot run it on Windows. The owner, or the contributor on Windows, runs the test on
  Windows; until then the definition of done is open there, and the owner is told.
- **A browser that cannot be opened.** `webbrowser` returns false; the command then says
  so and goes on: the address is printed.
