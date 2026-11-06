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

## Part B

- **Internal folders**: names of the board's storage may hold `/`, under the card's path
  rule; LittleFS has real directories; the host's `write_open`, `rename` and `remove`
  take such names, `make_folder` takes `<path>`. `show.json`'s `file` may be a path; the
  internal catalog's names are already up to 100 bytes. `list` gives the root's internal
  folders as playlists with ids from the show's free ids, and `list in` their levels.
  Clocks stay on the card.
- **`move external <id> <path>`**: one catalog commit whose actions are `move <from> <to>`
  for each file of the moved subtree and whose index change removes the rows at the
  source and adds them last at the destination; ids are kept; the saved settings of the
  moved paths are renamed in the same order of writing as an upload's settings.
- **Downloads**: `read` with a count; the app writes a ZIP of stored entries with
  CRC-32s, streamed file by file, and saves it through the browser's download or the
  APK's share sheet.
