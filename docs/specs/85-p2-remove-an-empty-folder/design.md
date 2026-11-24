# Design

## Boundaries

`folder remove <id>` is one new command of the core, judged in one place and carried out
by the storage the id belongs to: the board's own storage in `core/src/folders.cpp`, the
card in `core/src/catalog.cpp`. The hosts learn nothing new but the text of `remove`: the
test host, the emulator's storage and the firmware's card host remove an empty folder of
the drive when `remove` names one. The command tool and the app send the line. The card's
catalog format, its commit record, the Python library, the converter and the firmware tool
stay as they are; the prune of either storage is unchanged. No field of `Core`, `FileInfo`
or `Upload`, no host function and no block of memory is added.

Seed 74's task 6 moved a card folder with a job of the app, not a stepped job on the board
(the fallback the owner allowed on 2026-11-09). So no condition of a stepped card folder
move enters the refusals.

## The command

`core/src/commands.cpp`, beside `folder make`:

```
folder remove <id>
```

`words.count == 3`, `words.is(1, "remove")`, the id by `number_word(words, 2, 1,
0xFFFFFFFFu, &id)`; any other form of `folder` keeps `bad-argument`. Then `show-invalid`,
then `content_folder_remove(core, id, reply)` in `core/src/content.cpp`, beside
`content_remove`, which sorts the id:

1. an item of the show: `in-use`;
2. `drive_find` gives `'f'`, an animation of a drive: `in-use`;
3. `drive_find` gives `'d'`: `catalog_folder_remove(core, ordinal, reply)`;
4. an id above `kFolderIdMost` (60,000): `busy` while `catalog_drive_loading(core)`, as the
   core cannot place a card's id while it reads the card's catalog, else `unknown-id`;
5. any other id: `internal_folder_remove(core, id, reply)`.

`refuse()` codes stay those of the table of `docs/commands.md`; no code is added.

## The board's own storage

`internal_folder_remove(Core &, uint32_t id, Reply &)` in `folders.cpp`, beside
`internal_folders_prune`, `ODRIG_NOINLINE`:

1. `unsupported` when `!storage_changes(core)`, the host has no `read_at`, or there is no
   chunk buffer: a storage the core cannot change.
2. `busy` while `core.upload.state != kUploadNone` or `catalog_rebuilding(core)`:
   `folders.txt` is written through the chunk buffer, which each may hold.
3. `storage-error` while `core.folders_error`.
4. `unknown-id` when `folder_by_id` finds no line.
5. `in-use` when `holds_files(core, line.number)` (every file of the file table whose
   stored name has that number, those listed at the root for a long path among them), or
   when the line after it in `read_tree`'s order is deeper.
6. The edit: `edit_clear(edit, tree.next)`, `edit.drops = 1u << line.index`; `write_part`
   then `commit_part`. A failure removes `folders.part` and answers `storage-error`, the
   file then as it was.
7. `host.remove("<n>")`, its answer not judged: a folder that stays is listed nowhere and a
   later folder of that number takes it, as after a cut of the prune.
8. `core.internal_folders` one less; `folders_derive(core)`; when `core.current` changed,
   `player_playlist_chosen(core, core.latest)` and `playlist_changed(core)`, as the prune
   does. `folders_derive` gives the root a fresh window and `save_due` when the current
   playlist's line is gone (`root_again`).

`Tree` (72 bytes) and `FolderEdit` (44) are on the stack of the function; `read_tree`,
`write_part` and `find_folder` keep their `FolderScan` in their own frames.

## The card

`catalog_folder_remove(Core &, uint32_t ordinal, Reply &)` in `catalog.cpp`, beside
`catalog_folder_make`, with its frame split as `folder make`'s is:

1. `busy` while an upload is open, `catalog_drive_loading`, `catalog_rebuilding` or
   `core.mapping_test`, as `catalog_folder_make` judges it.
2. `read-only` while `!catalog_drive_writable(core) || !core.indexed`: a USB stick, a
   read-only card and a card without a catalog among them.
3. `drive_folder(core, ordinal, folder)`, else `storage-error`; `in-use` when
   `folder.files != 0 || folder.folders != 0`.
4. Its path, `drive_folder_path`, kept for the removal on the card.
5. `folder_entry_removed(core, folder)`, `ODRIG_NOINLINE`, holds the `IndexChange`: the
   parent found as `folder_chain` finds it (the nearest folder before it one level up);
   `clear_change(index)`; `index.map_changes = true`; `gone_ids[0] = folder.id`,
   `gone_count = 1`; `table.gone_from = folder.ordinal`, `table.gone_count = 1`,
   `table.folders_of = parent.ordinal`; `map.gone_from = folder.ordinal`,
   `map.gone_count = 1`; one edit, the parent's file, `edit_of(parent)` with `child =
   folder.id` and `child_files = kNothing`, which leaves the row out; then
   `commit_index`. The table's writer already lowers every ordinal and end past the gone
   line, the ends of the folders above among them, and the map's writer lowers the ordinals
   past it. The record's `remove index-<id>.txt` of the gone folder removes a file that a
   folder without lines does not have, which `act` takes as done. No page is written and no
   file moves. A failure answers `storage-error`, the index as it was.
6. `remove_drive_folder(core, path)`, `ODRIG_NOINLINE`, gives the host `drive/<path>`; its
   answer is not judged.
7. What follows `folder make external`: `current_again`, whose `tree_find_current` finds
   the current folder again or makes the root current when it is gone (keeping the saved
   path in Clocks-only mode, as today), then `repeats_reload`, `brightness_start` and
   `ignored_start`. No file position changes, so the player keeps its turn.

## The hosts

- **Test host**, `tests/core/host/host.cpp`: `remove_file` of a name of the drive whose
  path is a folder removes it with `rmdir` (`std::filesystem::remove` on Windows) when it is
  empty, 1; 0 when there is none; -1 when it holds anything. The call is a store call, so
  `--cut-at` and `--store-fails-at` reach it.
- **Emulator**, `emulator/host.py`: `FolderHost.remove` of a drive's name whose path is a
  folder uses `os.rmdir`: 1, 0 for `FileNotFoundError`, -1 for any other `OSError`. The
  drive's `path(..., changing=True)` keeps refusing a drive that cannot be written.
- **Firmware**, `firmware/usermod/odrig_drive.cpp`: `removeDriveFile` stats the path; a
  directory is removed with `rmdir` (1), `ENOENT` gives 0, and any other failure gives -1
  without `capacityWriteFailed()`: FAT answers a folder that is not empty with a refusal,
  not a failed write, and the card's capacity stays known. A file is unlinked as today. The
  guard, `StorageCall` and `changing()` stay. The stick's stub stays -1.

## The command tool

`odrigctl/cli.py`: `COMMANDS["folder"]` takes `make internal|external PATH` and `remove
ID`; `folder remove ID` sends `folder remove <ID>` as typed and prints the reply. The usage
text and the epilog name it.

## The app

- `commands.js`: `folderRemove(id)` sends `folder remove <id>` through `carriedOut`.
- `messages.js`: the refusals of `folder remove`, by code, `REMOVINGS`: `in-use` "Only an
  empty folder can be removed: it holds a file or a folder.", `read-only` "The card cannot
  be written now, so the folder cannot be removed.", `unknown-id` "The folder is not on the
  installation any more. The list is read again.", `busy` and `storage-error` keep the
  general texts, `unsupported` "This installation cannot remove folders in that storage."
- `screens/explorer.js` owns the action, as it owns `New folder`: `removeActions(folder)`
  gives the menu's items for a folder row, which `show.js`'s `fillMenu` appends to the
  folder's items through a new folder hook of `extend` (`folderMenu`). Its rules:
  - a folder of the board's storage (`external` not true), or of the card while
    `cardWritable(state)`: `{label: "Remove folder", danger: true}`, disabled unless the
    target answers, no change of the list runs (`client.contentBusy()`, the explorer's own
    run, the selection's lock) and the row's `files` is 0; with files, the note "Only an
    empty folder can be removed.";
  - a folder of a card the board may not write: the note "External storage is read-only:
    this folder cannot be removed.".
- Pressing it runs `askRemove(folder)`: `client.operation("folder", () =>
  commands.list(0, folder.id))`; a level with a row says "The folder <label> is not empty:
  only an empty folder can be removed." and sends nothing; a refusal or failure of that list
  is said and nothing is sent. Else the dialog `#folder-remove-dialog` (an
  `explorer-dialog`) shows "Remove the empty folder <label>? This cannot be undone." with
  `Remove` and `Cancel`; Escape closes it; nothing is sent until `Remove`.
- `Remove`: `client.operation("folder", () => commands.folderRemove(id))`, then
  `client.refreshContent()` and "Removed the folder <label>." A `Refusal` says
  `The folder <label> was not removed. <text>`; `unknown-command` says "This installation's
  firmware cannot remove folders. Install the newer firmware." A `Failure` (no reply) lists
  the parent level again (`commands.list` of the level shown, all its pages) and says
  "No confirmed reply. The folder <label> was removed." or "No confirmed reply. The folder
  <label> is still there; press Remove folder again to remove it." by whether a row of that
  id and path is there. The line is never sent again by the app.
- The dialog and the run hold the target's version: a change of target closes the question
  and drops the answer.
- `<label>` is `moves.label(storage, path)`, "Internal /shows" or "External /shows".
- `Delete selected` is unchanged.

## Documents

`docs/commands.md`: the row `folder remove <id>` in the table of commands, the folder
sections of both storages without "No command removes a folder", the refusals in their
order, and the error codes' table where `in-use` and `busy` name the command.
`docs/core.md`: the host's `remove` of a drive's folder, and "Internal folders".
`docs/catalog.md`: a folder leaves the index also by `folder remove`, and the row of the
change in its table of what each change writes. `docs/emulator.md` and `docs/firmware.md`
for the hosts and the command tool. `docs/android-app.md`: `Remove folder`, and a step of
"The check on a phone". The change log of `docs/decisions.md`, with the owner's approval of
2026-11-09, and the drifts at the end of `docs/drifts.md`.

## Tests

Each seen failing first, its failure in the commit message.

- **Core** (`tests/core/test_folder_remove.py`, new): every refusal in the order of the
  requirements; an empty folder of the board's storage made and removed, its line and its
  numbered folder gone, its id given to the next new folder, `list` and `status`; a folder
  holding a file, one holding only a file whose path passes 100 bytes, one with a
  sub-folder; a nested folder removed while its parent stays; the current playlist removed,
  the root current and saved; a cut at each store call (the part's open, write, close, its
  rename, the folder's removal); a card folder removed while folders after it keep their
  ids and their `list in` replies; a current card playlist after it found again, and the
  removed card folder current; a Clocks folder of the card; `read-only`, a USB stick, a
  test that shows and a catalog being read; a cut during the commit, replayed at the next
  mount; a cut after the commit, the folder on the card left and made again by `folder make
  external`. The command lists of `tests/core/test_docs.py` and
  `tests/emulator/test_tool.py`.
- **Emulator**: the line over HTTP and over TCP, the drive's folder removed on the disk.
- **Firmware**: `removeDriveFile`'s text: `rmdir` for a directory under the guard,
  `ENOENT` 0, no `capacityWriteFailed()` for a directory.
- **Command tool**: `folder remove ID` sent as typed; its usage errors.
- **App**: the menu's states and notes on both storages and on a read-only card; the `list
  in` check; the dialog, `Cancel` and Escape; success; a refusal; `unknown-command`; a lost
  reply, both outcomes; in Chrome against the emulator. `tests/app/test_scope.py` takes the
  line `folder remove <n>`.
