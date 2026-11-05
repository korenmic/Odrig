# Design

## Boundaries

The core changes what it does without two files, and nothing else about what it does
with them. The reader of the mapping file falls back to bytes the core holds; the
reader of the show file falls back to an empty show; the first change that writes the
show file writes the mapping file first. The emulator's page server serves the same
bytes when the folder has no mapping file. The reference model of the core's tests
follows the core. The firmware is rebuilt from the core and is not changed; the
converter, the Python library, the firmware tool and the app are not changed; no
command, reply member or error code is added.

## The built-in mapping

- `core/mapping_data.py`, beside `core/diagonal.py` and in its form: `generated()`
  reads `mapping/legs-20.json` and gives the text of a header that holds its bytes as
  `static const uint8_t kBuiltInMapping[] = { ... };`, sixteen bytes a row; without an
  option it writes `core/src/mapping_data.h`, with `--check` it exits with a message
  when the header is missing or differs from the file. The header is committed, as
  `diagonal_data.h` is, so that the core builds without Python.
- `core/src/asset.h`, new: the in-memory host that `decode_diagonal()` of
  `mapping_control.cpp` builds today, moved there so that two readers share it. `Asset`
  holds the bytes, their size and the offset; `asset_open()` resets the offset and
  answers 1 for any name, `asset_read()` copies the next bytes, `asset_close()` does
  nothing; `asset_host(Asset &)` fills an `odrig_host` with the three and nothing else.
  `decode_diagonal()` uses it as it used its own.
- `core/src/mapping.cpp`: `read_once()` takes the host to open `mapping.json` on.
  `read_mapping()` clears `core.mapping_builtin`, reads once on `core.host`, and when
  that answers `kMappingMissing` sets `core.mapping_builtin`, builds the asset host
  over `kBuiltInMapping` and reads on it instead; the second reading opens on the same
  host as the first. Every other outcome, `kMappingMalformed`, `kReadError` and
  `kOutOfMemory`, is as today. The host is asked to open `mapping.json` once in the
  built-in case, twice when the file is there.
- `core/src/core_state.h`: `uint8_t mapping_builtin;` beside `mapping_test`: 1 while
  the legs are the built-in mapping's and no file holds them.
- `core/src/mapping_control.cpp`: `persist()` clears `core.mapping_builtin` when the
  rename succeeded. `mapping_materialize(core)`, new and declared in
  `mapping_control.h`: true at once when `mapping_builtin` is 0; otherwise it opens
  `mapping.part` for writing, writes the bytes of `kBuiltInMapping` in pieces of at
  most `kChunkSize`, closes, and renames the part over `mapping.json`; when any step
  fails it removes the part and answers false; when all succeeded it clears
  `mapping_builtin` and answers true. `mapping_get()`, `mapping_set()`,
  `mapping_editable()` and the tests are unchanged: the built-in legs are twenty legs of
  180 LEDs in their own three columns, so they are editable and the revision is the
  CRC-32 of the default pins.
- `core/src/content.cpp`: `content_write_show()` begins with
  `if (!mapping_materialize(core)) return false;`. Its four callers, the end of an
  upload, the removals and the inclusion, already remove `show.part` and answer
  `storage-error` when it answers false, so a mapping file that cannot be written
  refuses the change before `show.part` is opened.

## The empty show

- `core/src/show.cpp`: `kEmptyShowBrightness = 128`. `read_show()` reads once as
  today; when that answers `kShowMissing` it calls `empty_show()` instead of failing:
  the item and file tables get `kFewestItems` entries and the entry table one, as a
  show file with no item gets them, `item_capacity` is set, `item_count`,
  `entry_count` and `file_count` are 0, `has_start` and `has_min_seconds` are 0,
  `start_item` is 0, `min_seconds` is `kMinSeconds`, and `brightness` and
  `show_brightness` are 128; it answers `kOutOfMemory` when a table cannot be taken and
  `kNone` otherwise. The comment of `read_show` in `show.h` says so, and that
  `kShowMissing` is not among its answers.
- `core/src/core.cpp`: unchanged. `start()` goes on after `read_show()` as for a show
  with no item: the catalog is read, no file is opened, `pending.txt` is settled, the
  order and the repeats are read, the check is complete at once, and the player starts
  with nothing to play. `status` reports `readiness` `ready`, `playing` null,
  `animation` null, `error` null, `width` 60 and `height` 60; `brightness` 128.
- The first upload: `upload begin 1 <name> <size>` is accepted as into any show
  whose storage changes, the file is checked against the canvas of 60 x 60, and at
  `upload end` the change writes `mapping.json` through `mapping_materialize()`, then
  `show.json` with the one item, and the playlist starts with it.

## The reference model

- `tests/core/support.py`, `ReferencePlayer._check()`: a file set without
  `mapping.json` takes `mapping/legs-20.json`'s text for the canvas and the legs and
  sets `self.mapping_builtin`; one without `show.json` takes
  `{"version": 1, "brightness": 128, "items": []}`. `_Invalid("mapping-missing")` and
  `_Invalid("show-missing")` are gone. Every place that writes `self.files["show.json"]`
  first writes `self.files["mapping.json"]` with the bytes of `mapping/legs-20.json`
  when `mapping_builtin` holds, and clears it; a `mapping set` that persists clears it
  too. `TARGET_MAPPING`, the path of the file, is one name of the module.

## The emulator

- `emulator/httpd.py`: `BUILT_IN_MAPPING`, the path of `mapping/legs-20.json` from the
  repository root beside the `emulator` package. `mapping()` serves the folder's
  `mapping.json` byte for byte when it opens, as today, and the built-in file when the
  folder's cannot be opened; 404 only when neither can be read.
- `emulator/app.py`, `engine.py`, `binding.py` and the page: unchanged. The `hello`
  event carries the twenty legs from the core, the page fetches `show/mapping.json`,
  gets the target file, and draws the legs; the reason band stays hidden because
  `error` is null.
- `docs/emulator.md`: the reason band paragraph says the reason text is shown for a
  file that cannot be used, `show-malformed` for example; the route table and the
  paragraph of `GET /show/mapping.json` say what is served when the folder has no
  mapping file; step 22 of the check list writes `{` over `show.json` of the copy
  instead of removing it and sees `show-malformed`; `tests/emulator/test_docs.py`
  looks for `show-malformed` where it looked for `show-missing`.

## The tests

- `tests/core/test_mapping.py`: `RefusedMappings` loses `test_a_missing_file_gives_
  mapping_missing_and_no_legs`; `BuiltInMapping`, new: a file set with no mapping file
  gives `run.error` None, the twenty legs of `(number, pin, 180)` on the pins 1 to 18,
  21 and 47, `status` with `width` 60 and `height` 60, no log line, and `mapping.json`
  opened once; a file under another name is not the mapping and the built-in one is
  used; `mapping get` reports `editable` true, the default pins and the CRC-32 revision
  of them; `mapping set` with two pins swapped writes `mapping.json` and the next start
  on the files left reads the swapped pins. The tests that start on a mapping file
  alone expect `run.error` None and dark refreshes where they expected `show-missing`.
- `tests/core/test_startup.py`: `test_mapping_missing` and `test_show_missing` become
  the tests of the two fallbacks: `status` of an empty file set and of a file set with
  the mapping file alone, `error` null, `brightness` 128, `playing` null, `readiness`
  `ready`; `OrderOfTheChecks` drops the two missing cases and gains `mapping-malformed`
  with no show file and `show-malformed` with no mapping file; the `pending.txt` test
  drops the two missing cases and gains one that settles `pending.txt` with both files
  missing; the test of the files opened expects, for a file set without the show file,
  `show.json` opened once and the start going on to `pending.txt` and `catalog.txt`,
  and for one without the mapping file, `mapping.json` opened once and the show file
  twice; and `test_a_folder_with_no_file_opens_these_and_writes_nothing` states the
  whole sequence of host calls of an empty file set, which `docs/core.md` repeats.
- `tests/core/test_status.py`: the two missing cases leave the table of invalid shows;
  a case of the empty file set with `error` None and `width` 60 joins the valid ones.
- `tests/core/test_json.py` and the other tests that read `show-missing` as "a valid
  mapping, no show": `run.error` None.
- `tests/core/test_first_animation.py`, new: the first upload into an empty file set
  with a clip of 60 x 60, `upload begin 1 first.odrg <size>`, its pieces and
  `upload end`: the reply, `status` with `playing` `"all"` and `animation` 1, `list`
  with the one item, and the files left: `mapping.json` byte for byte
  `mapping/legs-20.json`, `show.json` as the model writes it, `first.odrg`, and no
  part; the same against the reference model. A second test makes the host refuse the
  write of `mapping.part` with the test host's failing-write option and expects
  `storage-error`, no `mapping.json`, no `show.json`, no part, and `mapping get` still
  editable. A third starts on a file set with `show.json` and its animation but no
  mapping file and sees the animation play. `tests/core/test_build.py` checks
  `python core/mapping_data.py --check` as it checks the diagonal, and that a header
  with one byte changed fails it.
- `tests/emulator/test_binding.py`, `OtherFolders`: an empty folder gives `error`
  None, twenty legs, `led_bytes` 10800, a refresh of 10800 zero bytes, `status` with
  `error` null and `width` 60, and nothing logged; a folder with a mapping and no show
  gives `error` None and dark refreshes.
- `tests/emulator/test_events.py`, `OtherShows`: an empty folder gives `hello` with
  twenty legs and `error` null, a status event with `error` null, and
  `GET /show/mapping.json` with status 200 and the bytes of `mapping/legs-20.json`; a
  mapping the core refuses is still served as it is.
- `tests/app/test_upload.py`: `test_the_first_upload_into_an_empty_installation`:
  the emulator started on an empty folder, the `uploads` scenario with `clip.gif`,
  the message `Uploaded as animation 1 clip.odrg. It plays in the playlist.`, the file
  converted for 60 x 60 as the command line converts it on `mapping/legs-20.json`, the
  item listed, and the folder's `mapping.json` byte for byte the target file.

## The documentation

- `docs/core.md`: the row of `odrig_core_leg_count` says "those of the mapping file,
  or of the built-in mapping when there is no file, or 0 when the mapping file cannot
  be used"; the Startup section says that a missing mapping file is the installation's
  mapping, `mapping/legs-20.json`, held by the core, and a missing show file the empty
  show of brightness 128, that nothing is written for either at the start, and that
  the first change which writes `show.json` writes `mapping.json` first; the paragraph
  of the host calls of a folder with none of the files states the new sequence.
- `docs/reasons.md`, "The core": the sentence "from `mapping-missing` to `nested-cycle`"
  becomes "from `mapping-malformed` to `nested-cycle`", the two rows leave the table,
  and a sentence says what the core does without the two files.
  `tests/core/test_docs.py` expects the table without them.
- `docs/commands.md`: the row of `width` and `height` says they are `null` while the
  mapping file cannot be used, and that a target without a mapping file reports the
  built-in mapping's 60 x 60; "Mapping controls" says that `mapping get` on a target
  without a mapping file reports the default pins, editable, and that the first save
  writes the file.
- `docs/mapping.md`: a paragraph after the rules says that the player holds the
  target's mapping and uses it when `mapping.json` is not there, that the tools still
  refuse a missing file with `mapping-missing`, and that the first change of the show
  writes the file.
- `docs/android-app.md`: the row of `no-canvas` says "it has a mapping file it cannot
  use, or its software is older than seed 76".
- `agent/getting-started.md`: the example of a reason is `show-malformed`.
- `docs/decisions.md`: a change-log entry of 2026-11-05 with the owner's ruling and
  what it changes of the decision of seed 32: a missing mapping file or show file no
  longer refuses the show.
- `docs/drifts.md`: the decisions made here: the brightness of the empty show, nothing
  written at the start and the mapping file written with the first show file, the
  reasons left to the tools, the emulator serving the repository's file.

## Delivery

- The branch `seed-76-empty-board-first-animation` from `master` at 9c13db4, one
  commit per task, a pull request against `master`.
- The firmware is built on this Windows computer from the pull request's head with
  `python firmware/fw.py setup` and `build`, the toolchains shared through
  `ODRIG_TOOLS` from an earlier build on the computer, verified with
  `python firmware/verify_build.py`, and its host suites run. The image, its
  `.sha256`, its `.build.json`, `image-info.txt`, `verification.json` and a README go to
  the Drive under `odrig archive/seed-76/`; nothing above that folder is touched. The
  README says: the application image at offset 0x10000, the flash settings kept, no
  erase, the bootloader and the partition table not written, as the earlier deliveries
  say; and that the APK of seed 75 is the one to use.
- `verification.md` of this spec records the suites, the build, the hashes, where the
  files are, and what stays open: the owner's check on the spare board, and the memory
  of a board without PSRAM, which the firmware takes from the chip's internal memory
  first and which the original board left 65,000 bytes of with twenty outputs.
- The seed's state is `in_progress` from the first task on, and stays so until the
  merge; the line of seed 76 in `AGENTS.md` names the open pull request.
