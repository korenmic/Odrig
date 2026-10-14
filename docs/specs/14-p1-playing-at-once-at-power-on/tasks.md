# Tasks: playing at once at power-on (seed 14)

Seeds 02 to 09 and 16 are implemented before these tasks start. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

Task 6 needs the board on USB, at `/dev/cu.usbmodem*`. No task needs the owner.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board and no phone, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`
  and `python3 -m unittest discover -s tests/app -t .`.
  Run them so that a failing suite stops the commit: no pipe hides its status.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- A command is read and answered in `core/src` only. No command is added, and no reply
  gains a member or an error code.
- The core allocates nothing after `odrig_core_begin`, no function of the core gets a
  local array above 256 bytes, and the core object stays at most 4,096 bytes.
- A page changes in the commit that changes the code it describes.
- In task 6: only one program uses the board at a time; every show put on the board has
  a brightness of 40 or less; `esp32-backup/` and `firmware/wled-16.0.1/` are never
  touched; no eFuse is written and the whole flash is never erased; the firmware is built
  only as the tool builds it; the task ends with the board running the firmware and the
  dim example show and says so in its commit message.
- Before a push, fetch: another contributor pushes to this repository.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. The start opens the files, the show plays, and the bodies are checked after
  - Set `"state": "in_progress"` in
    `project-seeds/14-p1-playing-at-once-at-power-on/state.json`.
  - `core/src/`: the start as the design's section has it; the check after the start;
    playing without the length; `busy` for `list`, `remove` and `upload begin`.
  - `tests/core/support.py`: the reference player's start, its count of the check's
    steps, and `busy`.
  - `tests/core/`: the start decodes no record; the check's order and pace and the
    refresh at which it is complete; `busy` before and the replies after; an animation
    played before its file was checked. The tests that send `list`, `remove` or an upload
    at the start let the check end first.
  - `docs/core.md`, `docs/commands.md`, `docs/show.md`: the start, the check, `busy`.
  - Prove it fails first: the test that reads the host's trace of a start, against the
    core as it is, fails: the start reads every file to its end.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 3.1, 3.2, 3.3, 3.6,
    4.1, 4.2, 4.3, 4.4, 4.5, 6.1, 6.3

- [ ] 2. Damaged bodies, late refreshes, a host that cannot change its storage, the memory
  - `tests/core/`: every invalid vector whose fault is in a body, found by the check and
    found by the player, with the reason of today and the refresh inside its bounds; a
    late refresh and a long gap with lengths not known, in the playlist and in a cycle,
    with `max_seconds`; a host whose storage cannot be changed; the memory test with its
    number.
  - `core/src/`: what these tests show to be wrong.
  - `docs/core.md`: the memory figures, and what a late refresh costs.
  - Prove it fails first: the test of a damaged second animation, against a check that
    never takes a step, fails: the show stays valid.
  - Requirements: 2.5, 3.4, 3.5, 5.1, 6.2

- [ ] 3. The emulator and the command tool
  - `tests/emulator/`: `busy` and then the list over each transport; record mode; a show
    with dense animations of 60 seconds in all reports the playlist in the first second
    after its start. The tests that list, remove or upload right after a start wait for
    the check.
  - `docs/emulator.md`: what a client sees after a start.
  - Prove it fails first: the test of the dense show, against the core of before task 1,
    fails: the first reply comes after the files were decoded.
  - Requirements: 7.1, 7.3

- [ ] 4. The firmware tool waits for the check
  - `firmware/fwtool/`: `install-show` and `install-firmware` wait until `list` is no
    `busy`, and read `status` again; `check-not-done`.
  - `tests/firmware/`: against the stand-in for a board: `busy` three times and then a
    list; a reason in `status` after the wait; `busy` beyond the time.
  - `docs/firmware.md`: the commands and the reason.
  - Prove it fails first: the test of a show that turns invalid during the check, against
    the tool as it is, fails: the tool reports the show as installed.
  - Requirements: 7.2

- [ ] 5. The app takes `busy` for what it is
  - `app/www/client.js`: a `busy` to `list` is no invalid show; the list is asked for
    again a second later.
  - `tests/app/`: a target that answers `busy` twice and then lists; the scenarios
    against the emulator still find their rows.
  - `docs/android-app.md`: what the show screen has right after the installation
    started.
  - Prove it fails first: the test of the target that answers `busy`, against the client
    as it is, fails: the rows come ten seconds later.
  - Requirements: 7.4

- [ ] 6. The firmware on the board
  - `python3 firmware/fw.py build`, `build --probe`, `flash`. `tests/board/`: the time
    from a restart to the first `status` with the demo show and with 9 MB of dense clips
    behind a small animation; `status` while the check runs, with the demo show and with
    a dense clip; the time the check takes. The board tests that list, remove or upload
    after a restart wait for the check.
  - Prove it fails first: the new test of the start with 9 MB, against the firmware that
    is on the board, fails: the first reply comes after 39 seconds.
  - `python3 firmware/fw.py test-board`; it passes. `docs/firmware.md`: what the board
    gave.
  - Requirements: 8.1, 8.2, 8.3, 6.4

- [ ] 7. The documents and the seed's state
  - `docs/decisions.md`: a line in the change log. `AGENTS.md`: the seed leaves "What is
    coming". Every page of Requirement 9 read once more against the code.
  - Run every suite that needs no board and no phone.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 9.1, 9.2
