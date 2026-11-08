# Design

## Boundaries

The firmware gets a second build environment, for the spare board's module, and the
firmware tool a second image, built and verified beside the installation's, which stays
as it is in its environment, its image and its release name. The tool learns the spare's
partition table as a third layout, writes the spare's image on it, and refuses the stock
files and the installation's image on it. The usermod's host text names the memory the
board has, and the core's room for the text grows from 96 to 128 bytes, the one change
of the core. The 192 KB reserve of `allocate()`, the reader of the card, the probe, stick
and standalone builds, `--microsd`, the emulator and the app are not changed; no
command, reply member or error code is added; no wiring, power or LED is touched.

## The second environment

- `firmware/platformio_override.ini.in`: a fifth section after
  `[env:odrig_microsd_probe]`, verbatim:

  ```
  [env:odrig_microsd_n8r2]
  extends = env:odrig_microsd
  board_build.arduino.memory_type = qio_qspi
  board_build.partitions = @REPO@/firmware/partitions/odrig-8mb.csv
  board_upload.flash_size = 8MB
  board_upload.maximum_size = 3145728
  build_unflags = ${env:odrig_microsd.build_unflags}
    -D WLED_RELEASE_NAME=\"odrig_ESP32-S3_16MB_opi\"
  build_flags = ${env:odrig_microsd.build_flags}
    -D WLED_RELEASE_NAME=\"odrig_ESP32-S3_8MB_qspi\"
  ```

  The platform, `platform_packages`, `lib_ignore`, the usermod, the core, the include
  paths, `odrig_newer.h`, the SD pins, the flash mode `qio` and `-DBOARD_HAS_PSRAM` are
  inherited. `board_upload.maximum_size` is given because PlatformIO does not take it
  from a table without an `ota_0` slot. The `build_unflags` precedent is WLED's own
  `waveshare_esp32s3_32MB_hub75`, which takes out an inherited release name the same
  way. The comment at the head of the file gains a sentence naming the environment as
  the spare's module's. `override_text()` of `firmware/fwtool/wled.py` is unchanged: it
  fills `@REPO@` in the table's path as in the include paths.

## The partition table

- `firmware/partitions/odrig-8mb.csv`, new and tracked: a first line
  `# Name,Type,SubType,Offset,Size`, then the five rows as the seed gives them, one a
  line, LF, a final newline: `nvs,data,nvs,0x9000,0x5000`,
  `otadata,data,ota,0xE000,0x2000`, `app0,app,factory,0x10000,0x300000`,
  `spiffs,data,spiffs,0x310000,0x4E0000`, `coredump,data,coredump,0x7F0000,0x10000`.
- `firmware/fwtool/partitions.py`: `EIGHT_MB`, beside `BIGGER` and in its form:
  `nvs` 0x02 0x9000/0x5000, `otadata` 0x00 0xE000/0x2000, `app0` of the type
  application and the subtype 0x00 at `APPLICATION_ADDRESS` of 0x300000, `spiffs` 0x82
  0x310000/0x4E0000, `coredump` 0x03 0x7F0000/0x10000; `EIGHT_MB_NAME = "8 MB"`;
  `EIGHT_MB_END = 0x800000` and `SIXTEEN_MB_END = 0x1000000`. `layout_of(found)`: with
  more than one application partition `WLEDS`, as today; with one or none, the end of
  the last partition, the largest `offset + size`, names it: `EIGHT_MB_NAME` at
  `EIGHT_MB_END`, `BIGGER_NAME` at `SIXTEEN_MB_END`, and any other end is
  `Failure("layout-mismatch", ...)` naming the end found and the two ends known; a table
  with no application partition is named by its end as a one-slot table is, and
  `check()` refuses it afterwards, no application partition at 0x10000, as today.
  `layout_line()` is unchanged and so prints `layout: 8 MB, storage 5111808 bytes` on
  the spare's table, and refuses any other one-slot table. `table()`, `parse()`,
  `application()`, `storage()` and `check()` are unchanged. The docstring of the module
  says three layouts.
- `firmware/fwtool/cli.py`: `installations_layout(port)`, new: reads the board's table
  through `flasher.Flasher(port).read_table()`, which reads the table once more, before
  `wleds_storage()` or `write_application()` read it; a table that `partitions.parse()`
  cannot read, `layout-mismatch` from `parse()`, is let through as `wleds_storage()`
  lets it through, so that `restore-stock --full` still brings back a board whose
  table is half-written; a parsed table that `partitions.layout_of()` names `8 MB`
  raises `Failure("layout-mismatch", ...)`: for `restore-stock`, that the stock files
  are the 16 MB module's and their table ends at 0x1000000; for `install-firmware`,
  that the installation's image is not the spare's and `flash --image` writes the
  spare's. `_restore_stock()` calls it after `stock.checked()` and `board.find()` and
  before `wleds_storage()` and `write_application()`, so that the refusal comes with or
  without `--full` and before any write; `_install_firmware()` calls it after
  `board.find()` and before `write_application()`. `wleds_storage()`, which answers
  nothing for a layout that is not `bigger`, is not the gate. `write_application()`,
  `storage_of()`, `_flash()`, `_recover_storage()` and `_big_storage()` are unchanged:
  on the spare's table `flash`, `install-show`, `set-wifi`, `set-limit`, `read-limit`,
  `read-show` and `recover-storage` go through `layout_line()` and `partitions.check()`
  as on the bigger layout, with the storage at 0x310000 of 0x4E0000, and `big-storage`
  refuses the table entry for entry as today.
- `firmware/fwtool/provenance.py`: `GROUPS` gains `'firmware/partitions'` and
  `SOURCE_ENDINGS` gains `'.csv'`, so that `source_inputs()` lists
  `firmware/partitions/odrig-8mb.csv` with its SHA-256.

## The firmware tool

- `firmware/fwtool/build.py`: `KINDS["n8r2"] = Kind("odrig_microsd_n8r2",
  "odrig-firmware-n8r2.bin")`; `ON_NEWER = ("firmware", "probe", "microsd", "n8r2")`;
  `MODULES = ("n16r8", "n8r2")` and `DEFAULT_MODULE = "n16r8"`; `module_of(kind)`, new:
  `"n8r2"` for the kind `n8r2` and `DEFAULT_MODULE` for every other kind. `_build()`
  calls `provenance.write(kind, made.environment, image, newer, module_of(kind))`; the
  rest of `build()`, `_build()`, `keep()`, `check_size()` and `APPLICATION_SIZE` is
  unchanged, the comment of `APPLICATION_SIZE` saying that `app0` has that size on
  WLED's 16 MB layout and on the 8 MB one.
- `firmware/fwtool/provenance.py`: `record()` and `write()` take `module`, a keyword
  with the default `'n16r8'`, and the record has the field `module` after
  `environment`.
- `firmware/fwtool/cli.py`: `parser()` gives `build` the option `--module` with
  `choices=build.MODULES` and `default=build.DEFAULT_MODULE`. `_build()` takes the kind
  `n8r2` when `arguments.module` is `n8r2`, before the choices of today. `parsed()`
  checks first, for `build` with a module other than the default, that the kind is
  `firmware` and that `--stick`, `--standalone` and `--microsd` are not given, else
  `made.error("--module n8r2 does not go with --stock, --probe, --stick, --standalone
  or --microsd")`, exit status 2 as for `--microsd`'s conflicts. `flash`,
  `install-firmware` and the other commands get no option.
- `firmware/verify_build.py`: `Module = namedtuple("Module", "kind environment
  flash_size release suffix")` and `MODULES = {"n16r8": Module("firmware",
  "odrig_microsd", 0x4, "odrig_ESP32-S3_16MB_opi", ""), "n8r2": Module("n8r2",
  "odrig_microsd_n8r2", 0x3, "odrig_ESP32-S3_8MB_qspi", "-n8r2")}`. `checked(image,
  module)`: after the header check of today, `data[3] >> 4 != module.flash_size` is
  `build-failed`, "the image header says a flash size that is not the module's"; the
  bytes must hold `module.release` encoded as ASCII, else `build-failed`, "the image
  does not hold the release name of its module", and must not hold the other module's,
  else `build-failed`, "the image holds the release name of the other module"; the
  environment check compares with `module.environment` in place of the literal
  `'odrig_microsd'`; the checks of the provenance's hash and bytes, WLED's commit, the
  inputs and the commit are as today. `inspect(name)`: `module = MODULES[name]`,
  `image = build.image_path(module.kind)`, the ELF at
  `paths.WLED / '.pio' / 'build' / module.environment / 'firmware.elf'`, the entry
  points as today, and the files `paths.OUT / f'image-info{module.suffix}.txt'` and
  `paths.OUT / f'verification{module.suffix}.json'`; the report keeps its fields,
  `environment` being the module's. `__main__` parses `--module` with
  `choices=sorted(MODULES)` and the default `n16r8` and calls `inspect()` with it; the
  docstring says the default build or the spare's.

## The host text

- `firmware/usermod/odrig_usermod.cpp`: `size_t internalFreeAtStart = 0;` in the
  anonymous namespace before `aboutHost()`. `setup()` sets it to
  `heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)` on the line after
  `host.about = aboutHost;` and before `core = odrig_core_begin(&host);`. `aboutHost()`
  prints `"%s %s %s %s external %u internal %u reset %s"` with `WLED_RELEASE_NAME`,
  `__DATE__`, `__TIME__`, the storage, `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)`
  and `internalFreeAtStart` cast to `unsigned`, and the reset reason as today; the
  reset reasons and the storage names are unchanged. The comment above it names the two
  numbers. The longest text is 119 characters, with `odrig_ESP32-S3_16MB_opi`, an
  external of seven digits, an internal of six and `interrupt-watchdog`.
- `core/src/commands.cpp`: `kAboutSize = 128`, its comment "127 bytes and the closing
  zero"; the trim of the escaped text at 160 bytes and the reply's room are unchanged.
- `emulator/host.py`, `app/www/messages.js` and `app/www/screens/`: unchanged.

## The workflow

- `.github/workflows/firmware-hosts.yml`: after "Offline image, source and symbol
  inspection", the steps "Spare module build", `python -X utf8 firmware/fw.py build
  --module n8r2`, and "Offline inspection of the spare's image", `python -X utf8
  firmware/verify_build.py --module n8r2`; the artifact's paths gain `odrig
  source/build/firmware/WLED/.pio/build/odrig_microsd_n8r2/firmware.elf`, and
  `build/firmware/out/` carries both images, their records and the four verification
  files already. The timeout stays at 90 minutes; a run that reaches it is a question
  for rule 7.

## The tests

- `tests/firmware/test_wled.py`, `Override`: the file-wide check of
  `test_it_has_the_two_environments_on_wleds_own` for `board`,
  `board_build.partitions`, `board_build.flash_mode` and `board_upload.flash_size` is
  narrowed to the sections `odrig`, `odrig_probe`, `odrig_microsd` and
  `odrig_microsd_probe`; `test_the_spares_environment_names_its_module`, new, seen
  failing first against the override without the section: `[env:odrig_microsd_n8r2]`
  extends `env:odrig_microsd`, and by `configparser` the section's
  `board_build.arduino.memory_type` is `qio_qspi`, `board_build.partitions` is
  `<root>/firmware/partitions/odrig-8mb.csv` with the repository's posix path,
  `board_upload.flash_size` is `8MB`, `board_upload.maximum_size` is `3145728`, it sets
  neither `board` nor `platform` nor `board_build.flash_mode`, its `build_unflags` ends
  with `-D WLED_RELEASE_NAME=\"odrig_ESP32-S3_16MB_opi\"` and its `build_flags` with
  `-D WLED_RELEASE_NAME=\"odrig_ESP32-S3_8MB_qspi\"`.
- `tests/firmware/support.py`: `EIGHT_MB_LAYOUT`, the five tuples of the spare's table,
  and `small_eight_mb_layout(blocks=64)`, the same with a storage of a few blocks at
  0x310000 and `coredump` still at 0x7F0000.
- `tests/firmware/test_layouts.py`, `Tables`: `test_the_8_mb_layout_is_the_spares_table`,
  new, seen failing first: `partitions.table(partitions.EIGHT_MB)` equals
  `support.partition_table(support.EIGHT_MB_LAYOUT)`, has the SHA-256
  `dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`, and equals
  `.pio/build/odrig_microsd_n8r2/partitions.bin` of `paths.WLED` when that file is
  there; `check()` of it gives `app0` 0x00 at 0x10000 of 0x300000 and the storage at
  0x310000 of 5,111,808 bytes ending at 0x7F0000; `firmware/partitions/odrig-8mb.csv`,
  read line by line past the comment with the names `data`, `app`, `nvs`, `ota`,
  `factory`, `spiffs` and `coredump` turned into the numbers of `Partition`, equals
  `list(partitions.EIGHT_MB)`. `test_each_table_is_named_by_its_firmware_slots` gains
  `(support.EIGHT_MB_LAYOUT, "8 MB")` and `(support.small_eight_mb_layout(), "8 MB")`,
  and a one-slot table whose `coredump` lies at 0xBF0000 is `layout-mismatch` from
  `layout_of()`; `test_the_line_names_the_layout_and_the_size_of_its_storage` gains
  `layout: 8 MB, storage 5111808 bytes`. `OnEachLayout.LAYOUTS` gains `("8 MB",
  support.small_eight_mb_layout(), 0x310000)`, so that `install-show`, `read-show`,
  `read-limit`, `set-limit` and `flash` run on the spare's table and `flash` writes
  `("0x10000", "odrig-firmware.bin")`. `RefusedOnTheSpare`, new, seen failing first:
  `restore-stock`, `restore-stock --full`, each with a stand-in stock folder and the
  listing of its hashes as `Temporary.stock_folder()` of `tests/firmware/test_flasher.py`
  makes them, `stock.LIST` patched to that listing, and `install-firmware` with
  `build.checked_image` patched to a small image file of the test, as `InstallFirmware`
  of `tests/firmware/test_wifi_commands.py` does, so that the refusal comes from the
  table and not from a missing image, each on `support.RecordedEsptool` of the 8 MB
  stand-in, end with status 1, `error: layout-mismatch: ...`, `esptool.wrote == []` and
  `"write-flash"` not in `esptool.commands()`; and `restore-stock --full` on a stand-in
  whose table is all 0xFF still writes the three stock files at 0x0, 0x8000 and
  0x10000, as today.
- `tests/firmware/test_flasher.py`, `RestoreStock`, both tests of the command sequence,
  `tests/firmware/test_wifi_commands.py`, `InstallFirmware`, the test of what it does,
  the test of a board that does not answer after the flash and
  `test_storage_is_read_only_after_the_firmware_has_answered`, whose `answered` becomes
  `[4, 9]` and `reads_of_storage` `[5]`, and `tests/firmware/test_limit_commands.py`,
  `InstallFirmware`: the expected sequence of `restore-stock`, `restore-stock --full`
  and `install-firmware` gains a first `read-flash`, the table `installations_layout()`
  reads before anything is written; in the test of `--full` that checks the arguments
  of the one `read-flash` call, that check becomes a check of the first `read-flash`
  call's arguments, both reads being of `0x8000`, `0xc00`, since
  `RecordedEsptool.call()` insists on one call of a command;
  `installations_layout()` prints nothing, so the first line `layout: bigger, ...` that
  `test_big_storage.py` expects of `restore-stock --full` on the bigger layout stays.
- `tests/firmware/test_partitions.py`: `parse()` of `partitions.table(EIGHT_MB)` gives
  its five partitions, and `layout_of()` of them is `8 MB`.
- `tests/firmware/test_cli.py`: `test_the_three_images_and_their_environments` gains
  `KINDS["n8r2"] == ("odrig_microsd_n8r2", "odrig-firmware-n8r2.bin")` and `"n8r2"` in
  `ON_NEWER`, seen failing first; `Building` gains the case `--module n8r2` with the
  environment `odrig_microsd_n8r2` and `--module n16r8` with `odrig_microsd`, seen
  failing first; `TheModule`, new, seen failing first: `--module n8r2` with each of
  `--stock`, `--probe`, `--stick`, `--standalone` and `--microsd` ends with status 2 and
  `--module n8r2 does not go with` in the error, `build.build` not called, and
  `--module n4r2` is refused by the choices.
- `tests/firmware/test_microsd_build.py`: gains one test, seen failing first:
  `build --microsd --module n8r2` ends with status 2, `does not go with` in the error
  and `build.build` not called; its loop of `--microsd`'s conflicts stays as it is,
  since `parsed()` answers the module's conflict first.
- `tests/firmware/test_newer_software.py`, `TheImages`: the test of the newer
  software's kinds expects `build.ON_NEWER == ("firmware", "probe", "microsd", "n8r2")`,
  seen failing first.
- `tests/firmware_host/test_build.py`: `expected` gains `'n8r2':
  ('odrig_microsd_n8r2', 'odrig-firmware-n8r2.bin', True)`, and the recorded call is
  `(kind, environment, image, newer, module)` with `n8r2` for that kind and `n16r8` for
  every other, seen failing first.
- `tests/firmware_host/test_provenance.py`: the test of the inputs puts
  `firmware/partitions/odrig-8mb.csv` into its root and expects it listed, beside
  `core/player.cpp`, seen failing first; the test of the record expects `module`
  `n16r8` without the keyword and `n8r2` with it.
- `tests/firmware_host/test_verify.py`, new, seen failing first: `verify_build.checked()`
  on an image made in a temporary `paths.OUT` with a header of the module's flash size,
  the module's release name in its bytes and a provenance made with `provenance.write()`
  under mocked `git_identity()`, `versions()` and `source_inputs()`, passes for each
  module and refuses, as `build-failed`, a header of the other flash size, bytes that
  hold the other release name, bytes that hold none, and a provenance of the other
  environment; and `verify_build.MODULES` names the two kinds, environments, nibbles
  0x4 and 0x3, release names and suffixes.
- `tests/firmware/test_usermod_kept.py`, `TheAbout`: gains the words
  `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)`,
  `heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)`, the format
  `"%s %s %s %s external %u internal %u reset %s"` and `internalFreeAtStart`, and that
  in `setup()` the line setting `internalFreeAtStart` lies after
  `host.about = aboutHost;` and before `core = odrig_core_begin(&host);`, seen failing
  first.
- `tests/core/test_readiness.py`, `TheHostsName`: `"x" * 127` reported whole and
  `"x" * 200` cut to `"x" * 127`, seen failing first against the core of 96 bytes,
  which cuts both to 95.
- `tests/firmware/test_docs.py`: `test_it_names_every_option_of_every_command` fails
  first once `--module` exists and the synopsis lacks it, and the synopsis line is
  changed in the task that adds the option, so that the firmware suite passes at every
  commit; the test of the regions gains the rows of the 8 MB table,
  `| \`spiffs\` | \`0x310000\` | \`0x4E0000\`` among them, and a check of the Commands
  section for the line `layout: 8 MB, storage 5111808 bytes`; the test of the kinds
  table, or a new one, expects the row `build --module n8r2` with `odrig_microsd_n8r2`
  and `odrig-firmware-n8r2.bin`.
- `tests/air/test_wled.py`: unchanged, `RELEASE = "odrig_ESP32-S3_16MB_opi"`.

## The documentation

- `docs/firmware.md`: the synopsis line of `build` becomes `python3 firmware/fw.py
  build [--stock | --probe] [--standalone | --stick | --microsd] [--module n16r8|n8r2]
  [--verbose]`; the code block of `build` gains `python3 firmware/fw.py build --module
  n8r2`; the table of kinds gains the row `build --module n8r2`, `odrig_microsd_n8r2`,
  `odrig-firmware-n8r2.bin`, "The spare board's firmware: the firmware built for the
  module with 8 MB of flash and 2 MB of quad PSRAM, the memory type `qio_qspi`, the
  tracked table `firmware/partitions/odrig-8mb.csv` and the release name
  `odrig_ESP32-S3_8MB_qspi`"; a paragraph after the one of `--microsd` says what
  `--module` is, that `n16r8` is the default, that `n8r2` does not go with `--stock`,
  `--probe`, `--stick`, `--standalone` or `--microsd`, that the framework is compiled
  again for it, about 12 minutes, that `.pio/libdeps/odrig_microsd` can be copied by hand
  to `.pio/libdeps/odrig_microsd_n8r2` first, and that `flash --image
  build/firmware/out/odrig-firmware-n8r2.bin` writes it; the paragraph of `--microsd`
  says it does not go with `--module n8r2` either; "All eight kinds" becomes "All nine
  kinds" with "the spare's module" in the list; "Host builds and verification" names
  `build --module n8r2`, `verify_build.py --module n8r2`, `image-info-n8r2.txt` and
  `verification-n8r2.json`, and says the workflow builds and verifies both images; the
  libdeps sentence names `.pio/libdeps/odrig_microsd_n8r2`; "The layout" says "which
  of the three layouts" with the line `layout: 8 MB, storage 5111808 bytes`; the row of
  `layout-mismatch` says also a one-slot table that ends neither at `0x800000` nor at
  `0x1000000`, and the `8 MB` layout under `restore-stock` and `install-firmware`; "The
  regions of the flash" says the installation's board has WLED's 16 MB layout and the
  spare the 8 MB one, keeps its table of WLED's layout as it is, and after the bigger
  layout's table gives the 8 MB layout's: `nvs`, `otadata` as in WLED's; `app0`, a
  factory slot, `0x10000`, `0x300000`; `spiffs`, `0x310000`, `0x4E0000`, 5,111,808
  bytes; `coredump`, `0x7F0000`, `0x10000`; with the sentence that `flash --image`
  writes the spare's image on it, that `restore-stock` and `install-firmware` refuse it,
  and that no command writes its bootloader or its table; "The name in `status`" gains
  `external` with the external memory in the heap, 0 when none was found, and
  `internal` with the internal memory free when the core started, both plain decimals,
  between the storage and `reset`.
- `docs/core.md`: the row of `about` says room for 128 bytes where it says 96; line 187,
  `as95input bytes`, becomes `as 127 input bytes`; and the sentence of the status
  metadata that says `95-byte ASCII descriptions` says `127-byte`.
- `docs/commands.md`: the row of `host` says "on the board its build, its storage, the
  external memory it found and the internal memory free when the core started, and the
  reason of its last start, at most 127 characters"; line 438, `at most95input bytes
  and256escaped bytes`, becomes `at most 127 input bytes and 256 escaped bytes`.
- `docs/android-app.md`: the sentence of the target screen says the board gives its
  release, the date and the time of its build, its storage, its external memory and the
  internal memory free at its start, and the reason of its last start.
- `docs/firmware-additions.md`: line 29 of the list: names in `status` the memory the
  board has, the external memory in the heap and the internal memory free when the core
  started; seed 77; `odrig_usermod.cpp`; Written again; Seed 12: No.
- `docs/firmware-prerequisites.md`: the row of the board says that the spare board's
  module, 8 MB of flash and 2 MB of quad PSRAM, has an image of its own,
  `odrig-firmware-n8r2.bin` from the environment `odrig_microsd_n8r2`, and that the
  installation's board keeps its image.
- `docs/decisions.md`: the line `Board: ESP32-S3-N16R8 (16 MB flash, 8 MB PSRAM)` stays;
  a change-log entry appended at the end of the file, after the paragraph of seed 69,
  dated 2026-11-05: the owner's words of that day, that the two issues persisted after
  the flash of seed 76's image and that the fix is a seed on master with no open
  questions, and the decision taken under that order: the firmware comes in two images
  from now on, one for the installation's module and one for the spare's, the
  installation's environment, image and release name unchanged, the spare's from
  `odrig_microsd_n8r2` with the tracked table equal to the spare's, and the 192 KB
  reserve kept.
- `docs/drifts.md`: what rule 7 decides on the way, appended at the end as entries
  `## Seed 77: <subject>` with the question, the answer and the resolution: first
  `## Seed 77: the core's page and the room for the host text`, that `docs/core.md`,
  which the seed does not name, says the room the core keeps and is changed with it.
  The seed leaves nothing else open that this design does not fix; what the build or
  the suites turn up is recorded there by the implementer.

## Delivery

- The branch `seed-77-firmware-for-the-spare-module` from `master` at bb0658e, one
  commit per task, a pull request of its own against `master`; pull request #49 stays
  seed 76's and is not touched.
- Both images are built on this Windows computer from the pull request's head with a
  clean tree, so that the records say `trackedDirty` false: `python firmware/fw.py
  setup`, `python firmware/fw.py build --module n8r2` and `python firmware/fw.py build`,
  the toolchains shared through `ODRIG_TOOLS`, a folder of this checkout's `scratch/`
  whose `firmware/hosts` is a junction to the host toolchains of an earlier build on
  the computer, as seed 76's delivery arranged them, which hold the `qio_qspi`
  libraries already; `.pio/libdeps/odrig_microsd` may be copied by hand to
  `.pio/libdeps/odrig_microsd_n8r2` first. The spare's build compiles the framework
  again, about 12 minutes. Then `python firmware/verify_build.py --module n8r2` and
  `python firmware/verify_build.py`, the spare's `image-info-n8r2.txt` saying
  `Flash size: 8MB`, and the suites: `python tests/run.py --suites
  firmware,firmware-host,runner --workers 2`, the core's suite, the converter's
  documentation test and the onboarding suite.
- The Drive, `odrig archive/seed-77/`: `odrig-seed77-<commit>-n8r2-at-0x10000.bin` and
  `odrig-seed77-<commit>-n16r8-at-0x10000.bin`, `<commit>` the short hash of the pull
  request's head, each with `.bin.sha256`, the hash and the new name, and
  `.bin.build.json`, the tool's record as it is, and `<stem>-image-info.txt` and
  `<stem>-verification.json`, the files of `verify_build.py` renamed, as seed 76's
  delivery named its files; `README.txt`, LF and ASCII, saying which image is for which
  module; that only the application image is flashed, at offset 0x10000 and no other,
  the flasher's offset field read before `Flash`, the flash settings kept, no erase, the
  bootloader and the partition table not written; that the `Installation:` line is read
  first after the flash, with the four readings: `odrig_ESP32-S3_8MB_qspi` with an
  `external` that is not 0 on the spare is the fix at work; `odrig_ESP32-S3_16MB_opi`
  with `external 0` on the spare is the installation's image, flashed by mistake;
  `odrig_ESP32-S3_8MB_qspi` with `external 0` on the installation's board is the
  spare's image there, that board running without its PSRAM until its own is flashed
  back; `odrig_ESP32-S3_8MB_qspi` with `external 0` on the spare is the PSRAM not found
  or its test failed, a finding for a seed of its own; that `reset other` right after a
  flash and `reset power-on` after a power cycle are neither a finding; that a spare
  showing no hotspot a minute after a flash is flashed again with the spare's image at
  0x10000, a spare showing none after that with the installation's image at 0x10000, a
  hotspot then meaning the spare's image does not come up on the spare, a finding for a
  seed of its own, and a spare showing none after the installation's image had a file
  written at 0x0 or 0x8000, for which the subfolder is; and that the APK of seed 75,
  `odrig-seed75-f5ad253.apk` of `odrig archive/seed-75/`, works with both, an APK that
  shows no `Installation:` line being older and replaced first. The subfolder
  `only-if-the-flash-was-erased/`: `odrig-seed77-<commit>-n8r2-bootloader-at-0x0.bin`,
  `bootloader.bin` of `.pio/build/odrig_microsd_n8r2/`, and
  `odrig-seed77-<commit>-n8r2-partitions-at-0x8000.bin`, its `partitions.bin`, byte for
  byte the Drive's `wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`, each with its
  `.sha256`, and a `README.txt` of their own: for a spare whose flash was erased, or on
  which a file was written at 0x0 or 0x8000 by mistake, and for nothing else; then the
  bootloader at 0x0, the table at 0x8000 and the spare's image at 0x10000, in that
  order, the flash settings kept, no erase, the storage at 0x310000 keeping the network
  name. No file is named `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`; nothing
  above `seed-77/` is touched; no storage image is read or printed. No APK is built.
- `verification.md` of this spec, written by the last task in the form of seed 76's:
  the commits by task; the suites by task with the failures seen first and their text;
  both images with their bytes, SHA-256, ELF SHA-256, the flash size of the header and
  the release name, `trackedDirty` false, the tool versions and the build times; the
  Drive paths and the Drive links of the folder and of each image; the result of the
  workflow's checks on the pull request; and what stays open: the owner's checks of
  7.4.
- The seed's state is `in_progress` from the first task on, and stays so until the
  merge; the line of seed 77 in `AGENTS.md` names the open pull request.
