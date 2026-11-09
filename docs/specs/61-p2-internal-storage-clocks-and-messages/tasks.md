# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first, and the failure goes into the commit message. The branch is
`seed-61-internal-clocks`, made from `all-unmerged-seeds` (pull request #63), which holds
seed 74's folders of the board's own storage and seeds 66 and 67's Clocks-only browsing.
Before a commit: `python core/build.py shared`, and the suites the task names with
`python tests/run.py --suites ...`.

- [x] 1. Play the board's own clocks and messages in both modes, the SD card's copy first
  - `FileInfo.clock` and `FileInfo.copy` in the spare bits of byte 38 and
    `Core.clocks_internal_id` in the end padding, the class and the id set by
    `folders_derive` and cleared on its early returns and by `folders_start`;
    `Core.clock_storage_internal` in the 8th bit of the byte of `turn_manual`, read as 0
    here. Measure `sizeof(Core)` (3,792 / 3,592), `FileInfo` (48) and `Upload` (72) again
    with g++ and the xtensa compiler; the memory suites pass unedited.
  - `pick` over E + I places with the marks of copies in `FileInfo.copy`, written in the
    draw that reads them, `breaks_has_face`, the pass-over in `lowest_playing` while the
    clocks are on, and every Only entry point of the design's table:
    `breaks_position_allowed`, `play_only` (an internal item, the internal Clocks folder,
    an internal folder inside or outside), `player_jump`, `player_only_refresh`,
    `player_first_in_playlist`, `breaks_only_state` (today's states without an internal
    Clocks folder), and `player_inclusion_changed`, `player_internal_inclusion_changed` and
    `player_file_failed` refreshing Only; `status`'s `playing`, `playlist` and
    `clock_only.folder`.
  - Tests: a new `tests/core/test_internal_clocks.py` with recognition, Between, Only, Only
    and Ignore, the LEDs' `off`, and copies under `SD card` with a show of more than 132
    items and each copy's brightness (the design's list), and a flat show's replies byte
    for byte.
  - Documents: `docs/core.md` ("Clocks", "Internal folders"; the memory figures stay),
    `docs/show.md`, `docs/commands.md` (the Only boundary, `clock_only`, the copies);
    `docs/drifts.md` for what the task decides.
  - Suites: `core`, `emulator`, `firmware-host`.
  - Requirements: 1.1–1.5, 2.1–2.5, 3.1–3.6, 4.1–4.5 with `SD card`, 8.1–8.2.

- [x] 2. Choose the preferred storage with `clocks storage sd|internal`
  - `breaks_command` with the storage setting, its refusals in the message line's order, a
    no-op that writes nothing, both bags drawn again at their next draw; `clocks.txt`
    version 3 written only for `Internal storage`, versions 1, 2 and 3 read strictly;
    `breaks_start` setting `SD card`; the draw's rule for `Internal storage`; `status`'s
    `clock_storage` after `clock_mode`.
  - The command tool's `clocks storage sd|internal`, its usage and help.
  - Tests: core (every refusal in order, the no-op, versions 1, 2 and 3 and a version 3
    without its line, a failed write, a version 3 read by `breaks_poll` after an
    unreadable start, a change during a message's turn, copies under both preferences with
    each kind of ineligible preferred copy, the shapes of
    `test_the_longest_reply_to_status_fits_1024_bytes` with `clock_storage`, 1,019 bytes at
    most, and its new shape of Only with `clock_error`); the tests that hold the exact
    bytes or the order of `status`'s members (`test_status.py`, `test_commands.py`,
    `test_folders.py`, `test_clocks.py`, `test_internal_folders.py`) and the reference
    player of `tests/core/support.py` with the member; emulator (the line over the serial
    port, TCP and HTTP, the choice kept across a restart); the command tool; firmware (the
    firmware tool keeps a `clocks.txt` of version 3 through a show install).
  - Documents: `docs/commands.md` (the table, the clocks section, `clock_storage`, the
    example reply of `status`), `docs/show.md`, `docs/emulator.md`, `docs/firmware.md`
    (three settings), `docs/drifts.md`.
  - Suites: `core`, `emulator`, `firmware-host`, `app`, and `firmware` on its own with
    `ODRIG_TOOLS`.
  - Requirements: 4.2–4.3 with `Internal storage`, 5.1–5.6, 7.1–7.2.

- [x] 3. Give the app the preferred storage and Clocks only over both storages
  - `commands.js` (`clock_storage`, `clockStorage`), `index.html` and `screens/clocks.js`
    (the dropdown, its states and words, older firmware), the panel's words, `client.js`
    (the boundary of both storages, the Clocks level, Back, play, `canUpload`),
    `upload-destination.js` and `screens/storage.js` (the form's storage in Only, the
    selector, `blocked`, the words of a blocked form by target), `screens/archive.js`,
    `screens/batch-list.js` and `batch.js` (the same rule for the archive and the batch),
    `screens/show.js` and `screens/brightness.js` (the storage of a Clocks file playing
    now), `messages.js`.
  - Tests: `tests/app` and the page's scenarios against the emulator, as the design lists:
    the parsing, the dropdown, Only with the board's Clocks alone and with both, the Clocks
    level, play and upload inside, the root not offered, the archive and the batch in
    Only, a target without `clock_storage` with today's boundary and words, the bar of the
    animation playing now; the tests of seeds 66, 67, 73 and 80 keep passing for a target
    whose Clocks folder is the card's alone, but for the words this task changes.
  - Documents: `docs/android-app.md` (the panel, the dropdown, Only, uploads, the command
    table), `docs/drifts.md`.
  - Suites: `app`, `emulator`.
  - Requirements: 6.1–6.6.

- [x] 4. Rehearse the deployment of the seven messages on the emulator
  - A test of the emulator suite that runs the design's board-session commands over TCP
    with the command tool against the emulator, with a card that has a face in `clocks/`:
    `space`, `folder make internal clocks` and `clocks/message`, the seven uploads of the
    tracked files of `collection/card/clocks/message/`, each read back 720 bytes at a time
    and compared by SHA-256 with the design's table, the show folder's `<n>/` files, the
    internal catalog `ok`, `list in` with the seven paths, and in Only with the message on
    an internal message after the card's face.
  - It is reported as a rehearsal, never as a deployment.
  - Suites: `emulator`.
  - Requirements: 9.1–9.2.

- [x] 5. Deliver seed 61
  - From the pushed head with a clean tree: the image of the installation's board
    (`odrig_microsd`, N16R8) and the spare's (`odrig_microsd_n8r2`), each through
    `verify_build.py` for its module, and the APK signed with the persistent key, checked
    with `apksigner` and `zipalign -c 4`; their bytes and SHA-256; the files on the Drive.
  - Every suite that works on this computer passes (`firmware` with `ODRIG_TOOLS` and on
    its own).
  - `verification.md`: the software, the builds, the rehearsal of task 4, and the board
    session of the seven messages with the design's exact commands, room and record,
    marked not done: no board is connected here, so the deployment, its read-back and the
    selection in both modes stay open for the owner, with the LED check of a card face
    followed by an internal message in both modes and of both preferences with a copy, and
    the phone check of the dropdown, its persistence across a restart of the board, and of
    Clocks only showing and uploading into the board's own Clocks folders.
  - `project-seeds/61-p2-internal-storage-clocks-and-messages/state.json` and the seed's
    line in `AGENTS.md`.
  - Suites: all that work on this computer.
  - Requirements: 9.2–9.3, 10.1–10.2.
