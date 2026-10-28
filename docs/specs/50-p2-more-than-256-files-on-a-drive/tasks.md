# Tasks: more than 256 files on a drive (seed 50)

The code these tasks start from is `master` at `afc7b09`, with the one-line fix of the
owner's open PR #18 (`949cbb7`, its `core/src/catalog.cpp` alone) cherry-picked before
them so that the core builds with GCC on Windows. The seed has no open question: the owner
approved its four decisions on 2026-10-28. A question that comes up is decided and
recorded in `docs/drifts.md` under "Seed 50", never asked. Tasks 1 to 7 need neither the
board nor a phone; task 8 is the owner's.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .`, `git add -u` or `git commit -a`. After committing, read
  `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites the
  task names from the repository root; on Windows: `npm test --prefix converter`,
  `.venv\Scripts\python -m unittest discover -s tests/converter -t .`,
  `.venv\Scripts\python core/build.py test`,
  `.venv\Scripts\python -m unittest discover -s tests/emulator -t .`,
  `.venv\Scripts\python -m unittest discover -s tests/app -t .` and
  `.venv\Scripts\python -m unittest discover -s tests/onboarding -t .`, one suite at a
  time. The failures that `master` has on Windows outside this seed are noted, not mended.
- "Prove it fails first": run the test against the state described, watch it fail, and
  put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- No command, no error code and no host member is added. The forms `list in`, `order get
  in`, the folder items' `files` and `status`'s `file` and `playlist` are the owner's by
  the seed's approval of 2026-10-28.
- The board is not touched, and the firmware is not changed.
- The memory stays below today's 130,509 bytes with a drive, the core object within
  4,096; `docs/core.md`'s memory table and `tests/core/test_drive.py` follow what the suite
  measures.
- Every task that changes a page of `agent/` or `docs/` runs the onboarding suite, and the
  decisions a task takes beyond the seed go into `docs/drifts.md` under "Seed 50" in the
  task's commit.

- [x] 1. The PC tool keeps a drive's index
  - Set the seed's `state.json` to `in_progress`.
  - `odrig/catalog.py`: a storage knows whether it is a drive (`Storage(folder,
    drive=True)`, `MemoryStorage(files, drive=True)`); a drive's catalog is of version 2,
    its marker with `folders` and `ids`, and the board's stays of version 1, each reader
    finding the other `incompatible`. The index's three kinds of file, written and read:
    `rebuild` (the walk, the ids, the old rows' order, the removals in the record), `add`
    (a new file and a replacement), `remove` (a folder left empty and its ancestors), and
    `move` (a file before another or last); `finish` of any `move <from> <to>`; `read`
    checks that the index agrees with the pages. `Storage.names()` lists every file;
    `cut_listing` stays for a listed drive's limits. The CLI manages a drive; `status`
    and `check` say whether the index agrees, `recover` removes `rebuild.tmp`,
    `rebuild-folders.tmp` and the index's `.new` files.
  - Tests: `tests/converter/test_catalog_index.py`, new: the files of an import of a card
    of folders, their widths, the walk's ids, an upload, a replacement, a removal that
    empties a folder and one that empties its parent, a move, a rebuild that keeps the
    old rows' order with files added and removed, a card of 1,000 files and 50 folders, a
    cut in every step of a change finished by `finish`, version 1 on a drive and version 2
    inside; `test_catalog_changes.py` and `test_catalog_cli.py` follow the drive's
    version; `tests/converter/build_catalog_vectors.py` gains an indexed card and
    `tests/vectors/catalog/cases.json` is written again.
  - `docs/catalog.md`: the index, the marker of version 2, the record's moves, the writers'
    changes, the costs; `docs/microsd.md`: the import without a limit.
  - Prove it fails first: `import` of a card of 300 files indexes 256 of them and writes no
    `index-folders.txt`.
  - Suites: library, onboarding.
  - Requirements: 1.1 to 1.6, 2.1, 2.2, 3.1 to 3.5

- [x] 2. One level at a time in the replies
  - `core/src/commands.cpp`: ids of `play`, `read`, `remove`, `ignore`, `order move` up to
    4,294,967,295; `list in <folder-id> [<from>]` and `order get in <folder-id> [<from>]`,
    `<from>` up to 4,294,967,295. `core/src/content.cpp`: `list` gives the show's items and
    the root's level, `list in` a folder's level, folder items with `files`.
    `core/src/order.cpp`: `order get` the root level, `order get in` a folder's, the
    revision of the level. `status` gains `file` and `playlist` before `left`.
  - `odrigctl/cli.py`, `odrigctl/content.py`: `list in ID [FROM]`, `order get in ID
    [FROM]`, every part printed.
  - `emulator/engine.py` keeps reading the cycles from `list`.
  - Tests: `tests/core/test_folders.py` (the levels, `next` and `<from>` within a level, a
    level of the longest paths, `unknown-id`, `files`), `test_status.py` and the exact
    statuses of the other core tests (`file`, `playlist`), `test_order.py` (a level's
    order and revision), `test_commands.py` (the ranges of the words);
    `tests/emulator/test_tool.py` (`list in`, `order get in`); `tests/core/support.py`'s
    `ReferencePlayer` writes the two members.
  - `docs/commands.md` (`list in`, `files`, `order get in`, the status members and their
    example, the ranges), `docs/show.md` (a folder's level), `docs/emulator.md` where it
    shows a status.
  - Prove it fails first: `list in 60007` is `bad-argument`, and `list` holds the files of
    the card's folders.
  - Suites: core, emulator, onboarding.
  - Requirements: 2.4, 6.1 to 6.4, 9.3

- [x] 3. The app reads one level at a time
  - `app/www/commands.js`: `list(from, folder)` and `orderGet(from, folder)`.
    `app/www/client.js`: the level's path, folder id, items and order, read in parts with
    `list`/`list in` and `order get`/`order get in`, read anew when a folder is entered or
    left and when it is out of date; nothing of another level kept. `screens/show.js`: the
    explorer from the level, folder rows' counts from `files`, what plays and the marks
    from `status.file` and `status.playlist`; `screens/reorder.js`, `selection.js`,
    `filters.js` on the level; `capacity.js` counts the drive's animations by the external
    catalog's `entries`.
  - Tests: `tests/app/test_folders.py`, `test_order.py`, `test_filters.py`,
    `test_counts.py`, `test_management.py`, `test_scope.py` and the scenarios of
    `tests/app/page/scenarios/` that serve a list: the stand-ins answer `list in` and
    `order get in`; a test that the app never asks for a level it does not show.
  - `docs/android-app.md` (the explorer reads a level, the counts).
  - Prove it fails first: entering `night` asks for no `list in`, and the level is empty
    on a target that lists only the root's level.
  - Suites: app, onboarding.
  - Requirements: 9.1, 9.2

- [x] 4. The core keeps a drive's index
  - `core/src/index.h`, `core/src/index.cpp`, new: the index's rows, read through the
    cursor's room, and written: a folder's file, the table, the map, streamed from the
    old ones with a change; the binary search of the map; the lowest free id.
  - `core/src/core_state.h`: the drive's cursor in a block of its own, the rows and the
    folder records; positions in the walk; ids of 32 bits; the tree's records with `first`
    and `files`; the per-place keys, hashes and folder bytes gone; the rebuild's counters.
  - `core/src/catalog.cpp`: the marker of version 2 for the drive and 1 inside; the
    plug-in reads the record and the marker and publishes the drive at once; the record's
    general `move` and index removals, written and read in pieces; an upload, a
    replacement and a removal commit the index; `catalog rebuild external` in the phases
    of the design, by the bytes of the names in every folder; `catalog cancel` and the
    failures remove what it wrote.
  - `core/src/core.cpp`: the listed drive cut by the core, its places in the walk;
    `drive_touch`, `free_drive_id`, the drive's check. `core/src/player.cpp`: the walk by
    ranges of positions, the rounds only without an indexed drive, the positions held
    following a change, a played row's fault remembered. `core/src/order.cpp`:
    `order.txt` keeps the show's items; the tree from the listed drive's places; `order
    get` from the rows; `order move` of a drive's file `read-only`. `core/src/content.cpp`,
    `commands.cpp`, `upload.cpp`, `playlist.cpp`: the drive's rows through the cursor.
  - `tests/core/host/host.cpp`: the drive listed whole; its names check takes the index's
    and the rebuild's files. `emulator/host.py`: `drive_list` without the cut.
  - Tests: `tests/core/test_index.py`, new: an indexed card of 300 files in 40 folders
    played through every folder, listed level by level, `play` of the 300th file and of a
    folder, `status` naming it; the reads of a plug-in (marker only) and of a turn's end
    (one row) with `--trace-read-at`; a row out of its form; a file that fails while it
    plays; the look; uploads, replacements and removals byte for byte the PC tool's, with
    `--cut-at` at every storage call; a rebuild of 300 files byte for byte the PC tool's
    import, cancelled, failed and pulled out; the listed drive's cut of 300 files. The
    tests of the drive and the catalogs, `test_drive.py`, `test_folders.py`,
    `test_catalog_drive.py`, `test_catalog_writes.py`, `test_catalog_rebuild.py`,
    `test_catalog_page.py`, `test_order.py`, `test_memory.py` and the others that make a
    card, make it indexed with the PC tool and follow the walk and the order of the rows.
    `tests/emulator/`: a `--drive` folder of 300 files, read-only and written.
  - `docs/core.md` (a drive, the catalogs, the saved order, the memory table as measured),
    `docs/show.md` (the drive's files, the saved order), `docs/commands.md` (`order move`
    of a drive's file, `no-space`), `docs/emulator.md` (the `--drive` folder's limits),
    `docs/microsd.md` (preparing a card).
  - Prove it fails first: an indexed card of 300 files lists 256 of them, and `play
    60300` is `unknown-id`.
  - Suites: library, core, emulator, app, onboarding.
  - Requirements: 1.1, 2.1 to 2.3, 3.1 to 3.4, 4.1 to 4.6, 5.1 to 5.3, 6.5 to 6.7,
    7.1 to 7.3, 8.1, 8.2, 10.1

- [x] 5. A drive's file moves among its folder's rows
  - `core/src/order.cpp`, `core/src/catalog.cpp`, `core/src/index.cpp`: `order move` of a
    drive's file on an indexed drive the core may write commits the drive's catalog with
    its folder's file, the table and the map; `<before>` of another level `in-use`; a
    root's file before a show item first among the root's files, a show item before a
    root's file last among the show's items; the positions held follow the move.
  - Tests: `tests/core/test_index.py`: the move byte for byte the PC tool's `move`, with
    `--cut-at` at every call, the revision, the walk after it, the refusals;
    `tests/app/test_order.py` against the emulator, a move within a folder.
  - `docs/commands.md`, `docs/show.md` (the saved order of the drive's files).
  - Prove it fails first: `order move` of a file of `night` is `read-only`.
  - Suites: library, core, emulator, app, onboarding.
  - Requirements: 3.2, 3.3, 5.2, 6.5

- [ ] 6. A rebuild keeps the rows' order
  - `core/src/catalog.cpp`: the rebuild's folders' files begin with the old index's rows
    of the files still there, in their order, looked up in `rebuild.tmp`, and its new
    files are those the old pages have no line for; the removals of the old folders'
    files.
  - Tests: `tests/core/test_index.py`: a card whose rows were moved, with files added and
    removed and a folder gone, rebuilt by the core byte for byte the PC tool's import of
    the same card.
  - `docs/catalog.md` (the order a rebuild keeps).
  - Prove it fails first: after a move and a rebuild, the moved file is back in the order
    of the names.
  - Suites: library, core, onboarding.
  - Requirements: 3.2, 3.4, 7.1

- [ ] 7. The pages, the proof on the emulator, every suite, and the seed done
  - `docs/catalog.md`, `docs/core.md`, `docs/show.md`, `docs/commands.md`,
    `docs/android-app.md`, `docs/microsd.md`, `docs/emulator.md`: what exists, the figures
    as measured; `docs/decisions.md`: the change log entry of the seed and the memory
    decision changed; `AGENTS.md`'s line of seed 50.
  - On the emulator: a `--drive` folder of 1,000 files in 50 folders, indexed by the PC
    tool, listed level by level over HTTP, `play` of a file past the 256th and `status`
    naming it, the playlist past the 256th file; the same folder rebuilt by `catalog
    rebuild external` byte for byte the PC tool's; the numbers into `docs/catalog.md`.
  - Every suite that runs on Windows; the seed's `state.json` `completed` with
    `completedAt` once everything but the owner's task is done.
  - Suites: every one.
  - Requirements: 10.1 to 10.3

- [ ] 8. The board and the owner's checks (the owner's)
  - The owner's collection on its card, indexed once by `python3 -m odrig.catalog MOUNT
    import`, listed and played through every folder by the board; the firmware built and
    flashed by `firmware/fw.py`, the brightness 40 or less.
  - The owner walks the explorer's levels in the app on a phone.
  - Requirements: 10.4
