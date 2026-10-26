# Requirements: sub-folder playlists from the card

Seed: [`project-seeds/41-p1-sub-folder-playlists-from-the-card/seed.md`](../../../project-seeds/41-p1-sub-folder-playlists-from-the-card/seed.md).

The sub-folders of the card's folder `odrig` are playlists of their own, the folder
`odrig` itself the root playlist, and an operator picks one from the app as the playlist
that plays now; a playlist repeats for 24 hours of the board's running time, then the
next one starts. The owner asked that this spec be written without a question pass:
every decision is in the seed's constraints and in "The Owner's Answers", and where a
requirement decides a point the seed leaves open, the decision is recorded in
[drifts.md](../../drifts.md) under "Seed 41". The owner's acceptance of the seed is the
owner's word on the two additions to replies and on the change of the playlist decision
in `docs/decisions.md`.

In this document "the card" is the external storage, a microSD card or, in the USB
build, a stick, and "the drive" the core's view of it; "a folder" is a sub-folder of
the card's folder `odrig` at any depth, and "the root" the folder `odrig` itself; "a
path" is a file's or folder's name from `odrig`, the parts joined by `/`; "a playlist" is
the root or a folder with what it plays; "the current playlist" is the one that plays
now; "a window" is the 24 hours of running time a current playlist has; "the tree" is
the root and its folders in the depth-first order of the listing; "a turn" is as
`docs/show.md` defines it; "the saved order" is `order.txt`; "the test host" is
`core/build/odrig_host`; "the PC tool" is `python3 -m odrig.catalog`.

## Requirement 1: the tree and the listing

1. The root playlist SHALL hold the board's own included animations and the loose files
   of `odrig`, in the saved order, as the playlist does today, and after them the
   playlists of the sub-folders of `odrig`. A folder's playlist SHALL hold the animation
   files directly in it, in the saved order, and after them the playlists of its own
   sub-folders. The board's own animations SHALL belong to the root only.
2. Every lister of the drive, the firmware's, the emulator's `--drive` folder's, the test
   host's and the PC tool's, SHALL list a folder as its animation files by the bytes of
   their names, then its sub-folders by the bytes of their names, each sub-folder listed
   the same way: depth first. The animation files are those whose names end in `.odrg`
   or `.odrgx` in any case and do not begin with a dot, as today.
3. A lister SHALL pass over a folder deeper than three levels below `odrig`, a folder
   whose name does not keep requirement 2.2, a folder whose name starts with a dot, and
   `System Volume Information`. A folder without an animation file at any depth below it
   SHALL be no playlist: it is passed over and is not listed.
4. The 256 files of a card SHALL be counted over all folders together and be the first
   256 in the listing's order; at most 32 sub-folders SHALL be taken, the root beside
   them. Every lister SHALL count the sub-folders the same way: a folder is counted, with
   each of its ancestors not yet counted, when the first file at or below it is kept, and
   when a file's folder would be counted past the 32nd that file and every later file of
   the walk are passed over. The files after the 256th are passed over the same way, so
   that a catalog never names them.
5. Nothing logs a passed-over file today, and the emulator, the test host and the PC tool
   SHALL pass over silently, as today. The firmware's line at a listing SHALL say what it
   took and what it passed over: `card opened: <n> animation files in odrig` as today for
   a card without folders when nothing was passed over, else `card opened: <n> animation
   files in <m> folders of odrig` with `; <k> files and <f> folders passed over` added when
   anything was.
6. The core SHALL keep the tree in the listing's order whatever order a cataloged card's
   places come in from its pages, by putting its folders in order one level of the path at
   a time: a folder before the folders below it, and siblings by the bytes of their names;
   not by the bytes of the whole paths. A place whose folder would be the 33rd sub-folder,
   which only a catalog's pages can name since every lister cuts at 32, SHALL be left out
   with the reason `too-many-folders`.

## Requirement 2: names

1. A file in a folder SHALL be named by its path from `odrig`, the folder names and the
   file name joined by `/`, everywhere a name goes today: `drive_name` and the host's
   `drive/<name>`, the `x` entries of the saved order, the catalog's entries, and `file`
   in `list`. Two files with the same name in two folders SHALL be two animations.
2. A folder's name SHALL be 1 to 100 bytes of printable ASCII other than
   `/ \ : * ? " < > |`, neither beginning nor ending with a space or a dot; it MAY be
   digits alone. The file part of a path SHALL keep the whole rule of a drive file name
   today, the ending `.odrg` or `.odrgx` included. The whole path SHALL keep the limits of
   today: 100 bytes for the host and 127 bytes in the saved order and in `list`.
3. The catalog format SHALL stay version 1, with its name rule widened to the path and the
   page of an entry chosen by the hash of the whole path; the PC tool SHALL write the
   same bytes as the core from the same card. A card cataloged before this seed whose
   files are all loose SHALL read as before; folders added to such a card SHALL hold
   animations once `catalog rebuild external` or the PC tool's `import` has run, as a
   copied file does today. A reader from before this seed SHALL find a catalog that names
   a file in a folder `damaged`, by its name rule; the version is not raised for that.

## Requirement 3: exhausting

1. A playlist SHALL play its own items first, each for one turn under the turn rule of
   today, in the saved order; then each of its sub-playlists in order, each exhausted once
   the same way, depth first; then start again with its own items.
2. A file that is left out, unavailable or being checked SHALL be passed over, as today;
   an ignored animation of the board SHALL be passed over, as today.
3. After a jump by `play <id>` to an animation that is an item of the current playlist or
   of one of its sub-playlists at any depth, the current playlist SHALL go on with the
   animation after the jumped one in its exhausting order; after a jump to any other
   animation, with the animation whose turn the jump cut, from its first frame.

## Requirement 4: the current playlist and its window

1. Exactly one playlist SHALL be current, named by its path, the root by none. It becomes
   current by `play <id>` of a folder's id, by `play all` for the root, at power-on from
   the saved choice, or by the end of the window of the playlist before it.
2. A current playlist SHALL play, repeating, for a window of 24 hours of the board's
   running time from the moment it became current, the time the LEDs are off and the time
   a cycle or a jump plays included. The length of the window SHALL be a constant of the
   core. The window SHALL count running time only; calendar time is never considered.
3. When the window has passed, the turn in progress SHALL end as it would, and the next
   playlist in the tree's order SHALL become current with a window of its own, the root
   after the last. A window that ends while a cycle plays SHALL change which playlist is
   current and not what plays; the cycle goes on until a command ends it. A window that
   ends while a mapping test shows SHALL be taken when the test ends. When the window ends
   while the tree is not known, the card out or not yet read, the root SHALL become
   current with a fresh window. With no folder on the card the root is the only playlist
   and its window changes nothing that plays.
4. The core SHALL keep the current playlist's path and the time spent in its window in a
   file of its own in the board's storage beside `order.txt`, written as `order.txt` is
   written, when the current playlist changes and at most once in 15 minutes while it
   plays. The choice SHALL be saved the moment it is made, by a command or by the
   rotation.
5. At power-on the saved playlist SHALL be current with the saved time spent: the root
   plays from the animation `start` names or else from its first, as today; a folder
   plays from its first animation. When nothing is saved the root is current. A cycle
   named as `start` plays as today. A restart loses at most the last 15 minutes of the
   window.
6. The choice and its window SHALL be kept whatever the card does. While the current
   playlist has nothing it can play, the card out or not yet read, or every file of the
   folder and of the folders below it unavailable, the root SHALL play in its place, the
   board's own animations when the card is out; the current playlist takes over at the
   end of the turn in progress as soon as it has something to play. This holds at
   power-on, while the card is not yet read.
7. Only a card that is in and read and has no playlist of the saved path SHALL give the
   root the current place, with a fresh window, saved; so SHALL the removal of the
   current folder's last file while the card is in.

## Requirement 5: commands and replies

1. No command SHALL be added and no error code SHALL be added. `play <id>` of a folder's
   id SHALL make that folder's playlist current from its first animation with a fresh
   window, on the current folder too; `play all` SHALL do the same for the root. `play
   <id>` of an animation SHALL be a jump as today, under 3.3.
2. Folders SHALL have ids from the pool of the card's files, 60001 up, given after the
   card's files in the tree's order, so that the files keep the ids they have today; a
   card's ids go with its places, and while the card is out `play <id>` of a folder's id
   SHALL be refused with `unknown-id`, as of any id of a card that is out.
3. `list` SHALL give the folders as items after the show's items and before the card's
   files, in the tree's order, each as `{"id": <id>, "playlist": "<path>", "external":
   true}`, counted in the positions of `<from>` and `next`; a file's folder is read from
   its path in `file`.
4. `status` SHALL report `playing` as the current folder's id while the card is in and
   holds that folder, else `"all"` for the root, beside its values of today, and SHALL
   gain `left`, the whole seconds left in the current playlist's window, reported whatever
   the tree.
5. `ignore` SHALL work on the board's animations only, as today. `order move` SHALL move
   an animation within the saved order as today, so that a folder's files keep their
   relative order from it. `upload begin external` SHALL take a bare file name, a
   `<file>` with `/` refused with `bad-argument`, and put the file in `odrig` itself; the
   board makes and removes no folder. `remove` of a file in a folder SHALL remove that
   file, under the rules of a card file today. `catalog rebuild external` SHALL walk the
   sub-folders as the listing says.
6. `docs/commands.md`'s sentence that what `play` changes is not kept across a restart
   SHALL give way to the kept choice.

## Requirement 6: the hosts

1. The firmware SHALL list the folders of `/sd/odrig` depth first in the one call of
   `drive_list`, within the 250 ms of a card read, as the flat listing is today, and
   build the path of a file under `odrig` from its name; its name table SHALL not be
   enlarged. The USB build's drive code is the same code and gets the same behaviour. The
   line of this seed SHALL go into `docs/firmware-additions.md` in the same commit.
2. The emulator's `--drive` folder SHALL list sub-folders of `DIR/odrig` the same way, and
   open, remove and write files by their paths under `odrig`; it writes a file at the root
   only, as the board does.
3. The test host SHALL list sub-folders of its drive folder the same way, and SHALL allow
   the names of the core's new file beside `order.txt`.
4. The PC tool SHALL list sub-folders the same way in `import`, `check` and `status`, and
   SHALL write the same bytes as the core.
5. A legacy card, one without a catalog, SHALL be listed with its folders the same way.

## Requirement 7: the app

1. The Animations tab SHALL show the list as groups in the order they play: the root's
   group first, under the heading `Root` with the count of its rows, then one group per
   folder in the tree's order, each heading carrying the folder's whole path and the
   count of the files directly in it. The groups SHALL not be indented and SHALL not
   fold. A folder with no file directly in it SHALL keep its heading, its count `0` and
   its button. A group that has rows and none of which the filters show SHALL not be
   shown, heading included.
2. Every group, the root's included, SHALL have the button `Play this folder`: a folder's
   sends `play <id>` of the folder, the root's sends `play all`. The button `Playlist
   from the start` of seed 36 SHALL go.
3. The pinned Tests group of seed 36 SHALL stay above the list, outside the folder
   groups: no playlist, no button, no mark and no count of this seed, and the filters
   leave it alone.
4. The now-playing line SHALL read `Playlist night · 23 h 12 min left` for a current
   folder, by its path, or by its id while the list has no item of it; `Playlist · 23 h
   12 min left` for the root while the list holds a folder group; `Playlist` without a
   time while `playing` is `"all"` and the list holds no folder group; and `Playlist
   night, the root plays for now · 23 h 12 min left` while the root plays in the current
   folder's place, which the app knows from `status`: `playing` a folder's id and
   `animation` no file of that folder nor of a folder below it, read from the paths. A
   jump by `play <id>` to an animation outside the current playlist shows the same words
   for its turn. The hours and minutes come from `left`.
5. The current playlist's group SHALL be marked, the root's group when the root is
   current; while the root plays in a folder's place the folder's group keeps the mark.
6. The filters of seed 39 SHALL work within the groups; dragging and the menu's moves
   SHALL work within one group and not across groups; selection for deletion and the
   counts of animations SHALL take rows only, a folder item being no animation; uploads
   SHALL go to the root.
7. The app's validators SHALL accept a `list` item with `playlist` and `status` with
   `left` and with a folder's id in `playing`. The APK, the browser and the emulator's
   Controller view run the same files.

## Requirement 8: the documents

1. `docs/show.md` SHALL describe the tree, the listing, the exhausting, the window, the
   saved file and the kept choice; `docs/commands.md` the folder items of `list`, `left`
   and `playing` of `status`, `play` of a folder, the paths, and the kept choice;
   `docs/core.md` the saved file, the host's listing and the memory; `docs/catalog.md`
   the paths and what an older reader finds; `docs/microsd.md` how a card is prepared
   with folders; `docs/firmware.md` and `docs/emulator.md` the listing of a drive's
   folders; `docs/android-app.md` the groups, the button, the line and the mark;
   `agent/vocabulary.md` the playlist; `docs/firmware-additions.md` the seed's line.
2. The last task that needs neither the board nor a phone SHALL add the dated line to
   `docs/decisions.md`'s change log that records the owner's ruling of 2026-10-26: beside
   `A show plays its included animations in turn by itself`, which stays, a folder's
   playlist plays its folder alone for its window, and the saved order names a card file
   by its path. Every question decided on the way, in the design or in a task, SHALL be
   recorded at the end of `docs/drifts.md` under "Seed 41".

## Requirement 9: memory and budgets

1. The core's memory SHALL stay within its budget of today, 131,072 bytes with a drive,
   and the core object within 4,096 bytes: the folder of a place is found from its name,
   no host member giving it, and the core MAY keep each place's folder index; that index,
   the folders' table and the window's state fit in what the budget leaves.
   `tests/core/test_drive.py`, which asserts the drive's blocks to the byte, and the
   memory table of `docs/core.md` change with them, as the suite measures.
2. The core SHALL take no memory after `odrig_core_begin` and SHALL not call itself; a
   walk of the tree is iterative.
3. `status` SHALL stay within one reply of 1,024 bytes; a `list` page SHALL stay within
   1,024 bytes with folder items in it.

## Requirement 10: tests and delivery

1. The core's suite SHALL check, with the test host and its timestamps, a card of nested
   folders: the tree and its order on a legacy card and on a cataloged one; the
   exhausting of the root and of a folder; `play <id>` of a folder and of an animation
   inside and outside the current playlist; the window passing at 24 hours with the turn
   in progress ending first; the rotation to the next playlist and to the root after the
   last; a cycle and a mapping test at the window's end; the saved file written at a
   change and after 15 minutes and read at a restart; the root in place of a playlist
   with nothing to play; the card pulled and put back with the window kept; a card
   without the saved folder; the paths in the saved order, in `list` and in the catalog;
   the limits of depth, folders and files; and the memory within its budget.
2. The emulator's suite SHALL check the folders of `--drive` and the replies. The Python
   library's suite, `tests/converter/`, SHALL check the PC tool's `import`, `check` and
   `status` on a card with sub-folders; the core's `test_catalog_*` SHALL check that the
   core and the PC tool write the same bytes from such a card; `tests/vectors/catalog/`
   SHALL gain a storage with folders and its outcome in `cases.json`.
3. The firmware's suite SHALL check the depth-first listing of folders on the Mac with
   the stand-in card.
4. The app's suite SHALL check, in Chrome against the emulator, the groups, the headings
   and counts, the root's group and its button, the current playlist's mark and time
   left, `Play this folder` on a folder and on the root, the line while the root plays in
   place, the filters, moves within a group only, the Tests group left alone, and the
   card out and in.
5. Every suite that runs without a board and without a phone SHALL pass; the microSD
   firmware SHALL be built with `python3 firmware/fw.py build`, and the APK with
   `python3 app/app.py build` from the same commit.
6. Left to the owner, in a session with the board and a card prepared with sub-folders:
   the groups on a phone, a folder chosen there and playing, the board restarted and
   playing the same folder, the root chosen and playing, the card out and in, the time
   between `card mounted` and `card opened` noted for a card with 32 sub-folders and 256
   files, the time left counting down in the app, and the APK on the owner's phone. The
   24-hour rotation is checked in the core's suite only.
