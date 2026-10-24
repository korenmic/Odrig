# Tasks: a microSD card as the external storage (seed 38)

Seeds 20, 21, 23 and 24 are implemented before these tasks start, and the newer software
of seed 22's trial is built and fetched. Where the real code differs from what this spec's
design relies on, follow the code and record the difference in `docs/drifts.md`.

Tasks 1 to 5 are done: they are Codex's commits of 2026-10-22 and 2026-10-23 on the
branch `codex/microsd-storage`, made before this seed existed, and each is ticked here
with its commit named. Task 6 is done in the commit that merges `master` into the seed's
branch. Task 7 needs neither the board nor the owner. Tasks 8 and 9 need the board and
the owner, and task 9 the owner's answer to the seed's question 7. Task 10 needs the
owner's answer to question 8. Task 11 closes the seed.

Two more commits of the branch, `40cc3a9` and `533ceb8`, add the line test animations
`lines-test` and `rainbow-lines-01` to `-20` in `test-animations/` with their generators;
they are content for the owner's look at the strips, outside this seed's requirements,
and are named here so that the branch's history is accounted for.

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
- No command is added to the board, and no reply gains a member. The card is never
  written or formatted. No pin, clock or wiring changes without the owner.
- The board is touched only in a session with the owner: one program at a time,
  brightness 40 or less, no eFuse, the flash never erased whole, the firmware built only
  as the tool builds it, flashed with `flash --image build/firmware/out/odrig-microsd.bin`
  and never with `flash` alone, which writes the stick's build. Nothing is soldered.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked. The
  seed's questions 7 and 8 are the owner's and are not decided here.

- [x] 1. The card's code and the build variant — `d5bcef6`, 2026-10-22
  - `firmware/usermod/odrig_drive.cpp`: the card's backend behind `ODRIG_DRIVE_SD_SPI`:
    `cardBus` on the chip's second SPI unit, `mountCard()`, `sdStep()` once a second with
    the sector read, `readFailed()`, the lines of the kind `sd`, the summary texts; the
    stick's backend unchanged without the flag. `firmware/usermod/odrig_sd_config.h`: the
    defaults, every pin -1, 4 MHz, `/sd`, and the checks. `firmware/usermod/odrig_drive.h`.
  - `firmware/fwtool/build.py`: the kind `microsd` in `ON_NEWER`. `firmware/fwtool/cli.py`:
    `build --microsd` and the refused combinations. `firmware/platformio_override.ini.in`:
    the environment `odrig_microsd` extending `odrig_trial`, with the flag and no pins yet.
  - `tests/firmware/test_microsd_build.py`, `tests/firmware/test_usermod_sd.py`: the tool,
    and the card's code compiled on the Mac with a stand-in card and task scheduler.
  - `docs/microsd.md`, `docs/firmware.md`, `docs/firmware-additions.md`,
    `docs/decisions.md`: the owner's decision of 2026-10-21.
  - Proved failing first, as the commit records: the build flag was unrecognised, the
    card's compilation still wanted the USB unit's header, and the test of a failed SPI
    start failed its `SD.mounts == 0` assertion because `SD.begin` was still called.
    Firmware suite 544 OK.
  - Requirements: 1.1, 1.2, 1.3, 2.1 to 2.5, 2.7, 3.1, 3.2, 4.1 to 4.4, 4.6, 5.1 to 5.3,
    6.3, 8.1

- [x] 2. The pins, GPIO39 to GPIO42 — `551a52b`, 2026-10-22
  - `firmware/platformio_override.ini.in`: `ODRIG_SD_SCK=39`, `ODRIG_SD_MISO=40`,
    `ODRIG_SD_MOSI=41`, `ODRIG_SD_CS=42` in `odrig_microsd` only.
  - `tests/firmware/test_microsd_build.py`: the pins as agreed, none of them a pin of
    `mapping/legs-20.json` or of USB. `docs/decisions.md`: the owner's decision of
    2026-10-22; `docs/microsd.md`, `docs/firmware.md`, `docs/firmware-additions.md`.
  - Proved failing first, as the commit records: both tests of the pins failed because
    the four flags were absent. Firmware suite 545 OK.
  - Requirements: 6.1, 6.2, 6.4

- [x] 3. The image and its checks — `5b4b4e9` and `b1fbec5`, 2026-10-22
  - `python3 firmware/fw.py build --microsd` built `odrig-microsd.bin`, 1,765,808 bytes,
    within the application partition; the checksum, the card's symbols in the image, the
    mount path `/sd/odrig`, the four pins and the 4 MHz clock checked; 545 firmware tests
    and 82 tests of the core's drive and playlist passed. No board was touched.
  - `docs/microsd-preflight/build.md`, `verification.md`, `tasks.md`.
  - Requirements: 1.2, 1.4, 1.5, 8.2

- [x] 4. The first trial on the board — `4217f91`, 2026-10-22
  - The owner reported the wiring complete and authorised the flash. `flash --image`
    through the chip's own socket; the bigger layout and the installed show kept. The
    card mounted, its first two files listed as 60001 and 60002, `play 60001` at 41
    refreshes a second. Then listed entries disappeared and were found again, in one
    session, at 4 MHz, 1 MHz and 400 kHz alike; the 4 MHz image was rebuilt with the same
    hash and flashed back, SHA-256
    `fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`. The board was left
    on it, playing, at brightness 32.
  - `docs/microsd-preflight/board-trial.md`, `docs/microsd.md`.
  - Requirements: 9.1 in part, 9.2 in part

- [x] 5. The second look, through the socket marked COM — `d7f0120`, 2026-10-23
  - Both USB sockets of the board on the Mac, the commands through the socket marked COM,
    the firmware unchanged. All 122 animations of the owner's card listed as 60001 to
    60122 after the installed one, 123 items; 161 samples over fifteen minutes lost no
    entry. Four of them, the largest and the last among them, played past a loop boundary
    at 26 to 50 refreshes a second; `play all` restored, the playlist went on to 60002
    by itself. The board was left playing at brightness 32.
  - `docs/microsd-preflight/uart-verification.md`, `hardware-tasks.md`, `docs/microsd.md`,
    `docs/firmware.md`, `docs/firmware-additions.md`.
  - Requirements: 7.1, 9.2 in part

- [x] 6. The card's free and total space
  - In the commit that merges `origin/master` into `seed-38-microsd-card`, since seed 29's
    `drive_space` comes with `master` and the stick's `driveSpace()` names what the card's
    build leaves out.
  - `firmware/usermod/odrig_drive.cpp`: `driveSpace()` for the card from `SD.totalBytes()`
    and `SD.usedBytes()`, under the guard, -1 unless the card is mounted and the number is
    its current one or when the total is 0; the stick's behind `#ifndef ODRIG_DRIVE_SD_SPI`.
  - `tests/firmware/test_usermod_sd.py`: the stand-in card's `totalBytes()` and
    `usedBytes()`, and the numbers while mounted, -1 for another number, for an unmounted
    card and for a total of 0.
  - Prove it fails first: the test, against the merged sources as they are, fails: the
    card's build does not compile, `mounted` and `msc_host_vfs_space` undeclared.
  - Requirements: 2.6, 8.1

- [x] 7. The documents in the house style
  - `docs/microsd.md`: the card's page as the design's "The documents" has it, with the
    two session records of `docs/microsd-preflight/` folded in; then
    `docs/microsd-preflight/` goes, and every link to it.
  - `docs/firmware.md`: the external storage, the stick in `build` and the card in
    `build --microsd`; one sentence where the newer software is called "the trial"; the
    `sd` lines in "The log"; the two sessions in "Verified on the board"; the paragraph on
    `build --microsd`. `docs/show.md`: one sentence that on the board the drive is a stick
    or a card.
  - `docs/firmware-additions.md`: the card's line in the house style, with seed 12's
    column; "Coming" loses seed 22. `docs/firmware-prerequisites.md`: lines 9 and 16,
    and "Seeds not finished".
  - `tests/onboarding` and `tests/firmware` pass with the pages as changed.
  - Requirements: 1.5, 8.3, 8.4

- [ ] 8. The board session: the merged image, plugging in and pulling out
  - With the owner, steps 1 to 3 of the design's "The board session": `build --microsd`
    on the merged branch, its hash; `flash --image` through the socket marked COM, the
    show and the settings kept; the card's animations listed after the installed ones
    over the socket marked COM, over the chip's own socket and over Wi-Fi; `status` at 20
    to 50 while the largest file plays; the card pulled out while one of its animations
    plays and put back, with the times, the log's lines and any pause of the LEDs.
  - `docs/microsd.md` and `docs/firmware.md`, "Verified on the board": what was seen and
    what is left on the board. A fault in the card's code that the session shows is
    mended here, with its test seen failing first.
  - Requirements: 1.5, 3.1 to 3.3, 4.1 to 4.6, 5.1, 5.2, 7.1, 9.1 to 9.3, 9.6

- [ ] 9. The dropouts, the owner's look, and the board on its own
  - Only after the owner answers the seed's question 7.
  - With the owner, steps 4 and 5 of the design's "The board session": the cable
    arrangement of the event for fifteen minutes with `status`, `list` and the log
    sampled; a list that shrinks recorded before anything is changed. The owner sees the
    card's animations on the LEDs, and sees them while the board runs with no computer,
    powered as at the event, with the app's list on a phone.
  - `docs/microsd.md`, `docs/firmware.md`: what was seen. A cause in the card's code or
    its clock is mended here; a cause in the hardware is the owner's and is proposed as a
    new seed, in words.
  - Requirements: 9.4, 9.5, 9.6

- [ ] 10. The firmware that `build` makes
  - Only after the owner answers the seed's question 8.
  - When the answer is yes: `firmware/fwtool/` and `firmware/platformio_override.ini.in`:
    `build` and `build --probe` make the card's firmware and its probe build on the newer
    software, the stick's build stays behind an option, the environments `odrig_trial`
    and `odrig_trial_probe`, `build --trial` and `ODRIG_BOARD_IMAGES=trial` go;
    `tests/firmware/`, `tests/board/support.py`; `docs/firmware.md`, "What the tool
    needs", the work folder, the builds; the fallback's spec,
    `docs/specs/12-p2-standalone-firmware-as-a-fallback/`, takes the card's line; the
    board's suite on the card's firmware in a session.
  - When the answer is no: nothing changes; the answer goes into the seed's "The Owner's
    Answers" and this task is ticked with it.
  - Requirements: 10.1, 10.2

- [ ] 11. The state and the change log
  - `docs/decisions.md`: a line in the change log, what the board runs and what the
    sessions showed. `docs/firmware-prerequisites.md`: the final states of lines 9 and
    16. `AGENTS.md`: the seed leaves "What is coming". Set the seed's `state.json` to
    `completed`, with `completedAt`; what stays open, if anything, is told to the owner in
    words.
  - Requirements: 8.3
