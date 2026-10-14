# Tasks: animations from a USB drive (seed 20)

Seeds 02 to 09, 14 and 16 are implemented before these tasks start. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

Tasks 1 to 3 need neither the board nor a drive. Task 4 needs the board, the drive and the
owner's adapter. Task 5 needs them too, and the owner's yes for a download. Task 6 needs
the owner.

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
- No command is added, and no reply gains a member or an error code.
- The core allocates nothing after `odrig_core_begin`, no function of the core gets a
  local array above 256 bytes, and the core object stays at most 4,096 bytes.
- On the board: one program at a time, brightness 40 or less, no eFuse, the flash never
  erased, the firmware built only as the tool builds it. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. The core, the test host and the reference player
  - Set `"state": "in_progress"` in
    `project-seeds/20-p1-animations-from-a-usb-drive/state.json`.
  - `core/include/odrig_core.h`: the two members. `core/src/`: the drive's table, the
    plugging in and pulling out, the check of its files, the ids, the playlist, `play`,
    `status`, `list`, `remove`, `upload begin`, faults while playing.
  - `tests/core/host/`, `tests/core/support.py`: the drive of the test host and of the
    reference player. `tests/core/`: the tests of the design's list.
  - `docs/core.md`, `docs/commands.md`, `docs/show.md`.
  - Prove it fails first: the test that lists a drive's animations after the show's
    items, against the core as it is, fails: the list has the show's items only.
  - Requirements: 1.2, 1.3, 2.1 to 2.8, 3.1 to 3.4, 4.1 to 4.3, 5.1, 6.1, 6.4

- [ ] 2. The emulator
  - `emulator/`: `--drive DIR`, the drive of its host, the binding's two members, the
    header of the page.
  - `tests/emulator/`: the tests of the design's list. `docs/emulator.md`.
  - Prove it fails first: the test that starts the emulator with `--drive`, against the
    emulator as it is, fails: the option is a usage error.
  - Requirements: 6.2, 8.1

- [ ] 3. The app with a drive
  - `tests/app/`: an emulator with a drive; its animations are rows and play.
    `docs/android-app.md`: the drive's animations on the show screen.
  - Requirements: 2.5, 2.6

- [ ] 4. The trial on the board
  - The probe build gets the trial of the design; the tool builds it; the trial runs with
    the drive in the owner's adapter on the chip's own socket and the computer on the
    socket marked COM. The finding goes into `docs/firmware.md` and `docs/drifts.md`.
  - The board is left with the firmware and the bench show.
  - Requirements: 7.1

- [ ] 5. The firmware with the drive
  - Ask the owner for the download of the mass storage driver's sources, with the files,
    their source and their size, and wait for a yes.
  - `firmware/usermod/`: the USB host, the driver, FAT, the drive's list and number, and
    the host's two members. `tests/firmware/`, `tests/board/`. `docs/firmware.md`: how to
    prepare a drive, the adapter, the sockets, the figures.
  - `python3 firmware/fw.py build`, `flash`, the board tests with the drive.
  - Requirements: 1.1, 6.3, 7.2, 7.3, 7.5, 8.2

- [ ] 6. The owner's look, the documents and the state
  - The owner sees the drive's animations on the LEDs.
  - `docs/decisions.md` with a line in its change log; `AGENTS.md`: the seed leaves "What
    is coming".
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 7.4, 8.2
