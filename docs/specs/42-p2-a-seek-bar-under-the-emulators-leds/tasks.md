# Tasks: a seek bar under the emulator's LEDs (seed 42)

The tasks start from master at the seed's commit; seed 41 is not in it, and nothing here
relies on it. Everything is the emulator's: nothing in `core/`, `firmware/`, `app/` or
`odrigctl/` changes, and no command, reply member or error code is added. Task 5 needs
the owner.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit run the emulator's suite and the onboarding suite; task 3 runs the
  app's suite too; task 4 runs every suite that works on this computer.
- "Prove it fails first": watch the new test fail on the code before, and put what was
  seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.

- [x] 1. The position and the length
  - Set the seed's `state.json` to `in_progress`.
  - `emulator/host.py`: `on_open`, called with the name and the path after an open of an
    animation file. `emulator/engine.py`: the `Playback` record, the note of an open
    taken up after the poll, the start as the grid time, the turn's open and the loop's
    open, the status asked after a turn's open, the cycles from `list`, the `position`
    event at every change. `emulator/lengths.py` (new): the catalog tables, the
    converter's check in a thread when Node.js is on the path, the seen loop.
    `emulator/hub.py`: `position`, kept for new connections.
  - Tests: `tests/emulator/test_playback.py` (new) as the design says; `test_events.py`
    the `position` after the status on a new connection; `test_docs.py` five events.
  - `docs/emulator.md`: the fifth event, and the subsection "Seeking" for the position
    and the lengths (the seek itself comes with task 2); the `odrig` package named.
  - Prove it fails first: the hub has no `position`.
  - Requirements: 2.1 to 2.7, 4.1, 4.2, 5.2 (the status), 5.4, 6.1 (the events and the
    lengths)

- [x] 2. The seek and its route
  - `emulator/engine.py`: `seek`, the restart with its grid step, the move rounded down,
    the refusals, the log line with the transport `seek`, the reply.
    `emulator/httpd.py`: `POST /seek`, 411 and 405.
  - Tests: `tests/emulator/test_seek.py` (new): forward and backward against the
    reference player, the start at the grid, every refusal, `moved` on the grid, the
    route; `test_record.py`: record mode has no `position`.
  - `docs/emulator.md`: the route in the table, the seek in "Seeking", `seek` among the
    log's transports; `test_docs.py` for the transports.
  - Prove it fails first: the engine has no `seek`.
  - Requirements: 3.1 to 3.8, 4.3, 4.4, 5.2 (the transport), 5.3, 6.1 (the seeks)

- [x] 3. The bar on the page
  - `emulator/web/index.html`, `style.css`, `app.js`: the row between the drawing and
    the note, the drawing fitted to its host's room, the numbers from the frames and the
    `position` event, the drag, the press, the fetch of `seek`, the note of the clock's
    move, the `seek` chip, the reworded comment.
  - Tests: `tests/emulator/test_page_files.py`: the fetch `seek` allowed, `/odrig` still
    forbidden, no `<input>` or `<form>`, the fit and the observer pinned on the host;
    the shell syntax check as today; `tests/app/test_emulator_seek.py` (new) in Chrome
    with `--dump-dom`.
  - `docs/emulator.md`: the bullet of the bar in "The page" and the reworded rule;
    `test_docs.py` for the phrase.
  - Prove it fails first: the page has no `#seek`.
  - Requirements: 1.1 to 1.7, 4.5, 6.2, 6.3

- [x] 4. Every suite, the documents and the decision
  - Every suite that works on this computer passes: converter, Python library, core,
    emulator, app, firmware tool, onboarding.
  - `docs/decisions.md`: the change-log line; `docs/drifts.md`: the decisions taken
    beyond the seed; `docs/emulator.md` read through once for the whole.
  - Requirements: 5.1, 6.4

- [x] 6. A seek far into a long file shows its frame at once
  - The owner's look of 2026-10-27 found a seek into the middle of a long animation
    leaving the LEDs still for seconds: the core decodes a bounded part at one refresh.
    The engine moves its clock in strides of 400 ms with a refresh at each.
  - Tests: `tests/emulator/test_seek.py`, a file of random pixels whose seconds hold more
    bytes than the core's bound; the frame after the seek is the frame of the point.
  - `docs/emulator.md` says the move is made in strides; `docs/drifts.md` records why.
  - Prove it fails first: with one stride for the whole move the frame after the seek is
    the picture before.
  - Requirements: 3.2

- [ ] 5. The owner's look
  - The owner opens the emulator on a long animation, sees the bar move, drags it and
    sees the LEDs follow; then `state.json` becomes `completed` and the seed's line in
    "What is coming" says so, as the lines of built seeds do.
  - Requirements: the Definition of Done's second item
