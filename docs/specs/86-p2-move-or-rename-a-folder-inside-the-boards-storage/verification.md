# Verification

## Software

Seed 86 is on the branch `seed-86-move-a-folder-inside-the-board`, pull request #67, made
from `master` 89e9c75 with seed 74 part B's branch (pull request #64) merged as 7005884.
These are its commits, in order:

| Commit | What it is |
|---|---|
| 2742a2d | The spec |
| 999e7ac | Task 1: `move internal <folder id> <path>` in the core |
| c8b41cf | Task 2: the emulator's line and the command tool |
| aeb9ab7 | Task 3: `Rename…` and `Move to…` of a folder of the board's storage in the app |

- Task 1: `tests/core/test_folder_move.py`, 15 tests: a rename, a move to another parent,
  to the root and from the root to depth 3, each `folders.txt` byte for byte; its own path
  answered `"moved":false` with no store call; a rename that changes only the case; every
  refusal in its order; the limits of the subtree at 93 bytes and of its files at 100; a
  file listed at the root for its long path, which blocks no move; the other refusals; a
  failed store call at each of the move's calls; ids, numbers, stored names, saved
  brightness and repeat, the saved order, the internal catalog and `show.json` kept; the
  root's walk of the new tree; Ignore inherited and lost; a moved current playlist and one
  below it in `status` and `playlist.txt`; the animation that plays going on; a power cut
  at each of the move's store calls. The memory of the core is unchanged; the board's
  compiler gives 272 bytes to the largest new frame.
- Task 2: `tests/emulator/test_folder_move.py` over the serial line and HTTP and with the
  command tool, and the tool's line and its usage errors in `tests/emulator/test_tool.py`.
- Task 3: `tests/app/test_folder_move.py` in Chrome against the emulator behind a target
  of the test's own: the menu on both storages, `Rename…` with a name taken in another
  case, `Move to…` with its destinations and their reasons, a selected folder moved inside
  the board's storage by the same line, a refusal, a firmware without the command and a
  reply lost after the board moved the folder; the refusal texts in
  `tests/app/test_messages.py`.

The suites at the head aeb9ab7, the head these files were built from:

| Suite | Tests |
|---|---:|
| core | 1,162 |
| emulator | 667 |
| app | 501 |
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
and tests that failed on time under the load of a whole run and passed when run alone
(`tests.emulator.test_content`'s list over the line port, `tests.app.test_frozen`'s top
sideways).

## Builds

Built on Windows from the pushed head aeb9ab7 with a clean tree; each build record names
that commit and `trackedDirty` false. The installation's image first, then the spare's,
each passed `verify_build.py` for its module. The APK is signed with the persistent key;
`apksigner` confirmed the certificate of SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, and `zipalign -c 4`
passed. They are in the Drive folder `odrig archive/seed-86-aeb9ab7/`, each copy checked
against its SHA-256:

| File | Bytes | SHA-256 | Link |
|---|---:|---|---|
| `odrig-seed86-aeb9ab7-n16r8-installation.bin`, the installation's board, `odrig_microsd` | 1,906,624 | `d28de07d244552f1b2b579c5a6ebc20c6e07204f921edb22e9ccce0eb688ec64` | [download](https://drive.google.com/uc?export=download&id=1MY_v5Elb5P57n6XXC7H2wxr2Lp9SV436) |
| `odrig-seed86-aeb9ab7-n8r2-spare.bin`, the spare, `odrig_microsd_n8r2` | 1,904,080 | `92a75de526b3f00f7c458e28d258098f31f32425742cf4bbbdef7dd1350ab114` | [download](https://drive.google.com/uc?export=download&id=12bf30ajO8P-xu6FS46JhplAOpznU29ey) |
| `odrig-seed86-aeb9ab7.apk`, signed with the persistent key | 19,129,436 | `9ddb71657d0f72fd5b5bdef28b21d8b7f1f8f42515262d4652ba2454a421c6f3` | [download](https://drive.google.com/uc?export=download&id=1mWuChDG2YsvA_N4s8MSLjx3Opv6176Ux) |

## Open

- [ ] The owner's check on a phone, step 25 of "The check on a phone" in
  `docs/android-app.md`: a folder of the board's storage that holds an animation renamed,
  moved under another folder and back to the root; the animation keeps its preview,
  brightness and place in the order and plays on; a current playlist follows the folder;
  all of it after a restart too.
- [ ] The test of seed 61's internal clocks, a move into `clocks/message` and out of it,
  is added where seed 61 is built with this seed: when it joins pull request #63.
- [ ] On a board: the rewrite of `folders.txt` on LittleFS. No board is connected to the
  computer that built this.
