# Verification

## Software

Seed 85 is on the branch `seed-85-remove-an-empty-folder`, pull request #66, made from
`master` 89e9c75 with seed 74 part B's branch (pull request #64) merged as 7005884. These
are its commits, in order:

| Commit | What it is |
|---|---|
| 4d62fc6 | The spec |
| e075036 | Task 1: `folder remove <id>` in the core, on both storages |
| 1bb5ade | Task 2: the emulator, the firmware's card host and the command tool |
| b774a8d | Task 3: `Remove folder` in the app |

- Task 1: `tests/core/test_folder_remove.py`, 21 tests: every refusal in its order, an empty
  folder of the board's storage made and removed with its numbered folder and its id free
  again, folders that hold a file, a file listed at the root for its long path, or a
  sub-folder, no cascade, the current playlist removed and kept, the animation that plays
  going on, a folder the storage cannot remove, the store calls and a power cut at each of
  them; on the card a folder removed in one commit with every other id kept, the levels after
  it, folders that are not empty, an animation's id, the current playlist after it and the
  removed one, an empty `clocks` in Clocks only, a folder that holds a file the index does
  not know, a read-only card, a test that shows, an open upload, a USB stick, a card that is
  out, and a power cut at each storage call. The memory of the core is unchanged; the
  board's compiler gives 368 bytes to the largest new frame.
- Task 2: `tests/emulator/test_folder_remove.py` over the serial line and HTTP with the
  command tool, the card host's `rmdir` in `tests/firmware/test_usermod_drive.py`, and the
  tool's line and its usage errors in `tests/emulator/test_tool.py`.
- Task 3: `tests/app/test_folder_remove.py` in Chrome against the emulator behind a target
  of the test's own: the menu's states and notes on both storages and on a read-only card,
  the check of the level, the question with `Cancel`, Escape and `Remove`, a refusal, a
  firmware without the command, and a reply lost before and after the board removed the
  folder; the refusal texts in `tests/app/test_messages.py`.

The suites at the head b774a8d, the head these files were built from:

| Suite | Tests |
|---|---:|
| core | 1,168 |
| emulator | 668 |
| app | 502 |
| firmware | 678 |
| firmware host | 37 |
| converter | 552 |
| `npm test --prefix converter` | 1,602 |
| onboarding | 88 |
| mapping | 42 |
| runner | 26 |

They pass but for the failures known on this computer, which are not faults of the code:
`tests.app.test_message_source`, for Pillow is not installed here; the firmware suite's two
tests of `test_env` and its `test_paths`, for the toolchains are reached through a junction;
and tests that failed on time under the load of a whole run and passed when run alone
(`tests.emulator.test_preview`'s refusal within 5 s, `tests.app.test_order`'s drag by a
mouse, which passes alone here as on the commit before task 3).

## Builds

Built on Windows from the pushed head b774a8d with a clean tree; each build record names
that commit and `trackedDirty` false. The installation's image first, then the spare's,
each passed `verify_build.py` for its module. The APK is signed with the persistent key;
`apksigner` confirmed the certificate of SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, and `zipalign -c 4`
passed. They are in the Drive folder `odrig archive/seed-85-b774a8d/`, each copy checked
against its SHA-256:

| File | Bytes | SHA-256 | Link |
|---|---:|---|---|
| `odrig-seed85-b774a8d-n16r8-installation.bin`, the installation's board, `odrig_microsd` | 1,906,000 | `5105f905202669b5873adc062a33946ba35d8e6d1c8132f6c0f002a616c1c263` | [download](https://drive.google.com/uc?export=download&id=1kDVhSrMtjExQG75a_j6N-CY2CA3Ib0Hq) |
| `odrig-seed85-b774a8d-n8r2-spare.bin`, the spare, `odrig_microsd_n8r2` | 1,903,472 | `da2323eccac40ffb94ea7b4a21719e137fb2cc4e11af2a4a4dc672c4cb67c3b5` | [download](https://drive.google.com/uc?export=download&id=1LYdMSALPgfC35up3i3oUvda5Gpr9koL5) |
| `odrig-seed85-b774a8d.apk`, signed with the persistent key | 19,125,340 | `0490fc0faf7d5c4bf16e8bdf839aa9a8a629ff1bf6ccfe65259a2ce9d5ec24a9` | [download](https://drive.google.com/uc?export=download&id=1n1Y9vZ1V2KD_8HGDWIVbOMQk_w--8eed) |

## Open

- [ ] The owner's check on a phone, step 25 of "The check on a phone" in
  `docs/android-app.md`: an empty folder made on the board's storage and one made on the
  card are each removed with `Remove folder`, gone from the list and still gone after a
  restart; a folder with an animation cannot be removed, and the app says why.
- [ ] On a board: `rmdir` of an empty folder of a real SD card and of one that holds a file
  the index does not know, and the removal of a numbered folder of the board's own
  storage on LittleFS. No board is connected to the computer that built this.
