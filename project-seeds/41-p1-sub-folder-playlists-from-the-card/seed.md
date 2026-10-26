# Sub-folder playlists from the card

## Summary

The sub-folders of the card's folder `odrig` become playlists of their own. Each one
holds the animations of its folder and, after them, the playlists of its own sub-folders.
The folder `odrig` itself is the root playlist: the board's own animations and the card's
loose files, as the playlist is today, and after them the sub-folders. An operator picks
any folder as the playlist that plays now, from the Animations tab of the operators' app,
which the owner calls the Playlist screen. A playlist repeats for 24 hours of the board's
running time and then the next one starts, so a card laid out as folders plays a different
folder each day. The core keeps the playlists and the 24 hours, the firmware and the
emulator list the card's folders, and the app shows the folders and lets one be chosen.

## Priority

- `P1`

## Depends On

- Seed 20, for the drive: its places, the ids from 60001, the playlist that mixes the
  board's animations with the drive's, and the log of files left out.
- Seed 35, for the catalogs, which name the card's files and give a cataloged card its
  places, and for `catalog rebuild external` and the PC tool `odrig.catalog`.
- Seed 36, for the Animations tab, its one list in the saved order, `Playlist from the
  start`, and the saved order `order.txt` that names the card's files.
- Seed 38, for the microSD card, the firmware that reads it, and the emulator's `--drive`
  folder that stands for it.
- Seeds 29, 32, 37 and 39, for what stays as it is: `ignored` on the board's animations
  only, the quarantine of a faulty file, the passes of a text, and the app's filters.

## Product Context

On 2026-10-26 the owner asked for sub-folders on the card as playlists. The owner's words:
the Playlist screen gets an option of sub-folders, and a specific sub-folder can be
selected from the app as the playlist that plays now; the structure of the animation
sub-folders on the card dictates these sub-playlists; a playlist repeats for 24 hours only,
and afterwards the next sub-playlist starts; when a parent playlist is played, all of its
items that are not in sub-folders are exhausted first, and then its sub-folders start to
get exhausted. The seed was to cover the firmware changes and the app changes, and to be
ready for its spec with no open question.

The installation plays for days. Today the card is one flat folder, every file of it in
one playlist, and the only way to play a different set is to change the card. With
folders, an operator prepares the card once, a folder for each theme or day, and the
board walks through them by itself, a day each; and at any time an operator can put a
folder on with one tap.

## Technical Constraints

- **The tree.** The root playlist is the folder `odrig` of the card: its items are the
  board's own included animations and the loose files of `odrig`, in the saved order, as
  the playlist is today. Each sub-folder of `odrig` is a playlist whose items are the
  animation files directly in it, in the saved order, and whose sub-playlists are its own
  sub-folders. The board's own animations belong to the root playlist only. A folder
  without an animation file at any depth below it is no playlist: it is passed over, and
  the app does not show it. A folder is also passed over, and logged as a file passed over
  is today, when it lies deeper than three levels below `odrig`, when its name does not
  keep the rule below, when its name starts with a dot, and when it is `System Volume
  Information`.
- **The listing.** A folder is listed as its animation files by the bytes of their names,
  then its sub-folders by the bytes of their names, each listed the same way: depth first.
  The firmware, the emulator's `--drive` folder, the core's test host and the PC tool
  `odrig.catalog` all list so. The 256 files of a card are counted over all folders
  together and are the first 256 in that order; at most 32 sub-folders are taken, the
  first 32 in that order, the root beside them; the files after the 256th and the files of
  any sub-folder after the 32nd are passed over and logged, as the 257th file is today, so
  a catalog never names them. The tree keeps that order whatever order a cataloged card's
  places come in from its pages: the core puts its folders in the listing's order,
  comparing paths one level at a time, a folder before the folders below it and siblings
  by the bytes of their names, not by the bytes of the whole paths, since a space and `-`
  sort before `/`.
- **Names.** A file in a sub-folder is named by its path from `odrig`, the folder names
  and the file name joined by `/`, for example `night/comet.odrg`. That path is the file's
  name everywhere a name goes today: `drive_name` and the host's `drive/<name>`, the `x`
  entries of `order.txt`, the catalog's entries, and `file` in `list`. A folder's name is
  1 to 100 bytes of printable ASCII other than `/ \ : * ? " < > |`, neither beginning nor
  ending with a space or a dot, and may be digits alone, since the path is not; the file
  part keeps the whole rule of today, the ending `.odrg` or `.odrgx` included. The whole
  path keeps the length limits of today: 100 bytes for the host, 127 in `order.txt` and
  `list`. Two files with the same name in two folders are two animations. The catalog
  format stays version 1 with its name rule widened to the path, the page of an entry
  chosen by the hash of the path, and `odrig.catalog` in Python writes the same bytes as
  the core from the same card. A card cataloged before this seed, whose files are all
  loose, reads as before; folders added to it hold animations once `catalog rebuild
  external`, from the app's Settings, or the PC tool's `import` has run, as a copied file
  does today. A reader from before this seed, the core of a board not yet flashed or the
  PC tool of an old clone, finds a catalog that names a file in a folder `damaged`, since
  its name rule refuses `/`; the version is not raised for that, because the board and the
  PC tool change together with this seed.
- **Exhausting.** A playlist plays its own items first, each for one turn under the turn
  rule of today, in the saved order; then each of its sub-playlists in order, each
  exhausted once in the same way, depth first; then it starts again with its own items. So
  the root, played on its own, plays the board's animations and the loose files, then
  every folder once, and then again. A file that is left out, unavailable or being checked
  is passed over as it is today.
- **The current playlist and its window.** One playlist is current, named by its path from
  `odrig`, the root by none. It became current by a command, at power-on from the saved
  choice, or by the end of the window of the one before it. It plays, repeating, for a
  window of 24 hours of the board's running time counted from the moment it became
  current, the time the LEDs are off and the time a cycle or a jump plays included. When
  the window has passed, the turn in progress ends as it would, and the next playlist in
  the depth-first order of the tree becomes current with a window of its own, the root
  after the last. A window that ends while a cycle plays changes which playlist is current
  and not what plays: the cycle goes on until a command ends it, as today. A window that
  ends while a mapping test shows is taken when the test ends. When the window ends while
  the tree is not known, because the card is out or not yet read, the root becomes current
  with a fresh window, as on a card without folders. With no folder on the card the root
  is the only playlist, and its window changes nothing. The length of the window is a
  constant of the core, not a setting.
- **The clock.** The board has no clock: it counts the time since it started. The window
  counts running time and nothing else; calendar time is never considered, in this seed
  or after it. The window runs across restarts: the core keeps the current playlist's path
  and the time spent in its window in a file of its own in the board's storage, beside
  `order.txt`, written as `order.txt` is written, when the current playlist changes and at
  most once in 15 minutes while it plays. A restart goes on with the saved playlist and
  loses at most the last 15 minutes of its window.
- **The choice persists.** A playlist chosen by a command, the root included, is the
  current playlist until another choice or the end of its window, and it is saved the
  moment it is chosen; so is the playlist the rotation moves to. A restart, a power cut
  included, plays the playlist that was current, the chosen folder among them, from its
  first animation and with the window's saved time. Nothing but another choice, the
  rotation, or a card that is read and has no playlist of the saved path changes it.
- **The card out, or a playlist with nothing to play.** The choice and its window are kept
  whatever the card does. While the current playlist has nothing it can play, because the
  card is out or not yet read, or every file of the folder and of the folders below it is
  unavailable, the root plays in its place, which is the board's own animations when the
  card is out; the current playlist takes over at the end of the turn in progress as soon
  as it has something to play. This holds at power-on too: the saved choice stands while
  the card is not yet read. Only a card that is in and read and has no playlist of the
  saved path gives the root the current place, with a fresh window, and that is saved; so
  does the removal of the current folder's last file while the card is in.
- **Commands.** No command is added. `play <id>` of a folder's id makes that folder's
  playlist current, from its first animation, with a fresh window, on the current folder
  too; `play all` makes the root current in the same way, from its first animation. `play
  <id>` of an animation is a jump as today, and the current playlist goes on after it:
  with the animation after the jumped one in its exhausting order when the animation is an
  item of the current playlist or of one of its sub-playlists at any depth, else with the
  animation whose turn the jump cut, from its first frame. The `start` of `show.json` and
  cycles stay as they are: at power-on the root plays from the animation `start` names or
  else from its first, as today, and a folder from its first animation, since `start`
  names only the board's own. Folders have ids from the same pool as the card's files,
  60001 up, given after the card's files in the depth-first order of the tree, so the
  files keep the ids they have today; a card's ids go with its places, and while the card
  is out `play <id>` of a folder's id is refused with `unknown-id`, as of any id of a card
  that is out. The error codes stay those of today. These additions to replies need the
  owner's word, and the owner gives it by accepting this seed: `list` gives the folders as
  items after the show's items and before the card's files, in the depth-first order of
  the tree, each as `{"id": <id>, "playlist": "<path>", "external": true}`, counted in the
  positions of `<from>` and `next`, a file's folder read from its path; `status` reports
  `playing` as the current folder's id while the card is in and holds that folder, else
  `"all"` for the root, beside its values of today, and gains `left`, the whole seconds
  left in the current playlist's window, reported whatever the tree. The app of today
  takes `status` with a folder's id in `playing` and passes `left` over, but refuses a
  `list` that holds a folder item as `bad-reply`, since it wants `file` or `cycle` on
  every item: so the APK and the firmware of this seed go together, built from the same
  commit, and an APK from before it does not work against a board with this seed while a
  card with folders is in.
- **What stays.** `ignore` works on the board's animations only; `order move` moves an
  animation within the saved order as today, so a folder's files keep their relative order
  from it, and the app offers no move across folders; `upload begin external` takes a bare
  file name, a `<file>` with `/` refused with `bad-argument`, and puts the file in `odrig`
  itself, and the board makes and removes no folder; `remove` of a file in a sub-folder
  removes that file; `catalog rebuild external` and the PC tool's `import` walk the
  sub-folders as the listing says. A legacy card, one without a catalog, is listed with
  its folders the same way. The USB build's drive code is the same code and gets the same
  behaviour.
- **Where the work goes.** The playlists, the window, the saved choice and the new reply
  members are the core's, in `core/`, with its test host given the folder listing and the
  new file's name. The firmware lists the folders of `/sd/odrig` depth first in the one
  call of `drive_list`, within the 250 ms of a card read, as the flat listing is today,
  and builds paths from `odrig`; its line goes into `docs/firmware-additions.md` in the
  same commit. The emulator's `--drive` folder and the PC tool list sub-folders alike. The
  core's memory stays within its budget of today and the firmware's name table is not
  enlarged: the folder of a place is read from its name, and the folders' table and the
  window's state fit in the 1,251 bytes the budget leaves with a drive and the 288 bytes
  left in the core object, `docs/core.md`'s Memory; `tests/core/test_drive.py`, which
  asserts the drive's blocks to the byte, changes with them. The app changes in `app/www/`
  alone, once for the APK, the browser and the emulator's Controller view. The documents
  of each part change with it: `docs/show.md`, `docs/commands.md`, where the sentence that
  what `play` changes is not kept across a restart gives way to the kept choice,
  `docs/core.md`, `docs/catalog.md`, `docs/microsd.md`, `docs/firmware.md` and
  `docs/emulator.md`, which say that folders inside `odrig` are passed over,
  `docs/android-app.md`, and the vocabulary's `playlist`. This seed changes what the
  playlist is in `docs/decisions.md`: beside the sentence `A show plays its included
  animations in turn by itself`, which stays and which the core's suite pins, a folder's
  playlist plays its folder alone for its window, and the saved order of seed 36 names a
  card file by its path; the owner's request of 2026-10-26 is the ruling, and the
  change-log line goes in with the last task.

## Required Behavior

1. A card whose folder `odrig` holds sub-folders gives one playlist per folder that holds
   an animation file at some depth, the root included, in the depth-first order of the
   listing, at most 32 sub-folders and 256 files.
2. The root playlist plays the board's included animations and the loose files of `odrig`
   in the saved order, then each sub-folder's playlist once, then starts again. A folder's
   playlist plays its own files in the saved order, then each of its sub-folders'
   playlists once, then starts again.
3. `play <id>` of a folder makes its playlist current, from its first animation, with a
   fresh 24-hour window; `play all` does the same for the root. `status` says which
   playlist is current, in `playing`, and how many seconds its window has left, in `left`.
4. When a playlist's window has passed, the turn in progress ends and the next playlist of
   the tree becomes current, the root after the last; a cycle in progress plays on, and a
   mapping test in progress ends first. The window counts the board's running time,
   whatever plays, and goes on across restarts from the saved time, at most 15 minutes
   lost at a power cut.
5. The current playlist is saved the moment it is chosen or the rotation moves to it, and
   at power-on it plays again, the chosen folder included: the root from the animation
   `start` names or its first, as today; a folder from its first animation. The root plays
   when nothing is saved, and in the saved folder's place while the card is not yet read; a
   card that is read and has no playlist of the saved path makes the root current. A cycle
   named as `start` plays as today.
6. While the current playlist has nothing it can play, the root plays in its place, and
   the current playlist takes over as soon as it can.
7. `list` names each folder as an item with its id and path, after the show's items and
   before the card's files, and names a file in a folder by its path. `order.txt`, the
   catalog and `drive_name` name a file in a folder by its path; a card cataloged before
   this seed, whose files are all loose, reads as before.
8. The Animations tab shows the list as groups in the order they play: the root's group
   first, under the heading `Root` with the count of its rows, then one group per folder,
   the groups following one another in the depth-first order of the tree, each heading
   carrying the folder's whole path and the count of the files directly in it; the groups
   are not indented and do not fold. A folder with no file directly in it keeps its
   heading, its count `0` and its button, since it is the playlist of its sub-folders; a
   group that has rows and none of which the filters show is not shown, heading included.
   Every group, the root's included, has the same button, `Play this folder`: a folder's
   sends `play <id>` of the folder, the root's sends `play all`, and on the current
   playlist it restarts it with a fresh window. The button `Playlist from the start` of
   seed 36 goes, the root's button being it. The pinned Tests group of seed 36 stays above
   the list, outside the folder groups: it is no playlist, has no button, no mark and no
   count of this seed, and the filters leave it alone as today.
9. The now-playing line names the current playlist and the time its window has left in
   whole hours and minutes: `Playlist night · 23 h 12 min left` for a folder, by its path,
   or by its id while the list has no item of it; `Playlist · 23 h 12 min left` for the
   root while the list holds a folder group; `Playlist` as today, without a time, while
   `playing` is `"all"` and the list holds no folder group. The current playlist's group
   is marked, the root's group when the root is current. While the
   root plays in place of the current folder the line reads `Playlist night, the root
   plays for now · 23 h 12 min left` and the folder's group keeps its mark; the app knows
   it from `status`, `playing` a folder's id and `animation` no file of that folder nor of
   a folder below it, read from the paths, and a jump by `play <id>` to an animation
   outside the current playlist shows the same words for its turn, since `status` does not
   tell a jump from the root in its place.
10. In the app, the filters of seed 39 work within the groups, dragging and the menu's
    moves work within one group and not across groups, selection for deletion takes rows
    only, the counts of animations take rows only, a folder item being no animation, and
    uploads go to the root, as the board makes no folder.
11. The emulator's `--drive` folder and the core's test host give sub-folders of `odrig`
    the same meaning as the card's, and the PC tool `odrig.catalog` imports and checks a
    card with sub-folders, byte for byte as the core writes it.
12. The pages of the project describe the playlists of folders: `docs/show.md` the tree,
    the listing, the exhausting and the window, `docs/commands.md` the replies and the
    kept choice, `docs/core.md` the saved file and the host's listing, `docs/catalog.md`
    the paths and what an older reader finds, `docs/microsd.md` how a card is prepared
    with folders, `docs/firmware.md` and `docs/emulator.md` the listing of a drive's
    folders, and `docs/android-app.md` the groups and the choice.

## Definition Of Done

1. All test suites that need no board and no phone pass. The core's suite checks, with its
   test host and its timestamps, a card of nested folders: the tree and its order on a
   legacy card and on a cataloged one, the exhausting of the root and of a folder, `play
   <id>` of a folder and of an animation inside and outside the current playlist, the
   window passing at 24 hours with the turn in progress ending first, the rotation to the
   next playlist and to the root after the last, a cycle and a mapping test at the
   window's end, the saved file written at a change and after 15 minutes and read at a
   restart, the root in place of a playlist with nothing to play, the card pulled and put
   back and the window kept, a card without the saved folder, the paths in `order.txt`,
   `list` and the catalog, the limits of depth, folders and files, and the memory within
   its budget. The emulator's suite checks the folders of `--drive` and the replies. The
   Python library's suite, `tests/converter/`, checks `odrig.catalog`'s `import`, `check`
   and `status` on a card with sub-folders, the core's `test_catalog_*` check that the
   core and `odrig.catalog` write the same bytes from such a card, and
   `tests/vectors/catalog/` gains a storage with folders and its outcome in `cases.json`.
   The firmware's suite checks the depth-first listing of folders on the Mac with the
   stand-in card. The app's suite checks the groups, the headings and counts, the root's
   group and its button, the current playlist's mark and time left, `Play this folder` on
   a folder and on the root, the line while the root plays in place, the filters, moves
   within a group only, the Tests group left alone, and the card out and in, in Chrome
   against the emulator.
2. The microSD firmware is built with `fw.py build`, and in a session with the owner the
   board plays a card prepared with sub-folders: the groups show on a phone, a folder is
   chosen there and plays, the board is restarted and plays the same folder, the root is
   chosen and plays, and the card out and in behaves as this seed says; the log's
   time between `card mounted` and `card opened` is noted for a card with 32 sub-folders
   and 256 files. The 24-hour rotation is checked in the core's suite only; on the board
   the owner sees the time left count down in the app.
3. A new APK is built from the same commit as the firmware and installed on the owner's
   phone with it, and the owner checks it against the board.

## Open Questions

None. The owner asked for this seed to be ready for its spec with no open question; the
decisions it needed are taken in the constraints: the tree of folders with the root as the
parent of all, the depth-first listing by the bytes of the names, the path as a file's
name, at most three levels and 32 sub-folders, exhausting as one turn each in the saved
order and the sub-folders once each after the own items, a window of 24 hours of running
time kept across restarts in a file of the core's that names the playlist by its path, the
next playlist in the depth-first order and the root after the last, a cycle playing on
past the window's end, the choice saved when made and kept while the card is out with the
root playing in its place, `play <id>` of a folder's id in place of a new command, the
folder items of `list` after the show's items, `left` always reported, the root as a
group with the same button as a folder, and the words of the app's button and of its line.

## The Owner's Answers

On 2026-10-26 the owner asked for a seed, on a temporary worktree, that adds to the
Playlist screen an option of sub-folders, selectable from the app as the playlist that
plays now; the sub-folders of the card's animation folder dictate the sub-playlists; a
playlist repeats for 24 hours only and afterwards the next sub-playlist starts; when a
parent playlist is played, all of its non-sub-folder items are exhausted first and then
its sub-folders start to get exhausted; the seed covers the firmware changes and the app
changes, and is to be ready for its spec with zero open questions. Later the same day the
owner hardened it: a chosen folder is a persistent decision, so that a board that restarts
plays the same folder; the root folder must be a selectable option like any folder; and
calendar time is never to be considered. The owner's acceptance of this seed is the
owner's word on the two additions to replies, the folder items of `list` and `status`'s
`left` with `playing` as a folder's id, since every addition to the command list needs the
owner, and on the change of the playlist decision in `docs/decisions.md` that the
constraints name.
