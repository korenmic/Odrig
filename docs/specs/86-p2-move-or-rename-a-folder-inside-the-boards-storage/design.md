# Design

## Boundaries

A folder of the board's own storage is a numbered folder whose path lives only in its line
of `folders.txt`, so a move or a rename is one rewrite of that file. `move internal` is
parsed in `core/src/commands.cpp` and carried out by `internal_folder_move` in
`core/src/folders.cpp`. Nothing else of the storage is touched: no file is copied, renamed
or checked again, and the stored names `<n>/<name>` stay. The host contract, the format of
`folders.txt`, the card's catalog, `show.json`, the Python library, the firmware tool and the
sources of the emulator and of the firmware are unchanged. The command tool and the app
send the line. No field of `Core`, `FileInfo` or `Upload`, no host function and no block of
memory is added.

## The command

`core/src/commands.cpp`, in the `move` branch beside `move external`:

```
move internal <folder id> <path>
```

`words.count == 4`, `words.is(1, "internal")`, the id by `number_word(words, 2, 1,
0xFFFFFFFFu, &id)`, the path by `folder_path(words.text[3], words.size[3], path)`, which
decodes it once and holds it to the rule of `folder make` (93 bytes at most for a folder:
`length + 7 <= kCatalogNameMost`). Any other form is `bad-argument`; then `show-invalid`;
then `internal_folder_move(core, id, path, reply)`.

## The move

`internal_folder_move(Core &, uint32_t id, const char *path, Reply &)` in `folders.cpp`,
`ODRIG_NOINLINE`:

1. `unsupported` when `!storage_changes(core)`, the host has no `read_at`, or there is no
   chunk buffer.
2. `busy` while an upload is open or `catalog_rebuilding(core)`.
3. `storage-error` while `core.folders_error`.
4. The id: an item of the show, `in-use`; `drive_find` not 0 (an animation or a folder of a
   drive), `in-use`; `folder_by_id` finds no line, `unknown-id`. `folder_by_id` gives the
   folder's line and its old path, into room for `kFolderPathMost + 1`.
5. `folder_path_depth(path)`: 0 is `bad-argument`.
6. The plan, `plan_move`, `ODRIG_NOINLINE`, one reading of the file, as `MovePlan`:
   - `first` and `last`: the folder's line's index and the last index of its subtree, the
     lines after it of a greater depth, which stand together in the tree's order;
   - `inside`: the new path is the old one, `/` and more: `bad-argument`;
   - each line of the subtree gets its new path, the new path followed by its old path past
     the old one's length, checked for 93 bytes and for a depth of 3 at most (the new
     path's depth plus the line's depth below the folder); and each file of the file table
     whose stored name has that line's number and that is listed in its folder now
     (`path_fits` with the old path's length) is checked for 100 bytes with the new length:
     either fails `bad-argument`;
   - `same`: the new path is the old one in bytes: `moved:false`, nothing written;
   - `taken`: a line outside the subtree whose path has the new parent and whose last name
     is the new last name in bytes or in any case: `in-use`; the folder's own line is never
     its own twin;
   - `parent`: the new parent is the root or has a line: else `unknown-id`;
   - `before`: the index before which the subtree goes, found as `write_part` places a new
     line: once the new parent's line is met (at once for the root), the first line outside
     the subtree that is not deeper than the new folder and either is shallower or is a
     sibling whose last name comes after the new last name by its bytes; `kNoLine` for the
     file's end;
   - `next`: the header's next number, kept.
   The refusals of the plan are given in the order of the requirements: `bad-argument`
   (inside, then the limits), `moved:false`, `in-use`, `unknown-id`.
7. The writing, `write_moved`, `ODRIG_NOINLINE`: `folders.part` opened, the header with the
   same next number, then three readings of `folders.txt`, each from offset 0 to where it
   is needed, as the host contract wants a file read, each through its own
   `copy_lines` call so that one `FolderScan` is on the stack at a time:
   - the lines before `before` that are not in the subtree;
   - the subtree, each line with its number, id and Ignore and its new path;
   - the lines from `before` on that are not in the subtree.
   A file that cannot be read whole or written fails; `folders.part` is removed and the
   reply is `storage-error`, the file as it was.
8. `commit_part`, else `storage-error`.
9. What follows: `folders_derive(core)` gives every file its folder's new rank and Ignore
   and finds the current internal playlist's range again; `player_internal_inclusion_changed
   (core)` checks the turn in progress as after `ignore` of a folder. When the current
   playlist is internal and its number is one of the subtree's, `playlist_path` becomes `:`
   and its new path (read again with `folder_by_number`) and `save_due` is set, so
   `playlist.txt` is written at the next refresh. A cut before that leaves the old path,
   which the next start does not find and so falls back to the root.
10. `{"ok":true,"id":<id>,"moved":true}`.

`FolderEdit` is not changed: the move has its own small writer. `MovePlan` holds indexes
and lengths only; the subtree's paths are never kept. The frames: `internal_folder_move`
holds the old path (94 bytes), the line and the plan; `plan_move`, `copy_lines` and
`write_moved` each hold one `FolderScan` (about 170 bytes) or none.

## The command tool

`odrigctl/cli.py`: `COMMANDS["move"]` takes `external ID PATH` and `internal ID PATH`; the
path of `internal` is encoded name by name as `folder make` encodes it, and `/` is not a
path of `internal`. The usage text and the epilog name it.

## The app

- `commands.js`: `moveInternal(id, path)` sends `move internal <id> <encoded path>` and
  checks `id` and `moved` as `moveExternal` does.
- `messages.js`: the refusals of `move internal`, `MOVINGS`: `bad-argument` "A folder or an
  animation inside would pass the limits of 3 levels or 100 bytes.", `in-use` "A folder
  there has that name.", `unknown-id` "The folder or its new place is not on the
  installation any more. The list is read again.", `unsupported` "This installation cannot
  move folders in its storage."; `busy` and `storage-error` keep the general texts.
- `screens/explorer.js`, through the folder hook of `show.js`'s `extend` (`folderMenu`),
  gives a folder row of the board's storage `Rename…` and `Move to…`, disabled unless the
  target answers and no change of the list runs; a folder of the card gets neither.
- **`Rename…`** opens `#folder-dialog` in a rename mode: its title "Rename folder", the line
  `In Internal /<parent>/`, the name field holding the folder's name, a new line
  `#folder-path` with the new full path, updated as the name is typed, and the button
  `Rename`; the storage chooser is hidden. The checks are those of `moves.folderNameProblem
  ("internal", parent, name)` and of a sibling folder of the level shown with that name in
  any case, the folder itself left out. An unchanged name sends nothing. `Rename` sends the
  line through `client.operation("folder", ...)`.
- **`Move to…`** opens `#move-dialog` for that one folder with the board's storage alone
  (`moving.internalOnly`): the storage chooser holds `Internal storage` only; the folders
  are those of `foldersOf("internal")` without the folder itself and those below it; each
  destination that cannot take it stays in the list, disabled, its reason in its text:
  "It is there already." for its own parent; "A folder there has its name." for a taken
  name in any case; "It would pass 3 levels or 93 characters there." for a folder of its
  subtree past the limits; "An animation inside would pass 100 characters there." for a
  file of its subtree. The subtree's folders come from the paths `foldersOf` read, its files
  from `moves.subtree`. The preview shows "Folder Internal /<old>/ → Internal /<new>/".
  `Move` sends the line.
- **Folders selected and moved inside the board's storage.** `moves.folderPlan` plans a
  folder of the board's storage with a destination in the board's storage as a command
  move (`byCommand: true`), with the skips it gives today for the destination (into itself,
  there already, the name, a taken name, another selected folder of that name) and those of
  the limits; `runMove` sends one `move internal` for it, and reports it as it reports a
  folder moved today. No job is kept on the phone for it. Moves between the storages and of
  the card's folders keep seed 74's jobs.
- **The end.** On success: `client.refreshContent()`, "Renamed the folder Internal /a to
  Internal /b." or "Moved the folder Internal /a/ to Internal /b/a/."; `moved:false` says
  that it is there already. `client.followFolder(storage, from, to)` rewrites the paths of
  the levels shown inside the moved folder. A `Refusal` says its words; `unknown-command`
  says "This installation's firmware cannot move folders inside its storage. Install the
  newer firmware." A `Failure` (no reply) lists the levels again and says "No confirmed
  reply. The folder is at Internal /<path>/ now." by the folder's id found in the walk of
  `foldersOf("internal")`, or that it was not found. The line is never sent again by the
  app.
- Paths are encoded name by name, as `folderMake` encodes them.

## Documents

`docs/commands.md`: the row `move internal <folder id> <path>`, its refusals and reply in
"Folders of the board's own storage", the error codes' table. `docs/core.md`, "Internal
folders": the move's plan and its three readings. `docs/emulator.md`: the command tool's
`move internal`. `docs/android-app.md`: `Rename…`, `Move to…` of a folder of the board's
storage, and a step of "The check on a phone". The change log of `docs/decisions.md`, with
the owner's approval of 2026-11-09, and the drifts at the end of `docs/drifts.md`.

## Tests

Each seen failing first, its failure in the commit message.

- **Core** (`tests/core/test_folder_move.py`, new): a rename, a move to another parent, a
  move to the root, and a move from the root to depth 3; a subtree of three levels with its
  ids, numbers, stored names, Ignore, saved order, brightness and repeat, the internal
  catalog and `show.json` the same, byte for byte; the place among the new siblings; every
  refusal in order; a rename that changes only the case, which is taken; `moved:false`; a
  file listed at the root for its long path, which blocks no move; the walk's order;
  Ignore inherited and Ignore lost; a moved current playlist and one below it, with
  `status` and `playlist.txt`; an animation of the folder that plays on through the move;
  a cut at each store call (the part's open, its writes, its close, its rename), leaving
  the old file or the new one; each reading starting at offset 0, which the test host's
  check of reads holds. The command lists of `tests/core/test_docs.py` and
  `tests/emulator/test_tool.py`.
- **Emulator**: the line over HTTP and TCP.
- **Command tool**: `move internal ID PATH`, encoded; its usage errors.
- **App**: `Rename…`, its checks and its line; `Move to…` with its destinations disabled and
  their reasons; selected folders moved inside the board's storage by the command; the
  `bad-argument` text; `unknown-command`; a lost reply; a level that follows; in Chrome
  against the emulator. `tests/app/test_scope.py` takes `move internal <n> <n>`.
- **Seed 61**, where it is built with this seed: a move into `clocks/message` and out of it.
