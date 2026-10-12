# Tasks: Content commands (seed 07)

Seeds 02 to 05 are implemented before these tasks start: they change the core, the
emulator, the command tool and the firmware as seed 05 left them. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

Tasks 3, 7 and 8 need the board on USB, at `/dev/cu.usbmodem*`. Task 9 needs the owner.
The design's table "Assumed, to be verified on the board" names what task 3 settles: it
writes what it found into `docs/firmware.md` under "Verified on the board", and into
`docs/drifts.md` when the finding changes the design.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run the four suites that
  need no board, from the repository root; all four pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .` and `python3 firmware/fw.py test`.
  When `converter/` is there, also `npm test --prefix converter`.
- In tasks 3, 7 and 8 also run `python3 firmware/fw.py test-board`; it passes.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; each suite is selected by discovery.
- `docs/commands.md` and `docs/show.md` change in the commit that changes the code they
  describe. The texts are the design's; a task takes over the parts for what it adds.
- A command is read and answered in `core/src` only. No file of `emulator/` and none of
  `firmware/usermod/` looks into a command line or a reply beyond what it does today, and
  the tests that say so keep passing. The command tool sends lines and reads replies; it
  judges nothing about an id, a name or a file.
- The core allocates nothing after `odrig_core_begin`. No function of the core gets a
  local array above 256 bytes, and the core object stays at most 4,096 bytes.
- A change to a file of WLED exists only as a patch file in `firmware/patches/`. This seed
  needs none. Nothing is installed outside `build/firmware/`. Nothing fetched or built is
  staged.
- Only one program uses the board at a time. `esp32-backup/` is never written to, moved,
  deleted or staged. No eFuse is written. The whole flash is never erased.
- Every show put on the board has a brightness of 40 or less: one 60-LED strip is wired,
  on pin 1, fed from the board's 3.3 V pin. Nothing is judged by looking at the LEDs.
- No agent joins this Mac to the board's network or changes the Mac's network settings.
- A task that touches the board ends with the board running the firmware and the dim
  example show, with nothing of a test left in `/odrig`, and says so in its commit message.
- `animations/`, `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/`, `scratch/` and the
  stock image at the repository root hold untracked files that are not part of this work.
  Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. Lines of 2,048 characters and replies of 1,024 bytes
  - Set `"state": "in_progress"` in `project-seeds/07-p1-content-commands/state.json`.
  - `core/include/odrig_core.h`: the two limits. `core/src`: the line and the reply of the
    byte entry as two blocks taken at startup; the words of a line, up to five; `fits` in
    the reply. The five commands of today keep their replies.
  - `tests/core/host/host.cpp`: a reply may have 1,024 bytes.
  - `emulator/binding.py`, `httpd.py`, `engine.py`, `hub.py` and `web/app.js`, as the
    design's "The emulator" lists them for the limits and for the log: a body of 4,096
    bytes, the first 200 characters of a line and its `length`.
  - `docs/commands.md`, "Lines" and the row of `line-too-long`; `docs/core.md`, the two
    limits, "Command lines" and the two blocks in "Memory"; `docs/emulator.md`, the body
    limit and the `log` event.
  - Tests: `tests/core/test_commands.py`, `test_docs.py` and `test_memory.py`;
    `tests/emulator/test_binding.py`, `test_http.py`, `test_events.py` and
    `test_engine.py`, as the design's table lists them for the limits. The reference player
    gets the limit.
  - Prove it fails first: the test of a line of 2,048 characters, against the core as it
    is, fails with `line-too-long` in the reply.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 9.6, 13.5, 16.5

- [x] 2. The host interface for storage, and `space`
  - `core/include/odrig_core.h`: the seven members after `log`, as the design prints them.
    `core/src/storage.h`: the core's names. The command `space`.
  - `tests/core/host/host.cpp`: the seven functions on a folder and on the files of a
    batch session, the options of the design's "The test host", and its new checks.
    `tests/core/bench/bench.cpp` and every other host of the repository set the new
    members; `firmware/usermod/odrig_files.cpp` sets them to `NULL` until task 3.
  - `emulator/host.py`, `binding.py` and `app.py`: the seven functions on the folder, and
    `--storage`.
  - `docs/core.md`, "The host interface": the seven functions, their rules, a host without
    storage. `docs/commands.md`: `space`, `storage-error`. `docs/emulator.md`: `--storage`.
  - Tests: `tests/core/test_content.py` with `space`; `tests/core/test_build.py` and
    `test_docs.py` for the header; the guard tests for the new misuse checks, each shown to
    stop the test host; `tests/emulator/test_binding.py`, `test_start.py` for `--storage`,
    and `test_content.py` with `space` over serial and over HTTP.
  - Prove it fails first: `space`, against the core before this task, is answered with
    `unknown-command`.
  - Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 14.1, 14.2, 14.3, 14.5, 14.6, 14.7, 16.2, 16.3,
    16.4

- [ ] 3. Spike on the board: files written while the show plays
  - `firmware/usermod/odrig_files.cpp`: the seven functions on `/odrig`, as the design's
    table gives them, with every storage call timed. `odrig_usermod.cpp`,
    `odrig_serial.cpp` and `odrig_http.cpp`: the pacing; the port's queue of 4,096 bytes;
    a body of 4,096 bytes and a reply of 1,024, off the stack.
  - `firmware/usermod/odrig_probe.cpp`: `store` in the report, and the line `#store`.
  - `tests/firmware/test_usermod_files.py` as the design's table lists it. The test that
    nothing writes, creates or deletes a file gives way to one that says where it happens.
  - `tests/board/test_upload.py`, the spike's part, with the probe build and the dim
    example show playing: `#store 1000000` writes, renames, reads back and removes a file;
    the report's rate is 25 or more in every second meanwhile and 49 or more in each of
    the ten seconds after it; `space` before and after gives free bytes that differ by no
    more than 16,384; a line of 2,048 characters sent in one piece is answered with
    `unknown-command` and one of 2,049 with `line-too-long`, twenty times each; `read-show`
    afterwards gives the files that were installed.
  - On the board: `build --probe` and `build`; flash; the test; then the whole board
    suite. Write into `docs/firmware.md`, "Verified on the board", what was found for B1
    to B6: the times of the storage calls, shortest, mean and longest; the bytes a second;
    the rates; the time of `usedBytes` with storage nearly full, measured with a show of
    9 MB as seed 04 installed it.
  - If B3 does not hold: move the writes to a task of their own, record the design in
    `docs/drifts.md`, and make the test pass with it. If B1 or B2 does not hold: record
    it, stop, and say in the hand-over that the design of the core has to be looked at
    again before task 4.
  - Prove it fails first: with the pacing switched off, the test of the rate during
    `#store` fails with the rates it read. If it passes all the same, say so with the
    figures, and show instead that the test sees a low rate: with a wait of 30 ms added to
    every write and no pacing, it fails. Undo it.
  - The board is left with the firmware and the dim example show.
  - Requirements: 14.4, 17.1, 17.2, 17.3, 17.5, 17.6, 17.7, 17.8, 17.9

- [ ] 4. A show that changes: `list`, `remove`, and what a power cut leaves
  - `core/src/show.cpp`: tables with room; a show without items; `bytes` of every file;
    the brightness of the file kept. `core/src/content.cpp`: `list`, `remove`, the tables
    changed in place, `show.json` written. `core/src/storage.cpp`: the sequence of a
    removal, and the start with leftovers. `core/src/player.cpp`: positions that move.
    The chunk buffer as a block.
  - `odrig/show.py`: a show may have no items. If `converter/lib/show.js` is there, the
    same change in it, with its tests.
  - `docs/show.md`: the texts of the design. `docs/reasons.md`: `show-malformed`.
    `docs/commands.md`: `list`, `remove`, `busy`, `in-use`. `docs/core.md`: the tables,
    the files the core writes, the start.
  - `tests/core/support.py`: the reference player with storage, `list` and `remove`.
  - Tests: `tests/core/test_content.py`, `test_startup.py`, `test_json.py` and
    `test_memory.py` as the design's table lists them; `tests/core/test_powercut.py` for
    a removal: every `--cut-at`, every `--store-fails-at`; `tests/converter/` for the
    empty show and for reading back what the core wrote; `tests/emulator/test_content.py`
    with `list` and `remove` over both routes, and a removal that is there after the
    emulator was started again.
  - Prove it fails first: with `pending.txt` written after `show.json` was renamed, the
    power-cut test fails for the cut between the two: the folder holds a file no item
    names. Undo it.
  - Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.1, 4.2, 4.3, 4.4, 4.5,
    4.6, 4.7, 4.8, 4.9, 4.10, 9.4, 9.5, 10.1, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6,
    11.7, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 13.1, 13.2, 13.5, 16.1, 16.7

- [ ] 5. The upload
  - `core/src/upload.cpp`: `upload begin`, `data`, `end` and `cancel`; base64; the
    CRC-32; the 60 seconds; the check with its second source, decoders, pixel buffer and
    window, taken at startup when the host has storage. `core/src/file_source.cpp`: a
    source read with `read_at`. `core/src/storage.cpp`: the three sequences of an upload.
    `core/src/player.cpp`: a step of the check after a refresh; the item that starts
    again when its file was replaced.
  - `docs/commands.md`: "Uploading an animation" and the rest of the error codes with
    their order. `docs/core.md`: the upload, the check and its steps, the memory table
    with the measured figures.
  - `tests/core/support.py`: the reference player with the upload and the check counted
    in refreshes.
  - Tests: `tests/core/test_upload.py`; `tests/core/test_powercut.py` for the three kinds
    of upload and for an upload in each state; `tests/core/test_memory.py` with the total
    below 131,072; `tests/core/test_docs.py`: the error codes and the limits of
    `docs/commands.md` are those of the core; `tests/emulator/test_content.py` with an
    upload over each route and over the two mixed; `tests/emulator/test_record.py` with a
    script that uploads.
  - Prove it fails first, twice: with the step of the check taken in every request for a
    refresh, due or not, the test that counts the refreshes until `upload end` succeeds
    fails with the number it counted; and with the rename of `upload.part` made after
    `show.json` was renamed, the power-cut test fails for the cut between the two: the
    show names a file that is not there. Undo both.
  - Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7,
    7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1,
    9.2, 9.3, 10.2, 10.3, 10.5, 10.6, 10.7, 13.3, 13.4, 13.6, 13.7, 15.1, 15.2, 15.3,
    16.6, 19.1, 19.2, 19.3, 19.4

- [ ] 6. The command tool: `space`, `list`, `remove` and `upload`
  - `odrigctl/client.py`: the session. `odrigctl/content.py`: `list_all` and `upload`.
    `odrigctl/cli.py`: the four commands, the progress lines, the statuses.
  - `docs/emulator.md`, "The command tool": the four commands with an example each over
    the port and over HTTP, the progress line, the waiting on `busy`, the statuses.
  - `tests/emulator/test_tool.py` as the design's table lists it: an upload of Hello world
    made for the folder's canvas, over serial and over HTTP; the item in `list`; `play`
    and `status` naming it; the emulator stopped and started on the same folder; the item
    still in `list` and playing; `remove`; the folder holding what it held before. Each
    status; a file that cannot be read; a target that drops one reply; a file of another
    canvas, refused with `bad-file` and its reason; `no-space` with `--storage`.
  - Prove it fails first: with the tool sending `upload end` once and not again on
    `busy`, the upload test fails with status 1 and the reply `busy`. Undo it.
  - Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.11, 19.5

- [ ] 7. The board: every command over USB, and the measurements
  - `build` and `build --probe` with the core as it is now; flash the firmware.
  - `tests/board/test_upload.py`, the rest: with the dim example show, the command tool
    over the port uploads an animation made for the bench canvas; `list` shows it; `play`
    plays it, by what `status` reports; the board is restarted; `list` still shows it and
    it plays; `remove` removes it; `read-show` gives the folder as it was at the start.
    During an upload of a dense bench clip of 60 seconds, `status` is asked once a second
    through the same session: 25 or more in every full second; in each of the ten seconds
    after `upload end`, 49 or more. The speed, the time of the check and, with the probe
    build, the report's `store` are written to `build/firmware/out/upload.json`.
  - The replies of the session on the board equal those of the same session in an
    emulator started on the same folder with `--storage` set to the board's total, apart
    from `fps` and `free`.
  - `tests/air/test_upload.py`: the same session over HTTP. No agent can run it; say in
    the commit message that it was written, and run its session against the emulator.
  - `docs/firmware.md`: what the firmware writes and where; the pacing; the port's queue;
    the probe's `store`; "Measurements on the board" with the speed, the rates during and
    after an upload, and the longest storage call; the owner's check as numbered steps.
  - Prove it fails first: with the usermod's `read_at` always answering -1, the upload on
    the board ends with `storage-error` and the test fails naming that reply. Undo it,
    build and flash again.
  - The board is left with the firmware and the dim example show.
  - Requirements: 15.2, 17.4, 17.8, 17.9, 19.6, 19.7, 19.8, 20.5, 21.1, 21.2, 21.3, 21.4

- [ ] 8. The documents and the last check
  - Compare `docs/commands.md` and `docs/show.md` with the texts of the design, word for
    word, and settle every difference: in the document when the code is as the design
    says, in `docs/drifts.md` when a task found the design wrong.
  - `docs/decisions.md`, "Commands", and a line in its change log. `docs/core.md`,
    `docs/emulator.md` and `docs/firmware.md` read once more against Requirement 20.
  - Read every acceptance criterion of Requirements 1 to 21 once more and name, for each
    one a program can check, the test that checks it; add a test where one is missing.
  - Run the four suites that need no board, `npm test --prefix converter` when
    `converter/` is there, and `python3 firmware/fw.py test-board`. The last step of the
    board suite leaves the firmware and the bench show at brightness 32: confirm with
    `python -m odrigctl --port PORT list` that the show has the three items of the
    example show.
  - Requirements: 20.1, 20.2, 20.3, 20.4, 20.6, 20.7, 20.8, 21.4

- [ ] 9. The owner's check
  - This task needs the owner: a phone or a computer joined to the board's Wi-Fi network.
    Without the owner, leave the task open, say so in the hand-over, and write under this
    task what a program established over USB.
  - With a computer joined to the board's network, at the board's address there:
    `python -m odrigctl --http 4.3.2.1 upload 9 build/hello-bench.odrg` shows the
    percentage and the speed and ends with `{"ok":true}`; `list` shows item 9; `play 9`
    plays it; `remove 9` removes it. The steps of `docs/firmware.md` say how the file is
    made.
  - With this Mac joined and the board on USB, run
    `python3 firmware/fw.py test-air --http 4.3.2.1`: the suite ends with `OK`.
  - Fix what fails, each fix with a test where a program can check it, and put the result
    of every step, with the speed over Wi-Fi, in the commit message.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/07-p1-content-commands/state.json`.
  - Requirements: 21.5, 21.6
