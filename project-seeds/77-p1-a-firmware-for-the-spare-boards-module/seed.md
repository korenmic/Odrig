# A firmware for the spare board's module

## Summary

The firmware is built for the installation's board alone, an ESP32-S3 module with 16 MB
of flash and 8 MB of octal PSRAM: WLED's environment `esp32s3dev_16MB_opi`, which the
build environment `odrig_microsd` extends, and the release name `odrig_ESP32-S3_16MB_opi`.
The spare board the owner installed is another module, with 8 MB of flash and 2 MB of
quad PSRAM. Built for octal memory, the firmware never finds the spare's PSRAM, so the
board runs with no external memory; and since seed 22 the core gets internal memory only
while 192 KB of it stays free, and external memory otherwise, which the spare does not
have. The core starves at its start, the show is invalid, and the fix of seed 76, which
lets an empty board take its first animation, cannot show. This seed adds a second build
environment for the spare's module, with the memory type `qio_qspi`, 8 MB of flash and a
partition table of the repository equal to the one the spare has, which the firmware tool
builds and verifies as a second image, `odrig-firmware-n8r2.bin`, beside today's image,
which stays as it is for the installation's board; and the firmware says in `status` what
memory the board it runs on has, the external memory it found and the internal memory
that was free when the core started, which the app shows on its Target page. The 192 KB
reserve stays. No new command; the app is not changed. The branch is made on top of seed
76's, and one pull request carries both.

## Priority

- `P1`

## Depends On

- Seed 76, pull request #49, branch `seed-76-empty-board-first-animation` at `abc75ea`,
  not merged: the core plays a board without `mapping.json` and without `show.json`,
  which the empty spare needs; its image `odrig-seed76-7c397c5.bin` is the one the owner
  flashed on 2026-11-05. This seed's branch starts from that branch.
- Seed 22, commit `bddc2ce`: `allocate()` of `firmware/usermod/odrig_files.cpp`, which on
  ESP-IDF 5 gives the core internal memory only while `INTERNAL_RESERVE`, 192 KB, stays
  free, and external memory otherwise; `host_memory()` and `arena_take()` of
  `core/src/arena.h`, the one place where the core asks for memory.
- Seed 04, the firmware tool: `firmware/fw.py` and `firmware/fwtool/`; `KINDS`,
  `ON_NEWER`, `APPLICATION_SIZE`, `_build()` and `keep()` of `firmware/fwtool/build.py`;
  `parser()`, `_build()`, `parsed()`, `write_application()`, `wleds_storage()` and
  `_restore_stock()` of `firmware/fwtool/cli.py`; `WLED`, `BIGGER`, `table()`, `parse()`,
  `check()`, `layout_of()` and `layout_line()` of `firmware/fwtool/partitions.py`;
  `KEEP` of `firmware/fwtool/flasher.py`, which writes an image with the flash settings
  of its header.
- Seed 38, the microSD card: `[env:odrig_microsd]` of
  `firmware/platformio_override.ini.in` on the pioarduino platform `55.03.312-1`, which
  `override_text()` of `firmware/fwtool/wled.py` fills with the repository's path at
  `@REPO@`; `begin()` of `firmware/usermod/odrig_drive.cpp`, which asks the card's name
  tables from external memory.
- Seed 60, the firmware builds on every computer: the shared toolchains, with the quad
  variant of the libraries in them; `record()`, `source_inputs()` and `write()` of
  `firmware/fwtool/provenance.py`; `checked()` and `inspect()` of
  `firmware/verify_build.py`; the workflow `.github/workflows/firmware-hosts.yml`.
- The standalone template of seed 12, cancelled, `firmware/standalone/platformio.ini.in`:
  the precedent of an environment that names the memory type, the absolute path of its
  partition table, the flash size and the largest image itself, which
  `tests/firmware/test_standalone.py` accepts.
- The host text: `aboutHost()` of `firmware/usermod/odrig_usermod.cpp`, set as
  `host.about` in the usermod's `setup()` before `odrig_core_begin()`; `kAboutSize` of
  `core/src/commands.cpp`, 96 bytes, and `status`'s `host` in
  [commands.md](../../docs/commands.md); `ofHost()` of `app/www/messages.js`, which the
  Target page shows as `Installation: <host>`.

## Product Context

On 2026-11-05 at 14:06 the owner, at the installation with the spare board and the phone,
flashed the image of seed 76, `odrig-seed76-7c397c5.bin`, from the phone as that seed's
README says: the application image at offset 0x10000, the flash settings kept, no erase,
`Flash done`. The app then still showed no canvas, as at 06:41 that morning. The owner
wrote: "I flashed your new fw as you asked me to, but the 2 issues persisted." and "If
you think the actual fix is a new seed then create it on master right now. Then tell me
if its ready for s2s with zero open questions."

What the spare is, read on 2026-11-05:

- The installation's board is an ESP32-S3 with 16 MB of flash and 8 MB of octal PSRAM,
  the N16R8 of [decisions.md](../../docs/decisions.md). The spare's chip line in esptool,
  read by the owner on 2026-11-05, is `Chip features: Wi-Fi, BT 5 (LE), Dual Core + LP
  Core, 240MHz, Embedded PSRAM 2MB, AP_3v3`, and WLED's `/json/info` on 2026-11-03, in
  the field notes of pull request #47,
  `docs/field-notes/2026-11-03-rotation-and-sd-recovery.md` on its branch
  `codex/phone-storage-seeds-20261103`, not merged, gave `flash 8, psram 0, psrSz 0`.
  That is a module of the N8R2 kind: 8 MB of quad flash and 2 MB of quad PSRAM. The chip
  line is in no file; it is the owner's report.
- The spare's partition table was made on 2026-11-03 and is on the Drive as
  `Artifacts/odrig/odrig archive/wifi-storage/odrig-8mb-partition-table-at-0x8000.bin`,
  3,072 bytes, SHA-256
  `dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`. Parsed with
  `firmware/fwtool/partitions.py`: `nvs` 0x9000/0x5000, `otadata` 0xE000/0x2000, `app0`
  of the kind factory 0x10000/0x300000, `spiffs` 0x310000/0x4E0000, 5,111,808 bytes, and
  `coredump` 0x7F0000/0x10000: the bigger layout scaled to 8 MB. The `Internal storage:
  Free 5.1 MB of 5.1 MB` the app shows is that storage, so the table is what the spare
  has. One firmware slot: what the phone writes at 0x10000 is what boots.

What the code does, read on 2026-11-05:

- `[env:odrig]` of `firmware/platformio_override.ini.in` extends WLED's
  `esp32s3dev_16MB_opi`, whose memory type is `qio_opi`, flash size 16 MB and partition
  table WLED's 16 MB one, with `-DBOARD_HAS_PSRAM`; `odrig_microsd`, the firmware,
  extends it. The libraries of `qio_opi` in the newer software initialize the PSRAM at
  boot in octal mode and ignore it when it is not found, `CONFIG_SPIRAM_BOOT_INIT` and
  `CONFIG_SPIRAM_IGNORE_NOTFOUND` in their `sdkconfig.h`, which is why the image boots on
  the spare with `psram 0`. Every image delivered so far, seed 76's among them, was built
  so: the environment `odrig_microsd`, `Flash size: 16MB` in its header.
- `allocate()` of `firmware/usermod/odrig_files.cpp`: on ESP-IDF 5, internal memory only
  while the free internal memory is at least the block and 192 KB, then external memory,
  then nothing. Seed 22's commit `bddc2ce` measured 278,076 bytes of internal memory free
  before the core and 134,032 after, the core taking about 144 KB, and WLED's `Heap low`
  and `Heap panic! Reset strip, reset connection` when the LED outputs and ESP-IDF 5's
  Wi-Fi then took the rest: the core and WLED do not fit in the internal memory together,
  and the reserve is what keeps the network up on the installation's board. On the spare
  the blocks the reserve refuses have nowhere to go.
- The core asks its memory block by block through `host.alloc`, in `core/src/core.cpp`,
  `core/src/mapping.cpp` and `core/src/show.cpp`: the core object, the line of 2 KB and
  the reply of 1 KB, then in `read_mapping()` the legs, `led_pixel` of 7,200 bytes,
  `led_data` of 10,800 and the strip bits, then the pixels of 10,800, the window of
  32,768, the chunk of 1,500, the checker, `check_pixels` and `check_window` of the same
  sizes, the drive's tables, the show's tables of 128 items, the order's block and the
  mini. The first refused block fails the start with `out-of-memory`.
- `status` in `core/src/commands.cpp` reports `width` and `height` only while
  `leg_count` is not 0, which `read_mapping()` sets before its second reading; the app's
  test for `no-canvas`, `prepareReady()` of `app/www/convert.js` and `make()` of
  `app/www/screens/storage.js`, looks at the two alone, and the Target page shows the
  show's `error` as a line of its own, `The installed show is invalid: <reason>.`, from
  `ofInvalidShow()` of `app/www/messages.js`. So a start refused inside `read_mapping()`
  leaves no canvas beside `out-of-memory`, and a start refused after it leaves the canvas
  of 60 x 60 beside it. The old image stopped earlier, at `mapping-missing`, and hid the
  memory from view; the owner has not read the Target page's invalid-show line yet, and
  the diagnosis rests on the code and the numbers.
- `begin()` of `firmware/usermod/odrig_drive.cpp` asks the card's name tables, 65,536 and
  26,624 bytes, from external memory alone and returns without starting the reader when
  it gets none: on the spare the card reader cannot start either, for the same want.
  WLED's information then keeps its first text, `SD not configured`, since `begin()`
  returns before `setSummary()` ever runs, as the field notes of pull request #47
  recorded on 2026-11-03.
- `aboutHost()` of `firmware/usermod/odrig_usermod.cpp` gives `status` the host text,
  `<release> <date> <time> <storage> reset <reason>`, 76 characters today and 86 with
  `interrupt-watchdog`, and nothing about the memory; the core holds it in `kAboutSize`,
  96 bytes, and [commands.md](../../docs/commands.md) says at most 95 characters.
- WLED's `platformio.ini` has `esp32s3dev_8MB_qspi`, memory type `qio_qspi` and flash
  mode `qio`, the quad board; its partition table, `tools/WLED_ESP32_8MB.csv`, has two
  slots of 2 MB and is not the spare's. The newer software's libraries hold the
  `qio_qspi` variant beside `qio_opi`, in the shared toolchains already: no download. Its
  `sdkconfig.h` has `CONFIG_SPIRAM_MODE_QUAD` and no initialization at boot; the Arduino
  core's `psramInit()` initializes the PSRAM before `setup()`, and `psramAddToHeap()` of
  `initArduino()` adds it to the heap.

So the fault is the firmware's: it is built for one module, and the spare is another; the
reserve of seed 22 assumes an external memory that the spare has but the firmware never
turns on; and the board does not say what memory it has, so the owner at the installation
cannot tell a starved core from a missing file. Seed 76's change is right and cannot show
on the spare until the firmware is built for the spare's module.

Before the build, the owner reads the Target page of the spare as it is, one look and no
flash: `Installation: odrig_ESP32-S3_16MB_opi Nov  5 2026 07:44:48 internal+microsd reset
<reason>` and `The installed show is invalid: out-of-memory.` confirm that seed 76's image
runs and that the core starves; `The installed show is invalid: mapping-missing.`, or
another date in the line, means the image that runs is not seed 76's and the fault is in
the flash, not the memory, and the spare's image is then flashed with the same care, its
`Installation:` line read first. The build does not wait for this reading.

## Technical Constraints

- **Two images, one for each module.** The owner asked on 2026-11-05 for the fix as a
  seed on master with no open questions; under that order this seed decides that the
  fault is the firmware's and that the firmware comes in two images from now on, one for
  the installation's module and one for the spare's, and the change log of
  [decisions.md](../../docs/decisions.md) records the owner's words and the decision. No
  wiring, power or LED is touched: the
  spare's module is what the owner installed and read. The line
  `Board: ESP32-S3-N16R8 (16 MB flash, 8 MB PSRAM)` stays: the installation's board, its
  environment `odrig_microsd`, its image `odrig-firmware.bin` and its release name
  `odrig_ESP32-S3_16MB_opi` are not changed in any way. The 192 KB reserve of seed 22
  stays as it is: its numbers show the core and WLED do not fit in the internal memory
  together, so a fallback in `allocate()` is not a fix and is not made. No APK, no new
  command, the app unchanged.
- **The second environment.** `[env:odrig_microsd_n8r2]` in
  `firmware/platformio_override.ini.in`, extending `env:odrig_microsd`, so that it has
  the platform, the libraries left out, the SD pins, `odrig_newer.h`, the usermod and the
  core as the firmware has them, and sets what the module differs in:
  `board_build.arduino.memory_type = qio_qspi`, `board_upload.flash_size = 8MB`,
  `board_upload.maximum_size = 3145728`, which PlatformIO does not take from a table
  without an `ota_0` slot, and `board_build.partitions` with the absolute path
  `@REPO@/firmware/partitions/odrig-8mb.csv`, as the standalone template gives one,
  which `override_text()` fills. The flash mode `qio` and `-DBOARD_HAS_PSRAM` are
  inherited. The release name is `odrig_ESP32-S3_8MB_qspi`: the inherited
  `-D WLED_RELEASE_NAME=\"odrig_ESP32-S3_16MB_opi\"` is taken out with `build_unflags`
  and the new one given in `build_flags`, as WLED's own `waveshare_esp32s3_32MB_hub75`
  changes an inherited release name. The image's header then says 8 MB, which
  `flasher.KEEP` and the phone write as it is.
- **The partition table.** `firmware/partitions/odrig-8mb.csv`, tracked, equal to the
  spare's table row for row: `nvs,data,nvs,0x9000,0x5000`,
  `otadata,data,ota,0xE000,0x2000`, `app0,app,factory,0x10000,0x300000`,
  `spiffs,data,spiffs,0x310000,0x4E0000`, `coredump,data,coredump,0x7F0000,0x10000`.
  `firmware/fwtool/partitions.py` learns it as a third layout, `EIGHT_MB`, named `8 MB`:
  `partitions.table(EIGHT_MB)` is the Drive file byte for byte, and `layout_of()` names
  a one-slot table whose last partition ends at 0x800000 `8 MB` and one that ends at
  0x1000000 `bigger`, where today it names every one-slot table `bigger`; any other
  one-slot table is `layout-mismatch` to every command, and a two-slot table stays
  WLED's as today. So `flash`, `install-show`, `set-wifi`, `set-limit`, `read-limit`,
  `read-show` and `recover-storage` print `layout: 8 MB, storage 5111808 bytes` on the
  spare and work as on the bigger layout, with no other change.
  `restore-stock`, with or without `--full`, refuses the `8 MB` layout with
  `layout-mismatch`: the stock files of `firmware/fwtool/stock.py` are the 16 MB
  module's, their table ending at 0x1000000, so neither the stock application alone nor
  the full set belongs on an 8 MB chip; `wleds_storage()`, which answers nothing for a
  layout that is not `bigger`, is not the gate. `install-firmware` refuses the `8 MB`
  layout the same way: the installation's image runs on the spare without its memory,
  and the spare's image goes on with `flash --image`. `big-storage` refuses the layout
  already, entry for entry. `firmware/partitions` joins `GROUPS` and `.csv`
  joins `SOURCE_ENDINGS` of `firmware/fwtool/provenance.py`, so that the table is in the
  build's identity. The phone flash needs none of this.
- **The firmware tool.** `build` and `firmware/verify_build.py` take `--module`, with the
  values `n16r8`, the default and today's behavior, and `n8r2`. `KINDS` of
  `firmware/fwtool/build.py` gets the kind `n8r2`, `Kind("odrig_microsd_n8r2",
  "odrig-firmware-n8r2.bin")`, in `ON_NEWER`; `_build()`, `keep()` and
  `provenance.write()` then make the image, its `.sha256` and its `.build.json` as for
  every kind, and `record()` names the environment and, in a field `module`, the module.
  `--module n8r2` does not go with `--stock`, `--probe`, `--stick`, `--standalone` or
  `--microsd`, refused in `parsed()` as `--microsd`'s conflicts are: the probe builds
  stay the installation's module's. `verify_build.py --module n8r2` checks
  `odrig-firmware-n8r2.bin` against its provenance, the environment
  `odrig_microsd_n8r2`, the ELF of `.pio/build/odrig_microsd_n8r2/` and the entry points,
  and writes `image-info-n8r2.txt` and `verification-n8r2.json` beside the
  installation's `image-info.txt` and `verification.json`; `checked()` also reads the
  flash size of the header, the high nibble of byte 3, which must be 0x4, 16 MB, for the
  installation's image and 0x3, 8 MB, for the spare's, and finds the release name in
  the image's bytes, `odrig_ESP32-S3_8MB_qspi` and not `odrig_ESP32-S3_16MB_opi` for the
  spare's and the reverse for the installation's: the name is what the owner reads
  first, and a release name defined twice would win silently. `flash` and
  `install-firmware` get no option:
  `flash --image build/firmware/out/odrig-firmware-n8r2.bin` writes the spare's image on
  the spare's table as it writes any image, and `install-firmware` stays the
  installation's image, which it refuses to write on the `8 MB` layout as "The partition
  table" says. Before the first build of the new environment `.pio/libdeps/odrig_microsd`
  can be copied by hand to `.pio/libdeps/odrig_microsd_n8r2`, as the page says for the
  other environments, and what is missing there PlatformIO fetches; the tool copies
  nothing. The memory type and the release name change the flags, so the framework is
  compiled again, about 12 minutes on the Windows computer. `check_size()` keeps its
  limit of 0x300000, the size of `app0` on both tables.
- **The host text.** `aboutHost()` names, after the release name, the date, the time and
  the storage, the external memory the heap holds and the internal memory that was free
  when the core started, and then the reset as today, in this form and no other:
  `<release> <date> <time> <storage> external <bytes> internal <bytes> reset <reason>`,
  for example `odrig_ESP32-S3_8MB_qspi Nov  5 2026 07:44:48 internal+microsd external
  2097152 internal 201000 reset power-on`. External is
  `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)`, the external memory added to the heap,
  0 when none was, which `allocate()` can use; the `external` of the standalone
  firmware, `firmware/standalone/src/main.cpp`, is the free part of it, another number.
  Internal is `heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)`, the
  expression of `allocate()`, read in the usermod's `setup()` right before
  `odrig_core_begin()` into a static of the file, which `aboutHost()` reads at `status`
  time; both are plain decimals. The room for the text, `kAboutSize` of
  `core/src/commands.cpp`, grows from 96 to 128 bytes, the one change of the core: 95
  characters hold today's longest text, 86 with `interrupt-watchdog`, and not the two
  numbers beside it, which would then be cut; the longest new text is 119 characters.
  The trim of the escaped text at 160 bytes and the reply's room for it stay;
  [commands.md](../../docs/commands.md) says at most 127 characters where it says 95,
  and `TheHostsName` of `tests/core/test_readiness.py` cuts 200 characters to 127. The
  emulator's text, `odrig emulator on <system> <machine>` of `emulator/host.py`, is not
  changed. The app shows the text as it is, `Installation: <host>` on the Target page,
  unchanged. No new command.
- **The reader of the card.** Not changed: with external memory `begin()` of
  `odrig_drive.cpp` gets its tables and the reader starts on the spare, which it could
  not until now; WLED's information then reads `looking for SD`, `not readable` or the
  count of files, as [microsd.md](../../docs/microsd.md) says.
- **What the spare can show.** With the image for its module the Target page reads an
  `external` that is not 0, 2097152 when the whole of the 2 MB is in the heap, `error`
  null, and the canvas of 60 x 60; the show is empty until the first upload. The
  `Installation:` line names the image that runs by its release name and its build date
  and time, so the first thing read is the name: `odrig_ESP32-S3_8MB_qspi` with an
  `external` that is not 0 on the spare is the fix at work; `odrig_ESP32-S3_16MB_opi`
  with `external 0` on the spare means the installation's image was flashed, not the
  spare's; `odrig_ESP32-S3_8MB_qspi` with `external 0` on the installation's board means
  the spare's image was flashed there, and that board runs without its PSRAM until its
  own image is flashed back; and only `odrig_ESP32-S3_8MB_qspi` with `external 0` on the
  spare means the quad build did not find the PSRAM or its test failed: a finding about
  the module for a seed of its own, with the host text as its first evidence. A quad
  build whose PSRAM is not found starts all the same: `psramInit()` of the Arduino core,
  `cores/esp32/esp32-hal-psram.c` of the newer software, returns false after `PSRAM
  init failed!` when `esp_psram_init()` fails, or after `PSRAM test failed!`, nothing is
  added to the heap, and the start goes on, which is how the spare's image on the
  installation's board reads `external 0`. Right after a flash from the phone the line
  may end `reset other`,
  the reset having come from the flasher over USB; `reset power-on` is read after the
  board is powered again, and neither is a finding. The spare at the installation has no
  card; with a card that mounts, the playlist shows the card's animations beside the
  storage's, which is the reader at work and not a fault. The refresh rate on the spare
  may be below the installation's, its memory being quad and slower; any rate from 20 to
  50 a second is acceptable by working rule 12, and this seed does no work on it.
- **The spare's bootloader and table.** Not written, and in need of no change: on the
  ESP32-S3 the application initializes the PSRAM, `psramInit()` at the system's init
  before `setup()`, and the bootloader has no part in it; the bootloader the spare has,
  which the repository never wrote, boots seed 76's image of ESP-IDF 5.5.5 already, and
  the spare's image differs from it in nothing the bootloader reads. Only the application
  image at 0x10000 is flashed: an application flash never touches the bootloader or the
  table, and neither `flash` nor `restore-stock` writes them on the 8 MB layout. The way
  back from an image the spare does not come up on is the installation's image, flashed
  the same way at 0x10000, which boots on the spare without its PSRAM as it did. So the
  spare build's bootloader and table serve no scenario of the fix and are not placed
  beside the images on the Drive: a file meant for 0x0 or 0x8000 beside files meant for
  0x10000 is a wrong pick on the phone that only the `Installation:` line catches, after
  the flash. They go into the subfolder `only-if-the-flash-was-erased/` of the delivery,
  named by their offsets as "Where it lands" says, with a README of their own that says
  what they are for and for nothing else: a spare whose flash was erased, which then has
  no bootloader and no table, and a spare on which a file was written at 0x0 or 0x8000
  by mistake, which overwrote them and shows no hotspot afterwards; then the bootloader
  at 0x0, the table at 0x8000 and the spare's image at 0x10000, in that order, the flash
  settings kept, no erase, and the storage at 0x310000, which such a write does not
  reach, keeps the network name. The bootloader is the one the build makes from the
  newer software's `bootloader_qio_80m.elf` with 8 MB in its header, and the table is
  the tracked one as bytes, both from `.pio/build/odrig_microsd_n8r2/`. The bootloader's
  own header, not the image's, tells the chip's software the flash size, and the spare's
  bootloader is one the repository never wrote. A bootloader whose header says less than
  8 MB does not boot the spare's table: the bootloader refuses a partition that ends
  beyond that size, and the board shows no hotspot. The spare boots its table today, so
  its header says 8 MB or more, and a header of 16 MB on the 8 MB chip is harmless: the
  software takes the smaller of the header and the chip. The subfolder's bootloader is
  for the two cases above and for no finding of this seed.
- **Where the work goes.** `firmware/platformio_override.ini.in`,
  `firmware/partitions/odrig-8mb.csv`, `firmware/fwtool/build.py`,
  `firmware/fwtool/cli.py`, `firmware/fwtool/partitions.py`,
  `firmware/fwtool/provenance.py`, `firmware/verify_build.py`,
  `firmware/usermod/odrig_usermod.cpp` and `core/src/commands.cpp`; the tests
  `tests/firmware/test_wled.py`, whose `test_it_has_the_two_environments_on_wleds_own`
  forbids `board_build.partitions` and `board_upload.flash_size` anywhere in the
  override and is narrowed to the four environments of WLED's board, with the new
  environment's settings pinned beside it; `tests/firmware/test_microsd_build.py`,
  `tests/firmware/test_cli.py`, `tests/firmware/test_layouts.py` with the 8 MB layout
  beside the two in `tests/firmware/support.py` and the tracked table against
  `partitions.EIGHT_MB`, and against `.pio/build/odrig_microsd_n8r2/partitions.bin` when
  a build tree is there; `tests/firmware/test_partitions.py`,
  `tests/firmware/test_docs.py`, `tests/firmware/test_usermod_kept.py` for the words of
  the host text, `tests/firmware_host/test_build.py`, whose `expected` dict gains the
  kind, `tests/firmware_host/test_provenance.py` and `tests/core/test_readiness.py`;
  the workflow `.github/workflows/firmware-hosts.yml`, which builds and verifies both
  images and keeps the ELF of `.pio/build/odrig_microsd_n8r2/` and the spare's
  verification files beside the installation's; the pages `docs/firmware.md`, its
  synopsis of `build`, the table of kinds and its sentence of eight kinds, nine from now
  on, the three layouts, the regions of the flash of the 8 MB layout beside WLED's, the
  name in `status` and the copied libraries, `docs/firmware-additions.md`,
  `docs/commands.md`,
  `docs/android-app.md` and `docs/firmware-prerequisites.md`, which names the board;
  the change log of `docs/decisions.md` with the owner's ruling, and `docs/drifts.md`.
  `tests/air/test_wled.py` keeps `odrig_ESP32-S3_16MB_opi`: the board suites are the
  installation's module's.
- **Where it lands.** On a branch from `seed-76-empty-board-first-animation`, as a pull
  request that carries seed 76's change and this one and supersedes pull request #49.
  Both images are built from the pull request's head on Windows with the shared
  toolchains, `python firmware/fw.py build --module n8r2` and
  `python firmware/fw.py build`, verified with `python firmware/verify_build.py --module
  n8r2` and `python firmware/verify_build.py`, and placed on the Drive under
  `odrig archive/seed-77/`. On the Drive every file carries the seed, the commit, the
  module and its offset in its name, and none is called `odrig-firmware.bin`, which the
  archive's root holds already from 2026-11-01, nor `odrig-firmware-n8r2.bin`:
  `odrig-seed77-<commit>-n8r2-at-0x10000.bin` for the spare and
  `odrig-seed77-<commit>-n16r8-at-0x10000.bin` for the installation's board, `<commit>`
  the short hash of the pull request's head, each with its `.sha256` and its
  `.build.json` under the same name, and the image-info text and the verification record
  of `verify_build.py` renamed likewise, as seed 76's delivery `odrig-seed76-7c397c5.bin`
  and its files are. The README beside them says which module each image is for and how
  it is flashed from the phone: the application image at offset 0x10000 and no other,
  the flasher's offset field read before `Flash`, the flash settings kept, no erase, as
  seed 76's README says; that the `Installation:` line is read first after the flash,
  with the four readings of "What the spare can show" as they stand there; that a spare
  showing no hotspot a minute after a flash is flashed again with the spare's image at
  0x10000; that a spare showing none after that is flashed with the installation's image
  at 0x10000, and a hotspot then means the spare's image does not come up on the spare,
  a finding for a seed of its own; and that a spare showing none after the
  installation's image had a file written at 0x0 or 0x8000, for which the subfolder
  `only-if-the-flash-was-erased/` is, named there in words. The spare build's bootloader
  and table are not in that folder: they go into the subfolder as
  `odrig-seed77-<commit>-n8r2-bootloader-at-0x0.bin` and
  `odrig-seed77-<commit>-n8r2-partitions-at-0x8000.bin`, with their `.sha256` and a
  README of their own, as "The spare's bootloader and table" says. The installation's
  image stays the one for the installation's board. No APK: the app is unchanged, and
  the APK of seed 75, `odrig-seed75-f5ad253.apk` of `odrig archive/seed-75/`, works with
  both; the `Installation:` line is shown by every APK since seed 33's `ac81d15` of
  2026-10-25, and an APK that shows no such line on the Target page is older and is
  replaced first.

## Required Behavior

1. `python firmware/fw.py build --module n8r2` builds `odrig-firmware-n8r2.bin` from the
   environment `odrig_microsd_n8r2` on the newer software, with its `.sha256` and its
   `.build.json` naming the kind, the environment and the module; the image's header
   says 8 MB of flash, its size is at most 0x300000 bytes, and its release name is
   `odrig_ESP32-S3_8MB_qspi`. `python firmware/fw.py build` builds `odrig-firmware.bin`
   as today; its `.build.json` gains the field `module`, `n16r8`.
2. `python firmware/verify_build.py --module n8r2` passes on the spare's image and
   `python firmware/verify_build.py` on the installation's; each refuses a provenance of
   the other's environment, a header whose flash size is not its module's, and an image
   that holds the other's release name.
3. The firmware tool names the spare's table `8 MB` with its storage of 5,111,808 bytes,
   `flash --image` writes the spare's image on it, and `restore-stock` and
   `install-firmware` refuse it.
4. `status` of the firmware gives `host` in the form `<release> <date> <time> <storage>
   external <bytes> internal <bytes> reset <reason>`; the emulator's `host` is
   unchanged; the core carries a host text of up to 127 characters.
5. The app is unchanged and shows the text on the Target page as `Installation: ...`.
6. The probe build, the stick build, the standalone build and `--microsd` are unchanged,
   and `--module n8r2` is refused beside any of them.

## Definition Of Done

1. The firmware's host suites, each test of a fault seen failing before the change: the
   kind `n8r2` in `KINDS` and `ON_NEWER` with its environment and image; `--module` on
   `build` and its conflicts; the environment's settings in the override and the
   narrowed check of WLED's environments; the tracked table against `partitions.EIGHT_MB`
   and the Drive table's bytes; the `8 MB` layout named, its storage, `flash` on it and
   `restore-stock` and `install-firmware` refusing it; the table in the provenance's
   inputs; the release name and the flash size read from each image; the words of the
   host text in the usermod; the pages' synopsis and tables. The core's suite: a host
   text of 127 characters kept and a longer one cut.
2. Both images built on Windows with the shared toolchains from the pull request's head
   and verified, the spare's header saying 8 MB; the onboarding suite, the firmware's
   suites, the core's suite and the converter's docs test; the workflow building and
   verifying both.
3. The images on the Drive under `odrig archive/seed-77/` as
   `odrig-seed77-<commit>-n8r2-at-0x10000.bin` and
   `odrig-seed77-<commit>-n16r8-at-0x10000.bin`, each with its `.sha256` and its
   `.build.json` under the same name, and the README; the spare build's bootloader and
   table in `only-if-the-flash-was-erased/` under their names with the offsets 0x0 and
   0x8000, with their `.sha256` and a README of their own; no file of the delivery named
   `odrig-firmware.bin` or `odrig-firmware-n8r2.bin`.
4. The owner, first with the spare board as it is: the Target page's `Installation:`
   line and its invalid-show line, as Product Context says. Then with the spare board
   flashed with the spare's image from the phone: the Target page shows `Installation:
   odrig_ESP32-S3_8MB_qspi ... external <bytes> internal <bytes> reset <reason>`, the
   release name the spare's and the external bytes not 0, 2097152 expected, the reason
   `other` or `power-on`, neither a finding; then `Choose a ready-made animation`,
   `Internal storage`, `Upload to the installation`, and
   `Uploaded as animation 1 <file>. It plays in the playlist.`; the animation on the
   LEDs. `external 0` beside `odrig_ESP32-S3_16MB_opi` means the installation's image
   was flashed, and the spare's is flashed again; `external 0` beside
   `odrig_ESP32-S3_8MB_qspi` on the spare means the quad build did not find the PSRAM or
   its test failed, a finding about the module for a seed of its own with the host text
   as its first evidence. No hotspot a minute after a flash: the spare's image again,
   then the installation's image, then the subfolder, as the README says.

## Open Questions

None. The owner asked for a fix seed with no open questions; what is decided here is
that the fault is the firmware's and that the firmware comes in two images from now on,
one for each module, a decision taken under the owner's order of 2026-11-05, with the
installation's environment, image and name unchanged and the 192 KB reserve kept; that
the spare's module gets the environment
`odrig_microsd_n8r2`, memory type `qio_qspi`, 8 MB of flash, flash mode `qio`, the
release name `odrig_ESP32-S3_8MB_qspi` and the tracked table
`firmware/partitions/odrig-8mb.csv` equal to the spare's; that the firmware tool builds
and verifies it with `--module n8r2` as `odrig-firmware-n8r2.bin`, the probe builds
staying the installation's, and that `partitions.py` names the spare's table `8 MB`,
which `restore-stock` and `install-firmware` refuse and `flash --image` writes; that the
host text names the external memory and the
internal memory free at the core's start in the form given, with the core's room for it
grown to 128 bytes; that the branch starts from seed 76's and one pull request carries
both; that the delivery is two images on the Drive under `odrig archive/seed-77/`, each
named by the seed, the commit, the module and its offset, with the spare build's
bootloader and table in a subfolder of their own, named by their offsets, for a spare
whose flash was erased or written at 0x0 or 0x8000 by mistake and for nothing else; that
a spare showing no hotspot after a flash is flashed with the spare's image again, then
the installation's, and only then from the subfolder; and that `external 0` beside the
release name `odrig_ESP32-S3_8MB_qspi` on the spare, the PSRAM not found or its test
failed, is a finding about the module for a seed of its own, not a fault of this seed.
