# Tasks: The LED current limit as a setting (seed 15)

Seed 08 is implemented up to its owner's check: these tasks use `firmware/fwtool/wifi.py`,
`write_storage` and `store_settings` of `firmware/fwtool/cli.py`, and the board suite as
it left them. Where the real code differs from what this spec's design relies on, follow
the code and record the difference in `docs/drifts.md`.

Task 4 needs the board on USB, at `/dev/cu.usbmodem*`. No task needs the owner.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run
  `python3 firmware/fw.py test`; it passes. Task 4 also runs
  `python3 firmware/fw.py test-board`; it passes.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- No file of `firmware/usermod/` other than `odrig_probe.cpp` is changed, and no file of
  `core/`. The firmware is built only as the tool builds it.
- Only one program uses the board at a time. `esp32-backup/` and `firmware/wled-16.0.1/`
  are never touched. No eFuse is written. The whole flash is never erased.
- Every show put on the board has a brightness of 40 or less, whatever the limit is, and
  no command raises the brightness above 40. Nothing is judged by looking at the LEDs.
- A task that used the board ends with the board running the firmware and the dim
  example show, with the limit of the limit file and the name and the password of the
  settings file, and says so in its commit message.
- The network's password is never printed and never written anywhere new.
- Untracked files that are not part of this work are not moved, edited, deleted or
  staged.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The limit file and its checks
  - `firmware/limit.json` with 850. `LIMIT_SETTINGS` in `firmware/fwtool/paths.py`.
    `firmware/fwtool/limit.py` with `read` and the three reasons.
  - `tests/firmware/test_limit_settings.py`, the parts that call `limit.read`.
  - Set `"state": "in_progress"` in
    `project-seeds/15-p1-led-current-limit-as-a-setting/state.json`.
  - Prove it fails first: with the upper bound temporarily 65,536 in `limit.py`, the
    test of 65,536 fails. Undo it.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.6

- [x] 2. The limit in a storage image
  - `firmware/fwtool/wledfiles.py`, with what `wifi.py` has for one of WLED's settings
    files; `wifi.py` uses it. The tests of seed 08 pass unchanged.
  - `limit.apply` and `limit.stored`.
  - `tests/firmware/test_limit_storage.py`, as the design lists it.
  - Prove it fails first: with the tool temporarily writing a new `hw.led` object in
    place of the one the file has, the test on the bench board's files fails naming a
    member of `hw.led`. Undo it.
  - Requirements: 2.5, 2.7

- [x] 3. `set-limit`, `read-limit`, and the limit in `install-firmware`
  - `firmware/fwtool/cli.py`: the two commands; `install-firmware` reads both files
    first, makes one storage image with both, and prints four lines; `--limit FILE`.
  - `tests/firmware/test_limit_commands.py`; the refusals through the commands in
    `test_limit_settings.py`; `test_wifi_commands.py`, `test_wifi_settings.py`,
    `test_cli.py` and `test_docs.py` for what changed. `tests/board/test_wifi.py` expects
    four lines from `install-firmware`.
  - `docs/firmware.md`: the two commands in the list and their sections, `--limit`, the
    three reasons, the regions table.
  - Prove it fails first: with `install-firmware` temporarily not applying the limit,
    the test of its one storage write fails: storage does not hold the limit. Undo it.
  - Requirements: 1.5, 2.1, 2.2, 2.3, 2.4, 2.6, 3.1, 3.2, 4.1, 4.2, 7.1

- [x] 4. The limiter on the board
  - `firmware/usermod/odrig_probe.cpp`: `limited` counts only with a maximum above 0.
    `tests/firmware/test_usermod_files.py` for it. Build the firmware before and after
    and record that its SHA-256 is the same.
  - `tests/board/test_limit.py`, as the design lists it. `tests/board/support.py`:
    `leave_the_board()` applies the limit file when storage holds another value;
    `tests/board/__init__.py`: the last step asks storage for it.
  - Prove it fails first: with the probe build as it is before this task and the limit
    0, the first part of the board test fails: `limited` is above 0.
  - On the board: run the board suite. Record the time `set-limit` takes and what the
    reports gave with 0 and with 850.
  - `docs/firmware.md`: "The current limiter stays active", the probe table, and
    "Verified on the board".
  - Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4

- [x] 5. The documents and the seed's state
  - `docs/firmware.md`: the table of what a value means for the bench and for the
    installation, and that the value for the installation is the owner's.
    `docs/decisions.md`: a line in the change log. `AGENTS.md`: seed 15 leaves "What is
    coming"; `tests/onboarding/` for it.
  - Run every suite that needs no board.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 7.1, 7.2, 7.3
