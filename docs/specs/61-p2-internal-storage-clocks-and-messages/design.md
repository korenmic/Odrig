# Design

At no memory of the core. The model is seed 74 part B's folders of the board's own
storage: every file of a folder has the stored name `<n>/<name>`, the folders' paths are
lines of `folders.txt` in the tree's order, and each file of the file table carries its
folder's `rank` and `held` in two bytes that part B packed. This seed adds three bits to
each file, a 16-bit id and one bit to the core object, inside room that is there, and
works everything else out when it is needed.

## Memory, measured on this branch

Measured on 2026-11-09 on the head of `all-unmerged-seeds`, b1fa775f, with g++ of the test
host and with `xtensa-esp32s3-elf-g++` of the board's toolchain
(`scratch/seed76-tools/firmware/hosts/win32-x86_64/newer/pio/packages/toolchain-xtensa-esp-elf`),
by a probe that includes `core_state.h` and prints sizes and offsets:

| | Test host | Board |
|---|---:|---:|
| `sizeof(Core)`, alignment 8 | 3,792 | 3,592 |
| `rebuild_open`, the last whole byte | 3,785 | 3,585 |
| The byte of `internal_folders:6` and `folders_error:1` | 3,786 | 3,586 |
| The data's end, and the padding after it | 3,787, 5 bytes | 3,587, 5 bytes |
| The bit-field byte `turn_manual` ... `clocks_error`, 7 of 8 bits | 3,502 | 3,302 |
| `sizeof(FileInfo)`, byte 38 `checked:2 type:2 held:1 spare:3` | 48 | 48 |
| `sizeof(Upload)` | 72 | 72 |

The same probe with this design's fields in place:

| | Test host | Board |
|---|---:|---:|
| `uint16_t clocks_internal_id`, after the byte of the folders | at 3,788 | at 3,588 |
| The data's end, and the padding after it | 3,790, 2 bytes | 3,590, 2 bytes |
| `sizeof(Core)` | **3,792** | **3,592** |
| `clock_storage_internal:1`, the 8th bit of the byte of `turn_manual` | byte 3,502 | byte 3,302 |
| `FileInfo`, byte 38 `checked:2 type:2 held:1 clock:2 copy:1` | **48** | **48** |
| `Upload` | **72** | **72** |

So every figure of the memory table of `docs/core.md` stays: the total 125,257, the target
with a drive 131,045, the example show 88,546, the host without storage 77,717, 18 blocks
or 21 with a drive. `tests/core/test_docs.py`, `test_memory.py` and `test_drive.py` pass
unedited. Nothing is allocated after the start, no block, table or cache is added, and no
host function: `odrig_host` keeps its pointers.

- `FileInfo.clock`, two bits: `kNotClock` 0, `kClockFace` 1, `kClockMessage` 2,
  `kClockBelow` 3, a file of another folder of the Clocks subtree.
- `Core.clocks_internal_id`: the id of the internal folder `clocks`, 0 when there is none.
- `Core.clock_storage_internal`: the preferred storage, 0 for `SD card`, 1 for `Internal
  storage`.
- `FileInfo.copy`, the last spare bit of byte 38: the mark of a copy (below). It is written
  in a draw before that draw reads it, and read in no other place, so a mark left by an
  earlier draw is never taken. A bit of each file holds a show of any size: the item table
  has room for 32 items more than `show.json` lists, 128 at least, so a bitset of fixed
  size on the stack would not.

## The class of a file

`folders_derive` (`core/src/folders.cpp`) already reads `folders.txt` once and writes each
file's `rank` and `held`. In the same pass, for each line:

- the line's path is `clocks` exactly: its files are `kClockFace`, and
  `clocks_internal_id` is its id;
- the path is `clocks/message` exactly: `kClockMessage`;
- the path begins with `clocks/`: `kClockBelow`;
- else `kNotClock`.

It clears every file's `clock` and `clocks_internal_id` first, as it clears `rank` and
`held`, and on every early return: a show without folders, a boot that cannot read
`folders.txt` and a host without `read_at` have no internal clocks. A file at the root, and
an orphan whose folder has no line, keep `kNotClock`. The paths are compared by their
bytes, as `drive_folder_with_path` finds the card's. `folders_derive` runs at the start
and after every change that can move a file into or out of a class (spec 74): `folder make
internal`, a folder's Ignore, an install or a removal of a file of a folder, a prune.
`folders_start` clears them too before it reads.

## The bags

`pick` of `core/src/breaks.cpp` draws from one shuffled order of `size` places, as today.
For the class C, `kClockFace` for a clock and `kClockMessage` for a message:

- **E**, the card's candidates: `clocks_files` from `clocks_first`, or `message_files` from
  `message_first`, the card folder's own files, as today; 0 without the folder or the card.
- **I**, the board's candidates: the animation items whose file's `clock` is C, counted at
  each draw in item order, at most the item table's size.
- **The order** has E + I places, and a change of that count draws a new order, as a change
  of E does today. Place k < E is the card's position `first + k`; place k >= E is the
  (k - E)-th item of class C in item order.
- **A card place** is taken when `drive_automatic` holds and, with `Internal storage`
  preferred, no internal copy of it plays (`plays()`, which holds Ignore, `held` and
  quarantine).
- **An internal place** is taken when `plays()` holds and, with `SD card` preferred, it is
  not marked as a copy of an eligible card file.
- **The marks** are the `copy` bits of the files. They are made at most once in a draw, and
  only when the draw lands first on an internal place while `SD card` is preferred: the
  `copy` bit of every file of class C is cleared, the E rows of the card folder are read
  once, and every row that passes `drive_automatic` sets the bit of each file of class C
  that is a copy of it. A flag on the draw's stack says whether this draw made them; an
  internal place is judged by its bit only after that, so no bit of an earlier draw is
  read.
- **A copy**: the row's name after the exact prefix `clocks/`, or `clocks/message/`, equals
  the internal file's name after its `<n>/`, compared without the case of ASCII letters,
  and the row's `type` equals the file's `type`, both known (1 to 3). A type of 0, not yet
  known, is never a copy.
- At most two whole orders are tried, as today. A draw does what it did plus, at most, one
  pass over E rows that the card's own draw could read twice anyway, and passes over the
  item table in memory: no animation body, and no stack frame near 512 bytes.

`breaks_pick` and `breaks_message` keep their forms and return a position of the playlist,
`kDriveBase + position` for the card and the item's position for the board's own storage,
which every caller already takes as such.

## Between animations

- The card's Clocks subtree is passed over through `breaks_passes_over`, as today. The
  board's is passed over in `lowest_playing` (`core/src/player.cpp`): while `clocks_on` is
  not 0, an item whose file's `clock` is not `kNotClock` is skipped. That gives the root's
  walk, an internal playlist's walk, `first_in`, `next_in`, `judge_in_place` and the
  rotation's playlists the same pass-over as the card's. It is not put into `plays()`,
  which a break's own turns and the paused turn rely on.
- `breaks_has_face` also holds when an internal face `plays()`.
- A break with no face of either storage comes to nothing, as today, whatever messages
  there are.

## Clocks only

| Place | With the board's clocks |
|---|---|
| `breaks_position_allowed` | An item of the show is inside when its file's `clock` is not `kNotClock`. The card's rule is unchanged. |
| `play_only` (`commands.cpp`) | `clocks_internal_id` restarts Clocks, as `clocks_id` does. An item of the show inside the boundary plays as a manual turn through `player_jump`; a cycle or an item outside answers `in-use`; a quarantined one `unavailable`. An internal folder whose path is `clocks` or begins `clocks/`, read with `folder_by_id`, plays the first item of its subtree's ranks inside the boundary that `item_usable` holds, by the walk's key, or restarts Clocks when it has none; another internal folder answers `in-use`. |
| `player_jump` | The phase of an internal item comes from its class: a face is `kBreakClock`, a message `kBreakMessage` with its one complete loop, `kClockBelow` none. |
| `player_only_refresh` | An internal item stays while it is inside, `item_usable`, and manual, or `plays()` with a face to come (`breaks_has_face`). |
| `player_first_in_playlist` | In Only: the first eligible face of the preferred storage, then of the other. |
| `breaks_only_state` | While `clocks_internal_id` is 0, today's states in today's order, so a show without an internal Clocks folder answers byte for byte as today. Else `playing` while something plays, and `no-clocks` while nothing does. |
| `player_inclusion_changed`, `player_internal_inclusion_changed`, `player_file_failed` | In Only, each sets `only_dirty` and calls `player_only_refresh`, as `player_external_inclusion_changed` and `player_drive_changed` do; `player_file_failed` first closes the stream of the failed file, as today. Today the first plays on through `player_play_all`, which restarts Clocks and so cuts a manual turn; the second returns at once in Only, so taking an internal Clocks folder in again would leave Only dark; and the third restarts Clocks for a manual turn that only an Ignore keeps out of `plays()`. |

`player_item_added` and the removals already mark Only dirty, and its refresh above looks at
the program again, so an install into `clocks/message` or a removal is taken without a new
path.

`status` (`commands.cpp`): `playing` and `playlist` in Only, and `clock_only.folder`, take
`clocks_id`, else `clocks_internal_id`. `file` is the internal file's logical path through
`logical_path`, as part B gives it.

The reply gains `,"clock_storage":"sd"`, 21 bytes, or `,"clock_storage":"internal"`, 27,
after `clock_mode` (task 2). The longest reply of `status` on this branch is the one that
`test_the_longest_reply_to_status_fits_1024_bytes` of `tests/core/test_internal_folders.py`
builds: 991 bytes and the newline, 992, in Between, with a file of a 100-byte path playing
in a 93-byte internal playlist and every other member at its longest. With the member it is
1,019 of the 1,024 bytes, 5 to spare. In Only `playlist` is `clocks` or null, and `clock_mode`
is `only`: at most 966. `clock_error` comes only with a dark Only that names no file, with
`SD card` in force: at most 883, and 993 if those members were all at their longest at once.
That test's two shapes gain the member after `clock_mode`, and it gains a third shape, Only
with `clock_error`; each stays at 1,024 or less.

## The preferred storage

`clocks storage sd` and `clocks storage internal` are parsed beside the other `clocks`
lines and go to `breaks_command`, which takes which setting changes: the mode, the message
or the storage. Its checks are those of the message line, in the same order: `show-invalid`,
then `busy` (a rebuild, the check after the start not complete, an upload open), then
`storage-error` for a storage that cannot change or a host without `read_at`, then
`storage-error` while `clocks_error`. A choice in force answers `{"ok":true}` and writes
nothing. Else the file is written, verified and renamed, then
`clock_storage_internal` is set and `order_count` and `message_order_count` are set to 0, so
both bags are drawn again at their next draw; the turn in progress and a break are not cut.

`clocks.txt`:

```
odrig-clocks 3
mode between
message on
storage internal
```

- `write_file` writes version 2, byte for byte as today, while `SD card` is preferred, and
  version 3 with the fourth line `storage internal` while `Internal storage` is. The longest
  is 15 + 13 + 12 + 17 = 57 bytes, under the 64 that `kClocksRead` reads; the part, the read
  back, the compare and the rename are unchanged, and a mode or message change keeps the
  preference in what it writes.
- `load_settings` takes versions 1, 2 and 3, each strictly: version 3 must end with
  `storage sd` or `storage internal` and nothing after it. Versions 1 and 2, and a missing
  file, give `SD card`. It sets the preference only when the whole file is in form. A file
  out of form fails closed as today: `clocks unreadable`, dark Only, and the preference
  `SD card` in force until a mode line replaces the file or a later read of `breaks_poll`
  finds it in form, which then gives its preference as well.
- `breaks_start` sets the preference to 0 before it reads.

No catalog, animation or show file is touched by it, and the firmware tool already keeps
`clocks.txt` through show installs.

## The app

The shared code of `app/www`, which the emulator's Controller and the APK both run.

- **`commands.js`.** `status` takes `clock_storage` when it is there: `"sd"` or
  `"internal"`, any other value a `bad-reply`; the parsed status has `hasClockStorage` and
  `clockStorage`. `clockStorage(storage)` sends `clocks storage sd|internal`.
- **`index.html` and `screens/clocks.js`.** Under the mode's dropdown, the label `Preferred
  storage for matching clock/message files`, the explanation `Applies when the same relative
  path and file type exist in both storages.`, and `<select id="clock-storage">` with
  `SD card` (`sd`) and `Internal storage` (`internal`). `clocks.js` handles it as it handles
  the mode: `sending`, `uncertain`, the confirming status, the refusal's explanation, a
  change of target. Its saved words are `Saved: matching files play from the SD card.` and
  `Saved: matching files play from internal storage.`. It is disabled while a change is
  sent, without a fresh answering status, and while `clockError` is set. Without
  `hasClockStorage` it is disabled at `SD card`, and the line under it says `This target
  plays the card's clocks and messages only. Update its firmware to use those of the board's
  own storage.`
- **The panel's words.** `Clocks only restricts playback to the clocks folders.`; Only's
  states: `no-card`, `Clocks only is waiting: internal storage has no clocks folder and no
  external storage is present.`; `missing-folder`, `Clocks only is waiting: neither storage
  has a clocks folder.`; `no-clocks`, `Clocks only is waiting: no included, available clock
  face can play.`; `playing`, `Only the clocks folders play. Browsing stays inside Clocks;
  leave this mode to browse elsewhere.`. A target without `hasClockStorage` keeps today's
  words.
- **The boundary (`client.js`).** On a target with `hasClockStorage`:
  - `inClocks` takes a path of either storage; on another target the board's paths stay
    outside, as today.
  - The storage of the folder that `clock_only.folder` names is told by its id: above 60,000
    the card's, else the board's.
  - The other storage's Clocks folder is the root's row with `playlist` `clocks` of that
    storage, from the root's list, which the client reads in the background as it does for
    an upload's names.
  - **The Clocks level.** When only one storage has a Clocks folder, the trail begins at it,
    as today. When both have one, the trail begins at the Clocks level, a level of the root
    that shows only the two rows of the Clocks folders, each with its storage; Back from
    either Clocks folder goes there, and no higher. Entering Only opens the Clocks level.
    Until the root's list is known, the trail begins at the folder the status names; when
    the list shows the other storage's Clocks folder, the Clocks level is put under the
    trail without moving the level shown, so Back reaches it. A status that names another
    folder, or a root list that no longer has one of the two, takes the trail back to the
    Clocks level, or to the remaining Clocks folder; the unavailable Clocks view is
    unchanged.
  - `canEnter`, `canGoBack`, `inClockFolder`, `canPlay` and `play` take the board's Clocks
    folder and its descendants, by path and by the storage of the level; `Restart clocks`
    still sends `play <clock_only.folder>`.
  - `canUpload` takes a destination of the board's own storage whose file's path begins with
    `clocks/` as it takes the card's, without the card's writable checks.
- **Uploads (`upload-destination.js`, `screens/storage.js`).** In Only the form's storage is
  the storage of the explored level, `capture`, `select` and `synchronize` keep it there,
  and the storage selector offers only that storage. `blocked` lets a form through when its
  level is a folder, not the Clocks level, inside that storage's Clocks subtree, and for the
  card only while it is present and writable. The words of a blocked form become `Clocks
  only: choose a folder inside Clocks, a writable one on the card, or leave this mode in
  Settings.` on a target with `hasClockStorage`; on another target they stay today's
  `ONLY_REASON`. The text and clock form saves to the board's root, outside Clocks, so it
  stays disabled in Only, as today.
- **The archive and the batch (`screens/archive.js`, `screens/batch-list.js`, `batch.js`).**
  They take their forms from `upload-destination.js` and keep its rule: in Only their
  storage selectors, like the Upload screen's, offer only the storage of the folder
  explored (today `archive.js` and `batch-list.js` disable `External` by the card alone and
  never `Internal`), and `gone` of `batch.js` keeps checking a form of the board's own
  storage by its folder alone. The preview of an upload keeps its place (target, storage,
  name) as for any folder of the board's own storage; nothing of it changes.
- **The animation playing now.** `screens/show.js` and `screens/brightness.js` write a file
  whose path begins with `clocks/` with its storage, told by the id of `animation`: `Now 12
  Internal /clocks/message/v7-the-time.odrgx`, `Animation 60004: External
  /clocks/analog.odrgx`. Other files read as today.
- **`messages.js`.** The Only refusals of `play` and `upload` speak of the clocks folders.
- `docs/android-app.md`: the panel, the dropdown and its states, Only with both storages,
  uploads, and the command table's row `Chooses SD card or Internal storage under Preferred
  storage` with `clocks storage sd`, `clocks storage internal`.

## The command tool, the emulator and the firmware

- `odrigctl/cli.py`: `clocks` takes `storage sd` and `storage internal` beside its other
  words; its usage, epilog and help name them. `docs/emulator.md` names the form.
- The emulator hosts the core and has no code of its own for clocks: its show folder's
  `clocks.txt` keeps the choice, and the serial port, TCP and HTTP carry the line.
- The firmware has no source change: the core is rebuilt into both images.
  `firmware/fwtool` already keeps `clocks.txt` and `folders.txt` and refuses an install that
  would remove the files of folders. `docs/firmware.md` says the clocks' three settings.

## The documents

- `docs/commands.md`: the command table, the section on the clocks (the board's Clocks
  subtree, copies and the preference, `clocks.txt` version 3, the refusals of `clocks
  storage`), the members `clock_storage` and `clock_only`, and the Only boundary of `play`.
- `docs/show.md`: "Clocks between the animations" and "Clocks only" with both storages.
- `docs/core.md`: "Clocks" and "Internal folders": the class, `clocks_internal_id` and the
  preference bit in room that is there, the marks on the stack; the memory figures stay.
- `docs/android-app.md`, `docs/emulator.md`, `docs/firmware.md` as above; `docs/drifts.md`
  for what an implementing task decides.

## The seven messages

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

**Room.** In blocks of 4,096 bytes the files take 3 + 2 + 3 + 3 + 6 + 2 + 4 = 23 blocks,
94,208 bytes; the two folders 2 blocks each, 16,384; an upload stages its file once, at
most 6 blocks of the largest, 24,576; the internal catalog's records and pages a few
blocks more. The session goes on only when `space` gives `free` of 163,840 bytes or more,
40 blocks, and stops before it writes anything otherwise.

**The rehearsal.** A test of the emulator suite runs the commands below, over TCP, against
the emulator with a card that has a face in `clocks/`, using the tracked files: each file is
read back with `read <id> <offset> 720` and its SHA-256 compared with the table, the
emulator's show folder holds the same bytes under `<n>/`, `catalog` gives the internal
catalog `ok`, `list in` gives the seven rows with their paths, and in Only with the message
on a turn of an internal message follows the card's face. It is the rehearsal of the
commands, and is reported as such, never as a deployment.

**The board session**, run by the owner or with the owner's leave, with the installation's
board on USB at the port `PORT` (or `--http ADDRESS` in place of `--port PORT` over Wi-Fi),
no other client connected, and the firmware of this seed on the board. `python` is the
checkout's `.venv` Python, run from the repository's root:

```
python -m odrigctl --port PORT status
python -m odrigctl --port PORT brightness 40
python -m odrigctl --port PORT space
python -m odrigctl --port PORT catalog
python -m odrigctl --port PORT list
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
python -m odrigctl --port PORT clocks storage sd
python -m odrigctl --port PORT clocks message on
python -m odrigctl --port PORT clocks only
python -m odrigctl --port PORT status
python -m odrigctl --port PORT clocks on
python -m odrigctl --port PORT status
python -m odrigctl --port PORT clocks MODE
python -m odrigctl --port PORT clocks message MESSAGE
python firmware/fw.py read-show build/seed61-readback --port PORT
python -c "import hashlib,pathlib; [print(hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p) for p in sorted(pathlib.Path('build/seed61-readback').glob('*/v7-*.odrgx'))]"
```

- `status` first: the reply has `clock_storage`, which only this seed's firmware gives, and
  its `brightness`, `clock_mode` and `clock_message` are written down as the owner's. The
  brightness line is sent only when it is above 40; the owner is told the value found.
- `space` must give `free` of 163,840 or more, else the session stops here.
- `list`, and `list in` of every folder it shows, give the ids in use. `ID1` to `ID7` are
  seven ids that no row has, 60,000 or less. A `clocks` row with `"external":false`
  already there answers `folder make internal clocks` with `"made":false`, which is no
  fault; the same holds for `clocks/message`. `MESSAGE_ID` is the id that `folder make
  internal clocks/message` answers.
- Each upload must end with success; an upload refused or not answered stops the session,
  and its file is not counted.
- The `status` after `clocks only` and after `clocks on` is repeated until `file` is one of
  the seven, `clocks/message/v7-...`, with an `animation` of 60,000 or less, after a turn
  whose `file` is a face; in Between a break comes after five turns or five minutes. The
  owner looks at the LEDs.
- `MODE` and `MESSAGE` give back the owner's settings written down at the start (`on` for
  Between, `off`, `only`; `on` or `off`).
- `read-show` restarts the board and copies its storage into `build/seed61-readback`; the
  one-liner prints each file's SHA-256 and size, compared with the table. Its
  `folders.txt` names the folder's number `<n>`.
- The record names the internal paths, the ids, the folder's number, `catalog`'s internal
  state and generation, the hashes read back, the files and ids seen in both modes, and
  every step not done with its reason.

## Older clients, older firmware

- An APK before this seed ignores `clock_storage`. Its Clocks level in Only is the folder
  that `clock_only.folder` names, so on a target whose card has no Clocks folder it lists
  the board's own `clocks` as that level and plays inside it; it never shows the two
  Clocks folders together, and its uploads in Only still need a writable card. The APK of
  this seed is delivered with the firmware (task 5), as seed 74's must be.
- An APK of this seed with an older firmware sees no `clock_storage`: the dropdown is
  disabled and the boundary is the card's alone, which is what such a firmware plays.
- Going back to an older firmware: `clocks.txt` of version 2 is read as before. Version 3,
  written only while `Internal storage` is preferred, is out of form to an older firmware,
  which fails closed into a dark Only with `clocks unreadable` until a mode line is sent;
  before going back, `clocks storage sd` writes version 2 again. The internal clock files
  play there as ordinary animations of their folders.

## Tests

- **Core**, `tests/core`: a new `test_internal_clocks.py` and additions to
  `test_clock_modes.py`:
  - recognition: faces, messages, `clocks/old`, the root, an orphan, another folder, a boot
    with a damaged `folders.txt`, a flat show's replies byte for byte but for
    `clock_storage`;
  - Between: card faces with internal messages, internal faces with card messages, internal
    faces with no card, only messages (no break), the pass-over of the internal Clocks
    subtree by the root's walk, an internal playlist and the rotation, message on and off,
    a complete loop longer than 30 seconds, exhaustion of both bags across storages;
  - Only: both storages' faces and messages, message on and off, internal faces without a
    card, only messages (dark, `no-clocks`), every `clock_only.state` with and without an
    internal Clocks folder, `play` of an internal file, an ignored one and a message while
    messages are off, of an internal Clocks folder and a sub-folder, of an outside internal
    file and folder (`in-use`), restart, a removal, a quarantine, a card pulled out and put
    in, leaving Only;
  - Only and Ignore: an Ignore of an internal face playing automatically ends its turn at
    once, as a card face's does; a manual turn of an internal file goes on through its own
    Ignore and through a fault of another file; an Ignore of the internal Clocks folder
    darkens Only when it held the last faces, and taking it in again starts a clock at once;
  - the LEDs' `off` in Only: an internal message's turn goes on and `status` names it;
  - copies: identical and different bytes, under both preferences, a preferred copy ignored,
    held, quarantined, removed, or on a card pulled out; the same name with another type, in
    another folder, and names that differ only in case; a show of more than 132 items with
    copies; each copy's own saved brightness when it plays;
  - the preference: each refusal in order, a no-op writing nothing, versions 1, 2 and 3 and a
    version 3 without its line, a failed write keeping the file and the choice, a version 3
    read back by `breaks_poll` after an unreadable start, a change during a message's turn,
    `clock_storage` in `status`, and the longest replies of
    `test_the_longest_reply_to_status_fits_1024_bytes` with the member;
  - the tests that hold the exact bytes or the order of the members of `status` take the
    member after `clock_mode`: `test_status.py`, `test_commands.py`, `test_folders.py`,
    `test_clocks.py` and `test_internal_folders.py`, and the reference player of
    `tests/core/support.py` gives it and takes `clocks storage`, writing `clocks.txt` as the
    core does; the example reply of `docs/commands.md` with it;
  - memory: the suites of memory pass unedited.
- **Firmware**, `tests/firmware`: the firmware tool keeps a `clocks.txt` of version 3
  through a show install, as it keeps one of version 1.
- **Emulator**, `tests/emulator`: `clocks storage` over the serial port, TCP and HTTP with
  the same replies, the choice kept across a restart of the emulator; the rehearsal of the
  seven messages above.
- **Command tool**: the new words, and a usage error for another.
- **App**, `tests/app` and the page's scenarios against the emulator: the parsing of
  `clock_storage`; the dropdown's states, confirmation, refusal, lost reply, target change
  and older firmware; Only with an internal Clocks folder alone, with both, the Clocks level
  and Back, play and upload inside the board's Clocks, an outside folder hidden, the root
  not offered; the archive and the batch in Only, uploading into the board's
  `clocks/message` with only that storage offered, and refused at the board's root; a
  target without `clock_storage` keeping the card-only boundary and today's words; the bar
  of the animation playing now.

## Order of the tasks

The core first, with `SD card` the only preference; then the preference's command and file;
then the app; then the rehearsal of the seven messages on the emulator; then the delivery,
which prepares the board session and leaves it open.
