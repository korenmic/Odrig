# Tasks: a bigger animation space without Wi-Fi updates (seed 24)

Seeds 04, 08, 15, 20, 21 and 23 are implemented before these tasks start. Where the real
code differs from what this spec's design relies on, follow the code and record the
difference in `docs/drifts.md`.

Tasks 1 to 5 need neither the board nor the owner. Task 6 needs the board and the owner.

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
- No command is added to the board, and no reply gains a member.
- On the board: one program at a time, brightness 40 or less, no eFuse, the flash never
  erased whole, the bootloader never changed but by `restore-stock --full`, the firmware
  built only as the tool builds it. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The tool knows the two layouts
  - Set `"state": "in_progress"` in
    `project-seeds/24-p1-a-bigger-animation-space-without-wifi-updates/state.json`.
  - `firmware/fwtool/partitions.py`: `WLED`, `BIGGER`, `table`, `layout_of`.
    `firmware/fwtool/cli.py`: the layout line of `flash`, `install-firmware`,
    `install-show`, `set-wifi`, `set-limit`, `read-limit` and `read-show`.
  - `tests/firmware/`: the tables, `layout_of`, and the commands on a stand-in board of
    each layout. `docs/firmware.md`: the layouts, the layout line.
  - Prove it fails first: the test that `install-show` on a stand-in board of the bigger
    layout prints its layout line, against the tool as it is, fails: no line names the
    layout.
  - Requirements: 1.1, 1.2, 3.1, 3.2, 7.1

- [x] 2. The move and the way back
  - `firmware/fwtool/cli.py`: `big-storage`; `restore-stock --full` on the bigger layout.
    `firmware/fwtool/storage.py`: the settings, and a storage made with them at a size.
    `firmware/fwtool/flasher.py`: the regions of the move.
  - `tests/firmware/`: the tests of the design for the move and the way back.
    `docs/firmware.md`: the commands, the regions, rolling back.
  - Prove it fails first: the test that `big-storage` moves a stand-in board, against the
    tool as it is, fails: the command is a usage error.
  - Requirements: 2.1 to 2.5, 4.1 to 4.3, 7.1

- [x] 3. The firmware refuses an update over Wi-Fi without a second slot
  - `firmware/usermod/odrig_update.h`, `odrig_update.cpp`; `odrig_usermod.cpp` starts it.
  - `tests/firmware/`: the checks of the design. `python3 firmware/fw.py build` builds,
    and the probe build too. `docs/firmware.md`: the refused update, "What the firmware
    changes in WLED".
  - Prove it fails first: the test that the usermod answers `POST /update` on a board
    without a second slot, against the sources as they are, fails: `odrig_update.cpp`
    does not exist.
  - Requirements: 1.3, 5.1 to 5.3

- [ ] 4. The emulator's default storage
  - `emulator/host.py`, `tests/core/host/host.cpp` and the tests that state the default;
    `tests/board/`: the total that `space` reports is the board's partition size.
    `docs/emulator.md`, `docs/core.md`, `docs/commands.md`.
  - Prove it fails first: the test that the emulator's default storage is 13,500,416
    bytes, against the emulator as it is, fails: it is 10,354,688.
  - Requirements: 3.3, 6.1

- [ ] 5. The documents
  - `docs/firmware.md`: why the layout, what was given up, how a board is moved and moved
    back. `docs/decisions.md`: "What fits" and a line in its change log.
    `docs/format.md`, "What fits". `docs/firmware-prerequisites.md`.
  - Requirements: 7.2, 7.3

- [ ] 6. The board, the owner's show and the state
  - With the owner: `big-storage` on the board; the settings as they were, and `status`
    on the serial chip's port and over Wi-Fi. The owner's show of 113 animations of
    2026-10-15 installed whole, and `list` names all of them. An update over Wi-Fi on
    WLED's page refused with its message, the board playing on. `restore-stock --full`,
    then `install-firmware` and `big-storage` again. The board left playing with its
    settings, at a brightness of 40 or less. What was seen goes into `docs/firmware.md`.
  - `AGENTS.md`: the seed leaves "What is coming". Set the seed's `state.json` to
    `completed`, with `completedAt`.
  - Requirements: 2.5, 3.3, 5.2, 7.4
