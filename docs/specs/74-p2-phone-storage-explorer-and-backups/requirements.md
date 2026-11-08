# Requirements

Seed 74, `project-seeds/74-p2-phone-storage-explorer-and-backups/seed.md`. The core,
the emulator's host, the firmware's host, the Python library's catalog reader, the
shared app (the emulator's Controller and the APK), the command tool and the
documents. The owner approved the new commands in advance on 2026-11-06; each is
recorded in `docs/commands.md` and the change log of `docs/decisions.md` when it is
built. The work is delivered in two parts: part A gives the card real folders and moves
single files between the two storages, which is what clocks and messages need; part B
gives the rest of the seed.

## Part A: folders on the card, and moves of files

### 1. A folder made on the card

1.1 `folder make external <path>` makes the folder `<path>` in the card's folder
`odrig` and adds it to the card's index, so that `list` and `list in` show it at once,
with `files` 0, while it is empty, and after a restart or a replug as long as the index
stands.
1.2 `<path>` is written as `upload begin external` writes a path: decoded once from
URI escapes, one to three folder names joined by `/`, at most 100 bytes in all, each
name under the drive's naming rule; a name that ends in `.odrg` or `.odrgx`, in any
case, is refused. Its parent is the root or a folder the index has.
1.3 The reply is `{"ok":true,"id":<id>,"made":true}`, with the id the index gave the
folder. A folder the index already has at that path answers
`{"ok":true,"id":<id>,"made":false}` and writes nothing, so that a client may send the
line again after a reply that did not arrive.
1.4 Refusals: `bad-argument` for another form, a path outside the rule or a missing
parent; `unknown-id` for a parent the index does not have; `in-use` for a file of the
index at that path; `busy` while an upload is open, a rebuild runs or the card's catalog
is read; `read-only` while the core may not write the card; `no-space` when the index
has no free id; `storage-error` when the folder or the catalog could not be written;
`unsupported` for `internal` until part B, and for a host that cannot make folders;
`show-invalid` while the show is invalid.
1.5 A failure before the catalog's commit leaves the index as it was. A folder made on
the card whose commit failed is not listed, and making it again lists it.
1.6 An empty folder is a playlist with nothing to play: `play <id>` of it and a walk
through it behave as for a folder whose files are all ignored. Uploading a file into it
works as into any folder, and the file becomes its first.
1.7 The removal of the last file of a folder takes the folder out of the index only
when the folder has no sub-folder either, as today.
1.8 The Python library reads an index with empty folders as sound, and its writers keep
making indexes without them.

### 2. What is saved for an animation

2.1 `saved <id>` reports, for an animation of the show or of the card:
`{"ok":true,"brightness":<n|null>,"repeat":<n|null>,"start":<bool>}`: its saved
brightness, its saved repeat and whether it is the show's `start` item.
2.2 Refusals: `unknown-id`, `in-use` for a cycle or a folder, `busy` while the saved
repeats cannot be read yet, `show-invalid`.

### 3. The explorer in the app

3.1 Every row of a file names its storage, `Internal` or `External`, and its full path
from the storage's folder. The selection mode selects files of both storages at the
level shown, as many as the level has; `Select all shown` takes only the rows the
filters show; `Clear selection` empties it. A summary says how many files are selected
and in which storage.
3.2 At a level of the card that the core may write, `New folder` and `New playlist
folder` ask for a name and make that folder there with `folder make external`. Both
make the same real folder: every folder of the card is a playlist. Neither plays
anything nor changes the playlist that plays. A target that answers `unknown-command`
is told that its firmware cannot make folders.
3.3 `Move to…` moves the selected files. Its chooser names the destination storage and
folder in full; the card is offered only while it is present and writable, with the
reason when it is not. Before anything is sent it shows each file's new full path,
the files skipped and why.
3.4 A file whose name the destination already has is skipped unless the operator gives
it another valid name in the preview. Nothing is replaced, merged or renamed silently.
A name that the internal storage's rule does not allow must be renamed for it.
3.5 Each file is moved by the app as one recorded job: its bytes read with `read` and
checked against its size and CRC-32; uploaded to the destination with the absence
guard; its own ignore choice, saved brightness and saved repeat given to the new file;
the old file's saved brightness and repeat removed; then the old file removed, after
the app checked that its id still names the same path and size. The source is never
removed before the destination answered `upload end` with success.
3.6 A move is refused before anything is sent when the file is listed by a cycle, is
the show's `start`, or is named by another item of the show, saying why.
3.7 Progress shows the file and its bytes, `Stop` ends the run after the file under way
reaches a safe point, and the end says what was moved, skipped, failed and left
unstarted. A run is stopped by a change of target and waits while the app is hidden.
3.8 The job is kept on the phone until it is done. After a lost reply, a lost link or a
restart of the app, the app finds it again for the same target: with the new file in
place and the old one still there, it finishes the job; with the new file absent, the
old one is untouched and the job ends as not moved. It never sends a removal for a file
whose path or size is not the recorded one.
3.9 Moves inside one storage of a single file use the same job in part A.

## Part B: the rest of the seed

### 4. Folders inside the board's own storage

4.1 The internal storage gets real folders, with the card's path rule: an item of the
show may name a path of at most three folders and 100 bytes. Flat shows stay valid and
keep their ids. `folder make internal <path>` makes one; `list` and `list in` give the
internal folders as the card's are given.
4.2 Clocks and messages stay those of the card, as today; seed 61 decides internal
clocks.

### 5. Moves of folders, and moves inside the card by renaming

5.1 `move external <id> <path>` moves a file of the card, or a folder with its subtree,
to another folder of the card by renaming, in one commit of the card's catalog, keeping
its ids, its order inside a folder, and its saved settings; the moved entries go last in
the destination. A folder is never moved into itself or below itself.
5.2 Moves of folders between the storages are jobs of the app over the subtree's files,
the destination folders made first.

### 6. Downloads and backups

6.1 `read <id> <offset> <count>` reads up to 720 bytes at a time: a reply holds 1,024
bytes, and the reply's frame around the data, with a size of 10 digits, leaves room for
737.
6.2 `Download` saves one file's original bytes under its name; `Download selected`
saves one ZIP of the selection of one storage, relative to the level shown, with a
manifest `odrig-backup.json` of version 1: `sourceStorage`, `base`, and for each file
its full path, size, CRC-32, saved settings and outcome. A partial backup says so.

### 7. Delivery

7.1 Each part is delivered as a firmware image for the installation's board and the
spare's, and an APK signed with the persistent key, all built from the pushed head.
