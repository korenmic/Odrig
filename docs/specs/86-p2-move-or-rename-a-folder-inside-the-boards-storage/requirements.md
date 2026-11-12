# Requirements

Seed 86, `project-seeds/86-p2-move-or-rename-a-folder-inside-the-boards-storage/seed.md`.
The core, the command tool and the app. One command is added, `move internal <folder id>
<path>`, which the owner approved on 2026-11-09. The host contract, the format of
`folders.txt`, the card's catalog, `show.json`, the Python library, the firmware tool and
the sources of the emulator and of the firmware are not changed; the firmware images are
built again because they compile the core. Built on seed 74 part B, pull request #64, with
its task 6.

## 1. The command

1.1 `move internal <folder id> <path>`. The id is read as `remove <id>` reads one, 1 to
4,294,967,295 in decimal.
1.2 `<path>` is the folder's new full path from the root of the board's storage, written as
`folder make internal` writes one: decoded once from URI escapes, one to three names joined
by `/` under the card's naming rule, 93 bytes at most, the last not ending in `.odrg` or
`.odrgx`.
1.3 The new parent, the path without its last name, is the root or a folder of the board's
storage; the folder takes the last name as its own.
1.4 One parser takes the line from every transport: HTTP, the board's serial port, and the
emulator's serial port and TCP lines.

## 2. One rewrite

2.1 The folder's line and the line of every folder below it get the new path in place of the
old one at their start. They keep their order among themselves, and go to the folder's new
place in the tree's order: under the new parent, among its sub-folders by the bytes of their
names, where a folder made there would go.
2.2 `folders.txt` is written once, as `folders.part`, and renamed onto it. No other file and
no folder of the storage is written, renamed or removed.

## 3. What is kept

3.1 Every line's number, id and Ignore, and the header's next number.
3.2 Every item: its id, stored name, file and position; the saved order inside each folder;
the saved brightness and repeat; the internal catalog and its keys; `show.json`; the
previews on the phone.
3.3 No core memory is added: no field of `Core`, `FileInfo` or `Upload`, no host function,
and every new frame stays under 512 bytes.

## 4. The reply

4.1 `{"ok":true,"id":<id>,"moved":true}`.
4.2 When the folder has that path already, in bytes, `{"ok":true,"id":<id>,"moved":false}`,
and nothing is written.

## 5. What follows the move

5.1 The root's playlist and the daily rotation take the new tree's order at their next pick;
the turn in progress goes on, and no file is opened again.
5.2 A moved folder is held when one of its new ancestors is ignored, and is no longer held
when only an old ancestor was; the turn in progress is checked again, as after `ignore` of a
folder.
5.3 When the current playlist is the moved folder or a folder below it, it stays current with
its window; its path in `status` follows at once, and its path in `playlist.txt` is saved at
the next refresh. When a folder moves into the current playlist's subtree or out of it, that
playlist's range follows the tree.
5.4 `file` and `checking` in `status`, `list` and `list in` give the new paths.
5.5 When the board's own Clocks folders play (seed 61, where it is built), a move into or out
of `clocks` or `clocks/message` changes which files are clocks and messages, as a folder made
at the new path would.

## 6. Refusals, in this order

6.1 `bad-argument`: another form, or a path outside the rule of 1.2.
6.2 `show-invalid`: the show is invalid.
6.3 `unsupported`: a host whose storage cannot be changed.
6.4 `busy`: while an upload is open or a rebuild runs.
6.5 `storage-error`: the board could not read its folders in this boot.
6.6 `in-use`: the id of an item of the show, or of an animation or a folder of a drive;
`unknown-id`: an id nothing has.
6.7 `bad-argument`: a move into the folder itself or below it; a folder of the subtree that
would get a path over 93 bytes or more than 3 levels; a file listed in a folder of the subtree
that would get a path over 100 bytes. A file listed at the root for a long path does not
count.
6.8 `"moved":false`: the path is the folder's own path.
6.9 `in-use`: another folder of the new parent has the last name, in bytes or with only the
case of its letters different. A rename of the folder's own name that changes only its case
is taken.
6.10 `unknown-id`: the new parent is not there.
6.11 `storage-error`: `folders.part` cannot be written or renamed; the folders are then as
they were.

## 7. The app

7.1 The menu of a folder's row of the board's own storage gets `Rename…` and `Move to…`,
enabled while the target answers and no change of the list runs. A folder of the card gets
neither.
7.2 `Rename…` opens the dialog of `New folder` with the folder's name in its field, the line
`In Internal /<parent>/` above it, and the new full path under it. The name has the checks of
`New folder` for the board's storage, its siblings' names in any case among them but the
folder's own. `Rename` sends `move internal <id> <parent>/<new name>`.
7.3 `Move to…` opens the chooser of `Move to…` with the board's own storage alone: its root
and each of its folders, without the folder itself and those below it. A destination is
disabled, with its reason, when it is the folder's own parent, when another of its folders
has the folder's name in any case, or when the folder or a file inside would pass the limits
there. The old and the new full path are shown before anything is sent. `Move` sends
`move internal <id> <destination>/<name>`.
7.4 Each name of a path is encoded as `folder make` encodes it.
7.5 On success the app lists the level again; a shown level inside the moved folder follows
it to its new path. A `bad-argument` for the subtree is said as "A folder or an animation
inside would pass the limits of 3 levels or 100 bytes." Other refusals are said in words;
`unknown-command` says that the installation's firmware cannot move folders inside its
storage.
7.6 After a reply that did not arrive, the app lists the levels again and says where the
folder is. It never sends the line again by itself.
7.7 Folders selected and moved with `Move to…` from the board's storage to a destination in
the board's storage are moved by this command, one line for each folder, in place of a job
over their files; the preview, its skips and the report stay. Moves between the storages
and moves of the card's folders stay seed 74's.
7.8 The Controller in a browser and the APK use one code.

## 8. The command tool

8.1 `odrigctl move internal ID PATH` sends the line, each name of the path encoded as for
`folder make`, and prints the reply.

## 9. Documents and delivery

9.1 `docs/commands.md` (the table of commands, "Folders of the board's own storage", the
error codes), `docs/core.md` ("Internal folders"), `docs/emulator.md` for the command tool,
`docs/android-app.md` and its check on a phone, the change log of `docs/decisions.md` with
the owner's approval of 2026-11-09, and entries at the end of `docs/drifts.md`.
9.2 The core, emulator, app, command tool and onboarding suites pass with the new tests, each
seen failing first.
9.3 Firmware images for the installation's board and the spare's module, built as
`firmware/fw.py` builds them, and an APK signed with the persistent key, all built from the
pushed head.
9.4 The owner's check on a phone stays open until the owner reports it, with a folder of the
board's storage that holds an animation: renamed, moved under another folder and back to the
root; the animation keeps its preview, brightness and place in the order and plays on
through each move; a current playlist follows the folder; all of this after a restart too.
