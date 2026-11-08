# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first. Part A is delivered on its own before part B begins.

## Part A

- [x] 1. Make folders on the card with `folder make external`
  - The host's `make_folder`, the index's empty folders and the insertion of a folder
    in one catalog commit; the command and its refusals; the walk, `list`, `play` and an
    upload into an empty folder.
  - The emulator's and the firmware's hosts; the Python library's reader.
  - Core, emulator, Python library and firmware-host tests; `docs/commands.md`,
    `docs/catalog.md`, the change log of `docs/decisions.md`, `docs/drifts.md`.
  - Requirements: 1.1–1.8.

- [x] 2. Report what is saved for an animation with `saved <id>`
  - The command, its refusals, the command tool's line, tests and documents.
  - Requirements: 2.1–2.2.

- [x] 3. Move files and make folders from the app
  - The selection of both storages, `New folder` and `New playlist folder`, `Move to…`
    with its chooser and preview, the move job with its journal and reconciliation.
  - App tests against the emulator; `docs/android-app.md`.
  - Requirements: 3.1–3.9.

- [x] 4. Deliver part A
  - Firmware for the installation's board and the spare's, and the signed APK, built
    from the pushed head; the files on the Drive; `verification.md`.
  - Requirements: 7.1.

## Part B

The tasks are done in the order 5, 7, 6, 8, because task 6 builds on task 7's folders.

- [ ] 5. Read files back 720 bytes at a time, and download and back up from the app
  - Requirements: 6.1–6.2.

- [ ] 6. Move files and folders inside the card by renaming, and folders between storages
  - Requirements: 5.1–5.2.

- [ ] 7. Give the board's own storage real folders
  - Requirements: 4.1–4.2.

- [ ] 8. Deliver part B
  - Requirements: 7.1.
