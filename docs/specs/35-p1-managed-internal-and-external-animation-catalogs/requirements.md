# Requirements: managed internal and external animation catalogs

Seed: [`project-seeds/35-p1-managed-internal-and-external-animation-catalogs/seed.md`](../../../project-seeds/35-p1-managed-internal-and-external-animation-catalogs/seed.md).

After seeds 31 to 34 the board answers and plays from its start, reads every installed
animation whole in the check after the start (571.77 seconds for 84 animations on
2026-10-23), lists `"bytes":null` until then, says how far the check is, and changes one
file at a time. A card in the board is read-only: the core lists its folder `odrig` when
it is plugged in, reads every file whole before the file joins the playlist, and takes any
file copied onto it. This spec gives each storage a catalog of what it holds, kept by every
writer, so that a start and a card's mount read the catalogs and not the animations; lets
the board write the card and keep the card's catalog through uploads and removals, so that
the board's own storage can hold one or two small fallback animations and the card the
rest; gives a computer a Python tool that does to a card what the board does, byte for
byte; and makes a rebuild of a catalog an explicit command with progress and a cancel. The
choices were made under the owner's mandate of 2026-10-24 and are in `docs/drifts.md`,
"Seed 35".

Words used here:

- **a storage**: the board's own file system (**internal**) or the folder `odrig` of the
  card or USB drive in it (**external**). Each has its own catalog.
- **a catalog**: the file `catalog.txt` of a storage, its **marker**, and up to 16 page
  files `catalog-00.txt` to `catalog-15.txt`, which hold one **entry** for each animation
  of the storage: its name, size, CRC-32, canvas, length and type. Docs: `docs/catalog.md`.
- **a change**: an addition, replacement or removal of one or more animations of a
  storage, which ends in one **commit** of its catalog.
- **legacy**: a storage without a catalog, which is read as before this spec.
- **a rebuild**: the explicit reading of every animation of a storage, which writes its
  catalog anew; the **import** of a legacy storage is its first rebuild.
- **the PC tool**: `python3 -m odrig.catalog`, which manages a card mounted on a computer.

## Requirement 1: one format, two implementations

1. A catalog SHALL be text of printable ASCII and line feeds: a marker of fixed size with
   the format's version, the version of the check that admitted its entries, a
   generation and, for each of 16 pages, the number of its entries and the CRC-32 of its
   file, closed by the CRC-32 of the marker itself; and a page file for each page with
   entries. An entry's page SHALL follow from its name alone.
2. The core (C++) and the PC tool (Python) SHALL read and write the same format and
   SHALL carry out the same changes with the same storage operations, so that the same
   changes from the same storage leave the same files, byte for byte. This one duplicate
   implementation is the owner's approval of 2026-10-24.
3. Shared vectors SHALL hold valid catalogs and malformed ones; the core SHALL be tested
   on catalogs the PC tool wrote and the PC tool on catalogs the core wrote, with the same
   outcome for each malformed one.
4. A catalog SHALL name files by their name in their storage only: no mount path and no
   address. `show.json` stays the authority of the playlist (ids, inclusion, cycles,
   brightness, start), `order.txt` of the saved order, and `mapping.json` of the geometry;
   the catalog is the authority of what a file holds. A catalog entry for a file the show
   does not name is not an animation of the show.

## Requirement 2: the start reads the internal catalog

1. At its start the core SHALL read the internal catalog and take the size, length,
   canvas and type of every installed file it has an entry for, without opening the
   file: such a file is not opened at the start and not read by the check after the
   start, and `list` gives its size at once.
2. A file of the show without an entry SHALL be read as before (legacy): opened at the
   start and read by the check after the start. A catalog entry whose canvas is not the
   mapping's SHALL quarantine its file with `size-mismatch` without reading it.
3. A missing catalog is legacy. A damaged or incompatible catalog SHALL be reported and
   every file read as legacy; nothing SHALL rebuild, rewrite or remove a catalog by
   itself, and no restart loop SHALL follow.
4. A change that a power cut interrupted SHALL be finished or undone at the start, before
   the catalog is read: finished when its commit record is whole, undone otherwise.
5. Seed 31's bounded decoding and seed 32's quarantine SHALL stay: a catalog entry does
   not prove the bytes; a file whose playback finds a fault is quarantined for the boot.

## Requirement 3: changes of the internal storage keep its catalog

1. An upload that adds or replaces an animation, `remove` and `remove many` SHALL commit
   the internal catalog's change with the file: the entry of a new or replaced file holds
   the size, CRC-32, canvas, length and type its upload's check found, without a second
   read of the file.
2. A change SHALL write only the pages its entries are on, the new marker and its commit
   record, and the files of the change itself: no other page, no other animation, and no
   listing of the storage. `ignore` and `order move` do not change a catalog.
3. A power cut and a failed storage call at every step of a change SHALL leave, after the
   next start, the catalog before the change or the catalog after it, never a mix, and
   the show and the catalog SHALL agree on every file both name.
4. A legacy storage SHALL stay legacy through a change: the change writes no catalog
   until a rebuild has made one.

## Requirement 4: the external catalog

1. When a drive is plugged in, the core SHALL read its catalog in steps of at most one
   read of 512 bytes, at most as many steps at a refresh as the check after the start
   takes today, and SHALL publish its entries as animations of the playlist together,
   once every page is read and matches the marker; before that none of them plays, and
   the internal animations play on.
2. A drive with a catalog SHALL not be listed: the core takes the names of its files from
   the catalog and gives them to the host; no animation of it SHALL be read before it is
   played. A file of its folder that the catalog does not name SHALL not be an animation.
3. A drive without a catalog is legacy: it SHALL be listed and its files read and joined
   as before this spec.
4. While a drive with a catalog stays plugged in, the core SHALL read its marker once in
   10 seconds, in one read; when the marker is the one it read, nothing more is read.
   Another marker SHALL drop the drive's animations and read its catalog again as at the
   plug-in. Pulling the drive out drops its animations at once, as before.
5. A damaged or incompatible external catalog SHALL be reported, and none of the drive's
   files SHALL become an animation until a rebuild; the internal animations play on.
6. A file of a drive that a fault left out in this boot SHALL be left out again when the
   catalog is read again and its entry is the same, also on another plug-in; an entry
   with another CRC-32 is a new file.

## Requirement 5: the board writes the card

1. A host MAY say that its drive can be written. The core SHALL then take uploads to the
   drive and removals of its animations, and keep its catalog through each, by the same
   commit as on internal storage. A drive that cannot be written, and a legacy drive,
   SHALL refuse them with the new error `read-only`.
2. `upload begin external <file> <bytes>` and `upload begin external <file> <bytes>
   <crc32>` SHALL open an upload to the drive; the rest of the upload is as for internal
   storage, and its `upload end` reply SHALL give the animation's `id`. A file of that
   name on the drive is replaced and keeps its id; a new one gets the lowest free id from
   60,001 and its place in the saved order by its name.
3. `remove <id>` of an animation of a writable drive with a catalog SHALL remove its file
   and its entry. `remove many` stays for the internal storage.
4. `space` SHALL report `"read_only":false` for a drive the core can write.
5. The board's two writers are never both at work on one storage: the core changes the
   card only while it is plugged into the board, and the PC tool only while it is in the
   computer.

## Requirement 6: rebuild and import

1. `catalog rebuild internal` and `catalog rebuild external` SHALL read every animation of
   the storage with the check's bounded steps, while the show plays, and SHALL commit a new
   catalog of every file that passes, in one commit at the end. For the drive it lists the
   folder once. The files that pass join or stay in the playlist as the check's do; the
   files that fail are quarantined or left out.
2. `catalog` SHALL report each catalog: its state (`none`, `ok`, `loading`, `damaged`,
   `incompatible` or `absent`), generation, entries and, for internal storage, the files
   of the show without an entry; whether the drive can be written; and a rebuild under
   way with the files it has read and still has to read.
3. `catalog cancel` SHALL end a rebuild; the catalog stays as it was and the files read
   so far keep what was learned of them.
4. A rebuild is refused with `busy` while an upload is open or another rebuild runs, and
   an external one with `read-only` without a writable drive. A start, a plug-in or a
   reload of the app SHALL never start one.

## Requirement 7: the PC tool

1. `python3 -m odrig.catalog <mount> <command>` SHALL manage the folder `odrig` of a card
   mounted at `<mount>` on macOS and Windows: `status`, `import` (a rebuild), `add FILE…`,
   `remove NAME…`, `check` (each file's size and CRC-32 against its entry) and `recover`
   (finish or undo an interrupted change).
2. It SHALL check each file it adds or imports with the project's reader, with the same
   outcome as the core's check for every vector, and SHALL refuse a name the format does
   not allow.
3. Its changes SHALL leave the same files as the core's same changes, byte for byte, and
   SHALL survive an interruption at every step as the core's do.
4. The firmware tool's `install-show` SHALL write the internal catalog of the folder it
   installs, as `catalog rebuild internal` would, so that a board installed by image starts
   from its catalog; `--no-check` writes none.

## Requirement 8: what is measured

1. Tests SHALL first show the work this spec removes: a start that opens and reads every
   installed file, a drive whose folder is listed and whose every file is read before it
   plays, and a copied file that joins the playlist.
2. Tests SHALL record, with the library at 16, 64 and 256 animations and their sizes
   doubled: the bytes the start reads, the reads at a refresh while a drive's catalog is
   read and while it is unchanged, and the storage bytes and calls of an addition, a
   replacement and a removal, each apart: payload, pages, marker and commit record. A
   change SHALL be shown not to grow with the library beyond the page it is on.
3. The board session SHALL measure the time to the first reply, the first list with sizes,
   the first picture, and the end of a drive's catalog read, against the baseline of
   2026-10-23.

## Requirement 9: the app

1. Upload SHALL let the operator store a new animation on the card when the card can be
   written, and SHALL offer the card first then; otherwise it stores on the board as today.
2. Settings SHALL show both catalogs, a `Rebuild` button for each with a confirmation that
   says it reads every animation, a rebuild's progress, and `Cancel`.
3. An animation of a writable card SHALL have `Delete` in its row's menu.
4. The app stays usable through a mount, a reload and a rebuild, and shows seed 32's
   unavailable animations as before.

## Requirement 10: documents, tests and the board

1. `docs/catalog.md` SHALL state the format, the commit, the recovery, the two writers, the
   complexity of each operation and what the PC tool does; `docs/commands.md`,
   `docs/core.md`, `docs/show.md`, `docs/microsd.md`, `docs/firmware-additions.md`,
   `docs/emulator.md`, `docs/android-app.md`, `docs/python-library.md` and
   `docs/decisions.md` SHALL say what holds.
2. Every suite that needs no board SHALL pass. The board session flashes the firmware,
   imports the card, moves the board's animations onto the card through the board so that
   one or two small fallback animations stay inside, and measures; the owner checks the
   app and the LEDs.
