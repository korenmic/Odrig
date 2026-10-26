# Tasks: sub-folder playlists from the card (seed 41)

The code these tasks start from is `master` at `de838e3`, which holds seeds 20 to 40. The
owner asked for the spec without a question pass: a question that comes up is decided and
recorded in `docs/drifts.md` under "Seed 41", never asked. Tasks 1 to 9 need neither the
board nor a phone. Task 10 builds the firmware and the APK and does not flash. Task 11
is the owner's.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .` or `git commit -a`. After committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites the
  task names from the repository root, so that a failing suite stops the commit:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`
  and `python3 -m unittest discover -s tests/app -t .`. Task 10 runs every one of them.
- "Prove it fails first": run the test against the state described, watch it fail, and
  put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- No command, no error code and no host member is added. The two reply additions, the
  folder items of `list` and `left` of `status` with `playing` as a folder's id, are the
  owner's by the seed. The card is never formatted and the board makes no folder.
- The board is not touched by these tasks. The firmware is built with
  `python3 firmware/fw.py build` only, never flashed here.
- The memory stays within its budget: 131,072 bytes with a drive, the core object within
  4,096; the numbers of `docs/core.md`'s memory table and of `tests/core/test_drive.py`
  follow what the suite measures.
- Every task that changes a page of `agent/` or `docs/` runs the onboarding suite, and the
  decisions a task takes beyond the seed go into `docs/drifts.md` under "Seed 41" in the
  task's commit (requirement 8.2).

- [x] 1. The path rule and the depth-first listing of the hosts and the PC tool
  - Set the seed's `state.json` to `in_progress`.
  - `core/include/odrig_core.h`: the comments of `drive_name` and `drive_list` describe
    paths and the depth-first order. `core/src/catalog.cpp`: `catalog_name_allowed`
    becomes the path rule, applied to the commit record's names too.
  - `tests/core/host/host.cpp`: `list_drive` depth first with the counting rule and the
    limits on both branches, `drive_name_sound` the path rule, `drive replace` recursive on
    Windows. `tests/core/support.py`: `installed` makes parent folders and `folder_files`
    reads at every depth; `tests/core/test_drive.py`'s `a_drive` and
    `tests/core/test_catalog_writes.py`'s `a_card` make parent folders, its `folder_of`
    reads at every depth.
  - `emulator/host.py`: `drive_list` depth first with the counting rule and the limits,
    `drive_name_sound` the path rule, `Drive.path` of a path under `odrig`.
  - `odrig/catalog.py`: `name_allowed` the path rule, `Storage.names` and
    `MemoryStorage.names` in the depth-first order with the counting rule, parts joined
    with `/` on every system.
  - Tests: `tests/converter/test_catalog_format.py` (the rule's cases, the vector count),
    `test_catalog_types.py`, `test_catalog_changes.py`, `test_catalog_cli.py` (`import`,
    `check`, `status` of a card with sub-folders); `tests/converter/build_catalog_vectors.py`
    gains `ok-folders` and the damaged-path vectors, `tests/vectors/catalog/cases.json`
    regenerated; `tests/core/test_catalog_rebuild.py` and `test_catalog_writes.py` the byte
    identity on a card with sub-folders, siblings `a`, `a b` and `a-b` among them;
    `tests/core/test_drive_host.py` the host's listing; `tests/emulator/test_drive.py` and
    `test_drive_folder.py` the emulator's.
  - `docs/catalog.md` (the rule, the page of a path, the older reader, a deeper path as a
    damaged line), `docs/core.md` (the host rows and the test host's drive),
    `docs/emulator.md` (the drive's folders).
  - Prove it fails first: `odrig.catalog`'s `names()` of a storage with `night/comet.odrg`
    gives no path, and `name_allowed("night/comet.odrg")` is false.
  - Suites: converter's Python suite, core, emulator, onboarding.
  - Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 6.2, 6.3, 6.4, 6.5, 8.1, 10.2

- [x] 2. The firmware lists the card's folders
  - `firmware/usermod/odrig_drive.cpp`: `isDriveName` the path rule; `listFolder` the
    iterative depth-first walk with the pending-folders table taken in `begin()`, one
    directory open at a time, the counting rule and the limits, and the log line with the
    counts of what was passed over; `keepName` sorting within a folder's slots.
  - `tests/firmware/test_usermod_sd.py`: `case` makes parent folders; the mode `folders`:
    the order, three levels, the 33rd sub-folder and the 257th file passed over, a folder
    with files only in its sub-folders counted, the hidden and the system folder, the
    log line in its forms; `bind` with paths allowed and the malformed paths refused
    (`a//b.odrg`, `/b.odrg`, `a/`, `../b.odrg`, `a/.b/c.odrg`, `a /b.odrg`, four levels);
    the asserted log lines of the other modes as the design keeps them.
    `tests/firmware/test_usermod_drive.py`: the pins of the listing and the rule follow
    the code.
  - `docs/firmware-additions.md`: the seed's line. `docs/microsd.md` (preparing a card
    with folders, the log line, the stale `busy` sentence dropped) and `docs/firmware.md`
    (the drive's folder).
  - Prove it fails first: the stand-in card with `night/comet.odrg` lists one file in
    `odrig` and none in `night`.
  - Suites: firmware, onboarding.
  - Requirements: 1.2, 1.3, 1.4, 1.5, 2.2, 6.1, 8.1, 10.3

- [x] 3. The tree in the core and the folder items of `list`
  - `core/src/core_state.h`, `core/src/order.cpp`: the order block gains the folder byte
    per place, the folder table and the path room; `tree_build` in two passes, called from
    `drive_take_listed` and `publish`, the insertion in the listing's order, `end`, the
    folder byte, `tree_clear` at every site that drops places, `too-many-folders` in
    `reasons.h`, `reasons.cpp` and `docs/reasons.md`, folder ids after the files' through
    `free_drive_id` and `drive_id_taken`, `catalog_install_external` setting the new
    place's byte, the tree built again after `catalog_remove_external`.
  - `core/src/content.cpp`: the folder items of `list` after the show's items, counted in
    the positions.
  - Tests: `tests/core/test_folders.py`: the tree and its order on a legacy and a
    cataloged card, the folder ids after the files', the items of `list` and their
    positions, a page holding folder items of the longest paths within 1,024 bytes, the
    33rd sub-folder named by a catalog's pages left out with `too-many-folders`, the `x`
    entries of `order.txt` written as paths after `order move` of a file in a folder,
    `remove` of `night/comet.odrg` removing that file, `upload begin external` with a `/`
    in `<file>` refused `bad-argument`, the memory (`test_drive.py`'s delta and
    `docs/core.md`'s table). `tests/emulator/`: a nested `--drive` listed and the folder
    items of `list` over HTTP and the TCP line port.
  - `docs/commands.md` (the folder items with example paths without a space, the paths of
    `file` and of `order.txt`), `docs/core.md` (the tree and the memory), `docs/show.md`
    (the tree, the paths).
  - Prove it fails first: `list` of a card with `night/comet.odrg` holds no item with
    `playlist`.
  - Suites: core, emulator, onboarding.
  - Requirements: 1.1, 1.6, 5.2, 5.3, 5.5, 6.2, 8.1, 9.1, 9.3, 10.1, 10.2

- [x] 4. `play` of a folder and the refusals of a folder's id
  - `core/src/commands.cpp`: `play <id>` of a folder makes it current, kept as its path
    and index, and plays its first animation (the exhausting order of task 5 and the
    window of task 6 not yet: it plays from the folder's first animation and goes on in
    the saved order); `play all` makes the root current; `in-use` for `remove`, `remove
    many`, `ignore`, `read`, `order move` and `upload begin` of a folder's id; `unknown-id`
    while the card is out.
  - Tests: `tests/core/test_folders.py`: `play` of a folder and of the root, `in-use` for
    each command, `unknown-id` with the card out.
  - `docs/commands.md` (`play` of a folder, the codes).
  - Prove it fails first: `play <folder id>` answers `unknown-id`.
  - Suites: core, onboarding.
  - Requirements: 4.1, 5.1, 5.2, 8.1, 10.1

- [x] 5. The exhausting order and the current playlist
  - `core/src/player.cpp`: the exhausting key, `next_in` and `first_in` over a range, the
    root in place with `in_place` re-judged at every turn end and the take-over from the
    current playlist's first animation, the round of the range in `playlist_turn`,
    `player_first_in_playlist` and `player_start` for a folder, the jump inside and outside
    with `resume_item`, `player_item_leaves` and the drive changes keeping it.
    `core/src/commands.cpp`: `status` reports `playing` as the current folder's id while
    the card is in and holds the folder.
  - Tests: `tests/core/test_folders.py`: the root's exhausting (the board's animations,
    the loose files, then each folder once, then again), a folder's exhausting with a
    nested folder, the order within a folder from `order.txt`, the jump inside and
    outside, the root in place when the folder has nothing to play and the take-over at
    the turn's end, `playing` of `status` with the card in and out. `tests/core/support.py`'s
    `ReferencePlayer` unchanged for the root alone. `tests/emulator/`: `playing` of a folder
    over HTTP.
  - `docs/show.md` (the exhausting, the jump), `docs/commands.md` (`playing`),
    `docs/core.md` (the keys).
  - Prove it fails first: with `night` current, the board's own animation plays after
    `night/comet.odrg`.
  - Suites: core, emulator, onboarding.
  - Requirements: 3.1, 3.2, 3.3, 4.6 (the root in place), 5.4 (`playing`), 8.1, 9.2, 10.1,
    10.2

- [x] 6. The window, the rotation and `left`
  - `core/src/player.cpp`, `core/src/clock.cpp`: `kWindowMs`, `window_started` at the
    first timestamp, the judging at a turn's end, at a refresh during a cycle or nothing,
    and in `mapping_test_stop`; the rotation to the next of the table and to the root, and
    to the root when the tree is not known; the round bounded by the window's end and
    summed again after a rotation; the root alone bounded by nothing. `status` gains
    `left` after `seed`.
  - Tests: `tests/core/test_folders.py`: the window passing at 86,400,000 ms with the turn
    in progress ending first, the rotation through the tree and to the root after the
    last, a cycle at the window's end, a mapping test at the window's end, a gap of many
    windows, `left` counting down and 0 between the end and the turn's end, the root alone
    unchanged by the window. `tests/core/support.py`'s `ReferencePlayer` writes `left` by
    the design's rule; the exact `status` bytes of `test_status.py`, `test_commands.py`,
    `test_playlist.py`, `test_content.py`, `test_startup.py`, `test_failure.py` gain it;
    `tests/emulator/support.py`'s `without_fps` drops it, and the emulator's pinned
    statuses follow.
  - `docs/commands.md` (`left`, the example reply), `docs/show.md` and `docs/core.md` (the
    window; the memory table's rows and figures as the suite measures them),
    `docs/emulator.md` (the status event's example).
  - Prove it fails first: `status` at 1,000 ms has no `left`.
  - Suites: core, emulator, onboarding.
  - Requirements: 4.2, 4.3, 5.4 (`left`), 8.1, 9.1, 9.3, 10.1, 10.2

- [x] 7. The saved file and power-on
  - `core/src/playlist.cpp` and `playlist.h`, new: `playlist.txt` read at start, written as
    `playlist.part` and renamed at a choice, a rotation and every 900,000 ms while the tree
    has a folder, deferred while an upload receives or a rebuild holds a page, never while
    the tree has no folder and no file exists; `storage_clear_parts` probes the part;
    `start` keeps the path and the spent time, the root in place until the tree is known,
    the root current when the read card has no playlist of the path or the current folder
    loses its last file. `tests/core/host/host.cpp`: `playlist.txt` and `playlist.part` in
    `check_name`'s fixed list. `firmware/fwtool/storage.py` and `cli.py`: the file among a
    show folder's own.
  - Tests: `tests/core/test_folders.py`: the file written at a choice and after 900,000 ms
    (`--trace-store`), deferred under an upload, a restart that plays the same folder with
    the saved time, the root in place while the card is not read, the card pulled (`drive
    pull`) and put back (`drive plug`) with the choice and the window kept and the folder
    taking over at the turn's end, a card without the saved folder, the removal of the
    current folder's last file, no storage call more for a flat card or no card
    (`test_order.py`'s pattern), `--cut-at` across the write; `tests/core/test_startup.py`'s
    stored tuples unchanged; `tests/core/test_status.py`'s test of what a start does not
    keep renamed to the jump, `off` and `brightness`. `tests/firmware/` for the tool's list
    of names.
  - `docs/core.md` (the saved file, the reserved names), `docs/show.md` (power-on),
    `docs/commands.md` (what `play` keeps across a restart).
  - Prove it fails first: after `play <folder id>` and a restart, `status` says `"all"`.
  - Suites: core, firmware, onboarding.
  - Requirements: 4.4, 4.5, 4.6, 4.7, 5.6, 6.3, 8.1, 10.1

- [x] 8. The app's groups, button, line and mark
  - `app/www/commands.js` (the validators), `app/www/client.js` (`state.folders`, the
    list asked for an unknown `playing`), `app/www/screens/show.js` (the groups, the Root
    head with `#play-all` `Play this folder`, the folder heads, the counts, the hidden
    group, the line's forms, the mark), `app/www/index.html`, `app/www/style.css`.
  - Tests: `tests/app/test_folders.py` and `tests/app/page/scenarios/folders.js` against a
    stand-in with a fixed `left` and against the emulator with a nested `--drive`: the
    groups in order, the heads and counts, the Root group and its button, a 0-row folder's
    head, the mark, the four forms of the line, `Play this folder` on a folder and on the
    root, the Tests group, the card out and in. `tests/app/test_management.py` the
    validators' cases. `tests/app/test_controls.py`, `test_drive.py`, `test_messages.py`
    follow the root's button; `tests/app/test_look.py` passes with the heads.
  - `docs/android-app.md`: the row of `Playlist from the start` and the row of a tapped
    row in the table of what the operator does, reworded; every mention of `Playlist from
    the start` and of the line `Playlist`; the groups, the button, the line, the mark,
    `What is verified`, `What is open`.
  - Prove it fails first: the Animations tab shows no group `Root`.
  - Suites: app, onboarding.
  - Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7, 8.1, 10.4

- [x] 9. The app's moves, filters, selection and counts with groups
  - `app/www/screens/reorder.js` (moves within a group), `show.js` (a group hidden by the
    filters), `selection.js` and `capacity.js` checked unchanged.
  - Tests: `tests/app/test_folders.py`: dragging and Move up and Move down within a group
    only, no `order move` for a drop in place or at a group's edge, the filters hiding a
    group with rows and never a 0-row head, selection and the counts on rows only,
    uploads to the root. `docs/android-app.md`: moves within a group, uploads to the root.
  - Prove it fails first: Move down of the last row of `night` offers the first row of
    the next group.
  - Suites: app, onboarding.
  - Requirements: 7.6, 8.1, 10.4

- [x] 10. Every suite, the firmware and the APK, the vocabulary and the decision
  - Every suite that runs without a board and without a phone, all passing;
    `python3 firmware/fw.py build`, the binary and its SHA-256 recorded in
    `docs/firmware.md`; `python3 app/app.py build` and `tests/apk`.
  - `agent/vocabulary.md`: the playlist, in one to four sentences that use no word the
    page explains further down (not `turn`, `command`, `core`, `host`, `emulator`,
    `firmware` nor the operators' app) and name no file or path the clone does not hold.
    `docs/decisions.md`: the change-log line of the owner's ruling of 2026-10-26.
    `docs/drifts.md`: the section "Seed 41" holds the design's decisions beyond the seed
    and every question decided in tasks 1 to 9, those not yet recorded added here.
    `AGENTS.md`: the seed's line in "What is coming" says built, the board and phone
    session open. The seed stays `in_progress` for task 11.
  - Requirements: 8.1, 8.2, 10.5

- [ ] 11. The app's explorer: the levels, the folder rows, the heading with `Back`, the level's button and the marks
  - `app/www/screens/show.js` (the level kept in the screen, the level head with `Back`,
    the title and `#play-all` sending `play all` or `play <id>`, the level's rows and
    folder rows, the marks of the head and of the folder rows, `#none` and
    `#filter-empty` by the level), `app/www/index.html`, `app/www/style.css`; the flat
    groups of task 8 go.
  - Tests: `tests/app/test_folders.py` and `tests/app/page/scenarios/folders.js` against a
    stand-in with a fixed `left` and against the emulator with a nested `--drive`: the
    root's rows and folder rows with their names and counts, a 0-file folder's row,
    entering a folder and the heading, `Back` to the parent and to the root, the level's
    `Play this folder` inside a folder and at the root, the marks on the head and on the
    folder rows that lead to the current playlist, the line's forms, the Tests group, the
    card out and in bringing the list to the root. `tests/app/test_controls.py`,
    `test_drive.py`, `test_messages.py` keep the root's button; `tests/app/test_look.py`
    passes with the head and a folder row.
  - `docs/android-app.md`: the explorer in place of the groups, the rows, `Back`, the
    button, the marks, `What is verified`.
  - Prove it fails first: at the root the Animations tab shows `night/comet.odrg` as a
    row, and no folder row `night`.
  - Suites: app, onboarding.
  - Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7, 8.1, 10.4

- [ ] 12. The app's filters, moves and selection within the level shown
  - `app/www/screens/filters.js` (the counts of the level's rows), `selection.js` (the
    level's rows for `Select all` and what can be selected), `reorder.js` (checked: moves
    within the level, a folder row ending the level), `show.js` passing the level's rows.
  - Tests: `tests/app/test_folders.py`: the filter counts at a level, a folder row shown
    under every filter, `Move up` and `Move down` and a drag within the level only and
    nothing sent for a drop in place, `Select all` taking the level's rows only, the
    storage lines counting files only. `docs/android-app.md`: the filters, moves and
    selection within the level, uploads to the root. `docs/decisions.md`: the change-log
    line of the owner's correction of 2026-10-26.
  - Prove it fails first: `Select all` inside `night` selects the root's rows.
  - Suites: app, onboarding.
  - Requirements: 7.6, 8.1, 10.4

- [ ] 13. The owner's check on the board and a phone
  - In a session with the owner, with the firmware of task 10 flashed and the APK on the
    phone, a card prepared with sub-folders: the groups on the phone, a folder chosen and
    playing, the board restarted and playing the same folder, the root chosen and playing,
    the card out and in, the time between `card mounted` and `card opened` for a card with
    32 sub-folders and 256 files, the time left counting down. Then `state.json` becomes
    `completed` with `completedAt`, and the seed's line leaves "What is coming" in
    `AGENTS.md`.
  - Requirements: 10.6
