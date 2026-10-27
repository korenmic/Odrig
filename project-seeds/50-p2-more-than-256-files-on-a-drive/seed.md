# More than 256 files on a drive

## Summary

A drive, the board's microSD card or the emulator's `--drive` folder, shows at most 256
animation files in all, however they are spread over its sub-folders, and at most 32
sub-folders. The core keeps a 16-byte entry in memory for every file of the drive, in a
fixed budget that is 99 percent used. This seed takes those entries out of memory and
puts them on the card, beside the catalog, as an index: one file per folder of
fixed-width lines in the playlist's order, a table of the folders, and a map of the ids.
The core keeps a cursor and reads the row it needs when it needs it, as it reads the
catalog today. The number of files and folders is then bounded by the card alone.

## Priority

- `P2`

## Depends On

- Seed 35, the catalogs: the index is written and committed with the catalog, by the
  same two writers, the core and the PC tool.
- Seed 41, sub-folder playlists, whose tree and current playlist the index takes over.
- Seed 36, the saved order, and seed 42, the seek bar, whose commands name a drive's
  animation by its id.
- Seed 44, the previews, whose `catalog page` the app reads by key: unchanged.

## Product Context

The owner's collection, `E:\artifacts\odrig\collection`, holds 359 animation files in 18
folders; 103 of them are never listed. The collection grows.

Why the limit exists. The core takes no memory beyond one fixed budget, 131,072 bytes for
the 60 x 60 installation (`docs/core.md`, "Memory"), and keeps for each place of a drive
its state, size, length and id (12 bytes), its key in the saved order (4 bytes) and its
folder (1 byte); `kDriveMost = 256` in `core/src/core_state.h` sets the places, and
`kFolderMost = 33` the folders. With 256 places the target file takes 130,509 bytes. The
entries serve three jobs: walking the playlist to the next animation in the saved order,
finding a file by its id for `play` and `status`, and the check's state of each file.
Browsing is not among them: the app reads the whole list and shows one level of it.

Why the catalog shows the way. Since seed 35 a card's catalog is read in steps of at most
512 bytes while the show plays, and a cataloged drive's files join the playlist without
being read: a 256-file catalog, 11,161 bytes, is read in 10 refreshes on the board. What
is on the card costs no memory, and a 512-byte read of it costs less than a refresh.

On 2026-10-28 the owner chose this way over a bigger budget: a bigger budget only moves
the limit, costs 4 KB of the chip's scarce internal memory for each 256 files, and keeps
the 32 folders. The owner also asked that each folder's pages be precomputed and saved,
as the catalog is, so that any page of any folder can be read without a scan.

The owner's answers, 2026-10-28, to the four points the draft left open: ids of a drive's
files and folders are 32-bit from 60001 up, without a ceiling; the index is the saved
order of the drive's files, and `order.txt` keeps the show's items; `list in <folder-id>`
gives one level and `status` names the playing animation, approved as forms of the
command list; a drive without a catalog keeps today's limit of 256. Each is a
constraint below.

## Technical Constraints

- **The index is part of the catalog.** It lives in the drive's folder `odrig` beside
  `catalog.txt`, is written by the two writers of [catalog.md](../../docs/catalog.md),
  the core and the PC tool, in the same `catalog.do` commit as the catalog's pages, and
  is named by the marker with its files' CRC-32s. The marker's format goes to version 2;
  a reader of version 1 finds a version-2 catalog `incompatible`, as the format says.
- **Fixed-width lines, so that a row is an offset.** Every line of an index file has one
  length, padded with spaces before its line feed, so that row N is at offset N times
  the length and one `read_at` of 512 bytes gives whole rows. All text is ASCII, as the
  catalog's.
- **Three kinds of file.** For each folder, the root first, a file of its rows: the
  folder's own animation files in the saved order, then its sub-folders, each row with
  the entry's id, kind, type, size, length, CRC-32 and name. One table of the folders:
  for each, its ordinal, id, path, depth, number of files and number of sub-folders, in
  the listing's order, depth first, so that a folder's subtree is a range of the table.
  One map of the ids, sorted by id, each to its folder and row, found by binary search.
- **The core holds a cursor, not a table.** For the drive it keeps the current folder's
  record, the current row and the next one, the path of the current playlist and the
  window's time, as today, and the 16 remembered faults of the boot. The drive's table
  of 256 entries, the per-place block of the saved order and the tree of 33 folders go.
  No new block is asked for beyond room for one read of 512 bytes; the core's memory
  with a drive is less than today's, and the memory table of `docs/core.md` says so.
- **Ids are 32-bit for a drive's files and folders**, from 60001 up without an upper
  bound, kept stable as today: the lowest free id when a file is added, the same files
  with the same show the same ids. The show's items keep their ids of 1 to 65,535. Every
  command and reply that carries an id carries the number as it is; the app, the
  command tool and the firmware take it as a number.
- **The index is the saved order of the drive's files.** `order.txt` keeps the show's
  items only. `order move` of a drive's animation rewrites its folder's file; of a show
  item, `order.txt` as today. A rebuild and an import keep the order of the rows they
  find for the files still there, as a catalog page keeps a replaced line's place, and
  put new files after them by the bytes of their names.
- **A change touches little.** An upload or a removal rewrites the touched folder's
  file, the map of the ids, the catalog's page and the marker, in one commit; a folder
  left without a file leaves the table, the others keep their ids and their order. A
  rebuild and an import write everything.
- **A drive without a catalog keeps today's limit**: a USB stick, or the emulator's
  folder with `--drive-read-only`, is listed and held in a table of 256 as now. The way
  past the limit is a catalog with its index, which `catalog rebuild external` writes on
  a drive the core may write, and `python3 -m odrig.catalog MOUNT import` on a computer,
  so that the owner's collection gets its index once, on the share, and every start after
  that reads the marker and the rows it needs.
- **Nothing is read ahead.** A turn's end reads the next row of the current playlist's
  walk; `play <id>` reads the map and one row; `list` reads the rows of one level, as
  many as a reply holds; the rotation reads the next line of the folder table. The
  check after the start reads no row of a cataloged drive, as it reads no file of one.
- **The commands.** `list` and `list <from>` give the show's items and the root level:
  the root's folder rows and its own files. `list in <folder-id>` and
  `list in <folder-id> <from>` give one folder's level: its folder rows and its own files,
  with `next` as `list` has it. `status` names the playing animation's path, so that the
  app need not hold the whole list. `order get` takes `in <folder-id>` the same way. The
  owner approved these forms on 2026-10-28; the spec records the approval in
  `docs/decisions.md`.
- **The app reads a level when it enters it**, and again when the list is out of date,
  with `list in`; it keeps nothing of the other levels. Its filters, selection, moves
  and counts work on the level shown, as seed 41 left them.
- **What does not change.** The catalog's pages and `catalog page`, the keys and the
  previews; the name rule, a path of at most three folders and 100 bytes; the playlist's
  rules, the windows and the rotation of [show.md](../../docs/show.md); the firmware's
  host, which keeps the drive's names where it keeps them; the show's items, `show.json`
  and the board's own storage.
- **The budget decision.** This seed changes the decision of `docs/decisions.md` on the
  core's memory with a drive, which the owner approved on 2026-10-28; the spec writes
  the change log entry.

## Required Behavior

1. A cataloged drive with any number of animation files and folders, every one of them
   with a sound entry, plays every one of them in the playlist's order, the root's and
   each folder's as [show.md](../../docs/show.md) says, and lists every one of them with
   `list in` level by level, with no limit of 256 files or 32 folders.
2. `play <id>` of any file or folder of the drive plays it, and `status` names it, by its
   32-bit id, within one refresh's reads of the index.
3. An upload to the drive, a removal, an `order move` of a drive's animation and
   `catalog rebuild external` leave the catalog and its index agreeing, byte for byte the
   same from the core and from the PC tool for the same change on the same storage, and
   a power cut at any step leaves the catalog before the change or after it.
4. A card that the PC tool wrote the index of plays and lists on the board without a
   file of it being read before it plays, as a cataloged card does today.
5. The emulator's `--drive` folder without `--drive-read-only` gets its index from
   `catalog rebuild external` and keeps it across starts; with `--drive-read-only` it is
   listed as today, 256 files at most.
6. The app's explorer shows any level of any depth up to three, and the playing
   animation's name, without holding more than the level shown.
7. The core's memory with a drive is below today's, measured by the suite, and the
   board plays the owner's collection with every file listed.

## Definition Of Done

1. On the emulator, a drive of 1,000 files in 50 folders, with an index the PC tool
   wrote, lists every file by level and plays through every folder; the same drive's
   catalog rebuilt by the core is byte for byte the PC tool's.
2. Every suite that needs no board passes on macOS, and those of Windows pass there.
3. The board, with the owner's collection on its card and its index, lists and plays
   every folder, and the owner has seen the explorer walk the levels in the app.
4. `docs/catalog.md`, `docs/core.md`, `docs/show.md`, `docs/commands.md`,
   `docs/android-app.md`, `docs/microsd.md` and `docs/decisions.md` say what exists.

## Open Questions

None.
