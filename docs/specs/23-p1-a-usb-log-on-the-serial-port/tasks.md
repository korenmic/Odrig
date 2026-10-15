# Tasks: a USB log on the serial port (seed 23)

Seeds 20 and 21 are implemented before these tasks start: the firmware with a drive, and
the look for a computer. Where the real code differs from what this spec's design relies
on, follow the code and record the difference in `docs/drifts.md`.

Tasks 1 and 2 need neither the board nor the owner. Task 3 needs the board and the owner.

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
  erased, the firmware built only as the tool builds it. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The log in the firmware
  - Set `"state": "in_progress"` in
    `project-seeds/23-p1-a-usb-log-on-the-serial-port/state.json`.
  - `firmware/usermod/odrig_log.h`, `odrig_log.cpp`; `odrig_uart.cpp` writes it;
    `odrig_drive.cpp` and `odrig_usermod.cpp` add its lines.
  - `tests/firmware/`: the checks of the design. `python3 firmware/fw.py build` builds,
    and the probe build too.
  - `docs/firmware.md`, `docs/commands.md`.
  - Prove it fails first: the test that the serial port's code writes the log's lines,
    against the sources as they are, fails: `odrig_log.h` does not exist.
  - Requirements: 1.1 to 1.6, 2.1 to 2.4, 4.1

- [ ] 2. The command tool shows the log
  - `odrigctl/cli.py`: `--log`.
  - `tests/emulator/`: the tests of the design. `docs/emulator.md`.
  - Prove it fails first: the test that `--log` prints the log's lines, against the tool
    as it is, fails: the option is a usage error.
  - Requirements: 3.1 to 3.3, 4.2

- [ ] 3. The board, the documents and the state
  - Flash the firmware; with the Mac on the serial port, the owner plugs in and pulls out
    the hub, an adapter and a stick, and `python -m odrigctl --port ... --log` shows their
    lines while `status` is answered. What was seen goes into `docs/firmware.md`.
  - `docs/decisions.md` with a line in its change log; `AGENTS.md`: the seed leaves "What
    is coming"; `docs/firmware-prerequisites.md`.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 4.3, 4.4
