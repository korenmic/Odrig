# Catalogs

Each storage of animations keeps a catalog of what it holds: the board's own storage, and
the folder `odrig` of the card or USB drive in it. A catalog says, for each animation file,
its size, CRC-32, canvas, length and type, so that the board does not read the animations
to learn them again at every start. A drive's catalog also keeps an index of its files,
folder by folder in the order they play, with their ids, so that the board keeps none of
them in memory and a drive holds as many files as its card. This page states the format,
how a change is made and finished, who writes catalogs, and what each operation costs.

`show.json` stays the authority of the playlist ([show.md](show.md)), `order.txt` of its
saved order, and `mapping.json` of the LEDs ([mapping.md](mapping.md)). A catalog is the
authority of what a file holds. An entry for a file that the show does not name is not an
animation of the show; a file of the show without an entry is read as a storage without a
catalog is.

## The files

All text is ASCII; every line ends with one line feed; numbers are decimal without leading
zeros, `0` for zero; CRC-32s and the generation are 8 lowercase hexadecimal digits. The
CRC-32 is that of zlib and PNG.

### The marker: `catalog.txt`

Always 409 bytes, 18 lines:

```
odrig-catalog 1 check 1 generation 0000002a
page 00 0003 1a2b3c4d
page 01 0000 00000000
...
page 15 0001 9f00e1aa
crc 0a1b2c3d
```

- Line 1: the format's version, 1; the version of the check that admitted the entries,
  `check 1`, the check of ODRG version 1 that [reasons.md](reasons.md) states; and the
  generation, 1 for a first catalog and one more at each change, 00000001 after ffffffff.
- Lines 2 to 17: for page `00` to `15`, its number of entries in four digits and the
  CRC-32 of its file, or `0000 00000000` for a page without entries, which has no file.
- Line 18: the CRC-32 of the 396 bytes before it.

That is the marker of the board's own storage. A drive's is of version 2: always 461 bytes,
20 lines, with two lines more before its `crc` line, which names the index:

```
odrig-catalog 2 check 1 generation 0000002a
page 00 0003 1a2b3c4d
...
page 15 0001 9f00e1aa
folders 0000000004 0a1b2c3d
ids 0000000008 5e6f7a8b
crc 0a1b2c3d
```

- Line 18: `folders`, the number of lines of the table of the folders in ten digits and the
  CRC-32 of its file; the table has a line for the root always.
- Line 19: `ids`, the same of the map of the ids, `0000000000 00000000` when the drive has
  no file.
- Line 20: the CRC-32 of the 448 bytes before it.

Each reader takes only its storage's version: a drive's catalog of version 1, and a
catalog of version 2 in the board's own storage, are `incompatible`.

### The pages: `catalog-00.txt` to `catalog-15.txt`

One line for each animation:

```
1a2b3c4d 52340 60 60 12000 frames sunrise.odrg
```

The file's CRC-32, its size in bytes, its width and height, its length in milliseconds,
its type and its name. An ODRG file is of `frames`, its length the sum of the durations of
its frame records; an ODRGX container of [format.md](format.md) is of the type its header
names, `frames`, `text` or `widget`, its canvas and its length the header's, the loop. What
a file is, its first four bytes say, not its name. The page of a name is the low four bits
of the FNV-1a hash of its bytes, the whole path of a file in a sub-folder. A page's lines
stand in the order their entries came in: a rebuild writes them in the storage's order, an
addition puts its line last on its page, a replacement keeps its line's place, a removal
takes its line out. A line is at most 161 bytes.

The first two words of a line are the file's key, its CRC-32 and its size joined by a dash,
`1a2b3c4d-52340`: two files of the same bytes have one key whatever their names. The
operators' app learns the keys of a storage by reading its pages with `catalog page`
([commands.md](commands.md#catalogs)) and finds the preview of each animation by its key.

A name is the path of the file from the storage's folder: the names of at most three
folders and the file's name, joined by `/`, 1 to 100 bytes in all. Each part is printable
ASCII other than `/ \ : * ? " < > |`, neither beginning nor ending with a space or a dot. A
folder's name may be digits alone; the file's name is not, and ends in `.odrg` or `.odrgx`
in any case. A card's folder `odrig` is listed as a drive is: a folder's animation files by
the bytes of their names, then its sub-folders by the bytes of their names, each the same
way, every file of it; only a drive without a catalog is taken as at most 256 files and 32
sub-folders, a folder counted with its uncounted ancestors when the first file at or below
it is kept. A name of the board's own storage follows the
show's rule too: 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_` and `.`, so it holds no
folder. A reader from before paths were names finds a catalog that names a file in a
folder `damaged`, with `line` saying where.

### The index of a drive

A drive's catalog keeps its files a second way, beside the pages: in the order they play,
folder by folder, each with its id. The index is three kinds of file in the folder `odrig`.
Every line of a kind has one length, padded with spaces before its line feed, so that line
N of a file is at N times that length and a read of 512 bytes gives whole lines; a line's
last field is everything after its fixed fields with the padding cut off, which a name
never ends in.

**A folder's file, `index-<id>.txt`**, the root's `index-0.txt`: lines of 180 bytes. First
the folder's own animation files, in the saved order, each with its id and the fields of
its entry, then its sub-folders in the table's order, each with its id, its number of own
files and its path:

```
60001 f 1a2b3c4d 52340 60 60 12000 frames sunrise.odrg
60002 f 5e6f7a8b 1882 60 60 20000 text moon.odrgx
60006 d 1 night
60008 d 0 only
```

A folder without a line has no file.

**The table of the folders, `index-folders.txt`**: lines of 180 bytes, one for each folder
that has an animation file at or below it, the root first and always, in the listing's
order, depth first:

```
0 0 0 4 0 2 2 9f00e1aa
1 60006 1 3 2 1 1 0a1b2c3d night
2 60007 2 3 3 1 0 4c1e00a7 night/deep
3 60008 1 4 4 0 1 5e6f7a8b only
```

Its ordinal, the line's number; its id, 0 for the root; its depth, 0 for the root and 1 to
3 below it; the ordinal after its last descendant, so that its subtree is the lines from it
to there; the number of files of the folders before it, so that its files are the
positions of the walk from there, the walk being the root's files and then each folder's
in the table's order; its numbers of own files and of sub-folders; the CRC-32 of its file,
`00000000` without one; and its path, empty for the root. A folder with no file at or
below it is in no line of the table.

**The map of the ids, `index-ids.txt`**: lines of 36 bytes, one for each id of the drive,
sorted by id, so that an id is found by binary search: a file's to its folder's ordinal
and its line there, a folder's to its own ordinal and 0:

```
60001 f 0 0
60006 d 1 0
```

**The ids** are numbers from 60001 up to 4,294,967,295. A rebuild and an import give the
files theirs in the walk's order, a file's being 60001 and its position, and then the
folders theirs in the table's order; an upload of a new file takes the lowest id the map
does not hold, a replacement keeps its file's, and a removal frees its file's and those of
the folders it leaves without a file. No writer looks at the board's show: where an item
of the show has a drive's id, the commands mean the item.

The index agrees with the pages: the same files, with the same fields, and no file twice.
A reader that finds an index file shorter than its lines or with another CRC-32 than the
marker or the table gives it finds the catalog `damaged` with `page`, and one whose lines
are not those its folders make, or that do not agree with the pages, with `line`. The
board's core reads a drive's marker when the drive is plugged in, and the index's lines
only as it needs them: a line out of its form, or a file shorter than its lines, makes the
catalog `damaged` with `line` once it is read there; it does not read the pages or the
CRC-32s of the index's files, which the PC tool checks.

### What a reader finds

| State | When |
|---|---|
| `none` | There is no `catalog.txt`: the storage has no catalog. |
| `ok` | The marker is whole, every page with entries has a file whose lines and CRC-32 agree with it, every line is in its form, on its page, and no name is there twice. |
| `incompatible` | The marker names another version of the format or of the check. |
| `damaged` | Anything else: `marker`, `page` or `line` says where; `interrupted` is a whole commit record on a storage the reader cannot finish it on. |

The tests' vectors, in `tests/vectors/catalog/`, hold a storage for each case with the
outcome in `cases.json`; `python -m tests.converter.build_catalog_vectors` writes them again.

## A change

A change is a set of entries to add, replace or take out, with the file actions that go
with it: `move <from> <to>` and `remove <name>`. Its writer:

1. writes each page the change touches whole as `catalog-NN.new`, from its old file with
   the change applied; a page left without entries gets no file, and an old
   `catalog-NN.new` of it is removed;
2. writes the new marker as `catalog.new`, with the generation one more;
3. writes the commit record `catalog.do`:

   ```
   odrig-catalog-do 1 generation 0000002b
   pages 0008
   move upload.part sunrise.odrg
   crc 4c1e00a7
   ```

   the generation, the mask of the pages touched (bit N for page N), the actions in
   order, and the CRC-32 of the bytes before the `crc` line. **The change is committed
   when `catalog.do` is whole.**
4. finishes it: each action (a `move` whose source is gone is done already, a `remove`
   that finds no file too); each touched page, its `.new` file renamed onto
   `catalog-NN.txt`, or `catalog-NN.txt` removed when the page is now empty;
   `catalog.new` renamed onto `catalog.txt`; `catalog.do` removed.

Every file is written whole, through a new file, before a rename puts it in place. A writer
that finds a whole `catalog.do` finishes it before anything else, so that a cut at any
step comes to the catalog before the change or the one after it. A step that fails stops
the finishing there: `catalog.do` stays, and the next attempt goes on from that step. While
a whole `catalog.do` is left, no change begins and the `upload.part` it may move stays. A `catalog.do` that is not
whole, and `.new` files without one, are traces of a change that was not committed: they
are never read.

An upload adds or replaces with the action `move upload.part <name>`: the file is checked
as `upload.part` and becomes the animation in the same commit as its entry. A removal takes
the entry out with `remove <name>`.

### A drive's index in a change

A change of a drive's catalog writes each index file it changes whole as `.new` beside its
pages, before its marker, and its record names each one: `move index-0.new index-0.txt`,
or `remove index-60008.txt` for the file of a folder that leaves the table. The actions
stand in this order: the removals of the files of the folders that left, the animation's
own action, then each folder's file in the table's order, the table and the map:

```
odrig-catalog-do 1 generation 0000002b
pages 0008
move upload.part sunrise.odrg
move index-0.new index-0.txt
move index-folders.new index-folders.txt
move index-ids.new index-ids.txt
crc 4c1e00a7
```

What each change writes, besides its page and the marker:

| Change | The index files written |
|---|---|
| An upload of a new file, into the root: its line after the root's last file line, the lowest free id | the root's file, the table (the root's files one more, every other folder's first position one more), the map |
| A replacement: its line anew, its id and place kept | the root's file, the table |
| A removal of a file of folder k | k's file, and its parent's, whose line for k says one file less; when nothing is left at or below k, k and each ancestor left so leave the table, their files are removed and the parent of the topmost loses its line for it; the table; the map |
| A move of a file among its folder's files, before another or last | the folder's file, the table, the map; no page, the mask `0000` |
| A rebuild or an import | everything: every page, every folder's file, the table and the map, and the removal of the files of the old table's folders whose ids the new one does not have |

A rebuild and an import keep the order the drive's files were moved into. For each folder of
the new table they put first the files of the old index's file of its path, in their
order, that are still there and pass; then the folder's other files that pass and that
the old pages have no line for, by the bytes of their names. They take the old index when
its marker is of version 2 and every page, the table, the map and each folder's file agree
with their CRC-32s and each line is in its form; otherwise every folder's files are by the
bytes of their names. The PC tool's `import` takes every animation file of the folder; the
board's rebuild every file its host lists. The board checks the old index as the PC tool
does, a file at each step, before it writes the new one; it finds an old row's file in its
scan by binary search in the listing's order, and looks a folder's other files up on their
old pages, which stay in place until the commit.

## The writers

The board's core, in C++, and the PC tool, in Python (`odrig/catalog.py`), are the two
implementations of this page, the one duplicate the owner approved on 2026-10-24. They make
the same changes with the same calls of the storage, so that the same changes from the same
storage leave the same files, byte for byte; the tests run both on the same storages. They
never work on one storage at once: the board changes a card while it is in the board, a
computer while it is mounted there.

## What each operation costs

N is the number of animations of the storage, P the number of entries of the page a change
touches (N / 16 on average, at most N), S the size of an animation.

| Operation | Animation bytes | Catalog |
|---|---|---|
| A start | none of a cataloged file | the marker once, and the pages twice: checked, then taken |
| A drive with a catalog plugged in | none | the commit record and the marker, 461 bytes; no page; the index's lines later, as the core needs them, at most 512 bytes at a read |
| An unchanged drive | none | one read of the marker, 461 bytes, in 10 seconds |
| An addition or a replacement | S written and S read back by the check | one page of P lines read and written, the marker, the commit record; on a drive also the root's file of the index and the table, and for a new file the map, each read and written a line at a time |
| A removal | the file removed | one page, the marker, the commit record; on a drive also the file of its folder and of the parent, the table and the map |
| A rebuild or an import | every file read whole | every page, a drive's index and the marker written |

No change lists the storage, reads another animation or writes another page; a rebuild is
the one operation that reads the whole library, and it is a command.

Measured through the core's test host, with refreshes 20 ms apart:

| Case | Without a catalog | With a catalog |
|---|---|---|
| A start of the target file: 80 animations of 2,852 bytes, 228,160 in all | 80 files opened, 40,960 bytes read at the start, and the 228,160 bytes read again by the check after it | no animation opened or read; 7,289 bytes read of a catalog of 3,849 |
| A drive of 16, 64 and 256 animations plugged in | listed, and every file read before it plays | catalogs of 1,081, 3,097 and 11,161 bytes read in 7, 7 and 10 refreshes, at most 2,090, 1,947 and 2,266 bytes at one, 7,652, 9,674 and 17,738 bytes in all; no listing |
| The same drive unchanged | nothing | 410 bytes once in 10 seconds |
| An addition among 16, 64 and 256 animations | the file and the show file | 623, 707 and 1,169 bytes of the catalog written: the page (123, 207 and 669 bytes), the marker (409) and the record; 12 files opened, renamed or removed at each size |
| A rebuild of the target file | | done in the first second; 3,849 bytes of the catalog written, the same as the PC tool's |

Measured on the emulator on Windows, with a drive of 1,000 animations of 1,469 bytes in 50
folders of 20, indexed by the PC tool's `import` in 9.2 seconds: a catalog and index of 70
files, 281,441 bytes. Over HTTP the root's level, 50 folders, came in 4 replies, 5 ms in
all, and the 50 folders' levels in 100 replies, the slowest 24 ms; `play 60300` played
`f14/c19.odrg`, the 300th file, and `status` named it; after `play 60255` the playlist went
on to the 256th file and the four after it. `catalog rebuild external` took 7.6 seconds, and
its files were byte for byte those of the PC tool's rebuild of the same card.

The board's own figures are measured in its session: the first reply, the first list with
sizes, the first picture and the card's catalog published.
