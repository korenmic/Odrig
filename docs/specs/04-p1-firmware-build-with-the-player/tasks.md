# Tasks: Firmware build with the player (seed 04)

Seeds 01, 02 and 03 are implemented before these tasks start: they use the package
`odrig`, the core in `core/`, `odrigctl` and the emulator. Where the real code differs from
what this spec's design relies on, follow the code and record the difference in
`docs/drifts.md`.

Tasks 2 to 8 need the board on USB. Task 10 needs the owner. The design's table "Assumed,
to be verified by an early task" names the task that settles each assumption: that task
writes what it found into `docs/firmware.md` under "Verified on the board", and into
`docs/drifts.md` when the finding changes the design.

Rules for every task:

- One task is one commit on `master`. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run
  `python3 firmware/fw.py test`; it passes. From task 2 on also run
  `python3 firmware/fw.py test-board`; it passes.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- Nothing is installed outside `build/firmware/`. Nothing fetched or built is staged.
- `esp32-backup/` is never written to, moved, deleted or staged. No eFuse is written. The
  whole flash is never erased.
- Every show put on the board has a brightness of 40 or less: one 60-LED strip is wired,
  on leg 1, fed from the board's 3.3 V pin.
- A task ends with the board running what the task says it leaves, and says so in its
  commit message.
- No file of `core/src` or `core/include` is changed, and none is copied.
- `animations/`, `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/` and `scratch/` hold
  untracked files that are not part of this work. Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The tool, the work folder and the toolchain
  - Create `firmware/fw.py`, `firmware/fwtool/__init__.py`, `cli.py`, `paths.py`, `env.py`,
    `toolchain.py` and `wled.py` (fetch, commit check, patches), `firmware/requirements.txt`
    and `firmware/patches/README.md`, with the subcommands `setup` and `test`.
  - Create `tests/firmware/__init__.py`, `support.py`, `test_paths.py`, `test_env.py`,
    `test_cli.py` and the parts of `test_wled.py` about the commit check and the patches,
    as the design lists them.
  - Run `python3 firmware/fw.py setup` for real. Before and after, list the entries of the
    home folder with their modification times; the two lists are the same. Record in
    `docs/firmware.md`: the Python version used, the versions `pio --version` and
    `node --version` print from the work folder, and whether assumptions A1 and A2 held.
    If one did not, use the fallback the design names and add the entry to
    `docs/drifts.md`. Write the exact version of `nodeenv` into
    `firmware/requirements.txt`.
  - Start `docs/firmware.md`: what the tool needs, the work folder, `setup` and `test`.
  - Set `"state": "in_progress"` in
    `project-seeds/04-p1-firmware-build-with-the-player/state.json`.
  - Prove it fails first, twice. With a temporary `tests/firmware/test_canary.py` holding
    one failing test, `fw.py test` fails naming `test_canary`. With `PIP_CACHE_DIR`
    temporarily removed from `env.py`, `test_env.py` fails naming that variable. Undo both.
  - The board is not touched.
  - Requirements: 1.2, 1.3, 2.1, 2.3, 2.4, 2.5, 6.1, 15.1, 15.4

- [x] 2. Spike: stock WLED built from source, flashed and restored
  - Create `firmware/fwtool/build.py`, `partitions.py`, `flasher.py`, `stock.py` and
    `board.py`, and `firmware/stock.sha256` with the three lines of the design. Add the
    subcommands `build --stock`, `flash` with `--image` and `--expect`, `restore-stock`
    with `--full` and `--stock-dir`, and `test-board`.
  - `tests/firmware/test_partitions.py`, `test_flasher.py`, `test_stock.py` and
    `test_board.py` as the design lists them; extend `test_cli.py` with `image-missing`,
    `checksum-mismatch` and `image-too-large`.
  - `tests/board/__init__.py`, which refuses to run without a board, `support.py` and
    `test_flash_restore.py`, for now with the stock-built image in place of the firmware.
  - Run `python3 firmware/fw.py build --stock`. Record: the time it took; the size of the
    image; the `-std=` flag in the compiler command of one file of `wled00`, taken from a
    verbose build (A5); the home folder listed before and after, which must be the same
    (A3).
  - On the board: read the partition table and compare it with fact R2 of the design.
    `flash --image build/firmware/out/stock-built.bin --expect wled`: the board answers
    `v` (A4, A6, A7). Then `restore-stock`: the board answers `v`. If the untracked
    proof-of-concept script `tools/wled.py` is there, `tools/wled.py status` reports the
    preset WLED played before the task.
  - Prove it fails first: with one byte of a copy of the stock image changed and
    `--stock-dir` pointing at the copy, `restore-stock` stops with `checksum-mismatch`
    before any esptool call; with a temporary address of `0x8000` in `flash`,
    `test_flasher.py` fails naming the address. Undo it.
  - The board is left with stock WLED, as it was.
  - Requirements: 1.5, 1.6, 1.7, 2.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4,
    6.2, 6.3, 6.4, 15.2, 16.6

- [x] 3. Spike: a usermod that owns the LEDs
  - Create `firmware/platformio_override.ini.in` with the two environments, without the
    lines for the core, and add the override file and the subcommands `build` and
    `build --probe` to the tool.
  - Create `firmware/usermod/library.json`, `odrig_usermod.cpp`, `odrig_leds.h`, `.cpp`
    (`apply`, `hold`, `matches`, `send`), `odrig_serial.h`, `.cpp` and `odrig_probe.h`,
    `.cpp`, and `odrig_pattern.h`, `.cpp`: a stand-in for the core that lists ten legs on
    pins 1 to 10 with 180 LEDs each and gives every LED a fixed colour of its own with no
    value above 40, new every 20 ms. In this task the port answers `#probe` in the probe
    build and drops everything else.
  - `tests/firmware/test_usermod_files.py` and the override part of `test_wled.py`.
  - `tests/board/test_probe.py`: ten working outputs on pins 1 to 10, four `rmt` and six
    `parallel`; each output's `crc` is the CRC-32 of the pattern's bytes for that leg;
    `sent` is 49 or more for 10 seconds in a row; `overwritten` stays 0 over 30 seconds;
    `realtime` is 1; nothing arrives on the port in 5 seconds without a command, and `v`
    gets no answer.
  - On the board: `build --probe`, then
    `flash --image build/firmware/out/odrig-probe.bin --expect probe`, and run the board
    suite. Record `loops`, `send_us`, `gap_ms`, `heap` and the outcome of assumptions A8
    to A12. If an assumption fails, use the fallback the design names, or stop and record
    what was found.
  - Write the eye check for the owner into `docs/firmware.md`: with this build the 60 LEDs
    on leg 1 show a steady dim ramp and nothing else.
  - Prove it fails first: with `hold()` temporarily not called from `setup()` and
    `loop()`, WLED runs its own effect, and `test_probe.py` fails with `realtime` 0 and
    `overwritten` above 0. Undo it.
  - The board is left with the probe build of this task and the storage it had.
  - Requirements: 1.1, 1.4, 1.7, 3.3, 8.4, 9.2, 9.3, 9.4, 10.1, 10.2, 11.2, 11.3

- [x] 4. Installing a show into the board's storage
  - Create `firmware/fwtool/storage.py` and the subcommands `install-show` with
    `--no-check` and `read-show`.
  - `tests/firmware/test_storage.py` as the design lists it; extend `test_flasher.py` with
    the calls of `install-show`.
  - Add to `tests/board/support.py` the helper that packs a show with its brightness
    replaced by 32 and refuses a folder with a brightness above 40.
  - `tests/board/test_install.py`, the parts that need no reply from the board: after
    `install-show` of the dim example show, `read-show` gives byte-identical files and no
    other file; WLED's `cfg.json` and `presets.json`, read from storage before and after,
    are unchanged; a second install of another show leaves no file of the first; a copy of
    storage from before is in the work folder.
  - On the board: with the probe build of task 3 running, `install-show` ends with
    `no-reply` after all its checks passed, because that build answers no `status`; the
    test expects exactly that. Record the time the command takes and assumption A13 as far
    as it can be seen here.
  - Prove it fails first: with the removal of `/odrig` temporarily left out of
    `storage.py`, the test of the second install fails naming the file that stayed. Undo
    it.
  - The board is left with the probe build of task 3 and the dim example show in `/odrig`.
  - Requirements: 14.2, 14.3, 14.4, 14.5, 14.6, 14.8, 15.5

- [x] 5. The core in the firmware: files, start and the port
  - Create `core/library.json`. Add the core's lines to
    `firmware/platformio_override.ini.in`.
  - Create `firmware/usermod/odrig_files.h`, `.cpp`. Start the core in `setup()`, add the
    lock, and make `odrig_serial` carry bytes between the port and the core. Remove
    `odrig_pattern`; until task 6 the outputs stay WLED's and dark.
  - Extend `test_usermod_files.py`: `core/library.json`; no file under `firmware/` has the
    name of a file of `core/src`; the override names the core by `symlink://`.
  - `tests/board/test_install.py`, the remaining parts: `install-show` prints the reply to
    `status`, exits with 0 for the dim example show, and `status` reports no reason and
    `playing` 3; for each of the four invalid folders of the design, installed with
    `--no-check`, the reason text equals the emulator's for the same folder, the tool
    exits with 1, and `play 1` gives `show-invalid`.
  - `tests/board/test_commands.py` as the design lists it.
  - Make `tests/board/test_flash_restore.py` use the firmware, as the design lists it, and
    make `install-show` of `test_install.py` expect the reply to `status`.
  - Reduce `tests/board/test_probe.py` to what holds in this task: `realtime` 1, the silent
    port, `start_ms` present, `error` equal to the reason in `status`.
  - On the board: flash, install the dim example show, run the board suite. Record
    `start_ms` and what the verbose build shows of the flags the core was compiled with.
  - Prove it fails first: with `brightness 20` replaced by `brightness 21` in the session
    sent to the emulator only, `test_commands.py` fails at the next `status`, which shows
    that the comparison sees a difference. Undo it.
  - The board is left with the firmware of this task and the dim example show.
  - Requirements: 3.1, 3.2, 3.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 11.1, 11.4, 11.5, 14.1,
    14.7, 16.3, 16.4

- [x] 6. Outputs from mapping.json and playback
  - Make `apply()` and `matches()` use the core's legs, and add step 5 of the design's
    `loop()`: ask the core when the outputs can take data and send every refresh.
  - `tests/board/test_probe.py` in full, as the design lists it.
  - `tests/board/test_fps.py` as the design lists it. The dense clip and the one-frame show
    are generated and packed in a temporary folder at brightness 32.
  - On the board: run the board suite with the probe build and with the firmware. Record
    `poll_us`, `send_us`, `gap_ms` and `loops` for the example show and for the dense clip,
    compressed and uncompressed. If `fps` stays below 49, record the measurements and what
    they point to, as risks 1 and 2 of the design describe, before changing anything.
  - Prove it fails first: with `BusManager::setBrightness(255)` temporarily left out of
    `send()` and WLED's brightness at its start value, the `crc` test fails for every
    output. Undo it.
  - The board is left with the firmware of this task and the dim example show.
  - Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.5, 9.6, 9.7, 10.1, 10.2, 10.3,
    16.2, 16.5

- [x] 7. Commands over HTTP, the access point and the report in WLED's information
  - Create `firmware/usermod/odrig_http.h`, `.cpp`. Add to the usermod `addToJsonInfo`,
    `onUpdateBegin`, and the step of `loop()` that keeps WLED's captive portal answering.
  - Add the subcommand `test-air`, and `tests/air/__init__.py`, `test_http.py` and
    `test_wled.py` as the design lists them.
  - Extend `test_usermod_files.py`: `server.on` is called once, for `/odrig`, in
    `odrig_http`; the usermod's sources name no Wi-Fi function of WLED.
  - On the board: build, flash, run the board suite. `test-air` cannot be run by an agent,
    because joining the board's network needs a person; say in the commit message that it
    was written and not run, unless this Mac is on that network.
  - The board is left with the firmware of this task and the dim example show.
  - Requirements: 9.8, 12.1, 12.2, 12.3, 12.4, 13.1, 13.2, 13.3, 13.4, 15.3

- [x] 8. Measurements and acceptance by program
  - `tests/board/test_measure.py` as the design lists it.
  - Run `python3 firmware/fw.py test-board` in full, twice in a row. It leaves the firmware
    and the dim example show on the board both times.
  - Write the measurements into `docs/firmware.md`: the start-up time of the core for the
    example show, for one dense clip and for 9 MB of dense clips; `fps`, the longest gap,
    the longest poll and the longest send for the example show and for the dense 60 x 30
    clip, compressed and uncompressed; the time of `install-show`.
  - Write into `docs/decisions.md`, under its open questions, what was measured for the
    decode speed on the board and for ten outputs in the firmware, and what stays open
    until ten legs are wired.
  - Add to `docs/drifts.md`, under "Seed 02: Start-up time when every animation is
    checked", the measured start-up times and whether the limit of two seconds named there
    was passed.
  - Requirements: 7.7, 15.6, 16.2, 16.3, 16.4, 16.5, 16.6, 17.3

- [x] 9. Documentation and final check by program
  - Complete `docs/firmware.md` as Requirement 17 lists, with the owner's checks written as
    numbered steps that name what to run and what must be seen. Add one sentence to
    `README.md` pointing to `docs/firmware.md`.
  - `tests/firmware/test_docs.py` as the design lists it.
  - Read the acceptance criteria of Requirements 1 to 15 once more and name, for each one a
    program can check, the test that checks it; add a test where one is missing.
  - Remove `build/firmware/` and run `python3 firmware/fw.py build` from nothing, with the
    home folder listed before and after: the lists are the same. Then `flash`,
    `install-show` of the dim example show, `fw.py test` and `fw.py test-board`.
  - The board is left with the firmware and the dim example show.
  - Requirements: 1.1, 1.6, 2.2, 16.8, 17.1, 17.2

- [ ] 10. The owner's checks
  - This task needs the owner: eyes on the LEDs, two legs wired, and a computer or phone
    joined to the board's Wi-Fi network. Without the owner, leave the task open and say so
    in the hand-over.
  - With the example show installed, at the brightness the owner chooses for the power
    supply in use, switch the board's power off and on and send no command: Hello world and
    the bouncing square alternate every 15 seconds, upright and readable.
  - With two legs wired, `python3 -m odrigctl --port PORT status` reports 49 or more in
    `fps`.
  - After power-on, find the board's Wi-Fi network, join it with this Mac, and run
    `python3 firmware/fw.py test-air --http 4.3.2.1`. With a phone joined, open
    `http://4.3.2.1/`: WLED's interface opens and its information shows the `odrig`
    entries.
  - Fix what fails, each fix with a test where a program can check it, and put the result
    of every step in the commit message.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/04-p1-firmware-build-with-the-player/state.json`.
  - Requirements: 8.3, 12.1, 12.2, 12.3, 12.4, 13.1, 13.2, 13.3, 13.4, 16.1, 16.2, 16.7,
    16.8
  - Open: the owner. Done by a program over USB on 2026-10-11, with one 60-LED strip on leg
    1 and the example show at brightness 32:
    - The show plays from the start with no command sent: after a restart `status` reports
      `"playing":3`, animation 1 for the first 15 seconds, animation 2 for the next 15, then
      1 again, and the outputs hold the bytes the emulator records for the same show
      (`tests/board/test_autostart.py`, `tests/board/test_probe.py`). The restart was a
      reset through USB, not the power switched off and on, and nobody looked at the LEDs.
    - `python3 -m odrigctl --port /dev/cu.usbmodem101 status` reports `"fps":50`, with leg 2
      not wired.
    - The probe build reports WLED's access point as up within seconds of its start. The Mac
      did not join the board's network: `test-air` was not run and no phone opened
      `http://4.3.2.1/`. The tests of `tests/air/test_http.py` pass against the emulator.
    - Nothing failed, so nothing was fixed in this task.
  - Left for the owner: the four steps of `docs/firmware.md`, "The owner's checks": eyes on
    the LEDs after a power cycle, `status` with two legs wired, `test-air` with this Mac on
    the board's network, and WLED's interface on a phone. The task is not ticked and the
    seed's state stays `in_progress`.
