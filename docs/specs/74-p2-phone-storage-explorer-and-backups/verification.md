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
