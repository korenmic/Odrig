# Verification

## Software

Seed 61 is on the branch `seed-61-internal-clocks`, pull request #65, made from
`all-unmerged-seeds` (pull request #63). These are its commits, in order:

| Commit | What it is |
|---|---|
| 1218687 | The spec, with the owner's answers of 2026-11-09 |
| be461e8 | Task 1: the board's own clocks and messages play in both modes, the SD card's copy first |
| adf8182 | Task 2: the preferred storage chosen with `clocks storage sd\|internal` |
| 3e6b2f6 | Task 3: the app's preferred storage, and Clocks only over both storages |
| 8cfb96b | Task 4: the rehearsal of the seven messages' deployment on the emulator |

- Task 1: `tests/core/test_internal_clocks.py` holds recognition of the board's `clocks/`
  and `clocks/message/`, Between, Only, Only with Ignore, the LEDs' `off`, the copies under
  `SD card` with a show of more than 132 items and each copy's brightness, and a flat show's
  replies byte for byte. The memory of the core is unchanged: `sizeof(Core)` is 3,792 bytes
  on the test host and 3,592 on the board, `FileInfo` 48 and `Upload` 72 on both.
- Task 2: `clocks storage sd|internal` in the core, `clocks.txt` of version 3, `status`'s
  `clock_storage`, the command tool's line, the emulator over the serial port, TCP and HTTP
  with the choice kept across a restart, and the firmware tool keeping a `clocks.txt` of
  version 3 through a show install.
- Task 3: `tests/app/test_clock_storage.py` and `tests/app/test_only_both.py`, with their
  scenarios in Chrome against the emulator: the dropdown and its states, Only with the
  board's Clocks folder alone and with both, the Clocks level, play and upload inside, the
  archive and the batch in Only, a target without `clock_storage`, and the bar of the
  animation playing now.

The suites of task 4's run at the head 8cfb96b, the head these files were built from:

| Suite | Tests |
|---|---:|
| core | 1,258 |
| emulator | 698 |
| app | 669 |
| firmware | 691 |
| firmware host | 37 |
| converter | 552 |
| `npm test --prefix converter` | 1,606 |
| onboarding | 88 |
| mapping | 49 |
| runner | 26 |

They pass but for the failures known on this computer, which are not faults of the code:
`tests.app.test_message_source`, for Pillow is not installed here; the firmware suite's two
tests of `test_env` and its `test_paths`, for the toolchains are reached through a junction;
and tests that failed on time under the load of a whole run and passed when run alone.

For this delivery the firmware suite was run again at that head, on its own with
`ODRIG_TOOLS`, after both images were built: 691 tests, which pass but for the same two of
`test_env` and `test_paths`. The onboarding suite was run again with this file and the
seed's line in `AGENTS.md`: 88 tests, which pass.

## Builds

Built on Windows from the pushed head 8cfb96b with a clean tree; each build record names
that commit and `trackedDirty` false.

| File on the Drive | Bytes | SHA-256 | Link |
|---|---:|---|---|
| `odrig-seed61-8cfb96b-n16r8-installation.bin`, the installation's board, `odrig_microsd` | 1,912,368 | `bb99a3f6b05f8ac24eb855e99cbd8e193594eda8e8316fc39f23f1ebb04ee953` | [download](https://drive.google.com/uc?export=download&id=1Br02Cto9hyIxWf6paxs79mfXnEsfeWVK) |
| `odrig-seed61-8cfb96b-n8r2-spare.bin`, the spare, `odrig_microsd_n8r2` | 1,909,840 | `c96500e1c1fbfbb74c1cb28490a62a961110438c86a701f5763028c550f22d14` | [download](https://drive.google.com/uc?export=download&id=1v805-Kh3hfauQxX4XHz2ILN0ET1eVXcG) |
| `odrig-seed61-8cfb96b.apk`, signed with the persistent key | 19,257,425 | `d3c0959d2515d048d28d9dca1d48898cd94751d67a49bae92300386e614b2a86` | [download](https://drive.google.com/uc?export=download&id=1eesTkW4I3WZAhbwXpXokRNpUAX4gXXrK) |

Both images passed `verify_build.py` for their module, the installation's first. The APK's
signature, by the persistent key's certificate of SHA-256
`5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`, and its alignment were
verified with `apksigner` and `zipalign -c 4`. They are in the Drive folder
`odrig archive/seed-61-8cfb96b/`, each copy checked against its SHA-256.

Flashing an image installs no message: the seven are put into the board's own storage by
the board session below. The APK was not installed on an emulated phone this time; its web
code is the code the app suite ran in Chrome.

## The rehearsal of task 4

`tests/emulator/test_message_rehearsal.py` runs the board session's commands with the
command tool over TCP against the emulator, in the design's order, with the tracked files
of `collection/card/clocks/message/`. It is a rehearsal of the commands on the emulator,
not a deployment: nothing has been put on a board.

- The emulator's show has its own catalog, as the firmware tool installs one, and turns of
  a second. Its card has a catalog, a face in `clocks/` and a message of its own in
  `clocks/message/`; its board holds an animation in the internal folder `a/b` under an id
  that a walk of one level would give to one of the seven.
- `status`, `space` (163,840 bytes free or more), `catalog` (the internal catalog `ok`),
  the walk of `list` and `list in` at every depth, `folder make internal clocks` and
  `clocks/message`, the seven uploads with `--folder clocks/message` under ids chosen after
  both replies, `list in` with the seven paths, `catalog` with a new generation and seven
  entries more, and each file read back 720 bytes at a time, its SHA-256 compared with the
  design's table, 79,235 bytes in all.
- `clocks storage CHECK`, `clocks message on`, `clocks only`: a message of the board's own
  storage after the card's face; `clocks on`: an ordinary turn, the face, then a message of
  the board's own storage. The mode, the message and the storage found are given back, the
  brightness stays at 40 or less, the show folder's `<n>/v7-*.odrgx` hold the same bytes,
  and every row of the board found at the start is listed again.
- It runs twice:
  `test_the_board_prefers_its_own_storage_and_the_card_has_none_of_the_seven` (Between,
  the message off and `Internal storage` found, checked with `sd`, the preference given back
  to `internal`), and `test_the_card_holds_the_seven_and_the_sd_card_is_preferred` (a new
  board's settings and the seven copied on the card, checked with `internal`, no card copy
  of the seven seen playing).

## Not done: the board session

No board is connected to the computer that built this seed, so the deployment of the seven
messages has not been made, nor read back, nor seen chosen in either mode. It stays open for
the owner, or for a session run with the owner's leave, with the installation's board on USB
at the port `PORT` (or `--http ADDRESS` in place of `--port PORT` over Wi-Fi), no other
client connected, and the firmware of this seed on the board. `python` is the checkout's
`.venv` Python, run from the repository's root.

The files, as tracked in `collection/card/clocks/message/`:

| File | Bytes | SHA-256 |
|---|---:|---|
| `v7-consciousness.odrgx` | 9,588 | `592977056b2b7473d7c7b860f9a4f1e786d9abfe4cbd16962e9954cf461fed3d` |
| `v7-symmetry.odrgx` | 7,737 | `911f857d47a3d972d549566d54a57d794307b5e33f9be41d6becc4ebd6bb1347` |
| `v7-temperature.odrgx` | 9,574 | `a34aada473c03d6146fcb46da9a35001e0ecadd23d77d60cc98d2844f6285487` |
| `v7-the-time.odrgx` | 9,594 | `108fa62aabf425ca39f29dec7b6b8c9fed7457f6c16dfdc9536a49a2daa6fc0c` |
| `v7-countdown.odrgx` | 22,515 | `8cb82ff0b2fcd2cc35fb6f3507889b633d02bacc5673bd10a1b39e2352786d6c` |
| `v7-the-clock.odrgx` | 7,747 | `4963cc42d63ecec1dfca9f407e48dab39c6db61c08e435e405f238687d6a1256` |
| `v7-mistakes.odrgx` | 12,480 | `4aa1bfa59dcb8ce53f136cfc9229961cac11dbd454aa6e33c26f689a665bcf1f` |
| Together | 79,235 | |

**Room.** The files take 23 blocks of 4,096 bytes, 94,208 bytes; the two folders 2 blocks
each, 16,384; an upload stages its file once, at most 6 blocks of the largest, 24,576; the
internal catalog's records and pages a few blocks more. The session goes on only when
`space` gives `free` of 163,840 bytes or more, 40 blocks, and stops before it writes
anything otherwise.

**The commands**, as the design gives them:

```
python -m odrigctl --port PORT status
python -m odrigctl --port PORT brightness 40
python -m odrigctl --port PORT space
python -m odrigctl --port PORT catalog
python -m odrigctl --port PORT list
python -m odrigctl --port PORT list in FOLDER_ID
python -m odrigctl --port PORT folder make internal clocks
python -m odrigctl --port PORT folder make internal clocks/message
python -m odrigctl --port PORT --folder clocks/message upload ID1 collection/card/clocks/message/v7-consciousness.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID2 collection/card/clocks/message/v7-symmetry.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID3 collection/card/clocks/message/v7-temperature.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID4 collection/card/clocks/message/v7-the-time.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID5 collection/card/clocks/message/v7-countdown.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID6 collection/card/clocks/message/v7-the-clock.odrgx
python -m odrigctl --port PORT --folder clocks/message upload ID7 collection/card/clocks/message/v7-mistakes.odrgx
python -m odrigctl --port PORT list in MESSAGE_ID
python -m odrigctl --port PORT catalog
python -m odrigctl --port PORT read ID1 0 720
python -m odrigctl --port PORT clocks storage CHECK
python -m odrigctl --port PORT clocks message on
python -m odrigctl --port PORT clocks only
python -m odrigctl --port PORT status
python -m odrigctl --port PORT clocks on
python -m odrigctl --port PORT status
python -m odrigctl --port PORT clocks MODE
python -m odrigctl --port PORT clocks message MESSAGE
python -m odrigctl --port PORT clocks storage STORAGE
python -m odrigctl --port PORT list
python -m odrigctl --port PORT list in FOLDER_ID
python firmware/fw.py read-show build/seed61-readback --port PORT
python -c "import hashlib,pathlib; [print(hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p) for p in sorted(pathlib.Path('build/seed61-readback').glob('*/v7-*.odrgx'))]"
```

Their rules are those of "The seven messages" in [design.md](design.md): `status` first,
its `brightness`, `clock_mode`, `clock_message` and `clock_storage` written down as the
owner's, the brightness line sent only when it is above 40 and never raised again; `space`
of 163,840 or more, else the session stops; `catalog` asked again while the card's is
`loading`; the walk of `list` and `list in` at every depth, its rows with
`"external":false` written down as the board's content; `ID1` to `ID7` chosen after both
`folder make internal` replies, seven ids of 60,000 or less that no row of the walk has and
neither reply names; each upload ending with success, else the session stops; `CHECK` `sd`
when no row of the card's `clocks/message` has one of the seven names and `internal` when
one has; the `status` after `clocks only` and after `clocks on` repeated until `file` is one
of the seven after a face, and in Between after an ordinary turn before that face, for at
most 20 minutes; `MODE`, `MESSAGE` and `STORAGE` giving back the owner's settings; the walk
made again listing every row of the board's content found at the start; `read-show` and the
one-liner giving each file's SHA-256 and size, compared with the table above.

The session keeps the board's protections: one client of the board at a time, the flash
never erased, a brightness of 40 or less, and no change of wiring, power, Wi-Fi, display or
current limit. If access, space or a step only a person can make stops it, the board's
content is kept and the step not done is named.

**The record** of the session, to be written here when it is run:

- [ ] The settings found: `brightness`, `clock_mode`, `clock_message`, `clock_storage`.
- [ ] `space`'s `free` before the session and after it.
- [ ] The internal paths, `clocks` and `clocks/message`, and the ids of the two folders.
- [ ] `ID1` to `ID7`, each with its file.
- [ ] The folder's number `<n>` that `folders.txt` of the read-back names.
- [ ] `catalog`'s internal state and generation before and after the uploads.
- [ ] The SHA-256 and size of each file read back, compared with the table above.
- [ ] `CHECK`, and the card's messages it was chosen by.
- [ ] The files and ids seen playing in Only and in Between.
- [ ] The settings given back, and the walk made again.
- [ ] Every step not done, with its reason.

## The owner's checks, open

- [ ] On the LEDs: in Clocks only and in Between, with the message on, a face of the card
  followed by a message of the board's own `clocks/message`; and with a copy of a message
  in both storages, under `SD card` the card's copy plays and under `Internal storage` the
  board's, never both.
- [ ] On a phone, step 23 of the check on a phone in
  [docs/android-app.md](../../android-app.md): the dropdown `Preferred storage for matching
  clock/message files`, its choice kept across a restart of the board, and Clocks only
  showing the Clocks level of both storages, playing inside the board's own `clocks/` and
  `clocks/message/`, and taking an upload into them.
