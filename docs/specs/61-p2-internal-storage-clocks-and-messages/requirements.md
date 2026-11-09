# Requirements

Seed 61, `project-seeds/61-p2-internal-storage-clocks-and-messages/seed.md`, with the
owner's answers of 2026-11-09. The core, the emulator's and the firmware's builds of it,
the shared app (the emulator's Controller and the APK), the command tool and the
documents. It builds on the folders of the board's own storage (spec 74, requirement 4.1,
task 7) and on seeds 66 and 67's Clocks-only browsing, all on the branch of pull request
#63. On 2026-11-09 the owner approved the command `clocks storage sd|internal` and the
status member `clock_storage`, and changed the decision of 2026-11-01, "Clocks-only app
browsing and destinations": in Clocks only the app also shows the board's own `clocks/`
and `clocks/message/` and takes uploads into them, as it does the card's.

Words of these files: a *face* is a clock that plays as a break's clock; a *message* is an
animation that plays after a clock; the *Clocks subtree* of a storage is its folder
`clocks` and every folder below it; *both modes* are Between animations and Clocks only.

## 1. The clocks of the board's own storage

1.1 A file of the board's own storage whose folder has the path `clocks` is a face. One
whose folder has the path `clocks/message` is a message. One in any other folder of the
Clocks subtree, such as `clocks/old`, is in the Clocks subtree and is neither. The
folders are the lines of `folders.txt`, and their paths are compared by their bytes, as
the card's folders `clocks` and `clocks/message` are found today.
1.2 A file at the root, a file whose folder has no line, a file of any other folder, and
every file of a boot that cannot read `folders.txt` is never a face or a message,
whatever its name or type. A message is never a face because of its storage, and a face
never a message.
1.3 The class of each file is found when the folders are read: at the start, and after
`folder make internal`, a folder's Ignore, an install or a removal of a file of a folder,
and a prune. No animation body is read for it, and nothing is scanned at a refresh.
1.4 A show without an internal folder `clocks` plays as before: the replies to `list` and
`status`, the walk, the breaks and Clocks only are byte for byte what they are without
this seed, but for the member `clock_storage` that `status` gains (5.3).
1.5 Nothing is migrated: flat shows, their names, ids, catalogs, saved order, playlist,
repeats, brightness, Ignore and mapping are kept, and no file is rewritten to recognize a
clock. Firmware updates and show installs keep `folders.txt`, the folders and their files
(the firmware tool's guard of spec 74).

## 2. Between animations

2.1 While the clocks are on, in either mode, every playlist passes over the internal
Clocks subtree as it passes over the card's: the root's walk, an internal folder's
playlist and the first animation of a playlist skip its files, and an internal folder
whose every file is in it has nothing to play, so the root plays in its place. While the
clocks are off its files and folders play as any other.
2.2 A break's clock is drawn from one bag of the eligible faces of both storages, and its
message from one bag of the eligible messages of both storages. Each bag gives every
candidate a turn before it is drawn again; drawing a message takes no place in the bag of
faces; a message plays one complete loop, however long.
2.3 A card face followed by an internal message, and an internal face followed by a card
message, play as a break of one storage does.
2.4 Without a card, internal faces give the breaks and internal messages follow them.
With a read-only or missing card, internal messages still play.
2.5 Without an eligible face in either storage no break comes, as today, whatever messages
there are: the playlist goes on.

## 3. Clocks only

3.1 Only plays the faces and messages of both storages through the same two bags: a
clock, a complete message when the message is on, then the next clock.
3.2 With an eligible internal face, Only plays without a card. Without an eligible face in
either storage, Only stays selected, dark and responsive, and `clock_only.state` says why.
Without an internal Clocks folder the states are today's, in today's order: `no-card`
without a card, else `missing-folder` without the card's Clocks folder, else `no-clocks`
while nothing plays, else `playing`. With an internal Clocks folder they are `playing`
while something plays, else `no-clocks`. No ordinary animation and no message stands in
for a face.
3.3 The internal Clocks subtree is inside the boundary at every entry point:
- `play <id>` of one of its files plays it as a manual turn, also when it is ignored or
  held, and a message also while messages are off;
- `play <id>` of one of its folders plays the first available file of that folder's
  subtree, then the program goes on; of a folder with none, it restarts Clocks;
- `play <id>` of the internal Clocks folder restarts Clocks, as of the card's;
- automatic next, restart, resume, and the clean-up after a storage, catalog, Ignore,
  removal or quarantine change, keep playback inside the boundary of both storages. An
  Ignore of an internal file or folder, and a fault of an internal file, are taken as the
  card's are: an automatic turn that no longer plays ends at once, a manual turn goes on,
  and a dark Only starts a clock as soon as a face plays again.
A file or folder of the board's own storage outside it is refused `in-use`, as the card's
are, and `play all` stays refused.
3.4 `status` in Only: `clock_only.folder`, and `playing` while a turn plays, name the
card's Clocks folder when the card has one, else the internal one; `playlist` is
`clocks`. `file` gives an internal file's path, `clocks/message/<name>`, and `animation`
its id, which is 60,000 or less, so a client tells the storage by the id.
3.5 Leaving Only restores ordinary playback by the existing rules.
3.6 What this seed leaves as it is: the LEDs' On and Off, by hand or by the daily schedule
of seed 64, which hide the LEDs while the turns of both storages' clocks go on unseen; the
output's rotation; the display tests, still refused `in-use` in Only; and every Clocks
rule of seeds 54 and 59 for the card.

## 4. Copies in both storages

4.1 A file of the card and a file of the board's own storage are *copies* of one another
when they have the same class, face or message, the same file name with its extension,
compared without the case of ASCII letters, so the same path `clocks/<name>` or
`clocks/message/<name>`, and the same type the catalog or the check gives, frames, text or
widget. The same name with another type, the same name in another folder, the same type
under another name, and a file whose type is not known yet are no copies: each stays a
candidate of its own.
4.2 Copies make one automatic candidate, also when their bytes differ. With `SD card`
preferred the card's copy plays when it is eligible; with `Internal storage` preferred the
board's copy plays when it is eligible.
4.3 Each copy's eligibility is judged first, by its own storage's rules: listed and
readable, not ignored by its own or an inherited Ignore, not quarantined or unavailable.
A preferred copy that is not eligible gives its turn to the other copy when that one is
eligible. A copy that is not eligible is never chosen.
4.4 Each copy keeps its own id for manual play, `read`, edits, brightness, repeats,
Ignore, quarantine and removal: the preference never makes a command reach the other
storage's file. Nothing is removed, replaced, synchronized or renamed to settle copies.
4.5 Copies are worked out at each draw from what the core already holds, the card's index
rows and the show's file table: no animation body is read, and no mark of a copy is read
outside the draw that wrote it. A card put in or pulled out, a catalog refresh, a restart,
an install, a removal, an Ignore or a quarantine is taken at the next draw, with no stale
choice, no duplicate turn and no turn outside the boundary. The copy that plays takes its
own saved brightness.

## 5. The preferred storage

5.1 `clocks storage sd` and `clocks storage internal` choose the preferred storage for
copies, and answer `{"ok":true}` once the choice is saved; a choice already in force writes
nothing and answers the same.
5.2 Refusals, nothing changed: `bad-argument` for another form; `show-invalid` while the
show is invalid; `busy` until the player has read every installed animation after a
start, while an upload is open and while a rebuild runs; `storage-error` when the board's
storage cannot be changed, when the file could not be written or read back, and while the
saved clock settings are unreadable, until a mode line establishes them.
5.3 `status` reports `"clock_storage":"sd"` or `"clock_storage":"internal"`, the choice in
force, after `clock_mode`, also outside the clock modes. Every client sees the
installation's value. Every reply of `status` still fits its 1,024 bytes: the longest,
991 bytes and the newline today, grows by at most 27 to 1,019.
5.4 The choice is kept in `clocks.txt` with the mode and the message, through
`clocks.part`, read back and renamed, as they are. A file without it, of version 1 or 2,
and no file at all, mean `SD card`. A saved `SD card` writes version 2 byte for byte, so
an older firmware keeps reading it; `Internal storage` writes version 3, whose fourth line
is `storage internal`. It is kept across restarts, reconnections, firmware updates and
show installs.
5.5 A change takes effect at the next draw of either bag. The turn in progress plays to
its end, a message its complete loop. No catalog is rebuilt and no file of either storage
is rewritten.
5.6 The choice applies to faces and messages in both modes and to nothing else: ordinary
playlists, explicit play of a file of one storage, and every other command are unchanged.
It decides which copy plays, never whether a storage is used.

## 6. The app

6.1 The Settings panel `Clocks` gets one dropdown under the mode's, labelled `Preferred
storage for matching clock/message files`, with the explanation `Applies when the same
relative path and file type exist in both storages.` and exactly two options, `SD card`
and `Internal storage`, which send `clocks storage sd` and `clocks storage internal`. It is
a control of its own, apart from Off, Between animations and Clocks only.
6.2 It follows the target's `clock_storage` as the mode's dropdown follows `clock_mode`:
disabled while a change is sent; `Saved: matching files play from the SD card.` or
`Saved: matching files play from internal storage.` only after a status confirms the
value; a refusal explained, with
the value in force shown; a lost reply said unconfirmed until a status shows the value; a
different reported value shown as such; pending state cleared by a change of target. It is
disabled while the saved clock settings are unreadable.
6.3 A target whose status has no `clock_storage`, an older firmware, shows it disabled at
`SD card`, with the words `This target plays the card's clocks and messages only. Update
its firmware to use those of the board's own storage.`
6.4 The panel's other words name both storages: Clocks only plays the clocks folders, and
the waiting reasons of `clock_only.state` say which storages were looked in.
6.5 In Clocks only, on a target that reports `clock_storage`, the app's boundary holds the
Clocks subtrees of both storages. It shows the board's own `clocks`, `clocks/message` and
their sub-folders, plays inside them, and takes uploads into them as into the card's. When
both storages have a Clocks folder, the Clocks level shows the two, each named by its
storage, and Back stops there; when one has it, its Clocks folder is the Clocks level, as
today. Folders outside stay out of sight, the board's own root takes no upload in Only, and
Settings, Target and leaving the mode stay available. Every way of uploading keeps that
rule alike: the single upload, the archive of seed 73 and the batch of seed 80, each
offering in Only only the storage of the folder explored, and the preview of seed 79
keeping the upload's place as for any folder. A target without `clock_storage` keeps
today's card-only boundary and today's words.
6.6 The bar of the animation playing now and the brightness screen's line of the
animation name the storage of a file of a Clocks subtree, as `Internal
/clocks/message/v7-the-time.odrgx` or `External /clocks/analog.odrgx`, told by its id.

## 7. The command tool and the emulator

7.1 The command tool sends `clocks storage sd` and `clocks storage internal`, and refuses
another word after `storage` as a usage error.
7.2 The emulator gives the same replies over its serial port, TCP and HTTP, and keeps the
choice in its show folder's `clocks.txt` across a restart.

## 8. Memory and bounds

8.1 The core's memory does not grow: every figure of the memory table of `docs/core.md`
stays as it is; `sizeof(Core)` stays 3,792 bytes on the test host and 3,592 on the board,
`FileInfo` 48 and `Upload` 72; no block, host function, table or cache is added, and
nothing is allocated after the start.
8.2 A draw looks at the show's file table in memory, and reads the card's index rows of the
one folder of its class at most once, only after it drew a file of the board's own storage
while `SD card` is preferred. Its marks of copies take a bit of each file that is there
already, so they hold for a show of any number of items. Every new stack frame stays under
the 512 bytes the build checks.

## 9. The seven messages

9.1 The seven approved widgets, the files `v7-consciousness.odrgx`, `v7-symmetry.odrgx`,
`v7-temperature.odrgx`, `v7-the-time.odrgx`, `v7-countdown.odrgx`, `v7-the-clock.odrgx`
and `v7-mistakes.odrgx` of `collection/card/clocks/message/`, 79,235 bytes, exactly as
tracked, are to be put into the board's own `clocks/message/` with the project's tools
(`odrigctl` and `firmware/fw.py`): the free space read first and weighed against the
files, the two folders, the catalog's records and an upload's staging, the board's content
kept,
each file read back and compared byte for byte by its SHA-256 with the tracked file, the
catalog's state recorded, and the messages seen chosen in both modes.
9.2 No board is connected to the computer this seed is built on. The deployment is
rehearsed on the emulator by a test of the suite, and prepared for the board session as
exact commands. The board session itself stays open for the owner. A rehearsal on the
emulator, a copy in the collection, an archive and a copy on the NAS are never reported
as a deployment.
9.3 The board session keeps the board's protections: one client of the board at a time,
the flash never erased, a brightness of 40 or less, and no change of wiring, power, Wi-Fi,
display or current limit. If access, space or a person-only step stops it, the board's
content is kept and the step not done is named.

## 10. Delivery

10.1 A firmware image for the installation's board (`odrig_microsd`, N16R8) and one for
the spare's (`odrig_microsd_n8r2`), each passing `verify_build.py` for its module, and an
APK signed with the persistent key, all built from the pushed head with a clean tree, with
their bytes and SHA-256 in `verification.md`. Flashing installs no message: the seven are
put in by the board session of 9.1.
10.2 Left open for the owner, named in `verification.md` and told in words: the board
session of 9.1; the LED check of a card face followed by an internal message in both modes,
and of both preferences with a copy; the phone check of the dropdown, its persistence
across a restart of the board, and of Clocks only showing and uploading into the board's
own Clocks folders.
