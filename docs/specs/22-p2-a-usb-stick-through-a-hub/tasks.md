# Tasks: a USB stick through a hub (seed 22)

Seeds 20, 21 and 23 are implemented before these tasks start: the firmware with a drive,
the look for a computer, and the log. Where the real code differs from what this spec's
design relies on, follow the code and record the difference in `docs/drifts.md`.

Tasks 1 and 2 need neither the board nor the owner, and fetch nothing. Task 3 needs the
owner's approval of the downloads that the design lists, and fetches them. Task 4 needs
the board and the owner. Task 5 is done only when task 4 passed. Task 6 needs the board
and the owner. When the trial fails, at task 3 or 4, the seed stops there: its state
becomes `suspended`, and the owner is told what the trial showed.

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
- No command is added to the board, and no reply gains a member. No code names a maker or
  a model of hub.
- Nothing is fetched for the newer software before the owner has approved the list of
  downloads in the design. A further download the trial turns out to need is asked for
  first.
- On the board: one program at a time, brightness 40 or less, no eFuse, the flash never
  erased whole, the firmware built only as the tool builds it. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The tool builds a trial on the newer software
  - Set `"state": "in_progress"` in
    `project-seeds/22-p2-a-usb-stick-through-a-hub/state.json`.
  - `firmware/fwtool/paths.py`, `env.py`, `toolchain.py`, `build.py` and `cli.py`: the
    folder of the newer software, `child(newer=True)`, `newer_environment()`, the kinds
    `trial` and `trial-probe`, and `build --trial [--probe]`.
    `firmware/requirements-newer.txt`. `firmware/platformio_override.ini.in`: the
    environments `odrig_trial` and `odrig_trial_probe`. `tests/board/support.py`: the
    trial's images with `ODRIG_BOARD_IMAGES=trial`.
  - `tests/firmware/`: the checks of the design for the tool. No test fetches or builds.
  - `docs/firmware.md`: `build --trial`, the folder `newer/`, and what the trial build
    fetches.
  - Prove it fails first: the test that `build --trial` runs the newer software's
    PlatformIO on `odrig_trial`, against the tool as it is, fails: the option is a usage
    error.
  - Requirements: 1.1, 1.2, 1.3, 1.6, 7.1

- [x] 2. The log names every device that comes and goes
  - `firmware/usermod/odrig_drive.cpp`: the watcher keeps up to eight devices open, and
    the line of a device that goes names it as its line of coming did.
  - `tests/firmware/`: the watcher and its lines; no source of `firmware/usermod/`
    compares a maker's or a product's number. `python3 firmware/fw.py build` builds, and
    the probe build too, on the software known good, with what the work folder holds.
  - `docs/firmware.md`: the log's lines.
  - Prove it fails first: the test that the line of a device that goes names it, against
    the code as it is, fails: the line is `a device went`.
  - Requirements: 3.1, 3.2, 7.1

- [x] 3. The trial build, without the board
  - Only after the owner approved the list of downloads in the design.
  - `python3 firmware/fw.py build --trial` sets up the newer software. ESP-IDF 5.5.5's
    USB host library goes into `firmware/usb_host/`, with `README.md`, `LICENCE` and
    `library.json`; `odrig_trial` takes it and its flags. WLED's libraries are copied
    from `.pio/libdeps/odrig` to `.pio/libdeps/odrig_trial` before the first build.
  - The usermod: what the newer software needs, held by `ESP_IDF_VERSION_MAJOR`, and the
    hub's port in the line of a device that comes. A change WLED's source needs: a patch
    file of `firmware/patches/`, held the same way.
  - `build --trial` and `build --trial --probe` build, and `build` and `build --probe`
    still build on the software known good.
  - `tests/firmware/`: the library, its licence, `libArchive` false, the hub option among
    the flags, and no comparison of a maker's or a product's number in it.
  - `docs/firmware.md`: the trial build and whether it builds.
  - When it does not build, or needs more than the design allows: record what stopped it
    in `docs/firmware.md`, set the seed's state to `suspended`, and tell the owner.
  - Requirements: 1.4, 1.5, 1.6, 1.7, 2.1, 3.3, 4.2, 7.1

- [ ] 4. The trial on the board
  - The owner's board session, steps 1 to 4 of "The trial on the board" in the design:
    the last firmware known good kept in `build/firmware/out/known-good/`; the trial
    build flashed over the socket marked COM and checked without a hub, with
    `ODRIG_BOARD_IMAGES=trial python3 firmware/fw.py test-board` among the checks; the
    owner's hub and stick; a stick on an adapter, when the owner has one.
  - When anything is worse: the board flashed back to the last firmware known good at
    once, then the owner told; the seed's state `suspended`.
  - `docs/firmware.md`, "Verified on the board": what was seen, the hubs that were
    tried, and what is left on the board.
  - Requirements: 2.2, 2.3, 2.4, 2.5, 4.1, 5.1, 5.2, 5.3, 5.4, 5.5

- [ ] 5. The firmware and the fallback move to the newer software
  - Only after task 4 passed.
  - `firmware/platformio_override.ini.in`, `firmware/fwtool/`: `build` and
    `build --probe` on the newer software, `build --stock` on the software known good;
    the trial's environments, `build --trial` and `ODRIG_BOARD_IMAGES` go. The usermod
    loses what was held by version. `firmware/standalone/platformio.ini.in` on the newer
    software, with the same USB host library.
  - `tests/firmware/`: the checks of the design for the move. `python3 firmware/fw.py
    build`, `build --probe`, `build --stock` and `build --standalone` build.
  - `docs/firmware-additions.md`: the seed's line, and "Coming" loses it.
    `docs/firmware.md`: "What the tool needs", the work folder, the build.
  - Requirements: 6.1, 6.2, 6.3, 7.1

- [ ] 6. The owner's checks, the documents and the state
  - Flash the firmware of task 5. With the owner's hub fed by its power bank and the
    owner's stick in it, `list` shows the stick's animations after the installed ones,
    and `status` reports each in its turn at 20 refreshes a second or more; the owner
    sees them on the LEDs. Leave the board running the two-leg bench show, autostarting,
    at brightness 40 or less.
  - `docs/firmware.md`: the limits of the newer software that were found, and what the
    move changed. `docs/firmware-prerequisites.md`: lines 9, 16 and 18, and the tables of
    seeds. `AGENTS.md`: the seed leaves "What is coming". `docs/decisions.md`: a line in
    its change log.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 7.2, 7.3, 7.4
