# Remove an empty folder

## Summary

Add `folder remove <id>`, which the owner approved on 2026-11-09. It removes an empty folder
of the board's own storage or of the card. On the board's own storage it removes the
folder's line of `folders.txt` and then its numbered folder `/odrig/<n>`. On the card it
takes the folder's entry out of the card's index in one commit of the card's catalog, and
then removes its folder on the card. A folder that holds a file or a sub-folder is refused
with `in-use`. The app gets `Remove folder` in the menu of a folder's row, on both
storages, on the card only while the board may write it. This seed is built after seed 74
part B, pull request #64.

## Priority

`P2`.

## Product Context

Seed 74 gives both storages real folders. Part A is on `master`; part B is pull request
#64. The folders are made by `folder make internal <path>`, `folder make external <path>`
and the app's `New folder` and `New playlist folder`. Nothing removes a folder:

- **The board's own storage.** A folder loses its line and its numbered folder when its last
  file goes and it has no sub-folder. Each folder above it that is left empty the same way
  goes too (`internal_folders_prune`, `core/src/folders.cpp` of part B). A folder made by
  `New folder` and never filled stays. So does one emptied while a rebuild ran or an upload
  was received, and one emptied by a removal that a power cut ended before the prune. The
  `docs/commands.md` of part B says "No command removes a folder."
- **The card.** A folder leaves the card's index when its last file goes and it has no
  sub-folder, as before seed 74 (requirement 1.7 of its specification). A folder made by
  `folder make external` stays in the index, with `files` 0, until a rebuild. Its folder on
  the card always stays: the card's host removes a name with `unlink` only
  (`removeDriveFile`, `firmware/usermod/odrig_drive.cpp`) and has no `rmdir`.
- **What the operator sees.** A folder made by mistake, or under a wrong name, stays in the
  app. On the board's storage it stays for good. On the card it stays until a
  `catalog rebuild external`, which drops every empty folder of the card at once.

Seed 74's design of part B leaves the removal out ("No command removes a folder."), and the
gap was proposed to the owner as a new seed (rule 8). On 2026-11-09 the owner approved the
command and the app's action (see "The Owner's Answers").

Seed 86, written at the same time, adds `Rename…` and `Move to…` to the same menu of a
folder of the board's storage. Either seed may be built first.

## Required Behavior

1. **The command.** `folder remove <id>` takes the id that `list` gives a folder's row, in
   decimal, 1 to 4,294,967,295 as `remove <id>` takes an id, since the card's ids may pass
   65,535. The reply is `{"ok":true}` once the folder's entry is gone durably, as
   `remove <id>` answers. One parser takes the line from every transport: HTTP, the board's
   serial port, and the emulator's serial port and TCP lines.
2. **Only an empty folder.**
   - A folder of the board's own storage is empty when no file of the show's file table is
     stored in its numbered folder and no line of `folders.txt` is below it. A file stored
     there that is listed at the root, because its path passes 100 bytes, counts as a file
     of the folder.
   - A folder of the card is empty when the card's index gives it no own file and no
     sub-folder.
   - Any other folder is refused with `in-use`, and nothing changes.
3. **The board's own storage.** The folder's line leaves `folders.txt`, written through
   `folders.part` and a rename as every change of that file is. Then its numbered folder is
   removed with the host's `remove("<n>")`. Every other line keeps its number, id, Ignore and
   place, and the header keeps its next number. The folder's id is free again for a new item
   or folder, as a pruned folder's is.
4. **The card.** The folder's entry leaves the card's index in one commit of the card's
   catalog, which writes no page:
   - the table loses the folder's line; every ordinal and end after it is one less, the end
     of each folder above it is one less, and the parent has one sub-folder less;
   - the map loses the folder's line, and every ordinal after it is one less;
   - the parent's folder file loses the folder's row, and is removed when no line is left in
     it.

   Then the folder on the card is removed. Every other file and folder keeps its id, and no
   file of the card moves.
5. **The entry first, the folder of the storage after.**
   - On both storages the folder's entry goes first, and its folder of the storage after
     it.
   - A failure before the entry is durable leaves everything as it was, and the reply is
     `storage-error`. A cut leaves the old entry or none: on the board's storage the old
     `folders.txt` or the new one, and on the card what the next mount makes of the commit
     record, as for every commit of the card's catalog.
   - After that, the host may fail to remove the folder of the storage: a power cut came
     first, or the folder holds a file that neither the show nor the index knows of. Then
     that folder stays where it is and is listed nowhere, as the folder of a pruned card
     folder stays today. The reply is still `{"ok":true}`.
   - On the board's storage, a later folder given that number takes the left folder, as
     after a cut today. On the card, a folder made again at that path takes it.
6. **Only the folder named.** A parent that the removal leaves empty stays, as a folder that
   was never filled does. Its own `folder remove` removes it. Nothing is pruned in a cascade.
7. **The playlists.**
   - When the removed folder is the current playlist, the root's playlist becomes current
     with a fresh window and is saved in `playlist.txt`. This is what happens today when a
     current folder of the board's storage is pruned, or when `current_again` finds a
     current card folder gone, Clocks-only mode keeping the card's saved path as it does
     today.
   - When another folder is the current playlist, it stays current, and a card folder's
     place in the table is found again.
   - The animation that plays goes on.
8. **Saved choices.**
   - A folder of the board's storage keeps its Ignore in its line, so the Ignore goes with
     the line. A folder made later at that path starts included.
   - A card folder's Ignore, `d <path>` in `ignored.txt`, is kept, as every choice of an
     absent path is (`docs/commands.md`, "Playlist inclusion and batch deletion"). A folder
     made later at that path is excluded again.
   - An empty Clocks folder of the card, `clocks` or `clocks/message`, may be removed.
     `status` then reports the clocks as it does for a card without that folder.
9. **Refusals, in this order.**
   1. `bad-argument`: another form.
   2. `show-invalid`: the show is invalid.
   3. `in-use`: the id of an item of the show, an animation or a cycle, or of an animation of
      a drive. It is no folder.
   4. For a folder of the card:
      - `busy` while an upload is open, a rebuild runs, a test of the mapping shows, or the
        card's catalog is read; also while the board moves a card folder in steps, if seed
        74's task 6 builds that stepped move;
      - `read-only` while the core may not write the card, a USB stick among them;
      - `in-use` for a folder that is not empty;
      - `storage-error` when the commit fails, the index then as it was.

      The id of a folder of the card is unknown while the card is out.
   5. For any other id of 60,000 or less:
      - `unsupported` on a host whose storage cannot be changed;
      - `busy` while an upload is open or a rebuild runs, and while the board moves a card
        folder in steps, if seed 74's task 6 builds that stepped move: `folders.txt` is
        written through the chunk buffer, which each of these may hold;
      - `storage-error` while the board could not read its folders in this boot;
      - `unknown-id` when no folder of the board's storage has the id;
      - `in-use` for a folder that is not empty;
      - `storage-error` when `folders.txt` cannot be written, the folders then as they were.
   6. `unknown-id` for any other id.

   The `busy` and `read-only` conditions are those of each storage's `folder make`, so a
   removal is refused `busy` or `read-only` where a making would be. A removal needs only
   the host's `remove`, so a host that makes no folders is not `unsupported` for it: the
   card's list has no `unsupported`, and the board's storage has it only for a host whose
   storage cannot be changed.
10. **The app.** The menu of a folder's row gets `Remove folder` for a folder of the board's
    own storage, and for one of a card the board may write. It is marked as a danger, as
    `Delete` is.
    - **When it is enabled.** It is enabled while the target answers, no change of the list
      runs and the row counts 0 animations. For a folder with animations it is disabled, with
      the note "Only an empty folder can be removed." For a folder of a read-only card the
      note "External storage is read-only: this folder cannot be removed." takes its place.
    - **The check.** When pressed, the app lists the folder's level with `list in <id>`. When
      that level has a row, a sub-folder or an animation uploaded since, the app says that
      the folder is not empty, and sends nothing.
    - **The question.** Otherwise the app asks "Remove the empty folder <storage> /<path>?
      This cannot be undone.", with `Remove` and `Cancel`. `Cancel`, Escape or a dismissed
      dialog send nothing.
    - **The removal.** `Remove` sends `folder remove <id>`. On success the app lists the
      level again and says that the folder was removed. A refusal is said in words, and
      `unknown-command` says that the installation's firmware cannot remove folders.
    - **A lost reply.** After a reply that did not arrive, the app lists the level again. A row
      with that id and path means the folder was not removed, and the operator may press
      again. No such row means it was removed. The app never sends the line again by itself.
    - **What stays.** `Delete selected` is unchanged: it stays disabled while a folder is
      selected.
    - **One code.** The Controller in a browser and the APK use the same code.
11. **The command tool.** `odrigctl folder remove ID` sends the line and prints the reply.

## Technical Constraints

- **No memory of the core.** No field of `Core`, `FileInfo` or `Upload` and no host function
  is added. The memory table of `docs/core.md` is unchanged, and `tests/core/test_memory.py`,
  `test_docs.py` and `test_drive.py` pass unedited. Every new frame stays under the 512
  bytes that GCC and Clang check.
- **The host interface.** Only its text changes. `remove`, given `drive/<path>` where the
  path names a folder of the drive's folder `odrig`, removes that folder while it is empty.
  It returns 1 when it removed it, 0 when there was none, and -1 on failure and while the
  folder is not empty. It does the same today for `<n>` of the board's storage.
- **The core.**
  - The board's storage: `internal_folder_remove` in `core/src/folders.cpp`, beside
    `internal_folders_prune`, with its `FolderEdit.drops`, `write_part` and `commit_part`.
    After the change come `folders_derive` and, when the current playlist changed,
    `player_playlist_chosen` and `playlist_changed`, as after the prune.
  - The card: `catalog_folder_remove` in `core/src/catalog.cpp`. Its index change is planned
    as the cascade of `plan_removal` plans a folder that goes: `gone_ids`, the table's and
    the map's `gone_from` and `gone_count`, and the parent's `child` row. It has no file and
    no page. After the commit comes what follows `folder make external`: `current_again`,
    whose `tree_find_current` also finds the Clocks folders again through `breaks_tree`,
    then `repeats_reload`, `brightness_start` and `ignored_start`.
  - The command is parsed in `core/src/commands.cpp`, beside `folder make`.
- **What stays as it is.** The card's catalog format, its commit record and the Python
  library are unchanged: the record's actions stay `move` and `remove` of files, and the
  folder on the card is removed after the record, outside it. The prune of either storage
  is unchanged; on the card it still leaves the folder of a pruned folder on the card.
- **Firmware.** `removeDriveFile` in `firmware/usermod/odrig_drive.cpp` removes a directory
  with `rmdir`, under the same guard and `changing()`, and gives 0 for `ENOENT`. A directory
  that is not empty gives -1 without `capacityWriteFailed()`: the card is sound, and its
  capacity stays known without a remount. The board's own storage already removes `<n>`
  (`odrig_files.cpp`). The stick host stays read-only.
- **The emulator and the test host.** `FolderHost.remove` in `emulator/host.py` removes an
  empty folder of the drive, as it removes `<n>` of the board's storage today. The test
  host, `tests/core/host/host.cpp`, does the same in its `remove`: it refuses a folder that
  is not empty and counts the call among its store calls for the tests of a cut.
- **Tests seen failing first.**
  - The core suite, the board's storage:
    - every refusal, in order;
    - an empty folder made and removed: its line, its numbered folder, its id given to the
      next new folder or item, `list` and `status`;
    - a folder holding a file, one holding only a file whose path passes 100 bytes, and
      one with a sub-folder;
    - a nested folder removed while its parent stays;
    - the current playlist removed, and the root current and saved;
    - a cut at each store call, the part's write, its rename and the folder's removal, each
      ending as item 5 says.
  - The core suite, the card:
    - an empty folder removed while folders after it in the table keep their ids, and their
      `list in` replies stay correct;
    - a current card playlist after it found again, and the removed folder current;
    - a Clocks folder;
    - `read-only`, a stick, a test that shows and the card's catalog being read;
    - a cut during the commit, replayed at the next mount;
    - a cut after the commit: the folder on the card is left and listed nowhere, and
      `folder make external` makes it again.
  - The emulator suite, over HTTP and TCP.
  - The firmware host suite: `removeDriveFile` of an empty folder, of one that is not
    empty, which leaves the card's capacity known, and of none.
  - The app suite: the menu's states and notes, the `list in` check, the dialog, `Cancel`,
    success, a refusal, `unknown-command` and a lost reply; the test in Chrome against the
    emulator.
  - The command tool's suite.
- **Documents.**
  - `docs/commands.md`: the table of commands, the two folder sections in place of "No
    command removes a folder", and the error codes.
  - `docs/core.md`: the host's `remove` and "Internal folders".
  - `docs/catalog.md`, where it says when a folder leaves the index, and a row of its
    table of what each change writes.
  - `docs/emulator.md`, `docs/firmware.md`, and `docs/android-app.md` with its check on a
    phone.
  - The change log of `docs/decisions.md`, with the owner's approval of 2026-11-09.
  - An entry at the end of `docs/drifts.md`.

## Open Questions

None. The owner approved the command and the app's action. The seed decides the rest:

- **The reply.** It is `{"ok":true}`, as `remove <id>` answers. A line sent again after a
  lost reply gets `unknown-id`, so the app lists the level again instead of sending it
  again.
- **The order of the changes.** On both storages the entry goes first and the folder of the
  storage after it. A folder of the storage that cannot be removed stays, listed nowhere,
  and the reply is still a success. This is how the board's storage already prunes, and it
  keeps the card's commit record as it is.
- **No cascade.** Only the folder named goes. A parent left empty stays until its own
  `folder remove`.
- **When a folder is empty.** On the board, no file of the file table is in its numbered
  folder; the files listed at the root for a long path count. On the card, the index gives
  it no own file and no sub-folder. A file on the card that the index does not know of
  does not block the removal, and it stays in the left folder.
- **No new error code.** `in-use` is given for a folder that is not empty and for an id
  that is no folder, as `remove` gives `in-use` for a folder's id.
- **The id.** It is read as `remove <id>` reads one, 1 to 4,294,967,295, since the card's
  ids may pass 65,535.
- **`busy`, `read-only` and `unsupported`.** Each storage has the `busy` and `read-only`
  conditions of its `folder make`; the board's storage is also `busy` while a stepped card
  folder move holds the chunk buffer, if task 6 builds one. A removal needs only the host's
  `remove`, so the card has no `unsupported`, and the board's storage has it only for a
  storage that cannot be changed.
- **A card folder that is not empty on the card.** The host's `rmdir` fails, the folder
  stays, listed nowhere, and the firmware does not count it as a failed write of the card.
- **Ignore.** The card keeps a removed folder's `d <path>` line, as for every absent path.
  The board's storage loses the Ignore with the line.
- **The card's prune.** It keeps leaving the folder on the card, as today. Only
  `folder remove` removes one, though the host's `remove` could now remove it.
- **No new host function.** The text of `remove` grows to take a card's folder.
- **The app.** The action is in the menu of one folder's row only. `Delete selected` is not
  changed. A `list in` check finds a sub-folder before the question, the question asks for
  confirmation, and the app never sends the line again by itself.
- **The clocks.** An empty Clocks folder may be removed.
- **The command tool.** `odrigctl folder remove ID`.

## The Owner's Answers

On 2026-11-09 the owner was asked about the gap that seed 74's design named. The owner
approved a new seed in which `folder remove <id>` removes an empty folder of either
storage, with a Remove action in the app. The approval covers the addition to the command
list. The owner asked for the seed to be written now and built later. The approval is
recorded in `docs/commands.md` and in the change log of `docs/decisions.md` when the command
is built.

## Definition Of Done

1. A requirements/design/tasks specification of the command on both storages, the order of
   its changes and the app's action.
2. The core, emulator, firmware host, app, command tool and onboarding suites pass with the
   new tests, seen failing first.
3. Firmware images for the installation's board and the spare's module, built as
   `firmware/fw.py` builds them, and an APK signed with the persistent key, all built from
   the pushed head.
4. The owner's check on the phone. An empty folder made on the board's storage and one made
   on the card are each removed with `Remove folder`. Both are gone from the list, and still
   gone after a restart. A folder with an animation cannot be removed, and the app says why.
