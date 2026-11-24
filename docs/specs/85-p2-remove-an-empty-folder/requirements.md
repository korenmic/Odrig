# Requirements

Seed 85, `project-seeds/85-p2-remove-an-empty-folder/seed.md`. The core, the test host,
the emulator's storage, the firmware's card host, the command tool and the app. One command
is added, `folder remove <id>`, which the owner approved on 2026-11-09. The card's catalog
format, its commit record, the Python library, the converter and the firmware tool are not
changed. Built on seed 74 part B, pull request #64.

## 1. The command

1.1 `folder remove <id>` takes one id in decimal, 1 to 4,294,967,295, read as `remove <id>`
reads one. Any other form is refused `bad-argument`.
1.2 One parser takes the line from every transport: HTTP, the board's serial port, and the
emulator's serial port and TCP lines.
1.3 On success the reply is `{"ok":true}`, once the folder's entry is gone durably.

## 2. Which folders are empty

2.1 A folder of the board's own storage is empty when no file of the show's file table is
stored in its numbered folder and no line of `folders.txt` is below it. A file stored there
that is listed at the root because its path passes 100 bytes counts as a file of the folder.
2.2 A folder of the card is empty when the card's index gives it no own file and no
sub-folder. A file on the card that the index does not know of does not count.
2.3 A folder that is not empty is refused `in-use`, and nothing changes.

## 3. The board's own storage

3.1 The folder's line leaves `folders.txt`, written as `folders.part` and renamed onto it.
Every other line keeps its number, id, Ignore and place, and the header keeps its next
number.
3.2 Then its numbered folder `/odrig/<n>` is removed with the host's `remove("<n>")`.
3.3 The folder's id is free again for a new item or folder.
3.4 No core memory is added: no field of `Core`, `FileInfo` or `Upload`, no host function,
and every new frame stays under 512 bytes.

## 4. The card

4.1 The folder's entry leaves the card's index in one commit of the card's catalog, which
writes no page: the table loses the folder's line, every ordinal and end after it is one
less, the end of each folder above it is one less, and the parent has one sub-folder less;
the map loses the folder's line, and every ordinal after it is one less; the parent's folder
file loses the folder's row, and is removed when no line is left in it.
4.2 Then the folder on the card is removed with the host's `remove("drive/<path>")`.
4.3 Every other file and folder keeps its id, and no file of the card moves.
4.4 The commit record's actions stay `move` and `remove` of files; the folder on the card is
removed after the record, outside it.

## 5. The order of the changes

5.1 On both storages the folder's entry goes first, and its folder of the storage after it.
5.2 A failure before the entry is durable leaves everything as it was, and the reply is
`storage-error`.
5.3 A power cut leaves the old entry or none: on the board's storage the old `folders.txt`
or the new one; on the card what the next mount makes of the commit record.
5.4 When the folder of the storage cannot be removed after the entry went, because the power
was cut first or it holds a file that neither the show nor the index knows of, it stays and
is listed nowhere, and the reply is still `{"ok":true}`. On the board's storage a later
folder given that number takes it; on the card a folder made again at that path takes it.

## 6. Only the folder named

6.1 A parent that the removal leaves empty stays. Nothing is pruned in a cascade.

## 7. The playlists

7.1 When the removed folder is the current playlist, the root's playlist becomes current with
a fresh window and is saved in `playlist.txt`; in Clocks-only mode the card's saved path is
kept as it is today when a current card folder is gone.
7.2 When another folder is the current playlist, it stays current, and a card folder's place
in the table is found again.
7.3 The animation that plays goes on.

## 8. Saved choices and the clocks

8.1 A folder of the board's storage loses its Ignore with its line; a folder made later at
that path starts included.
8.2 A card folder's `d <path>` line of `ignored.txt` is kept, as for every absent path; a
folder made later at that path is excluded again.
8.3 An empty Clocks folder of the card, `clocks` or `clocks/message`, may be removed;
`status` then reports the clocks as for a card without that folder.

## 9. Refusals, in this order

9.1 `bad-argument`: another form.
9.2 `show-invalid`: the show is invalid.
9.3 `in-use`: the id of an item of the show, or of an animation of a drive.
9.4 For a folder of the card: `busy` while an upload is open, a rebuild runs, a test of the
mapping shows, or the card's catalog is read; `read-only` while the core may not write the
card, a USB stick among them; `in-use` for a folder that is not empty; `storage-error` when
the commit fails, the index then as it was.
9.5 While the card's catalog is read, an id above 60,000 that the core does not place yet is
`busy`.
9.6 For any other id of 60,000 or less: `unsupported` on a host whose storage cannot be
changed; `busy` while an upload is open or a rebuild runs; `storage-error` while the board
could not read its folders in this boot; `unknown-id` when no folder of the board's storage
has the id; `in-use` for a folder that is not empty; `storage-error` when `folders.txt`
cannot be written, the folders then as they were.
9.7 `unknown-id` for any other id.

## 10. The hosts

10.1 The host's `remove`, given `drive/<path>` where the path names a folder of the drive's
folder `odrig`, removes that folder while it is empty: 1 when it removed it, 0 when there
was none, -1 on a failure and while it is not empty. It already does so for `<n>` of the
board's storage. No host function is added.
10.2 The test host's `remove` does the same and counts the call among its store calls.
10.3 The emulator's `FolderHost.remove` does the same for a folder of the drive.
10.4 The firmware's `removeDriveFile` removes a directory with `rmdir`, under the same guard
and `changing()`, and gives 0 for `ENOENT`. A directory that is not empty gives -1 without
`capacityWriteFailed()`. The stick host stays read-only.

## 11. The app

11.1 The menu of a folder's row gets `Remove folder` for a folder of the board's own
storage, and for one of a card the board may write, marked as a danger as `Delete` is. For
a folder of a card the board may not write, the note "External storage is read-only: this
folder cannot be removed." stands in its place.
11.2 It is enabled while the target answers, no change of the list runs and the row counts
0 animations. For a row with animations it is disabled, with the note "Only an empty folder
can be removed."
11.3 When pressed, the app lists the folder's level with `list in <id>`. When that level has
a row, the app says that the folder is not empty and sends nothing.
11.4 Otherwise the app asks "Remove the empty folder <storage> /<path>? This cannot be
undone.", with `Remove` and `Cancel`. `Cancel`, Escape or a dismissed dialog send nothing.
11.5 `Remove` sends `folder remove <id>`. On success the app lists the level again and says
that the folder was removed. A refusal is said in words; `unknown-command` says that the
installation's firmware cannot remove folders.
11.6 After a reply that did not arrive, the app lists the level again: a row with that id
and path means the folder was not removed, and the operator may press again; no such row
means it was removed. The app never sends the line again by itself.
11.7 `Delete selected` is unchanged. The Controller in a browser and the APK use one code.

## 12. The command tool

12.1 `odrigctl folder remove ID` sends the line and prints the reply.

## 13. Documents and delivery

13.1 `docs/commands.md` (the table of commands, the folder sections in place of "No command
removes a folder", the error codes), `docs/core.md` (the host's `remove`, "Internal
folders"), `docs/catalog.md` (when a folder leaves the index, and what the change writes),
`docs/emulator.md`, `docs/firmware.md`, `docs/android-app.md` with its check on a phone, the
change log of `docs/decisions.md` with the owner's approval of 2026-11-09, and entries at
the end of `docs/drifts.md`.
13.2 The core, emulator, firmware, firmware host, app, command tool and onboarding suites pass
with the new tests, each seen failing first.
13.3 Firmware images for the installation's board and the spare's module, built as
`firmware/fw.py` builds them, and an APK signed with the persistent key, all built from the
pushed head.
13.4 The owner's check on a phone stays open until the owner reports it: an empty folder
made on the board's storage and one made on the card are each removed with `Remove folder`,
are gone from the list and still gone after a restart; a folder with an animation cannot be
removed, and the app says why.
