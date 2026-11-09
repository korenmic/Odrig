# Design

## Part A

### The host makes a folder

`odrig_host` gets one optional function at its end:

```c
/* Optional: makes the folder of the drive's folder odrig with this name, `drive/<path>`,
   whose parent is there. Returns 1 when the folder is there afterwards, made now or
   before, -1 on failure and when a file has that name. */
int (*make_folder)(void *ctx, const char *name);
```

A host without it answers `unsupported` to `folder make`. The emulator's `FolderHost`
makes the folder under its drive folder; the firmware's SD host calls `mkdir` on the
card under its guard, after closing the files `changing()` closes, and treats `EEXIST`
of a directory as success. The stick host has none.

### The index with empty folders

The table keeps its form. A folder line may say `0` own files and `0` sub-folders: an
empty folder, without a file `index-<id>.txt`, its CRC `00000000`. Its `first` is the
walk's position after the folders before it, `end` is its ordinal plus one. The map holds
its line `<id> d <ordinal> 0`.

`catalog_make_folder_external(core, path, &id)`:

1. Finds the parent's ordinal from its path (the root for a path of one name) and the
   ordinal the new folder takes: after the parent's line and the subtrees of its
   sub-folders whose names are before the new name by their bytes, the table's order.
2. Takes the lowest free id of the map.
3. Commits one change of the card's catalog without a page (mask `0000`): the parent's
   folder file with the line `<id> d 0 <path>` inserted among its sub-folder lines at the
   new folder's place; the table with the new line, the ordinals and ends after it one
   more, the `end` of every ancestor one more, the parent's sub-folders one more; the map
   with the new line in id order and every ordinal at or after the new one one more.
   The record: `move index-<parent>.new index-<parent>.txt`, the table, the map.
4. Then the cursor reads the new index, and the current playlist, the ignored folders and
   the saved settings find their positions again, as after an upload.

The edits are new members of `IndexChange` (`insert`: the ordinal, the id, the depth, the
first position and the parent's line), and the writers of the table, the map and a
folder's file read them; every other change leaves them empty.

`folder make` is handled in `commands.cpp` beside `upload begin external`: the same path
decoding and naming check, then `busy`/`read-only`/`unsupported` as the upload has them,
then the host's `make_folder`, then the catalog. A path the index has as a folder answers
`made:false` before any call.

The Python library's reader (`odrig/catalog.py`) accepts a table line of an empty folder
whose own and sub-folder counts are 0, with no folder file; its writers and the PC tool's
`import` stay as they are, so that a rebuild drops empty folders, as `catalog.md` then
says.

### `saved <id>`

`commands.cpp` resolves the id as `repeat <id> default` does, then answers from
`brightness_saved(position)`, `repeats_of(position)` and whether the position is the
show's start item. `busy` under the same condition as `repeat <id> default`.

### The app

- `screens/selection.js` selects files of both storages; its bar gets `Move to…`, and the
  list's level bar gets `New folder` and `New playlist folder` at a writable level of the
  card. `screens/explorer.js` holds the new folder dialog, the destination chooser and the
  preview.
- `moves.js` is the job: a pure state machine over the client's requests, with the
  journal `odrig-moves-<target>` in `localStorage`, one record per file:
  `{source: {storage, id, path, bytes, crc}, destination: {storage, folder, name},
  settings: {ignored, brightness, repeat}, stage}`. The stages are `read`, `sent`,
  `carried`, `cleared`, `removed`. A record is written before each stage that changes the
  target.
- Reconciliation at the link's return: the destination's level is listed; a file of the
  recorded name and size there goes on from `sent`; without it, the record ends as not
  moved. The source is removed only when a fresh listing of its level shows its id with
  the recorded path and size.
- The CRC-32 of the source is checked against the catalog's content key when the row has
  one, and the destination's `upload end` checks the same CRC-32 on the board.

## Part B, at no core memory

The owner's constraint: part B costs the core no memory. Every figure of the memory table
of `docs/core.md` stays as it is, on this branch and merged with the seeds not yet in
`master`, and no host function is added. Clocks and messages stay those of the card;
seed 61 builds internal clocks later on this model, in room that part B leaves free.

### The model

- **Stored names.** Every file of the board's storage has one short name that stays while
  the file stays in its folder, its stored name: `x.odrg` at the root, `<n>/x.odrg` in the
  internal folder `n`, 1 to 255 without a leading zero. `n` names a real LittleFS
  directory, `/odrig/<n>/`. The base name keeps today's rule, 32 characters at most, so a
  stored name has 36 at most. `FileInfo.name`, every host call, `show.json`'s `file`, the
  internal catalog's keys, `pending.txt` and the `f` keys of `repeats.txt` and
  `brightness.txt` hold the stored name.
- **Logical paths.** What the operator sees, `shows/night/stars.odrg`, is a folder's path
  and the base name, 100 bytes at most. Folder paths are kept in one file only,
  `folders.txt`, in tree order. The core reads it through `read_at` into a buffer on the
  stack when it needs it, and never keeps it in the arena.
- **Why the stored name.** `FileSource` keeps only a pointer to the name and reads through
  it at each refill, across refreshes, and so do the check after the start and the internal
  rebuild. A path built on the stack is gone by the next refresh, and the arena has no free
  101 bytes to hold one. Paths never reach LittleFS either: a folder called `drive` meets no
  routing, the case rules of FAT and the name limits of LittleFS do not apply, and a
  folder's path changes by rewriting one file.
- **`FileInfo` stays 48 bytes.** Today: `name[33]`, `fault`, `checked`, `type`, `bytes`
  (u32) at 36, `total_ms` (u64) at 40. In part B: `name[37]` at 0, `fault` at 37, byte 38
  `checked:2`, `type:2`, `held:1` and three spare bits, byte 39 `rank:6` and two spare
  bits, `bytes` at 40, `total_ms` (u32) at 44.
  - `total_ms` saturates at 4,294,967,295 ms, as the card's lengths already do: the
    function `drive_length` becomes `kept_length` and is applied wherever a length is
    stored. A rebuild writes the checker's exact `check_total_ms` into the catalog, so the
    catalogs on the storage stay exact and agree with the Python library.
  - Every store of `type` is normalised, `kTypeFrames` for a type that is not drawn, so the
    two bits never hold an unknown header byte; `list` already says `frames` for one.
  - `held`: the file's folder or one of its ancestors is ignored. `plays()` adds `!held`,
    as `drive_automatic` takes the card's inherited Ignore.
  - `rank`: 0 at the root, else 1 + the index of the folder's line in `folders.txt`. A file
    with a prefix whose folder has no line has rank 0 and is an orphan: it is listed and
    played at the root under its stored name.
  - The three spare bits of byte 38 are kept for seed 61's clock class and duplicate mark.
- **`Upload` stays 72 bytes.** `name` holds the base name, and `folder` holds `n` for an
  internal upload; today it is 0 there and read only for a card's upload.
- **`Core` gains one byte, inside its end padding**: `internal_folders:6`, the lines of
  `folders.txt`, 0 to 32, where 0 skips every scan so that a flat show pays nothing; and
  `folders_error:1`, `folders.txt` could not be read in this boot. Measured on the test
  host, `sizeof(Core)` is 3,720 with its data ending at 3,714 on this branch, and 3,792
  ending at 3,786 on the branch that fuses the seeds not yet merged: 6 bytes of end padding
  on both. A count by hand of the fused branch finds the same 6 on the board, and task 7
  counts this branch's there before it adds the byte. Seed 61 takes 2 bytes more and the
  spare bit of an existing bit-field byte, which leaves 3. Where a branch's padding cannot
  hold the new bytes, whole-byte flags of `Core` that hold one bit are packed into
  bit-fields first, so that `sizeof(Core)` grows on no branch.
- **The current playlist** reuses what is there: `core.current = kInternalLevel | n`, with
  `kInternalLevel` 0x40000000; `current_folder` holds `n`, the folder's id, its rank as
  `first`, the end of its subtree's ranks as `end`, and its depth; `playlist_path` holds
  `:<path>`. Card code that reads `current` as a card's ordinal goes through
  `playlist_is_folder(core)` and is guarded by `!(current & kInternalLevel)`.
- `static_assert`s hold `sizeof(FileInfo) == 48` and `sizeof(Upload) == 72`, and
  `tests/core/test_docs.py`, `test_memory.py` and `test_drive.py` pass unedited.

### On the storage

`folders.txt`, written through `folders.part`:

```
odrig-folders 1 <next>
<n> <id> <ignored> <path>        one line for each folder, in tree order
```

```
odrig-folders 1 4
2 41 0 shows
1 39 0 shows/night
3 42 1 shows/old
```

- `n` is 1 to 255, unique, without a leading zero; `id` is 1 to 60,000, unique and no
  item's; `ignored` is 0 or 1; `path` is one to three names under the card's rule, 93
  bytes at most, the last not ending in `.odrg` or `.odrgx`; `next` is 1 to 255.
- Tree order: depth first, siblings by the bytes of their names; a line's parent is the
  nearest earlier line one level up. Siblings are unique without ASCII case, so that a
  move to the card cannot collide. A line has 106 bytes at most, the header 20, the file
  3,412.
- The core reads it with `FolderScan`, always from offset 0, each read where the last
  ended, so the host contract and the test host's check of reads are unchanged.
- A line out of form or out of order, an orphan line, or a repeated `n` or id makes the
  file damaged: `folders_error` is set, `folders unreadable` is logged, the boot has no
  folders and the file is left for the PC tool. Files with a prefix still play and are
  listed at the root as orphans; `folder make internal`, a folder's Ignore and an upload
  with a folder path answer `storage-error`.
- It is written by streaming the old file through `FolderScan` into a `Writer` over the
  chunk with the change applied, then `write_close` and `rename(folders.part,
  folders.txt)`. A writer answers `busy` while an upload receives or a rebuild runs, both
  of which hold the chunk. `storage_clear_parts` removes a stray `folders.part`.
- No `folders.txt` is a flat show.

The other files:

| File | In part B |
|---|---|
| `/odrig/<n>/` | A LittleFS directory, made by `make_folder("<n>")` before its line is written, and again, at no cost, at each `upload begin` into it; removed by `remove("<n>")` after its line goes. A cut leaves at worst an empty directory without a line, which is harmless and used again. |
| `show.json` | `file` holds stored names. The writer is unchanged. |
| `pending.txt` | Stored names; its readers take 36 characters and `is_stored_name`; `add_line` gets the bound `length + size + 1 <= kPendingSize`: 32 x 37 = 1,184. |
| The internal catalog | Keys are stored names; `catalog_name_allowed` already takes a folder of digits. `catalog page internal` shows stored names, and the app maps them through `stored`. |
| `repeats.txt`, `brightness.txt` | `f <stored name>`, read with `is_stored_name`. |
| `playlist.txt` | Still version 1. An internal playlist's line is `:<folder path>`, 95 bytes at most. The card's rule has no `:`, so older firmware finds no such card folder and falls back to the root. |

### Ids, numbers and folders

- A folder's id is the lowest id that no item and no internal folder has: with 132 items
  and 32 folders at most it is 165 at most, so a bitset of 21 bytes on the stack finds it.
  The card's ids begin at 60,001.
- Folder numbers go round from `next`, 1 to 255 and back to 1, skipping a number that a
  line or any stored name of the file table uses, so that a stale `f <n>/…` key rarely
  meets a new file and a stored name whose line was lost is never taken over.
- `folders_start` runs after `storage_settle_pending` and before the reset of the items: it
  removes a stray part, validates the file, gives a new id to a folder whose id an item or
  another folder also has, rewriting the file, and calls `folders_derive`.
- `folders_derive` is one scan of `folders.txt`: by depth it carries each line's held
  state and the subtree end of the current internal playlist, and writes `held` and `rank`
  of the files whose prefix is that line's `n`, at most 32 x 132 compares of integers in
  memory. It runs at the start, after `folder make internal`, a folder's Ignore, an install
  or a removal of a file in a folder, a prune, and the choice of an internal playlist.
- A folder emptied of its last file, with no sub-folder, is pruned as on the card
  (requirement 1.7): its line goes, its empty ancestors after it, then `remove("<n>")`. A
  folder made by `folder make` stays while it was never filled. No command removes a
  folder.
- A folder is a playlist (seed 74, item 5). The walk key is `rank << 17 | order_key`; a
  flat show's ranks are all 0 and its order is unchanged. The root walk plays the root's
  items in their saved order, then each internal folder depth first, its own files before
  its sub-folders, then the card. The range of a current internal playlist is
  `[first, end)` of ranks; the daily rotation goes root, the internal folders by rank, the
  card's folders, root. `tree_find_current` resolves a `:` path with the folder's path, and
  falls back to the root as today when it is gone.

### Limits

| Limit | Value |
|---|---|
| Internal folders | 32, numbers 1 to 255 |
| Depth | 3 folders |
| A folder's path | 93 bytes |
| A file's logical path | 100 bytes, checked at `upload begin` |
| A base name | today's rule, 32 characters |
| A stored name | 36 characters |
| A folder's id | 1 to 60,000; 165 at most in practice |
| Files | 132, unchanged |
| `folders.txt` | 3,412 bytes |
| `read`'s count | 1 to 720 bytes |
| `remove many` | 32 ids, unchanged |

### Commands and replies

Under the owner's approval of 2026-11-06.

| Form | Reply and refusals |
|---|---|
| `read <id> <offset> <count>` | `{"ok":true,"bytes":<size>,"data":"<base64url>"}`. The count is 1 to 720, `kReadCountMost`; the form of three words keeps 600, `kReadMost`. The refusals are those of the offset form, so `read 1 0 0` stays `bad-argument`. A quarantined file stays `unavailable`; an internal folder's id is `in-use`. |
| `folder make internal <path>` | `{"ok":true,"id":<id>,"made":true}`, or `made:false` for a folder that is there by its bytes, which writes nothing. Refusals in this order: `bad-argument`; `show-invalid`; `unsupported` for a storage that cannot change or a `make_folder` missing or answering 0; `busy` while an upload is open or a rebuild runs; `storage-error` while `folders_error`; `in-use` for a sibling equal without case, or a file of the show at that path; `unknown-id` for a missing parent; `no-space` at 32 folders, without a free number or id, or with less than 8,192 + 106 bytes free; `storage-error` when `make_folder` or the write fails. |
| `upload begin <id> <path> <bytes> [crc]` | The form is unchanged. For the board's storage `<path>` is a base name, as today, or `<folder path>/<base>`, decoded once from URI escapes, and old clients are unaffected. A missing folder is `unknown-id`, an internal folder's id `in-use`, a path over 100 bytes `bad-argument`. |
| `list [<from>]`, `list in <id> [<from>]` | The rows below. |
| `order get in <id>`, `order move …` | Unchanged forms, for each internal level by `level_of`. |
| `play <internal folder id>` | `{"ok":true}`: the folder's playlist becomes current, as a card folder's does; `unsupported` without the saved order's block. |
| `ignore <internal folder id> 0\|1` | `{"ok":true}`: the folder's `ignored` in `folders.txt`; its files and its subtree's are `held`. |
| `remove`, `saved`, `repeat`, `brightness` of an internal folder's id | `in-use`, as for a card folder's id. |
| `move external <id> <path>` | Task 6, below. |
| `status` | As today. `file` and `checking` give the logical path of a file in a folder; `playing` and `playlist` give an internal playlist's id and path. `fault` keeps its cut at 32 characters, since a longer `FaultContext` would cost 8 bytes. |

`list` at the root: the root's items in position order (cycles, files without a prefix and
orphans, byte for byte as today), then the internal folders of depth 1 in tree order, then
the card's sub-folders, then the card's root files. At an internal level: its sub-folders
in tree order, then its own files in position order, as at a card's level.

- A folder's row: `{"id":<id>,"playlist":"<path>","external":false,"files":<its own
  animations>,"ignored":<its own>,"inherited_ignored":<an ancestor's>}`.
- A file's row in a folder: today's internal row with `"file":"<logical path>"`, and
  `"stored":"<n>/<base>"` and `"inherited_ignored":<held and not its own>`. Rows at the
  root gain nothing.
- A reply costs two scans at most, one to count `total` and one to write the rows, in
  `list_internal_level` with one `char path[101]`. `listed_size` counts the longer rows.

### The ceiling of `read`

The reply is `{"ok":true,"bytes":` (19 bytes), the size (10 digits at most), `,"data":"`
(9), the data, `"}` (2) and the newline (1): 41 bytes around the data. A reply holds 1,024
bytes, which leaves 983 base64url characters, 245 groups of four and three more: 735 + 2 =
737 bytes. At 720 the reply is 1,001 bytes, 23 to spare for a later member. `Reply::text`
does not check its bound, so the limit is held by this count and a test with a size of 10
digits. Requirement 6.1's 1,536 was beyond any reply.

### Where the changes go

- **Core.** A new `folders.h`/`folders.cpp`, every function `ODRIG_NOINLINE` on the stack
  only: `FolderScan` (`piece[128]`, `line[112]`, offsets, a length and FNV hash per depth;
  about 270 bytes), the lookups by number, id, path and rank, `stored_folder`,
  `stored_name`, `logical_path`, `folders_start`, `folders_derive`,
  `internal_folder_make`, `internal_folder_ignore`, `internal_folders_prune`,
  `internal_choose`, `internal_next_after` and `internal_marks`. `is_stored_name` beside
  `is_file_name` in `show.h`; `read_item` takes `file[kStoredNameRoom]`. The clamps and
  the type's normalisation in `core.cpp`, `catalog.cpp`, `content.cpp` and `player.cpp`.
  `commands.cpp`: `level_words`, `upload`, `read`, `folder make`, `status`, `checking_of`
  made `NOINLINE`, `play`, `ignore`, `remove` and `saved`. `content.cpp`: `content_read`
  with a count, `content_list`, `listed_size`, `set_file`, `content_ignore`.
  `storage.cpp`: name buffers of 37, `add_line`'s bound, the stored name through
  `storage_install_upload`, the prune after a removal, `folders.part`. `upload.cpp`:
  `upload_begin` takes the stored name, refuses a folder's id, makes the folder, and
  `upload_begin_known` compares the folder too. `player.cpp`, `order.cpp`,
  `playlist.cpp`: the walk key, the rank range, `plays()`, the rotation,
  `tree_find_current`, `level_of`, and `playlist_touch` saving while folders exist.
- **The host interface**, its text only: a name may begin with `<n>/`; `remove` and
  `make_folder` also take `<n>`; `make_folder` may answer 0, "this storage cannot make
  folders", which the core answers `unsupported`, so that the stick host keeps answering
  `unsupported` to `folder make external`.
- **Firmware.** `odrig_files.cpp`: `LONGEST_STORED` 36, `writtenName` and `secondName`
  of 37, paths sized by it, `isName` with the prefix, `makeFolder("<n>")` as `mkdir` of
  `/odrig/<n>`, an existing one a success, and `rmdir` in `removeFile("<n>")`, each
  counting 2 blocks; the board's storage is changed in this file only, as now.
  `odrig_drive.cpp`: `FILES_NAME_ROOM` 37, and `make_folder` sends a card's path to the
  card and a number to the board's storage. Where the firmware judges a storage fresh by
  the names it holds, a numbered directory makes it not fresh. On the board once:
  `LFS_NAME_MAX` covers a 32-character name in `/odrig/255/`.
- **Emulator and test host.** The name rule with `<n>/` as a sub-directory, `make_folder`
  and `remove` of `<n>`, `space()` one level down with 8,192 bytes for each folder. The
  test host keeps a set of folders, refuses a rename into a folder not made, and counts
  its store calls for the tests of a cut.
- **Tools.** `odrigctl`: `read ID OFFSET [COUNT]`, `folder make {internal|external}
  PATH`, `move external ID PATH`, and an upload to an internal path. The Python library's
  `odrig/show.py` and the converter's `lib/show.js` take the stored-name rule,
  `(?:(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-5])/)?[a-z0-9._-]{1,32}`, in parity.
  `firmware/fwtool/storage.py` keeps `folders.txt`, accepts the numbered folders it names,
  makes `/odrig/<n>` before writing into it, and refuses an install that would remove
  folder files with `folders-present` and the files, unless `--replace-folders` is given.
- **The app.** `commands.js` accepts playlist rows with `external:false` and the `stored`
  member, which today's APK refuses as `bad-reply`. `read(id, offset, count)` probes
  `read <id> 0 1` once for each target, falls back to 600 bytes on `bad-argument`, and
  else reads 720 bytes at a time. `client.keyOf` looks up `stored`, else `file`, and a new
  item id avoids the folders' ids. The explorer lists internal levels with `list in`,
  offers `New folder` and `New playlist folder` there, and moves into internal folders by
  an upload with a path; a move inside the board's storage uploads under the same id. A
  card move uses `move external` and falls back to part A's job on `unknown-command`.
  Folder moves between the storages make the destination's folders from the top, then run
  file jobs, and the sources prune themselves. `selection.js` lets folders and a
  read-only card be selected for a download.
- **Downloads and backups** (task 5). `zip-writer.js` writes stored entries with
  general-purpose bit 3 and data descriptors, the CRC-32 streamed per piece, one file in
  flight, directory entries for empty selected folders, and no zip64: above 4 GiB or 65,535
  entries it refuses. `odrig-backup.json`, version 1, goes last: `sourceStorage`, `base`,
  and for each file `path`, `stored` where it has one, `size`, `crc32`, `settings` from
  `saved`, `fault` and `outcome`; `partial:true` when any file failed. Each source is
  checked before and after its file by its row's id, path and size and the catalog's key.
  The browser saves through a `Blob`; the APK through a new native plugin beside
  `TargetPlugin.java`, `begin`/`append(base64)`/`finish`, which writes a file in the cache
  and shares or saves it through the Storage Access Framework, by the `FileProvider` and
  its `res/xml/file_paths.xml` that the APK has.

On the refresh path a `FolderScan` frame comes only at the daily rotation, at
`tree_find_current` with an internal path, and in commands; nothing scans at each frame.
Every new frame stays under the 512 bytes that GCC and Clang check; `checking_of` and
`list_internal_level` hold a `path[101]`, the internal branch of `upload` a `path[101]`
and a `stored[37]`.

### Task 6: `move external <id> <path>`

`<path>` is the destination folder, `/` for the root. The reply is
`{"ok":true,"id":<id>,"moved":true}` for a file, `moved:false` for one already there, so a
resent line changes nothing, and `{"ok":true,"id":<id>,"moving":true}` for a folder.

- **A file** moves in one commit of the card's catalog. A record line holds 162 characters
  (`kCatalogLineRoom`, also the arena's `OrderReader.line`), so the file goes through the
  card's `upload.part`: `move <old> upload.part`, then `move upload.part <new>`, each line
  117 bytes at most and replayed by `rename_there`. Its page entry moves to the page of the
  new path, its fields taken from the old line. The source folder's file drops the row and
  the destination's adds it last, with its id; counts, `first` positions and the map follow,
  and the source prunes as a removal does. `IndexChange` gains `more` and `more_count`, two
  extra edits held in the frame of `NOINLINE catalog_move_file_external`. The player
  releases the file's stream before the commit; then `current_again`,
  `player_drive_moved`, `repeats_reload`, `brightness_start` and `ignored_start`.
- **A folder** moves as a stepped job with one commit at its end, every id kept. It uses
  the rebuild's fields of `Core` and `DriveIndex`, since a move never runs beside a
  rebuild: `rebuild_ordinal` and `rebuild_end` hold the source and the destination
  parent. Each step derives the old and new prefixes again from the old index into the
  stack and writes a bounded number of lines, as a rebuild does. The commit's renames are
  done in steps; a cut is finished at the next mount from the record. Card-changing
  commands answer `busy` meanwhile; the end shows in `catalog`'s generation and in `list`.
  A folder into itself or below itself, or a subtree that would pass 100 bytes or 3
  levels, is `bad-argument`. `playlist_path` follows a current playlist in the subtree.
- **Saved settings** keyed by path, `x <path>` or `d <path>`, are renamed after the commit
  from `moving.txt` (`odrig-moving 1`, the generation, the old and the new path; 225 bytes
  at most; written through a part before the commit): each settings file is streamed with
  the prefix replaced, then the journal is removed. At a mount the job is finished when the
  generation after it shows the new path, else discarded.
- On the board the card's host renames files only, so a folder moves file by file with
  `make_folder`, and emptied card directories stay.
- **The order in the destination.** A moved file goes last among its files. A moved
  folder takes its place among its sub-folders by the bytes of its name, the order that
  `docs/catalog.md` records for the card's index, so the sub-folders stay in the order a
  rebuild gives them; the catalog's format, the converter and the Python library are
  unchanged. These are the owner's answers of 2026-11-09.
- **The folder's move is built in two steps.** File moves come first, as 6a; the stepped
  folder job on the board follows, as 6b. If 6b proves too large to build safely, the
  owner allowed on 2026-11-09 a job of the app instead: it makes the destination folder
  with `folder make external`, then moves the files one at a time with `move external`,
  each keeping its id and its saved settings, and records each step in its journal as
  the move job of task 3 does. The folder gets a new id, the move is not one commit, and a
  move cut short is finished at the next connection.

### Flat shows, the old APK and going back

- A flat show is unchanged: without `folders.txt`, `internal_folders` is 0, nothing scans,
  no name has a prefix and every rank is 0, so `list`, `status`, `show.json`,
  `pending.txt`, the catalogs, the order and the ids are byte for byte today's, which golden
  replies check. In memory, a frames file longer than 49.7 days keeps a saturated length;
  its catalog line stays exact.
- The first `folder make internal` writes `folders.txt`; the root's items keep their place
  and ids.
- An APK older than part B refuses a `list` that has an internal folder, so the new APK
  ships with or before the firmware that makes internal folders.
- Going back to older firmware: `folders.txt`, empty numbered directories and a `:` path in
  `playlist.txt` are harmless, and the root is played. But once an item names `<n>/…`,
  older firmware finds `show.json` invalid and the board stays dark; before going back,
  the files of folders are moved to the root or to the card. `f <n>/…` lines of
  `repeats.txt` and `brightness.txt` may be read as out of form.

### Tests

- Core: the memory suites unedited; `static_assert`s; a flat show's replies byte for byte;
  the read count at 0, 1, 720 and 721, an offset at the size, and a reply with a size of
  10 digits; an entry of 5,000,000,000 ms listed and played saturated and written exact;
  a quarantined type 6 listed `frames`; for internal folders every refusal in order,
  `made:false`, case, depth 4, a 94-byte path, the 33rd folder, uploads by path, `list`
  and `list in` with paging at 1,024 bytes, `status`, Ignore and its inheritance, `play`,
  the walk and the rotation, pruning and its `rmdir`, the round of numbers, the repair of
  an id at the start, a damaged `folders.txt`, and a cut at every store call of making,
  installing, removing and pruning; for `move external` every refusal, every record action
  cut and replayed, the journal finished and discarded, ids kept, files last, a folder
  among the sub-folders by its name.
- Emulator, firmware host, fwtool, Python library and converter, `odrigctl`: the name
  rule, the folders, the guard and the new forms. App: rows, `keyOf`, the read probe, a ZIP
  written and read back by a reader of the test, a partial backup, a source changed during
  a read, `New folder` inside the board's storage, moves; the Chrome tests against the
  emulator.
- Task 8: both images and the signed APK from the pushed head, the AVD check of the native
  plugin, `LFS_NAME_MAX` and the cost of a directory on the board, and the owner's check of
  `Download` and `Download selected` on the phone.

### Order of the tasks

Task 5, then 7, then 6, then 8: the moves of folders between the storages in task 6 need
task 7's internal folders. Task 6 is done as file moves first, then the folder job.
