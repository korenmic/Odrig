# Tasks: The board's Wi-Fi name and password (seed 08)

Seed 04 is implemented up to its owner's checks: these tasks use its tool
`firmware/fw.py`, the package `firmware/fwtool/`, the probe build and the suites in
`tests/firmware/`, `tests/board/` and `tests/air/`. Where the real code differs from what
this spec's design relies on, follow the code and record the difference in
`docs/drifts.md`.

Tasks 2, 4, 5 and 6 need the board on USB, at `/dev/cu.usbmodem*`. Task 7 needs the owner.
The design's table "Assumed, to be verified by an early task" names the task that settles
each assumption: that task writes what it found into `docs/firmware.md` under "Verified on
the board", and into `docs/drifts.md` when the finding changes the design.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run
  `python3 firmware/fw.py test`; it passes. A task that needs the board also runs
  `python3 firmware/fw.py test-board`; it passes.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- The password is the one the owner supplied. It comes with the hand-over of task 1 and is
  written into `firmware/wifi.json` and nowhere else: not into a test, a document, this
  file, `docs/drifts.md`, a commit message, a queue record or a hand-over. Nothing that is
  kept shows it: after a commit read `git show --stat`, not the content of that file.
- Only one program uses the board at a time: no two commands of the tool, no suite beside
  a command, and no other session on the port while a task works with the board.
- No agent joins this Mac to the board's network, changes the Mac's network settings, or
  types the password anywhere but into the settings file. Nobody presses a button on the
  board for a task.
- Every show put on the board has a brightness of 40 or less: one 60-LED strip is wired,
  on leg 1, fed from the board's 3.3 V pin.
- A task that used the board ends with the board running the firmware and the dim example
  show, from task 4 on with the name and the password of the settings file, and says so
  in its commit message.
- No file of `firmware/usermod/` other than `odrig_probe.cpp` is changed, and no file of
  `core/`. `flash`, `restore-stock`, `install-show` and `read-show` keep their behaviour.
- Nothing is installed outside `build/firmware/`. Nothing fetched or built is staged.
- `esp32-backup/` is never written to, moved, deleted or staged. No eFuse is written. The
  whole flash is never erased.
- `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/` and `scratch/` hold untracked files
  that are not part of this work. Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The settings file and its checks
  - Create `firmware/wifi.json` as the design gives it, with the name `odrig` and the
    owner's password from the hand-over. Without a password in the hand-over the task is
    blocked: record that and stop. Do not make one up.
  - Add `WIFI_SETTINGS` to `firmware/fwtool/paths.py`. Create `firmware/fwtool/wifi.py`
    with `Settings` and `read`, and the reasons `wifi-settings-missing`,
    `wifi-settings-malformed`, `wifi-name-invalid` and `wifi-password-invalid`.
  - `tests/firmware/test_wifi_settings.py`, the parts that call `wifi.read`: the lengths at
    and beside every limit; a tab, a letter outside ASCII and a zero character in either
    value; the missing file and every malformed form; that no detail quotes text of the
    file; that the settings file is accepted, names `odrig` and does not hold `wled1234`;
    that no other file `git ls-files` lists holds the password, with a failure that names
    the file only, and that the same search finds a word of `README.md` in `README.md`;
    that `repr` and `str` of `Settings` do not hold the password.
  - Set `"state": "in_progress"` in
    `project-seeds/08-p1-wifi-name-and-password/state.json`.
  - Prove it fails first: with the upper limit of the password temporarily 64 in
    `wifi.py`, the test of a password of 64 characters fails. Undo it.
  - The board is not touched.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.6, 5.2, 5.5, 5.6

- [x] 2. Spike: the probe build reports the access point's name and protection
  - Add `ap_name` and `ap_auth` to the report in `firmware/usermod/odrig_probe.cpp`, as the
    design gives them: read with `esp_wifi_get_config`, `null` while `ap` is 0, the name
    written as a valid JSON string.
  - Extend `tests/firmware/test_usermod_files.py`: `esp_wifi_` appears in the usermod only
    as `esp_wifi_get_config` and only in `odrig_probe.cpp`, and so do `ap_name` and
    `ap_auth`. The test that the usermod names no Wi-Fi function of WLED is not changed
    and passes.
  - Create `tests/board/test_wifi.py` with its first test, for the probe build: in every
    report taken from a restart until `ap` is 1, `ap_name` and `ap_auth` are `null` while
    `ap` is 0; with `ap` 1, `ap_name` is a text of 1 to 32 characters and `ap_auth` is 3.
  - Add the two members to the table and the example of the probe build's report in
    `docs/firmware.md`.
  - On the board: `build --probe`, flash it, run the board suite. Record what the board
    reports before any setting is applied, which assumption A1 expects to be `WLED-AP` and
    3. Build the firmware before and after the change in the same work folder and record
    whether its SHA-256 is the same. If A1 does not hold, record what was found in
    `docs/drifts.md` and take the name from the nearest thing the source offers, with the
    usermod still setting nothing.
  - Prove it fails first: with `ap_auth` temporarily left out of the report, the new board
    test fails naming the member. Undo it.
  - The board is left with the firmware and the dim example show, and with the name and the
    password it had.
  - Requirements: 4.7, 7.2, 7.3

- [x] 3. Editing WLED's stored settings in a storage image
  - Add `apply`, `holds` and `name_in` to `firmware/fwtool/wifi.py`, with the reason
    `wled-settings-malformed`, as the design's "Editing WLED's stored settings" gives them.
  - Add to `tests/firmware/support.py` two sets of files for a storage image: the files the
    board holds today, a `/cfg.json` with `hw` and `def` only and no `/wsec.json`; and the
    files WLED writes when it saves its settings, a `/cfg.json` with every member
    `serializeConfig()` writes, a `/wsec.json` with every member `serializeConfigSec()`
    writes, and a `/bkp.cfg.json`. The passwords in them are texts made for the tests.
  - `tests/firmware/test_wifi_storage.py` as the design lists it.
  - Prove it fails first: with the tool temporarily writing a new `ap` object in place of
    the one the file has, the test on WLED's saved files fails naming `chan`. Undo it.
  - The board is not touched.
  - Requirements: 3.8, 3.9, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6

- [x] 4. `set-wifi`: the settings on the board
  - In `firmware/fwtool/cli.py`, take the writing of a storage image out of
    `_install_show` into `write_storage`, as the design gives it, and add the subcommand
    `set-wifi` with `--port`, `--settings` and `--wait`. The tests of `install-show` pass
    unchanged.
  - `tests/firmware/test_wifi_commands.py`, the parts about `set-wifi`, and that nothing
    shows the password. Extend `test_wifi_settings.py`: every refusal through
    `set-wifi --settings` happens inside `support.untouched_board()`, with status 1 and one
    error line. Extend `test_cli.py` and `test_docs.py` for the new command.
  - `docs/firmware.md`: `set-wifi` in the list of commands, its section with an example and
    every option, the five new reasons, and `set-wifi` beside `install-show` in the table
    of regions.
  - `tests/board/test_wifi.py`, parts (1) to (3) of the design. `tests/board/support.py`:
    `leave_the_board()` also applies the settings file when the board's storage does not
    hold its settings.
  - Prove it fails first: before `set-wifi` has run on the board, the checks of part (2),
    run alone, fail: the report has `ap_name` `WLED-AP` where `odrig` is expected, and
    storage does not hold the settings.
  - On the board: run the board suite. Record the time `set-wifi` takes, what the report
    gave after each of the two runs, and the outcome of assumptions A2, A3 and A4. If one
    fails, record what was found, write the storage image from before, which is in the
    work folder, back with `write_storage`, and stop.
  - `docs/wifi.md`: replace "What our board does today" with "The board's network", as the
    design's table gives it, and take the name and the password out of the list of what is
    not decided. From this commit on the network `WLED-AP` is gone and the board hosts
    `odrig`; say so in the commit message, for whoever has a device that joined the old
    network.
  - The board is left with the firmware, the dim example show, and the name and the
    password of the settings file.
  - Requirements: 1.5, 1.6, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.10, 5.1, 5.3, 5.4,
    7.1, 7.4, 7.5, 8.1, 8.2, 8.5, 8.6, 9.4, 10.1, 10.2

- [ ] 5. `install-firmware`: a board from scratch
  - Add the subcommand `install-firmware` with `--port`, `--settings` and `--wait`, as the
    design gives it. `flash` and `restore-stock` are not changed.
  - `tests/firmware/test_wifi_commands.py`, the parts about `install-firmware`, and that
    `flash` still makes no call that reads or writes storage. Extend
    `test_wifi_settings.py`: every refusal through `install-firmware --settings` happens
    inside `support.untouched_board()`, also with a built image in place. Extend
    `test_cli.py` and `test_docs.py` for the new command.
  - `docs/firmware.md`: `install-firmware` in the list of commands, its section with an
    example and every option, its place in "From nothing to a playing board", in the table
    of regions, and one sentence under `flash` that it leaves the name and the password as
    storage has them.
  - `tests/board/test_wifi.py`, part (4) of the design, with the helper in
    `tests/board/support.py` that runs the command and remembers what the board runs.
  - Prove it fails first: with the settings step temporarily left out of
    `install-firmware`, the test with the stand-in fails: no call reads storage after the
    image was written. Undo it.
  - On the board: run the board suite. Record the time `install-firmware` takes.
  - The board is left with the firmware, the dim example show, and the name and the
    password of the settings file.
  - Requirements: 2.5, 4.8, 5.1, 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2

- [ ] 6. Documentation, the test for the owner's run, and the final check by program
  - Complete `docs/wifi.md` as Requirement 9 and the design's table list it: changing the
    name or the password, what else changes them, the owner's check as numbered steps with
    what must be seen, four devices at once as read in the source, and the list of what is
    not verified. Give what was read and not tried as read.
  - `docs/firmware.md`: one sentence under "Wi-Fi is WLED's" that names the settings file
    and `docs/wifi.md`; the network's name in the owner's checks of seed 04.
  - `tests/firmware/test_wifi_docs.py` as the design lists it.
  - `tests/air/test_wifi.py` as the design lists it. No agent can run it; say in the commit
    message that it was written and not run.
  - Read the acceptance criteria of Requirements 1 to 9 once more and name, for each one a
    program can check, the test that checks it; add a test where one is missing.
  - Prove it fails first: `test_wifi_docs.py`, run against `docs/wifi.md` as it is before
    this task, fails naming the section on changing the name or the password.
  - On the board: `python3 firmware/fw.py set-wifi` prints its three lines and writes
    nothing; then the board suite, twice in a row. It leaves the firmware, the dim example
    show and the settings of the settings file both times.
  - Requirements: 8.3, 8.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6

- [ ] 7. The owner's check
  - This task needs the owner: a phone or a computer joined to the board's Wi-Fi network.
    Without the owner, leave the task open, say so in the hand-over, and write under this
    task what a program established over USB.
  - Power the board. In the list of networks of a phone or a computer, `odrig` is there and
    `WLED-AP` is not.
  - Join `odrig` with the password of `firmware/wifi.json`: the device joins. WLED's old
    password, `wled1234`, is refused.
  - Send one command over HTTP. With a computer: `python -m odrigctl --http 4.3.2.1 status`
    prints a reply with `"ok":true`. With a phone: `POST http://4.3.2.1/odrig` with the
    body `status` gets the same reply.
  - With this Mac joined and the board on USB, run
    `python3 firmware/fw.py test-air --http 4.3.2.1`: the suite ends with `OK`.
  - Fix what fails, each fix with a test where a program can check it, and put the result
    of every step in the commit message, without the password.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/08-p1-wifi-name-and-password/state.json`.
  - Requirements: 7.1, 8.3, 10.3, 10.4
