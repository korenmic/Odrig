# Tasks: A playlist of everything by default (seed 16)

Seeds 02 to 08 and 11 are implemented before these tasks start. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

Task 7 needs the board on USB, at `/dev/cu.usbmodem*`. No task needs the owner.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .` and `python3 firmware/fw.py test`.
  Run them so that a failing suite stops the commit: no pipe hides its status.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- A command is read and answered in `core/src` only. No file of `emulator/`, `odrigctl/`
  or `firmware/usermod/` looks into a command line or a reply beyond what it does today.
- The core allocates nothing after `odrig_core_begin`, no function of the core gets a
  local array above 256 bytes, and the core object stays at most 4,096 bytes.
- A page changes in the commit that changes the code it describes.
- In task 7: only one program uses the board at a time; every show put on the board has
  a brightness of 40 or less; `esp32-backup/` and `firmware/wled-16.0.1/` are never
  touched; no eFuse is written and the whole flash is never erased; the firmware is built
  only as the tool builds it; the task ends with the board running the firmware and the
  dim example show and says so in its commit message.
- Before a push, fetch: another contributor pushes to this repository.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The show file: three optional members, in the page and in both converters
  - Set `"state": "in_progress"` in
    `project-seeds/16-p0-a-playlist-of-everything-by-default/state.json`.
  - `docs/show.md`: `min_seconds`, `repeat` and `max_seconds` in the tables of members,
    with their limits. What they mean for playback comes with task 3.
  - `odrig/show.py` and `converter/lib/show.js`: the members read and checked.
  - `tests/converter/` and `converter/tests/pack.test.js`: each member at and beside its
    limits, a fraction, a text, the two item members on a cycle, `pack` with all three.
  - Prove it fails first: the test of a show with `repeat`, against the readers as they
    are, fails: the show is refused as malformed.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6

- [x] 2. The core reads and writes the members
  - `core/src/show.cpp`, `core_state.h` and `content.cpp`: the members into the item
    table and the core; the file the core writes, in the design's order.
  - `tests/core/`: every show file of task 1's cases judged by the core as the reference
    judges it; the file written after a removal and after an upload keeps the members;
    the memory for 60 x 60 with 100 items, which is as before.
  - `docs/show.md`, "show.json after a change"; `docs/core.md`, the item table.
  - Prove it fails first: the test of the file written after a removal, with `repeat` in
    the show, fails against the writer as it is: the member is gone.
  - Requirements: 1.5, 6.8, 7.1, 7.2

- [x] 3. The playlist: the turn, the start and `status`
  - `core/src/player.cpp`, `player.h`, `core_state.h` and `commands.cpp`: the turn, the
    playlist with its fields, `player_play_all`, `player_start`, and `"all"` in `status`.
  - `tests/core/support.py`: the reference player's playlist, written from the design.
  - `tests/core/`: the turn for loops of 4, 10 and 45 seconds, `repeat`, `max_seconds`,
    `min_seconds`; three animations in order and around; late polls and a long gap; `off`
    and `on`; the three kinds of start; a show without an animation; `status`.
  - `docs/show.md`, "The turn of an animation" and "The playlist"; `docs/commands.md`,
    the values of `playing`; `docs/core.md`, the player.
  - Prove it fails first: the test of a show without `start`, against the core as it is,
    fails: nothing plays.
  - Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 5.1, 5.2,
    5.3, 5.4

- [x] 4. `play <id>` and `play all`
  - `core/src/commands.cpp`: `play` of an animation starts the playlist from it;
    `play all`. The reference player gets both.
  - `tests/core/`: a jump and what follows it; `play all` from a cycle and from the
    middle of the playlist; `play` of a cycle; every refusal of `play all`; the two
    entries of the core give the same replies.
  - `docs/commands.md`: the table, `play`, the error codes. `odrigctl/cli.py`: the usage
    text; a test that the tool sends `play all` as typed.
  - Prove it fails first: `play all`, against the core as it is, is answered with
    `bad-argument`.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.3

- [x] 5. The show changed while the playlist plays
  - `core/src/player.cpp` and `content.cpp`: an item added, an animation replaced, an
    item leaving, as the design gives them. The reference player gets the same.
  - `tests/core/`: an upload of a new item during the playlist, into an empty show, and
    onto the animation whose turn it is; the removal of the animation whose turn it is,
    of one before it and one after it, of the last one, and of the cycle that plays; an
    animation that a cycle lists is still `in-use`.
  - `docs/commands.md`, `remove` and uploading; `docs/show.md`, "Changing a show while
    it runs".
  - Prove it fails first: the removal of the animation whose turn it is, against the
    player as task 4 left it, fails: nothing plays afterwards.
  - Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7

- [x] 6. The emulator, the demo show and the pages that run it
  - `shows/demo-20/show.json`: two animation items, no cycle, no `start`.
  - `emulator/web/app.js`: `playlist` where `playing` is `"all"`.
  - `tests/emulator/`, `tests/walkthrough/` and the documents' tests that run the demo
    show: the playlist in place of the cycle. `docs/emulator.md`,
    `agent/getting-started.md`, `agent/animation-guide.md`, `agent/vocabulary.md`.
  - Prove it fails first: the emulator's test of the demo show, with the new show file
    and the test as it is, fails: `playing` is `"all"` where it expects the cycle's id.
  - Requirements: 8.1, 8.2, 8.4, 10.3

- [x] 7. The firmware on the board
  - `python3 firmware/fw.py build`, `flash`. `tests/board/`: the playlist from power-on
    with a show of two animations without `start`; `play all` and a `play <id>` of an
    animation in the session that is compared with the emulator.
  - Prove it fails first: the new board test against the firmware that is on the board
    fails: `playing` is `null`.
  - `python3 firmware/fw.py test-board`; it passes. `docs/firmware.md`: what the board
    gave, and the rate.
  - Requirements: 8.1, 9.1, 9.2, 9.3, 7.3

- [x] 8. The documents and the seed's state
  - `docs/decisions.md`: a line in the change log. `AGENTS.md`: seed 16 leaves "What is
    coming". Every page of Requirement 10 read once more against the code.
  - Run every suite that needs no board.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 10.1, 10.2, 10.3, 10.4
