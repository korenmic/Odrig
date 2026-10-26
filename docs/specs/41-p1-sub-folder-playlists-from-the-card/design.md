# Design: sub-folder playlists from the card

## Overview

The card's folder `odrig` becomes a tree of playlists. Every host that lists the card
walks its sub-folders depth first and names each file by its path, so the core, which
knows the card only as a list of names, sees `night/comet.odrg` where it saw `comet.odrg`.
The core reads the tree from those paths: a folder exists exactly when a path has it as
a prefix, and no host member is added. It keeps a small table of the folders in the
listing's order, a folder index for each place, the current playlist and its window, and
it walks the exhausting order as a pair of keys, folder then saved order, with no
recursion. The playlist file beside `order.txt` keeps the choice and the time spent, and
the replies gain only the folder items of `list` and `left` of `status`. The app draws
the list as groups with a button each, and reads a file's folder from its path.

## What this design relies on

From the sources at `de838e3`, on 2026-10-26:

- The core's host interface, `core/include/odrig_core.h`: `drive_name(drive, place)` gives
  the name of the file at a place, `drive_list` lists the drive when the core asks,
  `drive_bind` gives a cataloged drive's places their names, and a file is opened as
  `drive/<place>` or changed as `drive/<name>`. `tests/core/test_docs.py` pins the exact
  list of the host's members, so none is added.
- The player, `core/src/player.cpp`: `plays(position)`, `lowest_playing`, `next_animation`
  and `playlist_turn`, which walks turns from `core.zero` and takes whole rounds off by
  division; `player_play_all(from)`, `player_start`, `player_drive_changed`,
  `player_item_leaves`; `advance` and `player_poll`. The playlist's keys come from
  `order_key` in `core/src/order.cpp`: the entry number of `order.txt`, else
  `0x10000 + item` or `0x20000 + place`.
- The drive, `core/src/core.cpp`: `drive_touch`, `drive_take_listed`, `free_drive_id`,
  `drive_place_holding`; the places of a cataloged card are staged page by page in
  `core/src/catalog.cpp` (`stage`, `publish`), in the order of the pages, and
  `order_drive_named` is the one place that sees every place's name as it is counted.
- The memory, `docs/core.md`: 129,821 of 131,072 bytes with a drive, the core object
  3,808 of 4,096, nineteen blocks with a drive; `tests/core/test_drive.py` asserts the
  drive's blocks to the byte and `test_docs.py` the memory table's rows and sum.
- `order.txt`'s writing in `core/src/order.cpp` (`order.part`, the host's `write_open`,
  `write`, `write_close`, `rename`, `remove` on failure) and `storage_clear_parts` in
  `core/src/storage.cpp`, which probes `order.part` with `read_at` before removing it.
- The replies, `core/src/commands.cpp` and `core/src/content.cpp`: `status` writes its
  members in a fixed order ending in `seed`, `play` resolves an id among the show's items,
  then the drive's animations, then a left-out place, else `unknown-id`; `list` counts
  the show's items then the drive's listed places, pages of at most 1,024 bytes.
- The hosts' listers: `listFolder` and `keepName` in `firmware/usermod/odrig_drive.cpp`
  (one `opendir` of `/sd/odrig`, regular files only, `strcmp` order, 256 names of 256
  bytes in a table of the external memory, names given to the core cut to 100 bytes);
  `drive_list` and `drive_name_sound` in `emulator/host.py`; `list_drive`,
  `drive_name_sound` and `check_name` in `tests/core/host/host.cpp` (the fixed list of
  internal names, status 71 for any other); `Storage.names`, `MemoryStorage.names` and
  `name_allowed` in `odrig/catalog.py`. All four sort whole names by their bytes and keep
  the first 256; `odrig/catalog.py` and the core's `catalog_name_allowed` keep one rule.
- The app: `commands.js` validates `status` (`playing` null, `"all"` or 1 to 65,535) and
  `list` (every item a file or a cycle); `client.js` keeps `state.animations`,
  `state.cycles` and `state.order`, and keeps the order only when its ids are exactly the
  listed animations'; `screens/show.js` draws the rows as `#animations-list > .row`,
  `playing()` the now-playing line, `#play-all` `Playlist from the start`;
  `screens/reorder.js` moves over the whole shown order; `screens/filters.js` matches
  rows; `screens/selection.js` and `capacity.js` take the listed items.
- The suites: `tests/core/support.py`'s `ReferencePlayer`, compared with the core byte
  for byte, writes `status` ending in `seed`; `tests/emulator/support.py`'s
  `without_fps` drops the members that depend on real time; the app's scenarios read
  rows as `#animations-list > .row` and press a button by its text, one at a time.

## The path rule

One rule, applied alike by the firmware's `isDriveName`, the emulator's and the test
host's `drive_name_sound`, the PC tool's `name_allowed` and the core's
`catalog_name_allowed`. A name is a path of 1 to 100 bytes, split at `/` into 1 to 4
parts, none empty, so at most three folders. A folder part is 1 to 100 bytes of printable
ASCII other than `/ \ : * ? " < > |`, neither beginning nor ending with a space or a dot,
and may be digits alone. The last part, the file's, keeps the rule of today applied to the
part: the same characters, no leading dot or space, no trailing space or dot, not digits
alone, and the ending `.odrg` or `.odrgx` in any case. A leading dot on any part refuses
`.` and `..`, so `night/../x.odrg` stays refused as `drive/../x.odrg` is today. A place is
`drive/<digits>`, which no path can be, so `namesAPlace` and its kin stay right.

The core applies the widened rule to both catalogs, since one function serves both; the
internal storage never meets a path, because a show's file name is checked by its own
rule of 32 characters, and the test host refuses an internal name with a slash with
status 71 as today. On a cataloged card a path the rule refuses, a fourth level among
them, is a damaged line, as any name the rule refuses is today, and neither the PC
tool's `import` nor the firmware writes one.

## The listing

The depth-first order: a folder is listed as its animation files by the bytes of their
names, then its sub-folders by the bytes of their names, each listed the same way. In
Python the sort key of a path is `(tuple(folder parts as bytes), file part as bytes)`: a
tuple that is a prefix of another sorts first, so a folder's files come before its
sub-folders' and siblings sort by their bytes, `a` before `a b` before `a-b`. In C++ the
comparator finds the first differing byte of two paths and the part that holds it: when
exactly one of the two is at its file part there, that one comes first; otherwise the
bytes decide, with the end of a part ranking below every byte. The order of every lister
is this one, and a catalog's page lines follow it from both writers, which keeps the
byte identity of `odrig.catalog` and the core.

What a lister passes over: a folder deeper than three levels below `odrig`, a folder
whose name fails the rule, a folder whose name starts with a dot, `System Volume
Information`, and a folder without an animation file at any depth below it, which is no
folder of the tree. A lister takes at most 32 sub-folders and at most 256 files, counted
one way everywhere: walking the kept files in the depth-first order, a folder is counted,
with each of its ancestors not yet counted, when the first file at or below it is kept;
when a file's folder would be counted past the 32nd, that file and every later file of
the walk are passed over, and so is every file after the 256th. Since files are grouped
by folder in that order, the two cuts agree whichever is applied first, and a folder with
files only in its sub-folders counts, as the core's tree holds it. Nothing logs a
passed-over file today, and the emulator, the test host and the PC tool pass over
silently; the firmware's one line at a listing keeps its words, `card opened: <n>
animation files in odrig`, for a card without folders when nothing was passed over, and
otherwise reads `card opened: <n> animation files in <m> folders of odrig`, with `; <k>
files and <f> folders passed over` added when anything was. That line is the log the
seed asks for.

The firmware's `listFolder` stays one function called from `driveList` alone, as the
firmware suite pins. Inside it the walk is iterative: a table in the external memory,
taken once in `begin()` beside the names, of 256 pending folder paths of 104 bytes each,
26,624 bytes, used as a stack, since FAT's `readdir` is unsorted and every sub-folder of
a directory must be held before any is visited; for each folder taken from the stack,
one `opendir`, one pass of `readdir` that keeps the animation files into `names` from that
folder's first free slot with `keepName` sorting within the folder, and the sub-folders
into the stack in reverse byte order so that the first by bytes is taken next; the
directory is closed before the next is opened, so at most one `DIR` is open. When a
folder's sub-folders do not all fit the room left on the stack, those last by bytes are
passed over and counted, never the first. The walk counts folders by the rule above as
it keeps files, and stops keeping files at the 33rd sub-folder or the 257th file,
counting the rest. `isAnimation` keeps its ending rule; the folder rule is the path
rule's. The names table stays 256 by 256 bytes, and a path of at most 100 bytes always
fits.

The emulator's `drive_list` and the PC tool's `Storage.names` walk with `os.scandir` and
a list as the stack, filter by the same rules, sort by the key above and cut; the test
host's `list_drive` does the same with `readdir` on POSIX and `directory_iterator` on
Windows, and its `drive replace` copies with `copy_options::recursive`. `MemoryStorage`
sorts its names by the same key. On Windows the PC tool joins parts with `/`, never the
system's separator.

## The tree in the core

The core takes 624 bytes more for a drive, in the order block that `order_begin` takes,
so that the block count stays nineteen with a drive: one byte per place, the index of
its folder, 0 for the root and 255 for a place of no folder; a table of 33 folder records
of 8 bytes, the root at index 0; and 104 bytes of room for the current playlist's path.
A folder record holds `id` (uint16), `place` (uint16, a place whose path is at or below
the folder), `depth` (uint8, 1 to 3), `end` (uint8, the index after its last descendant),
and two spare bytes. The table is in the listing's order, depth first, so the subtree of
folder `f` is the index range `[f, end)` and the root's is the whole table. A folder's
path is the first `depth` parts of `drive_name(place)`. The window's state lives in the
core object, in its alignment holes and the room left: `window_started` (uint64, the
timestamp the current playlist became current, or `t0` after a start), `window_spent`
(uint32, the milliseconds spent before `window_started`, read from the file),
`playlist_saved` (uint64, the latest save), `current` (uint8), `folder_count` (uint8),
`resume_item` (uint32) and flags (`in_place`, `save_due`, `file_present`,
`tree_known`). `docs/core.md`'s memory table and `tests/core/test_drive.py`'s delta
change by these numbers, measured by the suite.

The tree is built from the names in one function, `tree_build`, called in two places:
in `drive_take_listed` for a legacy card, after every place has its name and its id, and
in `publish` for a cataloged card, after the last page, since its places come in page
order. It makes two passes over the places with a name: the first splits each name at
its `/` and adds every folder of the path that the table lacks, inserting it in the
listing's order by comparing paths part by part through `drive_name` of the records'
places, so that a late insertion moves no byte already set; the second finds each
place's folder in the finished table and sets its byte, and sets `end` in one walk. A
place whose folder would be the 33rd sub-folder, the 34th record with the root, is left
out as a place that gets no id is left out today: the log says `drive file <path> left
out: too-many-folders`, a reason added to `reasons.h`, `reasons.cpp` and the drive's table
of `docs/reasons.md`; only a catalog's pages can name such a place, since every lister
cuts at 32. Folder ids are given after every file has its id, in table order, through
`free_drive_id`, which gains the folders' ids in its scan of taken ids through one
helper, `drive_id_taken`, used also by `upload begin`'s check of a free id. The tree is
cleared, `folder_count` 0, `tree_known` 0 and every place's byte 255, wherever the places
are dropped: `drive_touch`, `drive_take_listed`, `drive_unusable`, `page_step` on a changed
marker, `catalog_drive_yields`, `catalog_drive_look` and the external rebuild, through
one `tree_clear`. `catalog_install_external` sets the new place's byte to 0, the root,
since the file goes to `odrig` itself. A removal of a card file
(`catalog_remove_external`) builds the tree again from the remaining places, keeping the
ids of the folders that remain; when the current folder is gone from it, the root
becomes current with a fresh window.

The current playlist is kept as a path, in the 104 bytes of room, empty for the root, and
as `current`, its index in the table while the tree is known, 0 when the tree is not
known or the path is not in it. Whenever the tree is built, `current` is found from the
path by the same part-by-part comparison; a path that no folder of a known tree has
makes the root current with a fresh window and is saved as such.

## The exhausting order

A position's exhausting key is the pair (folder index, `order_key`); an internal item has
folder 0. `next_in(core, range, position)` gives the position with the lowest key above
the position's within the folders of `[first, end)`, else the lowest in the range: a
folder's own items in the saved order, then each sub-folder's once, depth first, then
again from the folder's own items. `first_in(core, range)` is the lowest key in the range.
The range is the current folder's subtree, or the root's when the current one has no
playing position in its subtree: `in_place` records which, and is re-judged at every turn
end, so that the current playlist takes over at the end of the turn in progress, from its
first animation, as soon as it has something to play. `plays(position)` stays what it is,
so left-out, unavailable, checked and ignored animations are passed over as today.

`playlist_turn` keeps its shape. Its round, when every length is known, sums the turns of
the playing positions of the range in use, and whole rounds are taken off only up to the
window's end, so that a rotation is never skipped; a rotation clears `rounds_taken`, so
that the new range's round is summed and whole rounds are taken off again up to the new
window's end, and a gap of many windows costs one walk per window; with the root alone
in the tree the window's end bounds nothing, since a rotation from the root to the root
changes nothing but the window. At a turn's end, `next_in` replaces `next_animation` for the playlist; the
jump's resume comes first: when `resume_item` is set, the next turn is that animation's,
from its first frame, and `resume_item` is cleared. `player_first_in_playlist` becomes the
first of the current playlist's range, or of the root's in its place, and `player_start`
uses it for a folder and keeps `start` for the root.

A jump by `play <id>` of an animation inside the current playlist's subtree plays that
animation's turn and goes on from its key; one outside the subtree sets `resume_item` to
the animation whose turn was cut and plays the jumped turn. `player_item_leaves` moves
`resume_item` as it moves `turn_item`; a drive change that leaves it unplayable drops it.

## The window

`kWindowMs` is 86,400,000. The time spent in the window is `window_spent + (latest -
window_started)`, and `left` is `(kWindowMs - spent) / 1000` when spent is below the
window, else 0. At the first timestamp, `clock_touch` sets `window_started` to `t0`, since
`odrig_core_begin` carries no time. A rotation sets `current` to the next index of the
table, 0 after the last, `window_started` to the moment of the rotation, `window_spent`
to 0, the path from the table, and `save_due`; when the tree is not known it makes the
root current the same way.

Where the window's end is judged: in `playlist_turn`, at each turn's end, by the turn's
end time, which is where the turn in progress ends as it would; in `player_poll`, at
every refresh while a cycle plays or nothing plays, by `now`; and in `mapping_test_stop`,
before the saved selection resumes, so that a window that ended under a test makes the
next playlist current and plays its first animation in place of the saved one. During a
cycle the rotation changes `current` and nothing that plays. A `play <id>` that clears
the test is a choice and needs no judging.

## The saved file

`playlist.txt`, in the board's storage beside `order.txt`, written as `playlist.part` and
renamed, with the pattern of `order.txt`: `write_open`, one `write` of at most 130 bytes
from a buffer on the stack, `write_close`, `rename`; on a failure the part is removed and
nothing is refused, since the error codes stay. Its text is three lines: `odrig-playlist
1`, the current playlist's path or an empty line for the root, and the milliseconds spent
in its window. An absent file means the root with a fresh window. It is written when the
current playlist changes by a choice or by a rotation, and at most once in 900,000 ms
while the tree has a folder, from `player_poll`, since the root's window then decides when
the first folder starts; a write while an upload is receiving or a rebuild holds a page
open is deferred to the next refresh that is free, through `save_due`. It is not written while the tree has no folder and no file exists, because
the root with a fresh window is what an absent file means: so a show without a card, or
with a flat card, makes no storage call more than today, and the suites that count
storage calls stay as they are. The file is read at start, beside `order_start`, through
the second source line by line; `storage_clear_parts` probes `playlist.part` with
`read_at` and removes it when present, as it does `order.part`. The names join the core's
reserved names in `docs/core.md`, the test host's fixed list, and the firmware tool's
list of a show folder's own files (`firmware/fwtool/storage.py`, `cli.py`'s keep at
install), so that `fw.py install` keeps the board's `playlist.txt` as it keeps
`order.txt`. The firmware's storage accepts the names as it is.

At power-on, `start` reads the file, keeps the path and `window_spent`, and sets
`current` to 0 until a tree is known; the root plays in the folder's place meanwhile, by
`in_place`. `player_start` plays the root from `start` or its first, as today; a folder,
once the card is read and the tree known, from its first animation.

## The replies

`list`: `content_list` counts `item_count + folder_count + drive_listed`; the positions
after the show's items and before the files are the folders in table order, each written
as `{"id":<id>,"playlist":"<path>","external":true}`, the path read through `drive_name`
of the record's place and cut at its depth, escaped as a file name is. A folder item is at
most 135 bytes and a page of 1,024 holds it. `order get` and its revision stay over the
listed animations, so folder ids never appear in them.

`status`: `playing` is the current folder's id while `core.playing` is the playlist, the
tree is known and `current` is not 0; else `"all"`, a cycle's id or `null` as today.
`left` is the last member, after `seed`, as `seed` was added after `host`: `,"left":<n>`.
The example reply of `docs/commands.md` and the exact bytes the suites pin gain it; the
emulator's `without_fps` drops it beside `fps`, since the emulator runs in real time; the
`ReferencePlayer` keeps `window_started` as the core does, its first timestamp at first
and then the end of the first turn at or after `window_started + 86,400,000` in its own
walk of turns, or the refresh at which it judges while nothing or a cycle plays, and
writes `left` as `max(0, 86_400_000 - (now - window_started)) // 1000`.

`play <id>`: after the show's items, the drive's animations and the left-out places, the
folder table; a folder's id makes it current, with a fresh window and `save_due`, and
plays its first animation, or the root's in its place; `play all` makes the root current
the same way. While the card is out the table is empty and the id falls to `unknown-id`.
`remove`, `remove many`, `ignore`, `read`, `order move` and `upload begin` of a folder's id
answer `in-use`, the code a cycle's id gets from `ignore` and `order move`. `upload begin
external` keeps `is_file_name`, so `/` stays `bad-argument`. `remove` of a file in a folder
goes through `catalog_remove_external` with its path, as today with a name.

## The app

`commands.js`: `status()` accepts `left` as an optional whole number and returns it, null
when absent; `list()` accepts a third kind of item, `{"id","playlist","external":true}`
with a non-empty string `playlist` and none of `file`, `cycle`, `bytes`, `ignored`,
`type`, `fault`, and maps it to `{id, playlist}`; the file and cycle kinds stay as they
are and refuse `playlist`. `client.js`: `state.folders`, reset where `animations` is, set
from the last page's folder items in their order; `state.animations` takes the file
items alone, so the order, the counts, the filters and the selection are untouched by
folders; when `status.playing` is a number that is neither a cycle nor a folder of the
known list, the list is asked at once, as it is for an unknown `animation`.

`screens/show.js`: a file's folder is the path before its last `/`, the root when there is
none; a file lies under folder `p` when its path begins with `p` and `/`. The list is
drawn as groups: a static head before `#animations-list`, `div#root-head.folder-head`
with `h2#root-title` `Root · <n>` and `button#play-all` `Play this folder`, which keeps the
id the scenarios read and sends `play all`; inside `#animations-list`, before each
folder's rows, a `div.folder-head` with `data-group` (the path) and `data-id`, an `h2`
`<path> · <n>` and a `button` `Play this folder` with `aria-label` `Play folder <path>`,
which sends `play <id>`. The rows stay direct children `.row` of the list, each with
`data-group`, so every selector of the app and the suites keeps working; the heads are
not rows, not indented, and do not fold. One pass over `shownOrder(state)` puts each
animation into its group; a folder of the list with no row of its own keeps its head
with `0`; a group with rows and none shown by the filters is hidden with its head; the
root's group hides the same way. The count of a group is the number of its rows, filters
or not. `drawRows` compares heads and rows by their keys and rebuilds only on a change;
`rowsState` marks the current group's head with `aria-current="true"` and the row of the
animation as today, and updates the counts in place. The pinned Tests group stays where
it is, above, untouched. `.pair` keeps `#add-animation` alone.

The now-playing line, `playing(status, state)`, with `fmt(left)` as `<h> h <m> min left`:
the invalid show's text as today; `Nothing plays` for null; `Cycle <id>` for a number in
`state.cycles`; for a number in `state.folders`, `Playlist <path>`, then `, the root plays
for now` when `status.animation` names an animation of the list whose path is not under
the folder, then ` · ` and `fmt(left)`; for any other number, `Playlist <id> · <fmt>`
while `left` is known, else `Cycle <id>` as today; for `"all"`, `Playlist · <fmt>` when
`state.folders` is not empty and `left` is known, else `Playlist`. The marked group is the
folder of `playing`, the root for `"all"`, none for a cycle or null.

`screens/reorder.js`: `neighbour` runs over the ids of the row's own group; `lift` marks
the rows of the same group only; `place` with no mark below puts the placeholder after
the group's last row; `drop` takes the next sibling only while it is a row of the same
group, else `end`; the no-move check compares the group's ids before and after. Global
`end` is right for the last of a group: it changes no other group's relative order.
`filters.js`, `selection.js` and `capacity.js` change nothing, since folders are not in
`state.animations`. `messages.js` keeps its words: a folder's `play` refused with
`unknown-id` while the card is out reads as an animation's, which the seed accepts by
keeping the codes.

The style gives the heads `overflow-wrap: anywhere`, a 48 px root button and 44 px
folder buttons 8 px from their neighbours, at the contrast the look test asks.

## The documents

`docs/show.md`: the tree, the listing and the path rule under the drive, the exhausting
order under the playlist, the current playlist and its window, the saved file, and
power-on; the saved order's `x` entries as paths. `docs/commands.md`: `play` of a folder
and `play all`, the folder items of `list` with the positions, `playing` and `left` of
`status` with the example reply, `unknown-id` of a folder while the card is out, `in-use`
for the rest, and in place of the sentence that what `play` changes is not kept across a
restart: the current playlist is kept, a jump, `on`, `off` and `brightness` are not.
`docs/core.md`: the host rows of `drive_name` and `drive_list`, the reserved names, the
tree, the keys, the window, the saved file, the memory table and the test host's listing.
`docs/catalog.md`: the path rule, the page of a path, and `damaged` for a reader from
before this seed. `docs/microsd.md`: preparing a card with folders, the log line, and the
stale `busy` sentence dropped. `docs/firmware.md` and `docs/emulator.md`: the listing.
`docs/android-app.md`: the row `Presses Playlist from the start` of the table of what
the operator does, reworded to the root's button, and the row of a tapped row to a
folder's; every mention of `Playlist from the start` and of the line `Playlist`; the
groups, `Root`, the button, the line, the mark, moves within a group, uploads to the
root, `What is verified` and `What is open`; no heading and no check step added, so the
app's docs test keeps its counts. The example replies of `docs/commands.md` use paths
without a space, `night` and `night/deep`, since the docs test forbids a space in an
example line. `docs/reasons.md`: `too-many-folders` in the drive's table.
`agent/vocabulary.md`: the playlist, in one to four sentences that use no word the page
explains further down, `turn`, `command`, `core`, `host`, `emulator`, `firmware` and the
operators' app among them, and name no file or path the clone does not hold.
`docs/firmware-additions.md`: a new line for the listing of folders, seed 41,
`odrig_drive.cpp`, written again, seed 12 `No`. `docs/decisions.md`'s change log, with the
last task that needs neither the board nor a phone. `docs/drifts.md`: a section "Seed 41"
with the decisions this design takes beyond the seed: the summary log line in place of a
line per file; the file not written while there is nothing to keep; the save deferred
under an upload or a rebuild; the reason `too-many-folders`; `in-use` for the other
commands of a folder's id; the current playlist taking over from its first animation;
the count of a group under filters; the widened rule for both catalogs; a deeper path in
a catalog as a damaged line; the folder button's `aria-label`.

## Tests

- `tests/core/host/host.cpp`: the depth-first `list_drive`, the path rule, the two names
  in the fixed list, recursive copy on Windows. `tests/core/support.py`: `installed` makes
  parent folders and `folder_files` reads at every depth; `tests/core/test_drive.py`'s
  `a_drive` and `tests/core/test_catalog_writes.py`'s `a_card` make parent folders and its
  `folder_of` reads at every depth; the `ReferencePlayer` writes `left`. New
  `tests/core/test_folders.py`: the tree and its
  order on a legacy and a cataloged card, the ids, the folder items of `list`, `play` of a
  folder, of an animation inside and outside, the exhausting of the root and of a folder,
  the window at 86,400,000 ms with the turn in progress ending first, the rotation and the
  wrap, the cycle and the mapping test at the window's end, the saved file at a change
  and after 900,000 ms, a restart with the saved folder, the root in place, the card
  pulled and put back, a card without the saved folder, the limits, `in-use` and
  `unknown-id`, and the memory. The exact `status` bytes of the suites gain `left`.
- `tests/converter/`: the path rule's cases in `test_catalog_format.py`, the listing order
  in `test_catalog_types.py` and `test_catalog_changes.py`, `import`, `check` and `status`
  of a card with sub-folders in `test_catalog_cli.py`, the vector `ok-folders` and the
  damaged-path vectors in `build_catalog_vectors.py` and `cases.json`.
- `tests/core/test_catalog_rebuild.py` and `test_catalog_writes.py`: the byte identity of
  the two writers on a card with sub-folders.
- `tests/emulator/`: `drive_list` depth first with the limits, `drive_bind` of a path, a
  drive with sub-folders listed and played over HTTP, `without_fps` dropping `left`.
- `tests/firmware/`: `test_usermod_sd.py`'s `case` makes parent folders and gains the
  mode `folders`: the depth-first order, the limits, the passed-over folders and the log
  line; `test_usermod_drive.py`'s pins of the listing and the name rule follow the code.
- `tests/app/`: `test_folders.py` with `scenarios/folders.js` against a stand-in target with
  a fixed `left` and against the emulator with a nested `--drive`: the groups, the heads
  and counts, the Root group, the mark, the line's forms, `Play this folder` on a folder
  and on the root, filters and a hidden group, a 0-row folder's head kept, moves within a
  group, selection and counts on rows only, the Tests group, the card out and in. The
  validators' cases in `test_management.py`; the button lists of `test_controls.py` and
  `test_drive.py` and the presses of `test_messages.py` follow the root's button.
- `tests/onboarding/`: unchanged, run with every task that touches a page.

## What does not change

No command, no error code, no host member; `ignore`, `order move` and `upload begin
external` as today; the board makes no folder; the catalog format's version; the
internal show; the 256 files of a card; the refresh rate rules. The emulator's record
mode has no drive, so the window is tested in the core's suite alone.

## What needs the owner

The board session and the phone check of the definition of done. The reply additions
and the decision's change are the owner's by the seed.
