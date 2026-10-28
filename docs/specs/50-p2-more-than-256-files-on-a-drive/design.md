# Design: more than 256 files on a drive

## Overview

A drive's catalog keeps, beside its pages, an index of fixed-width rows: a file for each
folder with its files in the saved order and its sub-folders, a table of the folders, and
a map of the ids. The rows give the core everything it kept per file in memory: the id,
the size, the length, the type, the canvas and the CRC-32, and the path to open the file
by. So the core drops its table of 256 places for a cataloged drive and holds a cursor:
the row of the animation whose turn it is, the record of the current playlist's folder,
and the room for one read of 512 bytes. A drive's files become positions in the walk, the
order the playlist plays them in, and a folder's subtree is a range of the walk, so the
walk needs no keys: the next file is the next row.

The replies show one level at a time: `list` gives the root's level, `list in <id>` a
folder's, `status` names the file on the LEDs and the current playlist's path, and the app
reads only the level it shows. A drive without a catalog keeps its table of 256, now cut
by the core, since every host but the firmware lists the whole drive.

## What this design relies on

From the sources at `afc7b09`, on 2026-10-28, with the one-line fix of PR #18 for GCC:

- The host interface, `core/include/odrig_core.h`: `drive_name(drive, place)`,
  `drive_list`, `drive_bind`, `drive_writable`, `read_at`; a drive's file is opened as
  `drive/<place>` or as `drive/<path>` on every host, the firmware's `drivePath` among
  them; `tests/core/test_docs.py` pins the members, so none is added.
- The drive in the core: `DriveEntry`, `kDriveMost = 256`, `kDriveBase = 0x10000` in
  `core/src/core_state.h`; `drive_touch`, `drive_take_listed`, `drive_step`,
  `free_drive_id` in `core/src/core.cpp`; the catalog's reading in steps (`page_step`,
  `stage`, `publish`), its changes (`catalog_commit`, `write_page`, `finish`,
  `read_record`) and its rebuild (`catalog_rebuild_step`, `rebuild_line`,
  `rebuild_commit`) in `core/src/catalog.cpp`; the tree and the saved order in
  `core/src/order.cpp`; the walk by exhausting keys in `core/src/player.cpp`
  (`lowest_in`, `next_animation`, `playlist_turn`'s rounds); `list`, `read`, `remove` in
  `core/src/content.cpp`; `play`, `status`, the parsing of ids (1 to 65,535) in
  `core/src/commands.cpp`.
- The memory, `docs/core.md`: 130,509 bytes for the target file with a drive, of which
  the drive's table is 3,072, the boot's memory of 16 files 640, and the saved order's
  block 1,024 more for the places and 368 for the tree and the path; the core object 3,872
  of 4,096 bytes.
- The PC tool, `odrig/catalog.py`: `rebuild`, `commit`, `add`, `remove`, `finish`,
  `read`, `cut_listing`, the CLI's `import`, `status`, `check`, `recover`.
- The hosts' listers: the emulator's `drive_list` and `drive_cut` (`emulator/host.py`),
  the test host's `list_drive` (`tests/core/host/host.cpp`), the firmware's `listFolder`
  (`firmware/usermod/odrig_drive.cpp`), each cutting at 256 files and 32 folders.
- The app: `app/www/client.js` reads the whole `list` and `order get`; the explorer of
  `app/www/screens/show.js` (`levelOf`, `folderOf`, `markedPath`, `playing`) derives each
  level from the whole list; `screens/reorder.js` and `screens/selection.js` work on the
  rows of the level; `capacity.js` counts the external animations of the list.

## The index

All the files are in the drive's folder `odrig`. Text is ASCII; numbers are decimal
without leading zeros, `0` for zero; CRC-32s are 8 lowercase hexadecimal digits, of zlib;
every line ends in a line feed and is padded with spaces before it to its kind's length.
A field never ends with a space, so a reader takes a line's last field as everything after
its last fixed field with the padding cut off.

### A folder's file: `index-<id>.txt`

The root's is `index-0.txt`. Every line is 180 bytes. First a row for each of the
folder's own animation files, in the saved order:

```
<id> f <crc> <bytes> <width> <height> <length> <type> <path>
60001 f 1a2b3c4d 52340 60 60 12000 frames sunrise.odrg
```

then a row for each of its sub-folders that is in the table, in the table's order:

```
<id> d <files> <path>
60006 d 1 night
```

`<files>` is the sub-folder's number of own files. The file fields are those of the
file's catalog line: its CRC-32, size, canvas, length in milliseconds and type, and its
path, at most 100 bytes; the longest file row is 173 bytes with its line feed. A folder
without a row has no file, and its CRC-32 is `00000000`.

### The table: `index-folders.txt`

Every line is 180 bytes, one for each folder of the table, the root first, in the
listing's order, depth first:

```
<ordinal> <id> <depth> <end> <first> <files> <folders> <crc> <path>
0 0 0 4 0 2 2 9f00e1aa
1 60006 1 3 2 1 1 0a1b2c3d night
2 60007 2 3 3 1 0 4c1e00a7 night/deep
3 60008 1 4 4 1 0 5e6f7a8b only
```

`<ordinal>` is the line's number from 0; the root's id is 0, its depth 0 and its path
empty. `<end>` is the ordinal after its last descendant, `<first>` the number of files of
the folders before it in the table, `<files>` and `<folders>` its numbers of own files
and of sub-folders in the table, `<crc>` the CRC-32 of its file. A folder is in the table
when a file at or below it is; the root always. The files of a folder's subtree are the
walk's positions from its `<first>` to the `<first>` of the line at its `<end>`, or to the
number of files when `<end>` is the number of lines.

### The map: `index-ids.txt`

Every line is 36 bytes, one for each id of the drive, sorted by id:

```
<id> <kind> <ordinal> <row>
60001 f 0 0
60006 d 1 0
```

A file's id to its folder's ordinal and its row there; a folder's to its own ordinal and
0.

### The marker of version 2

The marker of [catalog.md](../../catalog.md) with `odrig-catalog 2` and two lines before
its `crc` line, 461 bytes and 20 lines:

```
odrig-catalog 2 check 1 generation 0000002a
page 00 0003 1a2b3c4d
...
page 15 0001 9f00e1aa
folders 0000000004 0a1b2c3d
ids 0000000008 5e6f7a8b
crc 0a1b2c3d
```

`folders` gives the table's lines and its file's CRC-32, `ids` the map's. A table or a
map without a line has no file and the CRC-32 `00000000`; a drive always has the root's
line, so the table has at least one. The `crc` line covers the 448 bytes before it. Only a
drive's catalog is of version 2: the board's own catalog, which has no folder, stays of
version 1, and each reader takes only its storage's version, finding the other
`incompatible`.

### The ids

- A rebuild and an import give the files the ids from 60001 in the walk's order, a file's
  id being 60001 and its position, and the folders the ids after them in the table's
  order: the folder at ordinal k gets 60000 + files + k.
- An upload of a new file takes the lowest id from 60001 up that the map does not hold:
  the first line i whose id is not 60001 + i, found by binary search, else 60001 and the
  map's number of lines. A replacement keeps the id of the file it replaces.
- A removal frees the file's id, and a folder's when it leaves the table; the other ids
  stay.
- Neither writer looks at the show. Where an item of the show has a drive's id, `play`,
  `status`, `read`, `remove`, `upload begin` and `order move` mean the item, as `play`
  finds the show's items first today. `upload begin <id>` of an id the map holds stays
  `in-use`.

## The commit

A change of a drive's catalog writes its new index files as `.new` beside the new pages
and the new marker, and its commit record names each of them:

```
odrig-catalog-do 1 generation 0000002b
pages 0008
move upload.part sunrise.odrg
move index-0.new index-0.txt
move index-folders.new index-folders.txt
move index-ids.new index-ids.txt
crc 4c1e00a7
```

The record's `move <from> <to>` takes any name of the catalog's files as `<from>`, not
`upload.part` alone, and `remove <name>` an index file too; the finishing is as in
[catalog.md](../../catalog.md): the actions in order, then the pages of the mask, then the
marker. The actions are written in this order: the removals of index files, `move
upload.part <name>` or `remove <name>` of the animation, the moves of the folders' files
in the table's order, of the table, then of the map. A record of a rebuild can be long:
the core writes it, as every file, in pieces of at most 1,500 bytes through the chunk
buffer, its CRC-32 summed on the way, and reads it line by line as today.

The writers make the same changes; for each, what is written:

- **An upload of a new file `X`** to the root: `index-0.txt` with a row for `X` after the
  root's last file row and before its folder rows; the table with the root's `<files>`
  one more, every other line's `<first>` one more and the root's CRC-32; the map with
  `<id> f 0 <root's files before>` in its place; the page of `X`; the marker.
- **A replacement** of `X`: `index-0.txt` with `X`'s row anew, its id kept; the table with
  the root's CRC-32; the page; the marker. The map stays.
- **A removal** of the file at row r of the folder at ordinal k: k's file without the row;
  when nothing is left at or below k, k and each ancestor left without a file leave the
  table, a range of ordinals a to a + m - 1, their files are removed, and the parent of a
  loses its folder row for a; else k's parent's folder row for k gets `<files>` one less.
  The table: the lines of the range gone, the ordinals and `<end>`s at or after a + m less
  m, the `<first>` of every line after k less one, k's `<files>` less one, the parent's
  `<folders>` less one when a went, the CRC-32s of the files written. The map: the file's
  line and those of the folders that went gone, the rows after r of k one less, the
  ordinals at or after a + m less m. The page, the marker.
- **A move** of the file at row r of the folder k before the file at row b, or last: k's
  file with the row moved; the map's rows of k between them following; the table's CRC-32
  of k; the marker, with the mask of no page.
- **A rebuild or an import**: everything, as below.

The PC tool does each in memory and writes the same bytes through the same calls; the
core streams each file from the old one through the chunk buffer, row by row, with the
second source.

## The rebuild and the import

A rebuild reads every file the host lists, the import every file of the folder, without
a limit; both keep the rows' order of the old index. Both write the same files:

1. **The check.** Each listed file, in the listing's order, is checked: an ODRG or ODRGX
   file of a name a catalog may hold and of the canvas passes, with its CRC-32, size,
   length and type; any other is refused. The import checks for the canvas of 60 x 60,
   the rebuild for the mapping's, as today.
2. **The pages.** Each page holds the lines of the passed files of its names, in the
   listing's order, as today.
3. **The table.** The folders of the passed files, each with every ancestor, in the
   listing's order, the root first: ordinals from 0, ids by the rule above, `<first>` the
   passed files before the folder's first file in the listing, `<files>` its passed own
   files, `<folders>` its sub-folders in the table, `<end>` after its last descendant in
   the table.
4. **The folders' files.** For each folder of the table, in its order: first the rows of
   the old index's file of the folder's path, in their order, of the files that passed;
   then the passed files of the folder that the old catalog's pages have no line for, by
   the bytes of their names; each file row with its new data and the next id of the walk;
   then a folder row for each of its sub-folders in the table. The old index and the old
   pages are used when the old marker is a whole marker of version 2, and not otherwise:
   then every folder's files are by the bytes of their names. Both writers look a new
   file up on the old pages, which the core reads fast, and not among the old rows.
5. **The map.** The files' ids in the walk's order, then the folders'.
6. **The commit.** The marker with the generation one more, or 1, and the record with
   every page in its mask, the removals of the old index's folder files whose ids the new
   table does not have, the moves of the new folders' files, of the table and of the map.

**In the PC tool** these are list operations: `rebuild(storage, names=None, canvas=...,
generation=None)` of a storage that is a drive (`Storage(folder, drive=True)`,
`MemoryStorage(files, drive=True)`) writes version 2 with its index, and of any other
storage version 1 as today. `Storage.names()` lists every animation file, without
`cut_listing`, which stays for a listed drive's limits.

**In the core** the rebuild runs in phases, one step at a time at the check's pace, with
no memory beyond the core's own, through two files of its own in the drive's folder that
no reader reads: `rebuild.tmp` and `rebuild-folders.tmp`.

- **Scan.** The host lists the drive once (`drive_list`); each listed name, in its order,
  is checked with the check's steps (`check_file_step`) and gets a line of 180 bytes in
  `rebuild.tmp`: `<passed> <crc> <bytes> <width> <height> <length> <type> <path>`, `1`
  for a passed file, `0` and zeros for a refused one. A listed drive's file of the table
  joins the playlist as the scan passes it, as today.
- **Pages.** For each page, one pass over `rebuild.tmp` writes the passed lines of its
  names into `catalog-NN.new`; the counts and CRC-32s wait at the end of the chunk buffer
  as today.
- **Draft.** One pass over `rebuild.tmp` writes the table, without the CRC-32s, into
  `rebuild-folders.tmp`. At each folder that the pass meets, in the listing's order, a
  look ahead over the lines of its subtree, which are one range of the file since the
  listing is depth first, counts its own passed files and finds the folders below it with
  a passed file, keeping the last counted path at each of the three depths; a folder
  without a passed file at or below it is passed over. Each line is read at most once for
  each of its at most four ancestors.
- **Folders.** For each line of the draft, the folder's file `index-<id>.new`: the old
  rows of its path, found in the old table, each looked up in `rebuild.tmp` by binary
  search in the listing's order; then its passed files in `rebuild.tmp`, a range found by
  binary search, each looked for on its page of the old catalog; then its folder rows
  from the draft's lines below it.
- **Map.** One pass over the draft writes `index-ids.new`.
- **Table.** One pass over the draft writes `index-folders.new`, each line with the
  CRC-32 of its folder's file, read again whole.
- **Commit.** The marker and the record, the finishing, and `rebuild.tmp` and
  `rebuild-folders.tmp` removed. The drive is read again from its new index, as after
  another marker.

`catalog cancel`, a failed call and a drive pulled out end the rebuild without its record:
the `.new` files it wrote and its two files are removed, but from a drive that is gone.
While the rebuild runs, an indexed drive plays from its old index, which no step changes.

## The core

### Positions and the walk

A drive's file is the position `kDriveBase + w`, w its position in the walk: the root's
files, then each folder's in the table's order, each folder's in its rows' order. For a
listed drive, w is its place: the core's cut keeps the listing's order, which is the walk.
`kNothing` and `kPlaylist` stay above every position.

The current playlist is the record of its folder: its ordinal, id, depth, `<end>`,
`<first>` and the position after its subtree, the `<first>` of the line at its `<end>`.
Its range is the show's items and every w for the root, and w from its `<first>` to the
end of its subtree for a folder. The walk's next animation after a position is the next
that plays in the range: after a show item the next show item in the saved order, then the
range's first file; after a file the next row that plays, and after the range's last the
range's first animation. A file plays unless it is left out; a row is read to know it.
The whole rounds that `playlist_turn` takes off at once are taken only while the drive is
not indexed, since summing them would read every row: with an indexed drive a long time
without a refresh is walked turn by turn, one row at each.

The rotation makes the next ordinal of the table current, the root after the last, and
reads its line; a choice by `play <folder-id>` reads the map and the line. The current
playlist's path is kept in `playlist.txt` as today; a drive read again finds its folder
by its path in the table.

### The cursor

The drive's block, taken at the start for a host with a drive whose storage can be
changed, holds:

- the room of 512 bytes for one read, with which file and offset it holds, so that rows
  read again come from it: a read takes as many whole rows as fit;
- the counts of the marker's table and map, and the number of files;
- the row of the animation whose turn it is and one more row, each with its position, id,
  CRC-32, size, length, canvas, type, its fault and its path: `play`, `list` and the walk
  read into the second, and the turn's row is kept while it plays;
- the current playlist's record, and the number of files left out since the drive was
  taken up.

For a listed drive the same calls answer from the table of 256 and the tree: a row from
the place's entry and its name from the host, a folder's record from the tree, whose
records gain `first` and `files` in place of the place they named. The per-place keys of
the saved order, their hashes and the folder byte of each place go.

### The plug-in and the look

The plug-in reads the commit record, finishing a whole one on a drive that can be
written, and the marker; a marker of version 2 makes the drive indexed at once, its
animations in the playlist and `list`, with no page and no row read. A marker of version 1
is `incompatible`. The look reads the marker every 10 seconds as today; the core's own
commits give it the new marker's CRC-32. Another marker drops the drive's positions, as
a pull does, and reads the catalog again.

### Faults

A row whose canvas is not the mapping's is left out with `size-mismatch`, and one whose
name and CRC-32 are among the 16 remembered faults with that fault: both listed with
`"bytes":null` and `fault`, refused by `play` with `unavailable`, and passed over by the
walk. A file that cannot be played while it plays is remembered by its name and its row's
CRC-32, logged as `drive file <name> left out: <reason>`, counted as unavailable, and the
playlist goes on as today. A row out of its form, or a file shorter than its rows, makes
the catalog `damaged`, `line`, and the drive's animations go, as a damaged page does today.

### Changes and the positions held

After an upload, a removal or a move the positions the core holds follow the walk: an
upload of a new file at the root's row r moves every w at or after r on by one, a removal
of w moves every w after it back by one, a move moves the rows between its two places;
the turn's row is read again. The files of the drive that is changed are opened by their
paths, which a change does not move but for the file it removes or replaces, which the
player closes first as today.

### The saved order

`order.txt` keeps the show's items: its `x` lines are passed over and the next write
leaves them out. A show's item has the key of its entry, or 0x10000 and its position;
the drive's files have no key. `order get` writes the root level: the show's animations by
key, then the root's files by row; `order get in <id>` a folder's files by row. The
revision is the CRC-32 of the level's ids in that order, each as four bytes, low byte
first. `order move` of a show item writes `order.txt` as today, `<before>` a root's file
putting it last among the show's items; of a drive's file it commits the drive's catalog
with its folder's file moved, `<before>` a show item putting it first among the root's
files; `<before>` of another level is `in-use`, and a drive's file of a listed drive, or
of a drive the core may not write, `read-only`.

### The listed drive's cut

Every host but the firmware lists every animation file of the drive. The core takes a
listed drive's first 256 files, counting a folder with its uncounted ancestors when the
first file at or below it is kept, and stops at the first file whose folder would be the
33rd, the rule `cut_listing` keeps. The firmware still cuts at the same limits, so on the
board a rebuild indexes at most 256 files and 32 folders; the PC tool's `import` indexes a
bigger card.

### Memory

| Block | Today | Now |
|---|---:|---:|
| The drive's table, 12 for each of 256 places, for a listed drive | 3,072 | 3,072 |
| The boot's memory of 16 files | 640 | 640 |
| The saved order: 2 for each of 132 items | 264 | 264 |
| The saved order: 4 for each of 256 places | 1,024 | 0 |
| The tree: 33 records of 8 bytes and 104 for the path | 368 | 368 |
| The drive's cursor | 0 | about 820 |

The cursor's exact size is what the suite measures; the total stays below 130,509 bytes
and the core object below 4,096, the rebuild's few counters moving into the core object
in place of the fields that go.

## The replies

- `list [<from>]`: the show's items, then the root's folder rows, then the root's files;
  `list in <folder-id> [<from>]`: a folder's folder rows, then its files. A folder item is
  `{"id":60007,"playlist":"night","external":true,"files":2}`. `<from>` counts the level's
  items, 0 to 4,294,967,295.
- `status`: `"file"` and `"playlist"` after `seed` and before `left`: the file of
  `animation`, a show item's file or a drive's path, and the path of the folder `playing`
  names, each `null` otherwise.
- `order get [<from>]`, `order get in <folder-id> [<from>]` as above.
- Ids in every command: `play`, `read`, `remove`, `ignore`, `order move`, `list in`,
  `order get in` take 1 to 4,294,967,295; `remove many` and `upload begin` keep the show's
  range of 1 to 65,535.

## The app

`client.js` keeps one level: its path, its folder's id (null for the root), its items and
their order, read with `list` or `list in <id>` and `order get` or `order get in <id>`, in
parts as today; entering a folder or going back drops the level and reads the new one.
`state.animations` and `state.folders` are the level's; the status's `file` and
`playlist` name what plays, and a `playing` id the level has not got is no reason to read
the list again. The explorer of `show.js` shows the level as it is read; a folder row's
count is its `files`; the marks follow `status.playlist`. `capacity.js` counts the drive's
animations by the external catalog's `entries` while it is `ok`, and does not count them
otherwise.

## The command tool

`odrigctl list in ID [FROM]` and `odrigctl order get in ID [FROM]`: without FROM every part
of the level is printed, as `list` prints every part.

## The hosts

- `emulator/host.py`: `drive_list` lists every animation file, depth first, without
  `drive_cut`.
- `tests/core/host/host.cpp`: `list_drive` the same; its names check takes the index's and
  the rebuild's files.
- The firmware is not changed: it lists 256 files and 32 folders, opens a drive's file by
  its path, and passes every command to the core as text.

## Testing

- `tests/converter/`: the index of an import, of an upload, a replacement, a removal that
  empties a folder and one that empties its parent, a move; the order kept by a rebuild
  with files added and removed; the ids; the marker of version 2 and version 1's
  incompatibility; `status`, `check`, `recover`; a vector of a card with an index.
- `tests/core/`: the levels of `list` and `list in`, `status`'s `file` and `playlist`;
  an indexed drive of more than 256 files and 32 folders played, listed and walked, with
  `play` of any id; the reads of a plug-in and of a turn's end (`--trace-read-at`); the
  faults; uploads, removals, moves and rebuilds byte for byte the PC tool's, with power
  cuts at every step; the cancel; the memory.
- `tests/emulator/`: the `--drive` folder of more than 256 files, read-only and written.
- `tests/app/`: the levels read one at a time, the counts, the moves and the marks.
