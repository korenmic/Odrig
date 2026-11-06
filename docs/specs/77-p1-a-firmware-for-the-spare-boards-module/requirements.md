# Requirements

Seed 77, `project-seeds/77-p1-a-firmware-for-the-spare-boards-module/seed.md`. The
firmware's build environments, the firmware tool, the host text of the usermod, the room
the core keeps for it, the workflow and the pages; the installation's environment, image
and release name stay as they are; no command is added; the converter, the Python
library, the emulator, the app and the 192 KB reserve of `allocate()` are not changed.

## 1. The second environment

1.1 `firmware/platformio_override.ini.in` has `[env:odrig_microsd_n8r2]`, which extends
`env:odrig_microsd` and so has the platform of the newer software, the libraries left
out, the SD pins, `odrig_newer.h`, the usermod and the core as the firmware has them, the
flash mode `qio` and `-DBOARD_HAS_PSRAM`, and sets what the spare's module differs in:
`board_build.arduino.memory_type = qio_qspi`, `board_upload.flash_size = 8MB`,
`board_upload.maximum_size = 3145728` and `board_build.partitions` with the absolute
path `@REPO@/firmware/partitions/odrig-8mb.csv`, which `override_text()` fills.
1.2 Its release name is `odrig_ESP32-S3_8MB_qspi`: the inherited
`-D WLED_RELEASE_NAME=\"odrig_ESP32-S3_16MB_opi\"` is taken out with `build_unflags`
and the new one given in `build_flags`, so that the name is defined once.
1.3 `[env:odrig]`, `[env:odrig_probe]`, `[env:odrig_microsd]` and
`[env:odrig_microsd_probe]` are not changed, and none of them sets `board`,
`board_build.partitions`, `board_build.flash_mode` or `board_upload.flash_size`.
1.4 An image built from the environment has a header that says 8 MB of flash, the high
nibble of its byte 3 being 0x3, holds the release name `odrig_ESP32-S3_8MB_qspi` and not
`odrig_ESP32-S3_16MB_opi`, and has at most 0x300000 bytes. `flasher.KEEP` and the phone
write the flash settings of the header as they are.

## 2. The partition table

2.1 `firmware/partitions/odrig-8mb.csv` is tracked and equal to the spare's table row
for row: `nvs,data,nvs,0x9000,0x5000`, `otadata,data,ota,0xE000,0x2000`,
`app0,app,factory,0x10000,0x300000`, `spiffs,data,spiffs,0x310000,0x4E0000` and
`coredump,data,coredump,0x7F0000,0x10000`.
2.2 `firmware/fwtool/partitions.py` knows it as a third layout, `EIGHT_MB`, named
`8 MB`: `partitions.table(EIGHT_MB)` is byte for byte the spare's table, the Drive file
`odrig-8mb-partition-table-at-0x8000.bin` of 3,072 bytes with the SHA-256
`dc19fc0fcd52efb130e273d9e69a3cfec1b86f1595a0f24bd74c0656f3efd17f`, and the bytes of
`.pio/build/odrig_microsd_n8r2/partitions.bin` when a build tree is there.
2.3 `layout_of()` names a table with two firmware slots `WLED's` as today, a one-slot
table whose last partition ends at 0x800000 `8 MB`, and one whose last partition ends at
0x1000000 `bigger`; any other one-slot table is `layout-mismatch` to every command.
2.4 `flash`, `install-show`, `set-wifi`, `set-limit`, `read-limit`, `read-show` and
`recover-storage` print `layout: 8 MB, storage 5111808 bytes` on the spare's table and
work on it as on the bigger layout, with no other change:
`flash --image build/firmware/out/odrig-firmware-n8r2.bin` writes the spare's image at
0x10000 on it as it writes any image.
2.5 `restore-stock`, with or without `--full`, and `install-firmware` refuse the `8 MB`
layout with `layout-mismatch` before anything is written; `big-storage` refuses it as
today, entry for entry; a table that cannot be read does not stop
`restore-stock --full`, as today.
2.6 `firmware/partitions` is in `GROUPS` and `.csv` in `SOURCE_ENDINGS` of
`firmware/fwtool/provenance.py`, so that the table is among the inputs of every build
record and a changed table changes the inputs' hash.

## 3. The firmware tool

3.1 `build` takes `--module`, with the values `n16r8`, the default and today's
behavior, and `n8r2`. `KINDS` of `firmware/fwtool/build.py` has the kind `n8r2`,
`Kind("odrig_microsd_n8r2", "odrig-firmware-n8r2.bin")`, in `ON_NEWER`.
3.2 `python firmware/fw.py build --module n8r2` builds `odrig-firmware-n8r2.bin` from
the environment `odrig_microsd_n8r2` on the newer software, keeps it in
`build/firmware/out/` with its `.sha256` and its `.build.json`, and prints its path, its
size and its SHA-256 as for every kind. `python firmware/fw.py build` builds
`odrig-firmware.bin` as today.
3.3 The build record names the kind, the environment and, in a field `module`, the
module: `n8r2` for the spare's image and `n16r8` for the installation's image and for
every other kind.
3.4 `--module n8r2` does not go with `--stock`, `--probe`, `--stick`, `--standalone` or
`--microsd`: `parsed()` refuses it as a usage error, exit status 2, as `--microsd`'s
conflicts are refused, and nothing is built. The probe build, the stick build, the
standalone build and `--microsd` are unchanged: the probe builds stay the installation's
module's.
3.5 `check_size()` keeps its limit of 0x300000 bytes, the size of `app0` on both
tables. `flash` and `install-firmware` get no option: `install-firmware` stays the
installation's image. The tool copies no libraries: `.pio/libdeps/odrig_microsd` can be
copied by hand to `.pio/libdeps/odrig_microsd_n8r2` before the first build, and what is
missing there PlatformIO fetches.
3.6 `firmware/verify_build.py` takes `--module` with the same values.
`python firmware/verify_build.py --module n8r2` checks `odrig-firmware-n8r2.bin`
against its provenance, the environment `odrig_microsd_n8r2`, the ELF of
`.pio/build/odrig_microsd_n8r2/` and the three entry points, and writes
`image-info-n8r2.txt` and `verification-n8r2.json` beside the image;
`python firmware/verify_build.py` checks `odrig-firmware.bin` as today and writes
`image-info.txt` and `verification.json`.
3.7 `checked()` reads the flash size of the header, the high nibble of byte 3, and finds
the release name in the image's bytes: each module's check refuses a provenance of the
other module's environment, a header whose flash size is not its module's, 0x4 for
`n16r8` and 0x3 for `n8r2`, an image that does not hold its module's release name, and
one that holds the other module's.

## 4. The host text

4.1 `aboutHost()` of `firmware/usermod/odrig_usermod.cpp` gives `status` the host text
in the form `<release> <date> <time> <storage> external <bytes> internal <bytes> reset
<reason>` and no other, for example `odrig_ESP32-S3_8MB_qspi Nov  5 2026 07:44:48
internal+microsd external 2097152 internal 201000 reset power-on`.
4.2 `external` is `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)`, the external memory
added to the heap, 0 when none was; `internal` is
`heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)`, the expression of
`allocate()`, read in the usermod's `setup()` right before `odrig_core_begin()` into a
static of the file, which `aboutHost()` reads at `status` time. Both are plain decimals.
4.3 `kAboutSize` of `core/src/commands.cpp` is 128: a host text of 127 characters is
reported whole and a longer one is cut to 127 characters. The trim of the escaped text at
160 bytes and the reply's room for it stay. This is the one change of the core.
4.4 The emulator's text, `odrig emulator on <system> <machine>`, is not changed. The
app is not changed and shows the text as it is, `Installation: <host>`, on the Target
page.

## 5. What stays as it is

5.1 The installation's board, its environment `odrig_microsd`, its image
`odrig-firmware.bin` and its release name `odrig_ESP32-S3_16MB_opi` are not changed in
any way; `tests/air/test_wled.py` keeps `odrig_ESP32-S3_16MB_opi`, the board suites
being the installation's module's.
5.2 The 192 KB reserve of `allocate()` stays as it is; no fallback is made in it.
5.3 `begin()` of `firmware/usermod/odrig_drive.cpp` is not changed: with external
memory the reader starts on the spare, and WLED's information reads `looking for SD`,
`not readable` or the count of files, as `docs/microsd.md` says.
5.4 Neither `flash` nor `restore-stock` writes the bootloader or the partition table on
the `8 MB` layout; an application flash never touches them. The spare build's
bootloader and table are delivered in the subfolder of 7.3 and nowhere else.
5.5 No wiring, power or LED is touched; no command, reply member or error code is
added; no APK is built.

## 6. The workflow and the pages

6.1 `.github/workflows/firmware-hosts.yml` builds and verifies both images,
`build --module n8r2` and `verify_build.py --module n8r2` beside today's steps, and
keeps the ELF of `.pio/build/odrig_microsd_n8r2/` and the spare's verification files
beside the installation's in its artifact.
6.2 `docs/firmware.md`: the synopsis of `build` has `--module`; the table of kinds has
the row of `build --module n8r2`, and the sentence of eight kinds says nine; the layout
paragraph names the three layouts and the line `layout: 8 MB, storage 5111808 bytes`;
"The regions of the flash" has the 8 MB layout beside WLED's and says that
`restore-stock` and `install-firmware` refuse it; the name in `status` has `external`
and `internal`; the copied libraries name `.pio/libdeps/odrig_microsd_n8r2`; the host
builds name both images and their verification files.
6.3 `docs/commands.md` says at most 127 characters where it says 95 and names the
memory in the row of `host`; `docs/core.md`, which says the room the core keeps for the
text, says 128 bytes and 127 input bytes where it says 96 and 95;
`docs/android-app.md` says that the board gives its external memory and the internal
memory free at its start; `docs/firmware-additions.md` has the memory in the host text
as a line of its list; `docs/firmware-prerequisites.md`, which names the board, names
the spare's module and its image.
6.4 The change log of `docs/decisions.md` records the owner's words of 2026-11-05 and
the decision that the firmware comes in two images, one for each module, with the line
`Board: ESP32-S3-N16R8 (16 MB flash, 8 MB PSRAM)` kept; `docs/drifts.md` records what
rule 7 decided on the way.

## 7. Proof and delivery

7.1 The firmware's suites, `firmware` and `firmware-host`, each new test of a fault seen
failing before the change: the kind `n8r2` in `KINDS` and `ON_NEWER` with its
environment and image; `--module` on `build` and its conflicts; the environment's
settings in the override and the narrowed check of WLED's environments; the tracked
table against `partitions.EIGHT_MB` and the Drive table's bytes; the `8 MB` layout
named, its storage, `flash` on it and `restore-stock` and `install-firmware` refusing
it; the table in the provenance's inputs and the field `module` of the record; the
release name and the flash size read from each image; the words of the host text in the
usermod; the pages' synopsis and tables. The core's suite: a host text of 127 characters
kept and a longer one cut.
7.2 The onboarding suite, the firmware's suites, the core's suite and the converter's
documentation test pass; the workflow builds and verifies both images.
7.3 Both images are built on Windows with the shared toolchains from the pull request's
head, `python firmware/fw.py build --module n8r2` and `python firmware/fw.py build`,
verified with `python firmware/verify_build.py --module n8r2` and
`python firmware/verify_build.py`, the spare's header saying 8 MB, and placed on the
Drive under `odrig archive/seed-77/` as `odrig-seed77-<commit>-n8r2-at-0x10000.bin` and
`odrig-seed77-<commit>-n16r8-at-0x10000.bin`, `<commit>` the short hash of the pull
request's head, each with its `.sha256` and its `.build.json` under the same name and
the image-info text and the verification record renamed likewise; a README says which
module each image is for, how it is flashed from the phone, that the `Installation:`
line is read first with the four readings, what is flashed when no hotspot shows, and
what the subfolder is for. The spare build's bootloader and table are in
`only-if-the-flash-was-erased/` as `odrig-seed77-<commit>-n8r2-bootloader-at-0x0.bin`
and `odrig-seed77-<commit>-n8r2-partitions-at-0x8000.bin`, with their `.sha256` and a
README of their own. No file of the delivery is named `odrig-firmware.bin` or
`odrig-firmware-n8r2.bin`; nothing above the folder is touched. No APK is built: the
app is unchanged, and the APK of seed 75 works with both images.
7.4 The owner, first with the spare board as it is: the Target page's `Installation:`
line and its invalid-show line. Then with the spare flashed with the spare's image from
the phone: `Installation: odrig_ESP32-S3_8MB_qspi ... external <bytes> internal <bytes>
reset <reason>`, the external bytes not 0, 2097152 expected, the reason `other` or
`power-on`, and `The installed show is invalid: mapping-missing.` until seed 76's change
is on the board too; then, with a firmware that has both, `Choose a ready-made
animation`, `Internal storage`, `Upload to the installation`, `Uploaded as animation 1
<file>. It plays in the playlist.`, and the animation on the LEDs. `external 0` beside
`odrig_ESP32-S3_16MB_opi` means the installation's image was flashed, and the spare's is
flashed again; `external 0` beside `odrig_ESP32-S3_8MB_qspi` on the spare is a finding
about the module for a seed of its own. These checks are the owner's and stay open until
the owner reports them.
