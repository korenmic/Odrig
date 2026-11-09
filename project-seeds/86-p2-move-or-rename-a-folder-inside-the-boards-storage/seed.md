# Move or rename a folder inside the board's storage

## Summary

Add `move internal <folder id> <path>`, which the owner approved on 2026-11-09. It gives a
folder of the board's own storage a new path: another parent, another name, or both, and
its sub-folders go with it. These folders are numbered folders `/odrig/<n>`, and their paths
are kept only in `folders.txt`. So a move is one rewrite of that file. No file is copied,
renamed or checked again, and every id, number, stored name, saved setting, catalog key and
preview stays as it is. The command is refused for a move into the folder itself or below
it, for a result past 3 levels or 100 bytes, and for a path that is taken. The current
playlist's path follows the move. The app gets `Rename…` and `Move to…` in the menu of
such a folder's row. This seed is built after seed 74 part B, pull request #64, and its
task 6.

## Priority

`P2`.

## Product Context

Seed 74 part B, pull request #64, gives the board's own storage folders
(`docs/core.md` of that branch, "Internal folders"):

- A file in a folder is kept under the stored name `<n>/<name>`. `show.json`, the internal
  catalog, `repeats.txt`, `brightness.txt`, `pending.txt` and the phone's previews use that
  name, and it stays while the file stays in its folder.
- A folder's path, id and Ignore are a line of `folders.txt`, in the tree's order:

  ```
  odrig-folders 1 4
  2 41 0 shows
  1 39 0 shows/night
  3 42 1 shows/old
  ```

What moves today, or will once part B is done:

- **A file inside the board's storage.** It moves by an upload under its id with the new
  path: the app reads it back and sends its bytes again.
- **A folder of the card inside the card.** It moves with `move external <id> <path>` (seed
  74 task 6, requirement 5.1).
- **A folder between the storages.** It moves as a job of the app over its files
  (requirement 5.2).
- **A folder of the board's storage inside the board's storage.** It cannot be moved or
  renamed. The only way would be a job that makes the new folders, uploads every file again
  under its id and lets the old folders prune. That sends the bytes twice over the link,
  checks every file again, gives every folder a new id and loses the playlist's path.

Part B's design gave the reason this is cheap: with numbered folders, a folder's path
changes by rewriting one file. The gap was proposed to the owner as a new seed (rule 8).
On 2026-11-09 the owner approved the command and the app's actions (see "The Owner's
Answers").

Seed 85, written at the same time, adds `Remove folder` to the same menu. Either seed may
be built first.

## Required Behavior

1. **The command.** `move internal <folder id> <path>`:
   - `<folder id>` is a folder of the board's own storage, as `list` gives it. It is read
     as `remove <id>` reads an id, 1 to 4,294,967,295 in decimal, so that the id of a card's
     folder or animation is `in-use` and not `bad-argument`.
   - `<path>` is the folder's new path from the storage's root, written as
     `folder make internal` writes one: decoded once from URI escapes, one to three names
     joined by `/` under the card's naming rule, 93 bytes at most, the last not ending in
     `.odrg` or `.odrgx`.
   - The new parent, the path without its last name, is the root or a folder of the board's
     storage. The folder takes the last name as its own.
   - One parser takes the line from every transport: HTTP, the board's serial port, and the
     emulator's serial port and TCP lines.
2. **One rewrite.**
   - The folder's line and the line of every folder below it get the new path in place of
     the old one at their start.
   - They keep their order among themselves, and go to the folder's new place in the tree's
     order. That place is under the new parent, among its sub-folders by the bytes of their
     names, where a folder made there would go.
   - `folders.txt` is written once, as `folders.part`, and then renamed onto it.
   - No other file and no folder of the storage is written, renamed or removed.
3. **What is kept.**
   - Every line's number, id and Ignore, and the header's next number.
   - Every item: its id, its stored name, its file and its position.
   - The saved order inside each folder (`order get in`), and the saved brightness and
     repeat.
   - The internal catalog and its keys, `show.json`, and the previews on the phone.
4. **The reply.** `{"ok":true,"id":<id>,"moved":true}`. When the folder has that path
   already, in bytes, the reply is `{"ok":true,"id":<id>,"moved":false}` and nothing is
   written, so a line sent again after a lost reply changes nothing.
5. **What follows the move.**
   - **The walk.** The root's playlist and the daily rotation take the new tree's order at
     their next pick, and the turn in progress goes on. No file is opened again, so the
     animation that plays goes on undisturbed.
   - **Ignore.** A moved folder is held when one of its new ancestors is ignored, and is no
     longer held when only an old ancestor was ignored. The turn in progress is checked
     again, as after `ignore` of a folder.
   - **The current playlist.** When it is the moved folder or a folder below it, it stays
     current with its window. Its path in `status` follows at once, and so does its path in
     `playlist.txt`, saved at the next refresh. When a folder moves into the current
     playlist's subtree, or out of it, that playlist's range follows the tree.
   - **Paths.** `file` and `checking` in `status`, `list` and `list in` give the new paths.
   - **Clocks.** Seed 61's internal clocks may be built before this seed. Then a move that
     brings a folder into `clocks` or `clocks/message`, or takes one out, changes which
     files are clocks and messages, as a folder made at the new path would. Their orders
     are drawn anew, and the Clocks-only state is found again.
6. **Refusals, in this order.**
   1. `bad-argument`: another form, or a path outside the rule of item 1.
   2. `show-invalid`: the show is invalid.
   3. `unsupported`: a host whose storage cannot be changed.
   4. `busy`: while an upload is open or a rebuild runs, or while the board moves a card
      folder in steps, if seed 74's task 6 builds that stepped move. `folders.txt` is
      written through the chunk buffer, which each of these may hold.
   5. `storage-error`: the board could not read its folders in this boot.
   6. `in-use`: the id of an item of the show, or of an animation or a folder of a drive.
      `unknown-id`: an id that nothing has.
   7. `bad-argument`:
      - the path is the folder's own path, then `/` and more: a move into itself or below;
      - a folder of the subtree would get a path over 93 bytes, or more than 3 levels;
      - a file listed in a folder of the subtree would get a path over 100 bytes, as
        `upload begin` would refuse that path. A file that a computer's tool put in such a
        folder under a longer path, and that is listed at the root for it, does not count;
        it is listed in its folder once its new path fits.
   8. `"moved":false`: the path is the folder's own path.
   9. `in-use`: another folder of the new parent has the last name, in bytes or with only
      the case of its letters different. A rename that changes only the case of the
      folder's own name is taken.
   10. `unknown-id`: the new parent is not there.
   11. `storage-error`: `folders.part` cannot be written or renamed. The folders are then
       as they were.
7. **The app.** The menu of a folder's row of the board's own storage gets `Rename…` and
   `Move to…`. Both are enabled while the target answers and no change of the list runs.
   - **`Rename…`** opens the dialog of `New folder`. Its field holds the folder's name, the
     line `In Internal /<parent>/` is above it, as `New folder` writes it, and the new full
     path is under it. The name has the checks of `New folder`, the case of its siblings
     other than the folder itself among them. `Rename` sends
     `move internal <id> <parent>/<new name>`.
   - **`Move to…`** opens the chooser of `Move to…`, with the board's own storage alone:
     the root and each of its folders, without the folder itself and the folders below it.
     A destination is disabled, with its reason, when it is the folder's own parent, when
     another of its folders has the folder's name in any case, or when the folder would pass
     3 levels or 93 bytes there. The old and the new full path are shown before anything is
     sent. `Move` sends `move internal <id> <destination>/<name>`.
   - **Paths.** Each name of a path is encoded as `folder make` encodes it.
   - **The end.** On success the app lists the level again. A shown level inside the moved
     folder follows it to its new path. A `bad-argument` for the subtree is said as "A
     folder or an animation inside would pass the limits of 3 levels or 100 bytes." Other
     refusals are said in words, and `unknown-command` says that the installation's
     firmware cannot move folders inside its storage.
   - **A lost reply.** After a reply that did not arrive, the app lists the levels again and
     shows where the folder is. It never sends the line again by itself.
   - **Seed 74's task 6.** Task 6 may give `Move to…` the selected folders. A selected
     folder of the board's storage with a destination in the board's storage is then moved
     by this command, one line for each selected folder, in place of a job over its files.
     Task 6's preview, skips and report stay. Moves between the storages, and moves of the
     card's folders, stay task 6's.
   - **The card.** A folder of the card gets no `Rename…`, since no command renames one.
   - **One code.** The Controller in a browser and the APK use the same code.
8. **The command tool.** `odrigctl move internal ID PATH` sends the line, with each name of
   the path encoded as for `folder make`, and prints the reply.

## Technical Constraints

- **No memory of the core.** No field of `Core`, `FileInfo` or `Upload` and no host function
  is added. The memory table of `docs/core.md` is unchanged, and `tests/core/test_memory.py`,
  `test_docs.py` and `test_drive.py` pass unedited. Every new frame stays under the 512
  bytes that GCC and Clang check.
- **The core.** `internal_folder_move(core, id, path, reply)` goes in `core/src/folders.cpp`,
  marked `ODRIG_NOINLINE`, and the command is parsed in `core/src/commands.cpp`.
  - **The plan.** A first reading of `folders.txt` finds the folder's line and its
    subtree: the lines after it of a greater depth, which stand together in the tree's
    order, so that their first and last index name them. It also finds the new parent, the
    siblings there, and the index before which the subtree goes. As it reads each line of
    the subtree it checks that line's new path, its depth and its 93 bytes, and the new
    path of each file of the file table in memory whose stored name has that line's number
    and that is listed in its folder now. Nothing of the subtree is kept but its indexes.
  - **The writing.** It reads the file three more times, each from offset 0 to its end, as
    the host contract wants a file read: first the lines before the new place without the
    subtree, then the subtree with its new start, then the rest without the subtree. Only
    one `FolderScan` is on the stack at a time. `FolderEdit`, which lives on the stack, gets
    the fields of a move.
  - **After the rename.** `folders_derive` runs, then `player_internal_inclusion_changed`
    as `internal_folder_ignore` calls it, and the record of the current playlist is found
    again. When the current playlist is in the subtree, `playlist_path` gets `:` and its
    new path, and `save_due` is set. A cut before `playlist.txt` is saved leaves the old
    path there, and the next start falls back to the root, as for a playlist that is gone.
- **What stays as it is.** The host contract, the format of `folders.txt`, the card's
  catalog, `show.json`, the Python library and the firmware tool's storage commands. The
  sources of the emulator and of the firmware are unchanged; the firmware images are built
  again because they compile the core.
- **Tests seen failing first.**
  - The core suite:
    - a rename, a move to another parent, a move to the root, and a move from the root to
      depth 3;
    - a subtree of three levels, with its ids, numbers, stored names, Ignore, saved order,
      brightness and repeat, the internal catalog and `show.json` the same, byte for byte;
    - the place among the new siblings;
    - every refusal, in order; a rename that changes only the case, which is taken;
      `moved:false`; a file listed at the root for its long path, which blocks no move;
    - the walk's order; Ignore inherited and Ignore lost; a moved current playlist and one
      below it, with `status` and `playlist.txt`;
    - an animation of the folder that plays on through the move;
    - a cut at each store call, the part's write and its rename, leaving the old file or
      the new one;
    - each reading starting at offset 0, which the test host's check of reads holds.
  - When seed 61 is built before this seed: a move into `clocks/message` and out of it.
  - The emulator suite, over HTTP and TCP.
  - The app suite: both dialogs, the destinations disabled with their reasons, the
    refusal for the subtree, `unknown-command`, a lost reply and the level that follows;
    the test in Chrome against the emulator.
  - The command tool's suite.
- **Documents.**
  - `docs/commands.md`: the table of commands, "Folders of the board's own storage" and the
    error codes.
  - `docs/core.md`, "Internal folders".
  - `docs/emulator.md`, for the command tool.
  - `docs/android-app.md` and its check on a phone.
  - The change log of `docs/decisions.md`, with the owner's approval of 2026-11-09.
  - An entry at the end of `docs/drifts.md`.

## Open Questions

None. The owner approved the command, its refusals, the playlist path that follows, and
the app's actions. The seed decides the rest:

- **`<path>` is the folder's new full path.** One form covers a rename and a move. This is
  unlike `move external`, whose `<path>` is the destination folder. A rename needs the new
  name, and the approved refusal of "an existing path" applies to the new full path.
- **The moved folder's place.** It goes among its new siblings by the bytes of their names,
  as the tree's order keeps every folder. The owner ruled the same for the card's moved
  folders on 2026-11-09.
- **The reply.** It is that of `move external` for a file: the id, and `moved` true or false.
  The folder's own path answers `moved:false`, so a line sent again is safe.
- **A rename that changes only the case** of the folder's name is taken.
- **The id.** It is read as `remove <id>` reads one, so a card's id is `in-use`.
- **The limits.** A folder's path is 93 bytes at most and 3 levels at most, and a file's
  path is 100 bytes at most. The file limit is checked for every file listed in a folder of
  the subtree, as `upload begin` checks a path, so a move never takes a file out of its
  folder's listing. A file that a computer's tool put there under a longer path is listed
  at the root already; it does not block a move the operator cannot see it in, and it is
  listed in its folder once its path fits.
- **The refusal codes.** A move into the folder itself or below it, and a passed limit,
  give `bad-argument`, as `move external` gives them. A taken path gives `in-use`, and a
  missing parent gives `unknown-id`, as for `folder make internal`.
- **`busy`.** While an upload is open, a rebuild runs, or the card's stepped folder move
  runs, if task 6 builds one.
- **The header's next number** is kept, since no folder is made.
- **The current playlist's path** follows at once in memory and is saved at the next
  refresh. A cut between the two falls back to the root.
- **No folder of the storage is renamed.** The emulator's and the firmware's sources are
  unchanged.
- **Three readings for the writing,** each from offset 0, so the host contract is
  unchanged.
- **The app.** `Rename…` uses `New folder`'s dialog, and `Move to…` uses the existing
  chooser, limited to the board's storage. Seed 74's task 6 sends a folder move inside the
  board's storage through this command. The card's folders get no `Rename…`.
- **The command tool.** `odrigctl move internal ID PATH`.
- **Seed 61.** If its internal clocks are built first, they follow a move as they follow a
  folder made at the new path.

## The Owner's Answers

On 2026-11-09 the owner was asked about the gap that seed 74's design of part B named. The
owner approved a new seed in which `move internal <folder id> <path>` moves or renames a
folder within the board's own storage: one rewrite of `folders.txt`, with every id, setting
and catalog key kept, and with Move and Rename in the app. The approval covers the addition
to the command list. The owner asked for the seed to be written now and built later. The
approval is recorded in `docs/commands.md` and in the change log of `docs/decisions.md`
when the command is built.

The same day the owner ruled, for seed 74's task 6, that moved folders keep the card's
order by name and moved files go last. This seed keeps that order for the board's storage.

## Definition Of Done

1. A requirements/design/tasks specification of the command, its one rewrite, what follows
   it, and the app's actions.
2. The core, emulator, app, command tool and onboarding suites pass with the new tests, seen
   failing first.
3. Firmware images for the installation's board and the spare's module, built as
   `firmware/fw.py` builds them, and an APK signed with the persistent key, all built from
   the pushed head.
4. The owner's check on the phone, with a folder of the board's storage that holds an
   animation:
   - the folder is renamed, moved under another folder, and moved back to the root;
   - the animation keeps its preview, brightness and place in the order, and plays on
     through each move;
   - a current playlist follows the folder;
   - all of this holds after a restart.
