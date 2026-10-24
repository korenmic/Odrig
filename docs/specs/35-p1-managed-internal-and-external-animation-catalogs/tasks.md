# Tasks: managed internal and external animation catalogs (seed 35)

Seeds 28, 31, 32, 33, 34, 36, 38 and 39 are in the code these tasks start from (the
unified branch with seeds 33 and 34). Where the real code differs from what the design
relies on, follow the code and record the difference in `docs/drifts.md`. Tasks 1 to 14
need no board; task 15 needs the board, task 16 the owner.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit run the suites of the parts the task changed, and always
  `python3 -m unittest discover -s tests/onboarding -t .`: the core's with
  `make -C core test`, the emulator's, the app's, the mapping suite, the firmware's with
  `python3 firmware/fw.py test`, the converter's two (the Python library's tests, the PC
  tool's among them, are in `tests/converter`). Task 14 runs every suite.
- "Prove it fails first": watch the new test fail on the code before, and put what was
  seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- The commands, the reply members and the error code are those of the design, approved in
  advance by the owner on 2026-10-24; each goes into `docs/commands.md` and a dated line of
  `docs/decisions.md` with the task that adds it.

- [x] 1. The regression: every start and every plug-in read the whole library
  - Set the seed's `state.json` to `in_progress`.
  - `tests/core/test_catalog_regression.py`, with catalog files written by hand in the
    design's format: a start with a catalog of every file opens and reads every installed
    file and lists `"bytes":null`; a drive with a catalog is listed (`drive_name` through
    every place) and every file read before it plays; a file copied onto a drive with a
    catalog joins the playlist. Each is an expected failure until the task that mends it.
  - Prove it fails first: the tests' assertions fail on today's core (recorded).

- [x] 2. The format and the PC library
  - `odrig/catalog.py`: the storage, the format's writers and readers, `page_of`,
    `entry_of`, `commit`, `finish`, `add`, `remove`, `rebuild`, `check`, `status`,
    `recover`.
  - `tests/vectors/catalog/`: valid and malformed catalogs and torn commit records with
    their outcomes; `tests/converter/test_catalog_format.py` and
    `tests/converter/test_catalog_changes.py`: every vector; each change's files and calls;
    an interruption at every call, then `recover`: the catalog before or after.
  - `docs/catalog.md`: the format, the commit, the recovery, the costs.
  - Prove it fails first: the tests on a library without `odrig/catalog.py`.

- [ ] 3. The core: room, and the internal catalog at the start
  - `DriveEntry.total_ms` in 32 bits; `CatalogState`; `kCheckedFromCatalog`;
    `core/src/catalog.h/.cpp`: the marker, the pages, `catalog_finish`,
    `catalog_read_internal`; the start opens and checks only uncataloged files; the
    command `catalog` (states, no rebuild yet).
  - Tests, `tests/core/test_catalog_start.py`: every vector read by the core as the PC
    tool reads it; cataloged files neither opened nor read, sizes listed at once; a
    canvas other than the mapping's; legacy, damaged and incompatible catalogs; a whole
    and a torn commit record at the start; seed 32's quarantine at playback; memory
    measured and `docs/core.md`'s table.
  - Task 1's start test passes. Prove it fails first.

- [ ] 4. The core: changes of the internal storage commit the catalog
  - `catalog_commit`; uploads, `remove`, `remove many`; legacy storage unchanged.
  - Tests, `tests/core/test_catalog_changes.py`: the files after each change; a cut and a
    failure at every storage call of each change, then a start; the same sequences
    through the PC library leave the same catalog files; the bytes and calls of each
    change at 16, 64 and 256 entries.
  - Prove it fails first.

- [ ] 5. The hosts: listing on demand, names given, a drive that can be written
  - `odrig_host`: `drive_list`, `drive_bind`, `drive_writable`; `drive/<name>` in the
    file functions. The test host (`--drive-read-only`, `drive_list` traced) and the
    emulator (`emulator/host.py`, `binding.py`, `--drive-read-only`). The core calls
    `drive_list` for a drive without a catalog.
  - Tests: legacy drives as before through `drive_list`; a drive is not listed before the
    core asks; writes by name inside the folder; read-only refusals.
  - Prove it fails first.

- [ ] 6. The core: a drive's catalog
  - `catalog_drive_step`: the commit record, the marker, the pages in steps, staging,
    publication, `order.txt`; `catalog_drive_look` once in 10 seconds and the reload;
    damaged and incompatible catalogs; `Remembered` by CRC-32; seed 33's readiness.
  - Tests, `tests/core/test_catalog_drive.py`: no listing and no animation read before
    play; nothing plays before publication, all at once after it; the reads at a refresh
    at 16, 64 and 256 entries; one read every 10 seconds while unchanged; a marker
    changed by the test reloads; a page that differs; pulled out while loading; a file
    left out by the player stays out on a reload and a new plug-in, a new CRC-32 comes
    back. Task 1's drive tests pass.
  - Prove it fails first.

- [ ] 7. The core: the board writes the drive
  - `upload begin external`, `upload end`'s `id`, `remove <id>` of a drive's animation,
    `space`'s `read_only`, the error `read-only`; docs/commands.md.
  - Tests, `tests/core/test_catalog_writes.py`: uploads to the card, a replacement keeps
    its id, a removal frees its place, the saved order by name; refusals in their order;
    a cut and a failure at every call; the same changes through the PC library on a copy
    of the card leave the same files, byte for byte.
  - Prove it fails first.

- [ ] 8. The core: rebuild and import
  - `catalog rebuild internal|external`, `catalog cancel`, the progress in `catalog`,
    `busy` for changes while a page is written; the check after the start and the legacy
    drive check give way to a rebuild and take up what it left.
  - Tests, `tests/core/test_catalog_rebuild.py`: a legacy storage imported; progress;
    cancel at every step; faults; the next start reads no animation; the core's rebuild of
    a folder and the PC library's are the same files. Task 1's copy test passes after an
    import.
  - Prove it fails first.

- [x] 9. The PC tool's command line
  - `python3 -m odrig.catalog <mount> status|import|add|remove|check|recover`;
    `docs/microsd.md` (preparing a card on a computer), `docs/python-library.md`.
  - Tests, `tests/converter/test_catalog_cli.py`: each command, its outcome lines and exit
    codes, a mount given as the folder `odrig` itself, paths with spaces.
  - Prove it fails first.

- [x] 10. The firmware tool writes the internal catalog
  - `fwtool/storage.py` `folder_files` adds the catalog of a checked folder, with the
    board's generation plus one; `--no-check` none.
  - Tests in `tests/firmware`: the catalog in the image; a second install of the same
    folder changes no page; a changed file changes its page and the marker only; the
    core's rebuild of the same folder gives the same pages.
  - Prove it fails first.

- [ ] 11. The firmware writes the card
  - `firmware/usermod/odrig_drive.cpp`: `drive_list` on demand, `drive_bind`,
    `drive_writable` (the SD card when mounted; the USB drive 0), the file functions by
    name, `rename` onto an existing file; `odrig_files.cpp` routes `drive/` names.
  - Tests in `tests/firmware`; `python3 firmware/fw.py build` and `build --microsd` build.
  - Prove it fails first.

- [ ] 12. The command tool and the emulator
  - `odrigctl catalog`, `odrigctl upload --external`; the emulator's documents.
  - Tests in `tests/emulator`: the commands through the emulator's routes; a card folder
    the emulator wrote is read by the PC tool and the other way round.
  - Prove it fails first.

- [ ] 13. The app
  - Upload's choice of storage, Settings' catalogs with rebuild, progress and cancel, a
    writable card's Delete; `docs/android-app.md`.
  - Tests in `tests/app` against the emulator and stand-ins.
  - Prove it fails first.

- [ ] 14. The documents, the measurements, the APK and every suite
  - `docs/catalog.md` with the measured costs; `docs/core.md`, `docs/show.md`,
    `docs/commands.md`, `docs/microsd.md`, `docs/firmware-additions.md`,
    `docs/emulator.md`, `docs/decisions.md`, `AGENTS.md`'s line of seed 35.
  - `python3 app/app.py build`; every suite.

- [ ] 15. The board (board session)
  - Flash the firmware of this branch. On the Mac, `python3 -m odrig.catalog
    /Volumes/<card> import` makes the card's catalog. With the card in the board: for each
    internal animation to move, `odrigctl upload --external FILE` and then `odrigctl remove
    <id>`, keeping one or two small fallback animations inside; `odrigctl catalog rebuild
    internal` once. Measure the first reply, the first list with sizes, the first picture
    and the card's catalog published, against 2026-10-23; brightness 40 or less.

- [ ] 16. The owner's check
  - On a phone: upload to the card, delete from the card, rebuild with progress and
    cancel; the LEDs play the card's animations and the fallbacks.
