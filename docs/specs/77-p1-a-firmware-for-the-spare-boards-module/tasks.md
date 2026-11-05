# Tasks

Each task is one commit on the branch `seed-77-firmware-for-the-spare-module` from
`master`, with only its own checkbox ticked. Every test of a fault is seen failing
before the change, and the failure seen goes into the commit message. Code carries no
history.

- [x] 1. The second environment and the spare's table
  - `firmware/platformio_override.ini.in`: `[env:odrig_microsd_n8r2]` with its settings
    and its release name; `firmware/partitions/odrig-8mb.csv`, new;
    `firmware/fwtool/partitions.py`: `EIGHT_MB`, `EIGHT_MB_NAME` and `layout_of()` by
    the end of a one-slot table; `firmware/fwtool/provenance.py`: `firmware/partitions`
    in `GROUPS` and `.csv` in `SOURCE_ENDINGS`.
  - `tests/firmware/test_wled.py`: the narrowed check of WLED's environments and
    `test_the_spares_environment_names_its_module`, seen failing first;
    `tests/firmware/support.py`: `EIGHT_MB_LAYOUT` and `small_eight_mb_layout()`;
    `tests/firmware/test_layouts.py`, `Tables`: the spare's table, its name, its line
    and the one-slot table refused, and `OnEachLayout` on the 8 MB stand-in, seen
    failing first; `tests/firmware/test_partitions.py`;
    `tests/firmware_host/test_provenance.py`: the table among the inputs, seen failing
    first.
  - Set the seed's state to `in_progress`. Run the firmware's suites.
  - Requirements: 1.1-1.3, 2.1-2.3, 2.6, and 2.4 in part, the line and `flash`.

- [x] 2. The commands on the 8 MB layout
  - `firmware/fwtool/cli.py`: `installations_layout()`, called by `_restore_stock()`
    and `_install_firmware()` before any write; `_flash()`, `storage_of()` and
    `write_application()` unchanged.
  - `tests/firmware/test_layouts.py`: `RefusedOnTheSpare`, new, seen failing first;
    `tests/firmware/test_flasher.py`, `test_wifi_commands.py`, with
    `test_storage_is_read_only_after_the_firmware_has_answered`, and
    `test_limit_commands.py`: the first `read-flash` of the three commands.
  - Run the firmware's suites.
  - Requirements: 2.5, 5.4, and 2.4 in part, the commands unchanged.

- [x] 3. The kind `n8r2` and `--module` on `build`
  - `firmware/fwtool/build.py`: `KINDS["n8r2"]`, `ON_NEWER`, `MODULES`,
    `DEFAULT_MODULE` and `module_of()`; `firmware/fwtool/provenance.py`: `module` in
    `record()` and `write()`; `firmware/fwtool/cli.py`: `--module` in `parser()`, the
    kind in `_build()` and the conflicts in `parsed()`.
  - `docs/firmware.md`: the synopsis line of `build` gains `[--module n16r8|n8r2]`;
    `tests/firmware/test_docs.py`, `test_it_names_every_option_of_every_command`, seen
    failing first.
  - `tests/firmware/test_cli.py`: the kind and its environment, `Building` with
    `--module`, and `TheModule`, seen failing first; `tests/firmware_host/test_build.py`:
    `expected` with the kind and the recorded module, seen failing first;
    `tests/firmware_host/test_provenance.py`: the field `module`, seen failing first;
    `tests/firmware/test_newer_software.py`: `ON_NEWER` with the kind, seen failing
    first; `tests/firmware/test_microsd_build.py`: `--microsd` beside `--module n8r2`,
    seen failing first.
  - Run the firmware's suites.
  - Requirements: 3.1-3.5, 1.4 in part, the size, and 6.2 in part, the synopsis.

- [x] 4. `verify_build.py --module`
  - `firmware/verify_build.py`: `MODULES`, `checked()` with the flash size of the
    header and the release name in the bytes, `inspect()` by module, the files
    `image-info-n8r2.txt` and `verification-n8r2.json`, and `--module`.
  - `tests/firmware_host/test_verify.py`, new, seen failing first.
  - Run the firmware's suites.
  - Requirements: 3.6, 3.7, 1.4 in part, the header and the name.

- [x] 5. The host text
  - `firmware/usermod/odrig_usermod.cpp`: `internalFreeAtStart` read in `setup()` before
    `odrig_core_begin()`, and `aboutHost()` with `external` and `internal`;
    `core/src/commands.cpp`: `kAboutSize` 128.
  - `tests/firmware/test_usermod_kept.py`, `TheAbout`: the words of the host text and
    the order in `setup()`, seen failing first; `tests/core/test_readiness.py`,
    `TheHostsName`: 127 characters kept and 200 cut to 127, seen failing first.
  - Run the core's suite and the firmware's suites.
  - Requirements: 4.1-4.4.

- [x] 6. The workflow and the documentation
  - `.github/workflows/firmware-hosts.yml`: the spare's build and inspection, and its
    ELF in the artifact. `docs/firmware.md` with `tests/firmware/test_docs.py`, the
    table of kinds, the `--module` paragraph, the nine kinds, the host builds, the
    copied libraries, the three layouts, the reasons table, the regions of the flash
    and the name in `status`; `docs/core.md`, `docs/commands.md`,
    `docs/android-app.md`, `docs/firmware-additions.md`,
    `docs/firmware-prerequisites.md`, the change log of `docs/decisions.md`, and
    `docs/drifts.md` with the entry of the core's page.
  - `tests/firmware/test_docs.py`: the 8 MB table's rows and the row of the kinds
    table, seen failing first.
  - Run the firmware's suites, the core's documentation tests, the converter's
    documentation test and the onboarding suite.
  - Requirements: 5.1-5.3, 5.5, 6.1-6.4.

- [x] 7. The pull request and the two images
  - Push the branch and open the pull request from `master`, of its own and beside
    #49, its description naming the seed, the verdict and the owner's open checks.
    Build both images from the pushed head on this computer with the shared toolchains
    and a clean tree, `build --module n8r2` and `build`, verify each with
    `verify_build.py`, the spare's header saying 8 MB, run the firmware's suites
    through the runner, the core's suite, the converter's documentation test and the
    onboarding suite, place the images with their hashes, their build records, their
    verification files and the README on the Drive under `odrig archive/seed-77/`, the
    spare build's bootloader and table with their hashes and their README in
    `only-if-the-flash-was-erased/`, and write `verification.md` with the commits, the
    suites, both images' hashes and headers, the Drive paths and links, the workflow's
    result and what stays open. Set the `AGENTS.md` line of seed 77 to name the open
    pull request; the state stays `in_progress`. Commit, push, read the CI, and notify
    the owner.
  - Requirements: 1.4, 7.1-7.4.

## Owner acceptance (not claimed by automated tasks)

On the phone, first with the spare board as it is: the Target page's `Installation:`
line and its invalid-show line, `out-of-memory` beside seed 76's build date confirming
the starved core, `mapping-missing` or another date meaning the image that runs is not
seed 76's. Then with the spare flashed with the spare's image at 0x10000 from the phone:
`Installation: odrig_ESP32-S3_8MB_qspi ... external <bytes> internal <bytes> reset
<reason>`, the external bytes not 0, 2097152 expected, the reason `other` or
`power-on`, and `The installed show is invalid: mapping-missing.` until seed 76's change
is on the board too; then, with a firmware that has both, `Choose a ready-made
animation`, `Internal storage`, `Upload to the installation`, `Uploaded as animation 1
<file>. It plays in the playlist.`, and the animation on the LEDs. No hotspot a minute
after a flash: the spare's image again, then the installation's image, then the
subfolder, as the README says. This remains open until the owner reports it.
