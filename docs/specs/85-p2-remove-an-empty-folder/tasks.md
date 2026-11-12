# Tasks

Each task is one commit on the branch `seed-85-remove-an-empty-folder`, which is `master`
with seed 74 part B (pull request #64) merged, with only its own checkbox ticked. Every test
of a fault is seen failing before the change, and the failure seen goes into the commit
message. Code carries no history.

- [x] 1. `folder remove <id>` in the core, on both storages
  - `core/src/commands.cpp`: the line. `core/src/content.cpp` and `.h`:
    `content_folder_remove`. `core/src/folders.cpp` and `.h`: `internal_folder_remove`.
    `core/src/catalog.cpp` and `.h`: `catalog_folder_remove`, `folder_entry_removed`,
    `remove_drive_folder`. `tests/core/host/host.cpp`: `remove` of an empty folder of the
    drive.
  - `tests/core/test_folder_remove.py`, new, seen failing first; the command lists of
    `tests/core/test_docs.py` and `tests/emulator/test_tool.py`.
  - `docs/commands.md` (the table, the two folder sections, the refusals, the error codes),
    `docs/core.md` (the host's `remove`, "Internal folders"), `docs/catalog.md`, the change
    log of `docs/decisions.md` with the owner's approval of 2026-11-09, and the drifts at the
    end of `docs/drifts.md`. Set the seed's state to `in_progress`.
  - Measure `sizeof(Core)`, `FileInfo` and `Upload` with g++ and the board's compiler: the
    memory table of `docs/core.md` unchanged; every new frame under 512 bytes.
  - Suites: core, onboarding, emulator (its tool's command list).
  - Requirements: 1.1–1.3, 2.1–2.3, 3.1–3.4, 4.1–4.4, 5.1–5.4, 6.1, 7.1–7.3, 8.1–8.3,
    9.1–9.7, 10.1–10.2, 13.1.

- [x] 2. The emulator, the firmware's card host and the command tool
  - `emulator/host.py`: `FolderHost.remove` of a drive's folder. `firmware/usermod/
    odrig_drive.cpp`: `removeDriveFile` of a directory. `odrigctl/cli.py`: `folder remove
    ID`.
  - Tests seen failing first: the emulator's line over HTTP and TCP
    (`tests/emulator/test_folder_remove.py`, new), the firmware source checks in
    `tests/firmware/test_usermod_drive.py`, the tool's sending and usage in
    `tests/emulator/test_tool.py`.
  - `docs/emulator.md`, `docs/firmware.md`, `docs/drifts.md` at the end.
  - Suites: emulator, firmware (alone, with `ODRIG_TOOLS`), firmware host, core, onboarding.
  - Requirements: 1.2, 10.3–10.4, 12.1, 13.1.

- [x] 3. `Remove folder` in the app
  - `app/www/commands.js` (`folderRemove`), `app/www/messages.js` (its refusals),
    `app/www/screens/explorer.js` (the action, its check, its dialog, the lost reply),
    `app/www/screens/show.js` (the folder hook of `extend`), `app/www/index.html` (the
    dialog), `app/www/style.css` if the dialog needs it.
  - Tests seen failing first: `tests/app/test_folder_remove.py` with its page scenario,
    new; `tests/app/test_messages.py`; `tests/app/test_scope.py` takes `folder remove <n>`.
  - `docs/android-app.md`: the action, and a step of "The check on a phone" with the counts
    of `tests/app/test_docs.py`; `docs/drifts.md` at the end.
  - Suites: app, emulator, onboarding.
  - Requirements: 11.1–11.7, 13.1.

- [x] 4. Deliver seed 85
  - Push the branch and open its pull request against `master`, saying it is built on pull
    request #64. From the pushed head with a clean tree: the installation's image
    (`odrig_microsd`) and the spare's (`odrig_microsd_n8r2`), each through
    `verify_build.py` for its module, and the APK signed with the persistent key, checked
    with `apksigner` and `zipalign -c 4`; their bytes and SHA-256; the files on the Drive
    in a new folder of `odrig archive/`.
  - Every suite that works on this computer passes.
  - `verification.md`: the commits, the suites, the builds with their links, and the
    owner's check on a phone, open. The seed's line in `AGENTS.md`.
  - Requirements: 13.2–13.4.
