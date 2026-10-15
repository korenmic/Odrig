# Tasks: one USB port for a computer or a stick (seed 21)

Seed 20's firmware is implemented before these tasks start. Where the real code differs
from what this spec's design relies on, follow the code and record the difference in
`docs/drifts.md`.

Task 1 needs neither the board nor the owner. Task 2 needs the board and the owner.

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
- No command is added, and no reply gains a member.
- On the board: one program at a time, brightness 40 or less, no eFuse, the flash never
  erased, the firmware built only as the tool builds it. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The firmware looks for a computer before it takes the port
  - Set `"state": "in_progress"` in
    `project-seeds/21-p1-one-usb-port-for-a-computer-or-a-stick/state.json`.
  - `firmware/usermod/odrig_drive.cpp`, `odrig_drive.h`, `odrig_usermod.cpp`: the wait,
    its setting, the look, the summary.
  - `tests/firmware/`: the checks of the design. `python3 firmware/fw.py build` builds.
  - `docs/firmware.md`.
  - Prove it fails first: the test that the drive's task looks for a computer before it
    installs the USB host, against the sources as they are, fails: `begin()` installs it.
  - Requirements: 1.1 to 1.5, 2.1 to 2.3, 3.1, 3.2, 5.1, 5.3

- [ ] 2. The board, the documents and the state
  - Flash the firmware; with the Mac on the port as the board starts, `status` answers on
    the port and on the serial chip's port, and the board's suite runs there. The owner
    starts the board without a computer on the port and reads WLED's information.
  - `tests/board/`: the port answers when the board was started with the Mac on it.
  - `docs/firmware.md` with what was seen; `docs/decisions.md` with a line in its change
    log; `AGENTS.md`: the seed leaves "What is coming"; `docs/firmware-prerequisites.md`.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 4.1, 5.2
