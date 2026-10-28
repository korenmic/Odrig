# Requirements: more than 256 files on a drive

Seed: [`project-seeds/50-p2-more-than-256-files-on-a-drive/seed.md`](../../../project-seeds/50-p2-more-than-256-files-on-a-drive/seed.md).

A drive's catalog gains an index, written beside its pages by the same two writers, so
that the core keeps a cursor over the drive instead of a table of its files, and a drive
holds as many animation files and folders as its card. The seed has no open question: the
owner approved its four decisions on 2026-10-28, the 32-bit ids, the index as the drive's
saved order, the forms `list in <folder-id>` and the playing animation named by `status`,
and a drive without a catalog kept as it is; and the change of the memory decision. Where
a requirement decides a point the seed leaves open, the decision is recorded in
[drifts.md](../../drifts.md) under "Seed 50".

In this document "the drive" is the external storage as the core sees it, the board's
microSD card, a USB stick or the emulator's `--drive` folder; "an indexed drive" is one
whose catalog is `ok` in the format of version 2, with its index; "a listed drive" is one
without such a catalog, listed by its host; "a folder" is a sub-folder of the drive's
folder `odrig` at any depth up to three, "the root" the folder `odrig` itself; "a level"
is what one folder holds directly, its sub-folders and its own animation files, the
root's with the show's items; "the walk" is the order the playlist plays a drive's files
in, the root's first and then each folder's in the tree's order; "the PC tool" is
`python3 -m odrig.catalog` and its library `odrig/catalog.py`; "the test host" is
`core/build/odrig_host`.

## Requirement 1: the index

1. A drive's catalog SHALL be of format version 2: the marker of version 1 with two lines
   more before its `crc` line, one naming the table of the folders and one the map of the
   ids, each with its number of rows and the CRC-32 of its file. The board's own catalog
   SHALL stay of version 1. A reader SHALL find a drive's catalog of version 1, and an
   internal one of version 2, `incompatible`.
2. The index SHALL be three kinds of file in the drive's folder `odrig`: for each folder of
   the table, the root among them, a file of its rows; one table of the folders; one map
   of the ids. Every line of an index file SHALL have the length that file kind has,
   padded with spaces before its line feed, so that row N stands at N times that length.
   All text SHALL be ASCII, numbers decimal without leading zeros, CRC-32s eight
   lowercase hexadecimal digits.
3. A folder's file SHALL hold its own animation files in the saved order, each with its
   id, its CRC-32, size, canvas, length, type and path, then its sub-folders in the
   listing's order, each with its id, its number of own files and its path.
4. The table SHALL hold every folder that has an animation file at or below it, the root
   always, in the listing's order, depth first, each with its ordinal, its id, its depth,
   the ordinal after its last descendant, the number of files before it in the walk, its
   numbers of own files and of sub-folders, the CRC-32 of its file and its path, so that
   a folder's subtree is a range of the table and its files a range of the walk.
5. The map SHALL hold every id of the drive, sorted by id: a file's to its folder's
   ordinal and its row, a folder's to its own ordinal; an id SHALL be found in it by
   binary search.
6. The index SHALL agree with the catalog's pages: the same files, with the same CRC-32,
   size, canvas, length and type, and no file twice.

## Requirement 2: ids

1. The ids of a drive's files and folders SHALL be numbers from 60001 up, without an upper
   bound below 4,294,967,295, kept in the index. A rebuild and an import SHALL give the
   files ids in the walk's order from 60001, and the folders the ids after them in the
   table's order. An upload of a new file SHALL take the lowest id from 60001 up that the
   map does not hold; a replacement SHALL keep its file's id; a removal SHALL free its
   file's id, and a folder's when the folder leaves the table.
2. The writers of the index SHALL not consider the show's ids. Where an item of the show
   has a drive's id, every command SHALL mean the show's item, as `play` does today.
3. A listed drive's files and folders SHALL keep today's ids: the lowest from 60001 up
   that neither the show nor the drive uses, given when the drive is taken up.
4. Every command that takes an id SHALL take 1 to 4,294,967,295, and every reply SHALL
   write an id as the number it is. The show's items keep their ids of 1 to 65,535: an
   upload to the show of an id above 65,535 SHALL be refused with `bad-argument`.

## Requirement 3: the writers

1. The core and the PC tool SHALL write the index in the same commit of the drive's
   catalog as its pages and its marker, with the commit record of
   [catalog.md](../../catalog.md) naming each index file it puts in place or removes, so
   that a cut at any step leaves the catalog and its index before the change or after it.
2. For the same change of the same storage the two writers SHALL leave the same files,
   byte for byte: an import and a rebuild, an upload, a replacement, a removal, and a
   move of a drive's file.
3. An upload or a replacement SHALL rewrite the root's file, the table, the map, the
   catalog's page of the name and the marker; a removal SHALL rewrite its folder's file
   and its parent's, the table, the map, the page and the marker, and SHALL remove the
   files of the folders it leaves without a file; a move SHALL rewrite its folder's file,
   the table, the map and the marker. Nothing else of the catalog SHALL be written.
4. A rebuild and an import SHALL write every file of the catalog and its index, keep for
   each folder the order of the rows they find in the old index for the files still
   there, put the new files after them by the bytes of their names, and remove the files
   of the folders that are no longer in the table.
5. The PC tool's `import` SHALL index every animation file of the folder, without a limit
   of 256 files or 32 folders; its `status` and `check` SHALL say whether the index agrees
   with the catalog; `recover` SHALL remove the traces a rebuild leaves.

## Requirement 4: the core's cursor

1. For an indexed drive the core SHALL keep the record of the folder of the current
   playlist, the row of the animation whose turn it is, the room for one read of 512
   bytes, the path of the current playlist and the window's time, and the 16 remembered
   faults of the boot; no table of the drive's files, no per-place block of the saved
   order and no tree.
2. At a plug-in the core SHALL read the commit record and the marker, and no page and no
   row: the drive's animations SHALL be in the playlist from then on, none of its files
   read before it plays.
3. The core SHALL read a row only when it needs it: the next row of the walk at a turn's
   end, the map and one row for `play <id>`, the rows of one level for `list`, a row of
   the table for a choice or the rotation, at most 512 bytes a read.
4. A row out of its form SHALL make the drive's catalog `damaged`, `line`, and its
   animations leave the playlist and `list`.
5. A file of an indexed drive that cannot be played SHALL be left out for the rest of the
   boot by its name and CRC-32 among the 16 remembered faults, logged as today, and
   listed with its fault; a row made for another canvas SHALL be left out with
   `size-mismatch`.
6. The marker SHALL be read again once in 10 seconds; another marker SHALL drop the
   drive's animations and read the catalog again, as today.

## Requirement 5: the playlist

1. A drive's files SHALL play in the walk: the root's playlist the show's animations in
   the saved order, then the root's files in their rows' order, then each folder's files
   in the table's order; a folder's playlist its own files and then its subtree's the same
   way. The windows, the rotation, the jump and the root in a folder's place SHALL stay as
   [show.md](../../show.md) states them.
2. `order.txt` SHALL keep the show's items only. Its entries `x <name>` SHALL be passed
   over, and written no more. The order of an indexed drive's files SHALL be the rows of
   its folders; that of a listed drive's files the listing's.
3. A listed drive SHALL be cut by the core: at most 256 files and 32 sub-folders, a folder
   counted with its uncounted ancestors when the first file at or below it is kept, the
   rest passed over. Every host but the firmware SHALL list every animation file of the
   drive; the firmware keeps its listing.

## Requirement 6: the commands

1. `list` and `list <from>` SHALL give the show's items and the root's level: the root's
   folder rows, then the root's own files. `list in <folder-id>` and `list in <folder-id>
   <from>` SHALL give that folder's level, its folder rows then its own files, with
   `next` as `list` has it, `<from>` 0 to 4,294,967,295; `unknown-id` for an id that is
   no folder of the drive.
2. A folder row SHALL carry the number of the folder's own files as `files`.
3. `status` SHALL name the file of the animation on the LEDs as `file`, a drive's by its
   path, and the path of the current playlist's folder as `playlist` while `playing` is a
   folder's id; each `null` otherwise; `left` stays its last member.
4. `order get` SHALL give the root level's animations in the saved order, and `order get
   in <folder-id>` a folder's, each with a revision of its own level.
5. `order move` of a drive's file SHALL move it among its folder's rows, on an indexed
   drive the core may write, in one commit of the drive's catalog; of a show's item among
   the show's items as today; `in-use` for a `<before>` of another level, `read-only` for
   a drive the core may not write and for a listed drive's file. A `<before>` of the
   other kind in the root's level SHALL put the moved animation as near to it as its own
   order allows.
6. `play <id>` of any file or folder of an indexed drive SHALL play it, and `status` name
   it, by its id, within the reads of one map search and one row.
7. `upload begin external` SHALL be refused with `no-space` only when the drive's space
   says the file does not fit; `remove`, `read` and `upload begin` SHALL find an indexed
   drive's file through the map.

## Requirement 7: rebuilds and imports

1. `catalog rebuild external` SHALL index every file the host lists, with no limit of 256
   files or 32 folders, in steps at the pace of the check, with no memory but what the
   core holds already; a drive that can be written SHALL get its index from it and keep
   it across starts.
2. While a rebuild runs, an indexed drive SHALL go on playing from its old index, and a
   listed drive's files SHALL join as the rebuild reads them, as today; at the commit the
   drive SHALL be read from its new index.
3. A rebuild that is cancelled, fails or loses its drive SHALL leave the catalog and its
   index as they were and remove what it wrote.

## Requirement 8: memory

1. The core's memory with a drive SHALL be less than today's 130,509 bytes for the target
   file, measured by the suite, and no block SHALL be asked for beyond the drive's cursor
   with its room for one read of 512 bytes.
2. The core object SHALL stay within 4,096 bytes.

## Requirement 9: the app and the command tool

1. The app SHALL read a level when it enters it, and again when it is out of date, with
   `list` for the root and `list in <folder-id>` for a folder, and SHALL keep nothing of
   the other levels. Its filters, selection, moves and counts SHALL work on the level
   shown, its folder rows SHALL show each folder's own files, and what plays SHALL be
   named from `status`.
2. The app's count of the drive's animations SHALL be the entries of the drive's catalog
   while it is `ok`.
3. The command tool SHALL send `list in ID [FROM]` and `order get in ID [FROM]`, and print
   every part of a level as it prints every part of `list`.

## Requirement 10: the pages and the checks

1. `docs/catalog.md`, `docs/core.md`, `docs/show.md`, `docs/commands.md`,
   `docs/android-app.md`, `docs/microsd.md` and the change log of `docs/decisions.md`
   SHALL say what exists, and `docs/emulator.md` where it names the drive's limits.
2. On the emulator a drive of at least 1,000 files in 50 folders, indexed by the PC tool,
   SHALL list every file level by level and play through every folder, and the same
   drive rebuilt by the core SHALL have the PC tool's files, byte for byte.
3. Every suite that runs on Windows SHALL pass there but for the failures of `master` it
   does not touch, which are named in the hand-over.
4. The board's session, the owner's collection on its card with its index, and the
   owner's look at the explorer on a phone, SHALL be left open for the owner.
