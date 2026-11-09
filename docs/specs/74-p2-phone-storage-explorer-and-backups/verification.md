# Verification

## Part A

### Software

Tasks 1 to 3 are the commits 878d9d4, c93c1b4 and 8964aec of the branch
`seed-74-phone-storage-explorer`, pull request #53.

- The core suite, 1,076 tests, passes with `folder make external` and `saved`, among them
  `tests/core/test_folder_make.py`: folders made at the root and below in the listing's
  order, a folder already there answered without a change, the refusals, a power cut at
  every storage call (the catalog at the generation before or after, the folder listed only
  after), an upload into an empty folder, an upload into an indexed folder removed from the
  card, and the last file out of a folder that keeps an empty sub-folder.
- The emulator suite and the command tool's tests pass with the host's `make_folder` and the
  tool's `folder make external PATH` and `saved ID`. The firmware's usermod tests pass: the
  SD host makes a folder only by the core's name of it, in the folder `odrig`.
- The app suite, 449 tests, passes but for four tests whose lists named the old controls,
  brought up to date in task 3. `tests/app/test_explorer.py` makes `clocks` from the page,
  moves an internal animation into it with its saved brightness through the real page and
  the emulator's core, checks the card's bytes and catalog, and checks that a file of a
  writable card is selected for a move but not for `Delete selected`.

### Builds

Built on Windows from the pushed head 8964aec with a clean tree.

| File on the Drive | Bytes | SHA-256 |
|---|---:|---|
| `odrig-seed74-8964aec-n16r8-at-0x10000.bin`, the installation's board, `odrig_microsd` | 1,886,800 | `d9d32e85253ebd317a56c924d7538b3fa86ac75eb29b778758fa17740d4b89d2` |
| `odrig-seed74-8964aec-n8r2-at-0x10000.bin`, the spare, `odrig_microsd_n8r2` | 1,884,256 | `bf764eda96d12f0f1a87e534a80c832a950fac91eaacac6069a0f720ad50bebd` |
| `odrig-seed74-8964aec.apk`, signed with the persistent key | 19,092,282 | `519f281793c74e39fd86e8fd5a5210f836e631ec3c71d28247ab294f7ac04fa4` |

Both images passed `verify_build.py` for their module. The APK's signature and alignment
were verified with `apksigner` and `zipalign -c 4`. They are in the Drive folder
`odrig archive/seed-74/`:

- https://drive.google.com/file/d/1xLlCgDkkZc3jS-Rx59kTHCS5Ncqf5xQ0/view
- https://drive.google.com/file/d/1uRtYbdhNq5Vlg32d-ncUYX2ERvXI9pab/view
- https://drive.google.com/file/d/1K_PX0RxtYMuOBK6gtxuGHLEpSV837Oci/view

The APK was not installed on an emulated phone this time; its web code is the code the app
suite ran in Chrome, and its native code is unchanged.

### The owner's checks, open

- [ ] On the installation's board with the card: `New folder` `clocks` and, inside it,
  `clocks/message`; `Move to…` of the internal clock files into `clocks` and of the message
  files into `clocks/message`; the clocks play between the animations and in Clocks only.
- [ ] A move cut by switching the phone's Wi-Fi off is finished or ended the next time the
  app reaches the board.

## Part B

### Software

Part B follows part A on the branch `seed-74-part-b`, pull request #64; its tasks were done
in the order 5, 7, 6. These are its commits after part A's head 81ae0db, in order:

| Commit | What it is |
|---|---|
| 58123a1 | The spec: part B at no memory of the core, and reads of 720 bytes |
| e6942c1 | Task 5: read files back 720 bytes at a time, and download and back up from the app |
| 9234086 | Task 7: give the board's own storage real folders |
| 33fbaff | A fix: a chosen internal playlist kept when `folders.txt` cannot be read, and an upload checked against its own folder |
| 0b610f5 | A fix: the texts and `Delete selected` no longer give every folder to the card, and a test of a saved folder that is gone |
| 6a6bc74 | The owner's answers of 2026-11-09 on a moved folder's order and the move's fallback, in the spec; no code |
| b7fdfd3 | A fix: the folder that plays marked by its id, not its path, on both storages |
| 9e2e329 | Task 6: move files and folders inside the card by renaming, and folders between storages |

The suites of task 6's run at the head 9e2e329:

| Suite | Tests |
|---|---:|
| core | 1,147 |
| emulator | 665 |
| app | 490 |
| firmware | 677 |
| firmware host | 37 |
| converter | 552 |
| `npm test --prefix converter` | 1,602 |
| onboarding | 88 |
| mapping | 42 |
| runner | 26 |

They pass but for the failures known on this computer, which are not faults of the code:
`tests.app.test_message_source`, for Pillow is not installed here; the firmware suite's two
tests of `test_env` and its `test_paths`, for the toolchains are reached through a junction;
and tests that failed on time under the load of a whole run and passed when run alone.

Part B's own tests are `tests/core/test_read_count.py`, `test_internal_folders.py` and
`test_move_external.py`; `tests/emulator/test_internal_folders.py` and
`test_move_external.py`; `tests/firmware/test_storage_folders.py` and
`test_usermod_files_folders.py`; and `tests/app/test_downloads.py`,
`test_internal_folders.py` and `test_moves.py` with their scenarios in Chrome against the
emulator. The memory of the core is unchanged: `sizeof(Core)` is 3,720 bytes on the test
host and 3,528 on the board, `FileInfo` 48, `Upload` 72 and `DriveIndex` 716 on both.

### Builds

Built on Windows from the pushed head 9e2e329 with a clean tree; each build record names
that commit and `trackedDirty` false.

| File on the Drive | Bytes | SHA-256 | Link |
|---|---:|---|---|
| `odrig-seed74b-9e2e329-n16r8-installation.bin`, the installation's board, `odrig_microsd` | 1,904,720 | `9e2b959c319e83ec3d425785a34fcda4156e0d0a4b73c2afabca75762aacc5a9` | [download](https://drive.google.com/uc?export=download&id=1QxsUVGR19XVLQg2-0FED8CL7ax5sctVT) |
| `odrig-seed74b-9e2e329-n8r2-spare.bin`, the spare, `odrig_microsd_n8r2` | 1,902,176 | `50f7f0bc45e8936aa3deed94446159576912460878d2b22d384953d6468e5656` | [download](https://drive.google.com/uc?export=download&id=1c3vLuuVu4HHl0ewF4t8PL5wgVRdRyg5s) |
| `odrig-seed74b-9e2e329.apk`, signed with the persistent key | 19,125,340 | `b3582f88fa2164c4d880819763a1a476ab79b63b607c245a085cece588e4ad49` | [download](https://drive.google.com/uc?export=download&id=1iNx260ANPwoVkIce9iVFKvi7-zit8FMS) |

Both images passed `verify_build.py` for their module, the installation's first. The APK's
signature, by the persistent key's certificate of SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, and its alignment were
verified with `apksigner` and `zipalign -c 4`. They are in the Drive folder
`odrig archive/seed-74-part-b-9e2e329/`, each copy checked against its SHA-256.

The APK was not installed on an emulated phone this time, so the native plugin `Save` has
still not run on Android; its web code is the code the app suite ran in Chrome.

### Not done: the board session

No board is connected to the computer that built part B, so none of this has been done:

- [ ] `read <id> <offset> 720` on the board, and a `Download` and a `Download selected` read
  through it.
- [ ] `folder make internal` on the board's LittleFS, with `LFS_NAME_MAX` covering a name of
  32 characters in `/odrig/255/` and the cost of a directory, and uploads into a folder of
  the board's storage.
- [ ] `move external` on a real SD card through `upload.part`, and the journal
  `drive/moving.txt` finished or dropped at the next mount after a power cut during a move.
- [ ] The stack margin of the command task for the deepest chain of `move external`, 2,416
  bytes by `-fstack-usage`.

### The owner's checks, open

- [ ] Step 24 of the check on a phone in [docs/android-app.md](../../android-app.md):
  moves of files and folders within and between the storages, and a folder's move cut by
  the phone's Wi-Fi and finished at the next connection.
- [ ] `Download` in a row's menu and `Download selected` for a folder of the card on the
  phone: a place chosen in the system's dialog, the file and the zip opened there, as
  "Downloads and backups on a phone" of its "What is open" says.
- [ ] On the LEDs, the playlist of a folder of the board's own storage, chosen with
  `Play this folder`.
