# Tasks: Standalone firmware as a fallback (seed 12)

Seeds 02, 04, 05 and 07 are implemented before these tasks start. Seed 08 is implemented
before task 8: without the network's name and password in the stored settings the
standalone firmware hosts no network. Where the real code differs from what this spec's
design relies on, follow the code and record the difference in `docs/drifts.md`.

Tasks 1, 2 and 6 to 11 need the board on USB, at `/dev/cu.usbmodem*`. Task 12 needs the
owner. The design's table "Assumed, to be verified by task 1" names what task 1 settles.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly
  the files of the task.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .` and `python3 firmware/fw.py test`.
- In the tasks that need the board also run `python3 firmware/fw.py test-board`; it
  passes. From task 9 on also `python3 firmware/fw.py test-board --standalone`.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates
  or earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- Nothing under `core/` changes. A command is read and answered in `core/src` only.
- A change to a file of WLED exists only as a patch file in `firmware/patches/`. This
  seed needs none. Nothing is installed outside `build/firmware/`. Nothing fetched or
  built is staged.
- The firmware is built only as the tool builds it: no other optimisation level, and no
  use of the chip's USB debug unit.
- Only one program uses the board at a time. `esp32-backup/` and `firmware/wled-16.0.1/`
  are never written to, moved, deleted or staged. No eFuse is written. The whole flash is
  never erased.
- Every show put on the board has a brightness of 40 or less: one 60-LED strip is wired,
  on pin 1, fed from the board's 3.3 V pin. Nothing is judged by looking at the LEDs.
- No agent joins this Mac to the board's network or changes the Mac's network settings.
  The network's password is never printed and never written to a log.
- A task that touches the board ends with the board running the WLED-based firmware and
  the dim example show, with nothing of a test left in `/odrig`, and says so in its
  commit message.
- Any refresh rate from 20 to 50 a second is acceptable. No work is done to raise a rate
  inside that range.
- Untracked files that are not part of this work are not moved, edited, deleted or
  staged.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. Spike on the board: a bare program with the outputs, the storage and the port
  - Set `"state": "in_progress"` in
    `project-seeds/12-p2-standalone-firmware-as-a-fallback/state.json`.
  - `firmware/standalone/platformio.ini.in` and `firmware/fwtool/standalone.py`, as far
    as a build needs them; `build --standalone` and `flash --standalone` in
    `firmware/fwtool/cli.py` and `build.py`.
  - `firmware/standalone/src/main.cpp` as a trial: it mounts the storage without
    formatting, makes sixteen outputs on the parallel driver and four on RMT for the pins
    of `mapping/legs-20.json` with 180 LEDs each, sends a dim pattern 50 times a second,
    counts the pulses of each pin in turn, and answers `#probe` on the port with what it
    found: whether the mount worked and what `/odrig` holds, which outputs started, the
    pulses of each, the sends in the last second, and the free memory.
  - Read the probe report of the WLED-based probe build for the target mapping and write
    down which legs it gives to RMT.
  - `docs/firmware.md`, "Verified on the board": S1 to S6, each with what was found.
    `docs/drifts.md` where a finding changes the design.
  - Tests in `tests/firmware/`: the kinds and the image names; `--standalone --stock` is
    refused; the text of `platformio.ini` for a given repository path; the pins against
    WLED's `platformio.ini`.
  - Prove it fails first: the test of the pins, with one pin of `platformio.ini.in`
    changed, fails and names the pin.
  - Requirements: 1.1, 1.3, 1.4, 1.5, 1.6, 5.1, 8.4

- [ ] 2. The platform header: three files of the usermod compile for either firmware
  - `firmware/usermod/wled/odrig_platform.h`, `firmware/standalone/platform/odrig_platform.h`.
  - `odrig_files.cpp`, `odrig_serial.cpp` and `odrig_http.cpp` include `odrig_platform.h`
    and name the file system `ODRIG_FS`. `firmware/platformio_override.ini.in` gains the
    include path.
  - `firmware/standalone/src/shared_files.cpp`, `shared_serial.cpp` and `shared_http.cpp`.
    The trial program of task 1 is built with them.
  - Tests in `tests/firmware/`: the three files include `odrig_platform.h` and not
    `wled.h`; `firmware/standalone/` names `wled.h` nowhere.
  - Prove it fails first: the test of the includes, against the usermod as it is, fails
    for the three files.
  - On the board: build and flash the WLED-based firmware and run the whole board suite;
    it passes as before.
  - Requirements: 1.4, 1.6, 10.5

- [ ] 3. The stored settings
  - `firmware/standalone/src/settings.h` and `settings.cpp`, without Arduino.
  - The host program for the tests, and its build in `tests/firmware/`.
  - Tests: the cases the design's "Tests without the board" lists under "Settings".
  - Prove it fails first: a password of 7 characters, against a reader that checks no
    length, gives a network.
  - Requirements: 4.1, 4.3, 4.4, 6.1

- [ ] 4. The limiter
  - `firmware/standalone/src/limit.h` and `limit.cpp`, without Arduino; the host program
    gains it.
  - Tests: the reference in Python from R6 and R7 of the design, and the cases the design
    lists under "The limiter".
  - Prove it fails first: 3,600 LEDs at 850 against a limiter that only scales, without
    the lowest bit of R7, differs from the reference.
  - Requirements: 6.2, 6.3

- [ ] 5. The outputs
  - `firmware/standalone/src/outputs.h` and `outputs.cpp`: one output per leg, the
    drivers as task 1 wrote them down, the refusal of pins 19 and 20, `fill` and `show`.
  - Tests in `tests/firmware/`: the source tests that concern the outputs: no file of
    the program opens a file for writing; the order green, red, blue is stated once.
  - Requirements: 5.1, 5.2, 5.3, 5.4

- [ ] 6. The program: the start, the task, the loop, and commands over USB
  - `firmware/standalone/src/main.cpp` in its final form, without the network: the mount
    without formatting, the settings, the core, the legs, the outputs, the limiter
    between `fill` and `show`, the lock, the task on processor 0, the port.
  - On the board, with the dim example show installed: `status` answers; the session of
    commands of the board suite gives the replies of the emulator; the port is silent
    without a command.
  - Tests in `tests/firmware/`: `main.cpp` holds no network name and no password.
  - Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 1.7

- [ ] 7. The probe build
  - `firmware/usermod/odrig_pulses.h` and `odrig_pulses.cpp`, moved out of
    `odrig_probe.cpp` unchanged; `firmware/standalone/src/shared_pulses.cpp`.
  - `firmware/standalone/src/probe.h` and `probe.cpp`; `build --standalone --probe`.
  - The WLED-based probe report gains `"firmware":"wled"`.
  - On the board: the standalone probe build answers `#probe`; with the target mapping
    twenty outputs are `ok` and each gives 4,320 pulses; with the example show the `crc`
    of each output is that of its leg's bytes. The WLED-based probe build passes the
    board suite as before.
  - Tests in `tests/firmware/`: the members of the two reports as `docs/firmware.md`
    lists them.
  - Requirements: 1.2, 9.1, 9.2, 9.3, 9.4, 5.1, 5.2

- [ ] 8. The network and commands over HTTP
  - `firmware/standalone/src/network.h` and `network.cpp`; `main.cpp` starts it.
  - On the board: with the settings of seed 08 stored, the probe report gives `ap` 1;
    with the two settings files taken out of a copy of the storage and that copy
    installed, `ap` is 0 and `status` answers over USB. The stored settings are put back.
  - `tests/air/`: the tests that reach `POST /odrig` run against either firmware; the
    test of WLED's own pages is skipped in the standalone run. They are run by the owner
    in task 12, and here with an emulator in the place of the board's network, as today.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6

- [ ] 9. The board suite against the standalone firmware
  - `tests/board/support.py`: `ODRIG_BOARD_FIRMWARE`, the kinds, `running()`,
    `needs_wled`, `leave_the_board()`. `test-board --standalone` in the tool.
  - The tests that depend on WLED carry `needs_wled`, as the design lists them.
  - Prove it fails first: `test-board --standalone` before `needs_wled` is put on the
    test of WLED's handshake fails in that test.
  - On the board: `test-board --standalone` passes; `test-board` passes.
  - Requirements: 10.1, 10.2, 10.3, 10.4, 10.5

- [ ] 10. Switching, the rates and the limiter on the board
  - The three tests of the design's "The board suite" that run only in the standalone
    run: the switch, the rates, and the limiter against the WLED-based report.
  - Prove it fails first: the switch test, with the installed show changed by one byte
    between the two flashes, fails and names the file.
  - `build/firmware/out/standalone-rates.json` is written by the run.
  - Requirements: 6.4, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3

- [ ] 11. The documents and the last check
  - `docs/firmware.md`, `docs/decisions.md`, `docs/wifi.md`, `AGENTS.md` and
    `agent/README.md`, as the design's "Documents" says, with the measured rates and
    start times of both firmwares side by side.
  - Tests: `tests/firmware/test_docs.py` and `tests/onboarding/` for what changed.
  - Run every suite that needs no board, `test-board` and `test-board --standalone`.
  - The board is left on the WLED-based firmware with the dim example show.
  - Requirements: 11.1, 11.2, 11.3, 11.4, 12.1, 12.2

- [ ] 12. The owner's check
  - With the standalone firmware on the board and this Mac joined to the board's network:
    `python3 -m odrigctl --http 4.3.2.1 status`, and
    `python3 firmware/fw.py test-air --http 4.3.2.1 --standalone`.
  - What the LEDs of leg 1 show with the standalone firmware, by eye.
  - Then `python3 firmware/fw.py flash` puts the WLED-based firmware back, and
    `project-seeds/12-p2-standalone-firmware-as-a-fallback/state.json` is set to
    `completed`.
  - Requirements: 4.5, 12.1
