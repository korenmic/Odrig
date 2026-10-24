# Design: managed internal and external animation catalogs

Requirements: [requirements.md](requirements.md). Each storage gets a catalog in a fixed
text format: a marker of 409 bytes and up to 16 pages, an entry's page given by its name.
A change writes its pages and marker under new names and then a commit record; finishing
it renames them into place, and a start or a plug-in finishes a change whose commit record
is whole. The core reads the internal catalog at its start and a drive's catalog in
bounded steps after the plug-in; the host is given the drive's names instead of listing
the folder. The board writes the card when its host says it may. A rebuild is a command.
The PC tool is a second implementation of the same changes, tested against the core byte
for byte.

## What this design relies on

The branch of seed 35 holds the unified branch (seeds 28, 31, 32, 36, 38, 39) and seeds 33
and 34. From them:

- The core's start (`core.cpp` `start`): reads `mapping.json`, `show.json`, then opens
  each file of the show (`open_file`, its header and canvas), or reads it whole on a host
  without storage (`check_file`); the check after the start (`check_after_start`,
  `check_step`) reads every file whole through the second source and decoders, sets
  `FileInfo.checked`, `bytes`, `total_ms`, and quarantines (seed 32). `list` gives
  `"bytes":null` for a file not read whole.
- A drive (`drive_touch`): the host lists the folder `odrig` when it is plugged in;
  `drive_name(place)` and `drive/<place>` serve it; every place gets an id at once; the
  drive's check (`drive_step`) reads `order.txt` (seed 36) and then every file whole after
  the installed files, and a file joins the playlist (`player_drive_joined`) when it
  passes; `Remembered` keeps 16 files left out in this boot by name and first read.
- `FileSource::open_at` keeps a running CRC-32 of what it read (`crc`); the upload's check
  reads `upload.part` back through it; `Upload` holds the received bytes' CRC-32, the
  length found and the name.
- Seed 34: `upload begin <id> <file> <bytes> <crc32>` and `unchanged`; `pending.txt` and
  the cleanup at the next change; the firmware tool's `install-show` writes only what
  differs (`storage.with_show`, `change_of`) and journals the write.
- Seed 33: `status` reports `readiness` and the check's counts; `fault`; the host's
  `about`.
- Seed 36: `order.txt` names internal items by id and card files by name; `order_hash`
  holds the low byte of each drive place's name's FNV-1a hash.
- Memory: with a drive the target file takes 130,701 of 131,072 bytes (seed 36's
  measurement on the unified branch; seeds 33 and 34 change it, and this design measures
  again).

## The catalog format

One format for both storages, version 1. All text is ASCII; every line ends with one line
feed; numbers are decimal without leading zeros, `0` for zero; CRC-32s and the generation
are 8 lowercase hexadecimal digits. The CRC-32 is zlib's.

### The marker: `catalog.txt`, 409 bytes

```
odrig-catalog 1 check 1 generation 0000002a
page 00 0003 1a2b3c4d
page 01 0000 00000000
...
page 15 0001 9f00e1aa
crc 0a1b2c3d
```

- Line 1, 44 bytes: the format's version `1`; the version of the check that admitted the
  entries, `check 1`, the check of ODRG version 1 as `docs/reasons.md` states it; the
  generation, 1 for the first catalog and one more at each commit, 00000001 after
  ffffffff.
- Lines 2 to 17, 22 bytes each: page `00` to `15`, its number of entries in 4 digits with
  leading zeros, and the CRC-32 of its file, `00000000` for a page without entries,
  which has no file.
- Line 18, 13 bytes: the CRC-32 of the 396 bytes before it.

A reader takes the marker as it is or not at all: a size other than 409, a line out of its
form, or a CRC-32 that differs make it **damaged**; a format or check version it does not
know makes it **incompatible**.

### The pages: `catalog-00.txt` to `catalog-15.txt`

One line for each entry:

```
<crc32> <bytes> <width> <height> <total_ms> <type> <name>
```

`crc32` and `bytes` are the file's CRC-32 and size; `width` and `height` its canvas,
1 to 65,535; `total_ms` the sum of the durations of its frame records, 0 to
18,446,744,073,709,551,615; `type` `frames` for an ODRG file (seed 37 adds `text` and
`widget`); `name` the file's name in its storage. The page of a name is the low four bits
of the FNV-1a hash of its bytes (the hash of seed 36's `order_hash`). Lines are in the
order their entries came in: a rebuild writes them in the storage's order (the show's
file order for internal storage, the bytes of the names for a drive), an addition appends
its line to its page, a replacement keeps its line's place, a removal takes the line out.

A name is 1 to 100 bytes of printable ASCII other than `/ \ : * ? " < > |`, does not
begin with `.` or a space, does not end with a space or `.`, is not made of digits alone,
and ends in `.odrg` in any case. Internal names follow the show's rule as well. A page
whose file is not its marker's count of well-formed lines with its marker's CRC-32, a name
on the wrong page or twice in the catalog, make the catalog damaged. A line is at most 161
bytes.

### A change and its commit

A change of a storage is a set of entries to add, replace or take out, and the file
actions that go with them: `move <from> <to>` and `remove <name>`. It is carried out in
this order, every file written with `write_open`, `write` and `write_close`:

1. Each page the change touches is written whole as `catalog-NN.new` from its old file,
   read with `read_at`, with the change applied; a page left without entries gets no file.
2. The new marker is written as `catalog.new`.
3. The commit record is written as `catalog.do`:

   ```
   odrig-catalog-do 1 generation 0000002b
   pages 0008
   move upload.part sunrise.odrg
   crc 4c1e00a7
   ```

   `pages` is a mask of the pages touched, bit N for page N, 4 hexadecimal digits; then
   the actions in order; then the CRC-32 of the bytes before the `crc` line. **The change
   is committed when `write_close` of `catalog.do` has returned 1.**
4. **Finishing**: each action in order (`rename`, `remove`); each touched page: its
   `.new` file renamed onto `catalog-NN.txt`, or `catalog-NN.txt` removed when the page is
   now empty; `catalog.new` renamed onto `catalog.txt`; `catalog.do` removed.

A step whose source is gone is done already: a `rename` that fails is taken as done when
`read_at` of its source fails, and a `remove` that finds no file is done. So finishing can
be repeated after a cut at any call, and a reader that finds a whole `catalog.do` (its
form and CRC-32) finishes it before it reads the catalog. A `catalog.do` that is not whole,
and `.new` files without one, are the traces of a change that was not committed: they are
not read, the next change writes over the `.new` files it needs, and a rebuild or the PC
tool's `recover` removes them. On a drive the core cannot write, a whole `catalog.do`
makes the catalog damaged (`interrupted`) until a writer finishes it.

The core writes the files of a drive with the names `drive/catalog.txt`,
`drive/catalog-NN.new` and so on; the host maps them into the folder `odrig`.

### What each operation costs

N is the number of entries of the storage, P the number of entries of the page a change
touches (N/16 on average, at most N), S the size of an animation.

| Operation | Payload | Catalog |
|---|---|---|
| Start | none for a cataloged file | the marker and every page: O(N) bytes, once |
| Plug-in of a drive with a catalog | none | the marker and every page in steps of ≤ 512 bytes |
| An unchanged drive, every 10 seconds | none | one read of the marker, 409 bytes |
| Addition or replacement | S written, S read by the check | P lines read and written for one page, the marker, the commit record |
| Removal | the file removed | the same, one page |
| `remove many` of k files | the files removed | up to min(k, 16) pages |
| Rebuild, import | every file read whole: O(Σ S) | every page and the marker written |

A change never lists the storage, reads another animation, or writes another page. The
tests of requirement 8 measure each line at 16, 64 and 256 entries.

## The core

### Memory

The drive's table holds `total_ms` in 32 bits from now on (a file longer than 49 days
counts as 4,294,967,295 ms): each of its 256 entries takes 12 bytes instead of 16, and the
1,024 bytes this frees are the room for the catalogs:

```cpp
struct DriveEntry { uint32_t total_ms; uint32_t bytes; uint16_t id; uint8_t state; uint8_t fault; };
// states: kDriveToCheck, kDriveInPlaylist, kDriveLeftOut, and kDriveStaged (read from the
// catalog, not published yet) and kDriveGone (removed by the board: not listed, its place
// free for the next upload).

struct CatalogState {          // in Core, for internal storage [0] and the drive [1]
    uint32_t generation;
    uint16_t entries;
    uint8_t state;             // kCatalogNone, Ok, Loading, Damaged, Incompatible, Absent
    uint8_t detail;            // why damaged: marker, page, line, interrupted
};
// The drive's catalog read: the page it is at, the bytes of it read, its running CRC-32
// and lines, the marker's CRC-32 once read; the time of the last look at the marker.
uint8_t catalog_page; uint32_t catalog_offset; uint32_t catalog_page_crc;
uint16_t catalog_page_lines; uint32_t catalog_marker_crc; uint64_t catalog_looked;
// A rebuild: its storage (0 none), page, cursor, files read and to read, the page being
// written, and each page's count and CRC-32 so far.
uint8_t rebuild; uint8_t rebuild_page; uint16_t rebuild_at; uint16_t rebuild_read;
uint16_t rebuild_total; uint16_t rebuild_lines; uint32_t rebuild_crc;
uint16_t rebuild_count[16]; uint32_t rebuild_page_crc[16];
```

`OrderReader`'s line grows from 130 to 162 bytes so that it reads a catalog's lines as well
as `order.txt`'s (they are read one after the other, never at once). `FileInfo.checked`
gets a third value, `kCheckedFromCatalog` (2): the size and length came from the catalog.
The test of the memory table measures the result; the core object stays under 4,096 bytes.

### The start

`start`, after `show.json` and before the files are opened:

1. `catalog_finish(core, internal)`: a whole `catalog.do` is finished (on a host that can
   change its storage); otherwise nothing is done.
2. `catalog_read_internal(core)`: reads the marker and the pages with the second source,
   whole, at once (they are metadata of at most 132 entries). Each entry whose name a
   file of the show has: that file gets `bytes`, `total_ms`, `checked =
   kCheckedFromCatalog`; a canvas that is not the mapping's quarantines it with
   `size-mismatch` (`kWorkStart`). Entries of names the show has not are left as they are.
   The state, generation and entries are kept; a damaged or incompatible catalog is
   logged (`catalog internal damaged: <detail>`) and taken as none: every file legacy.
3. The loop over the files opens (`open_file`) or checks (`check_file`) only the files
   that are not `checked`, and the check after the start passes over checked ones as it
   does already. With every file cataloged the check is complete at once.

### Changes of the internal storage

`catalog_commit(core, storage, Change)` carries out the steps of "A change and its
commit", with the second source to read old pages and the marker, and the chunk buffer to
make lines. `Change` holds up to 32 names to take out, one entry to add or replace (from
the upload: name, size, CRC-32 of the bytes received, the canvas, the length its check
found, `frames`), and up to two actions. It returns false on a failed storage call: the
change stays uncommitted (before the commit record) or is finished at the next start
(after it), and the command answers `storage-error`.

- An upload (`storage_install_upload`): when the storage has a catalog, the rename of
  `upload.part` onto the name becomes the action `move upload.part <name>` of a commit
  that adds or replaces its entry (and takes out the entry of the item's old file when
  the upload gave the item another name); the show file is then written as before for a
  new item or a new name. A replacement under the same name is thus one commit.
- `remove`, `remove many`: the show file and the file removals go as before (seed 34);
  then one commit takes the entries out.
- On a legacy storage nothing changes: no catalog is written.
- After a commit the file's `checked` is `kCheckedFromCatalog`, and the catalog's
  generation and entries are kept.

A cut between the commit and the show file leaves an entry for a file the show does not
name (an addition) or a file the show names without its entry (a removal's leftover is
the opposite: an entry of a file that is gone): both are harmless, as requirement 1.4 and
2.2 say, and the next rebuild leaves them out.

### The drive

`drive_touch` on a new drive number, for a host with `drive_bind`: sets the drive's catalog
state to `Loading` and its count to 0; the drive's part of the check (`drive_waits`,
`drive_step`) then runs `catalog_drive_step`, one step at a time:

1. The commit record: `read_at` of `drive/catalog.do`. Whole: finished when
   `drive_writable` says 1, damaged (`interrupted`) otherwise.
2. The marker: one `read_at` of `drive/catalog.txt`. None there: the drive is legacy —
   `drive_list`, then the places, ids and keys as `drive_touch` made them before this
   spec, and the drive's check as before. Damaged or incompatible: reported and logged,
   no animation.
3. Each page with entries, from page 00 on, one `read_at` of at most 512 bytes a step:
   its lines through `OrderReader`, each entry a new place: `drive_bind(place, name)`,
   `order_drive_named(place, name)`, the lowest free id, `bytes`, `total_ms`, state
   `Staged`; a canvas that is not the mapping's is left out with `size-mismatch`, and an
   entry whose name and CRC-32 a `Remembered` file has is left out again with its
   reason. At the end of the page its CRC-32 and count are compared with the marker's,
   read again in one `read_at`. A difference: every place is dropped, the catalog is
   damaged.
4. `order.txt` as before (`order_drive_due`, `order_drive_step`).
5. Publication: every `Staged` place becomes `InPlaylist` and joins the playlist at the
   same refresh; the state is `Ok`; `catalog_looked` is now.

While the state is `Ok` and no upload, rebuild or change of the drive is under way,
`catalog_drive_look` reads the marker once in 10,000 ms of the host's time, with the
second source when the check does not hold it; a CRC-32 other than `catalog_marker_crc`
drops the drive's places (`player_drive_changed`) and starts again at step 1.

`Remembered` gets a second kind of record, `first_read` = 0xFFFF and `crc` the entry's
CRC-32, for a file of a cataloged drive left out by the player: the player's fault on
such a file looks up its entry's CRC-32 in its page (one page read, at that refresh).

### The board writes the drive

- `drive_writable` says 1 and the drive's catalog is `Ok`: the drive can be written.
- `upload begin external <file> <bytes> [<crc32>]`: refused `bad-argument` for a name
  outside the show's naming rule or not ending in `.odrg`; `show-invalid`; `busy` while an
  upload is open, a rebuild runs or the drive's catalog is loading; `read-only` when the
  drive cannot be written; `no-space` when `drive_space` says the file does not fit or
  256 places are taken by others. The upload is `drive/upload.part`; its check reads it
  back; `upload end` commits on the drive with `move upload.part <file>` and the entry.
  The place: the one whose bound name is `<file>` (a replacement: its id stays, its fault
  goes), else the first `Gone` place, else a new one; `drive_bind`, `order_drive_named`,
  the lowest free id. The reply: `{"ok":true,"id":<id>}`.
- `remove <id>` of a drive's animation: when the drive can be written, one commit takes the
  entry out with `remove <name>`; the place becomes `Gone`; otherwise `in-use` as before.
- `space`: `"read_only":false` when the drive can be written.

### Rebuild

`catalog rebuild internal`: `bad-argument`, `show-invalid`, `busy` (an upload open, a
rebuild running), `read-only` on a host that cannot change its storage. It ends the
check after the start (its files are the rebuild's now), sets `rebuild_total` to the
show's files that are not quarantined, and at each step of the check's schedule
(`check_after_start` calls `rebuild_step` in place of `check_step` while a rebuild runs):
for page 00 to 15, the files of the show in their order whose name is on the page: the
check's `check_file_step`; a file that passes gets `bytes`, `total_ms`, `checked` and its
line in `catalog-NN.new` (opened at its page's first line, closed at its last, the
page's count and CRC-32 kept); a file that fails is quarantined. After page 15 the
marker and the commit record (mask ffff) are written and finished; the generation is one
more than the old catalog's, or 1. While a rebuild has a page open, every command that
writes storage (`upload begin`, `remove`, `remove many`, `ignore`, `order move`,
`mapping set`) is refused with `busy`.

`catalog rebuild external`: also `read-only` without a writable drive, or a host without
`drive_list`. It drops the drive's places, calls `drive_list`, gives each place its id and
key as a legacy plug-in does, and goes through the places page by page in the same way:
a file that passes joins the playlist at once, as in the legacy check; one that fails is
left out and remembered. At the end the drive's catalog is `Ok` with the places as listed.

`catalog cancel`: closes and removes the page being written, ends the rebuild; the files
read keep what was learned; the check after the start, or the legacy drive check, goes on
with the files not read. `{"ok":true}` also without a rebuild.

### `catalog`

```
catalog
{"ok":true,"internal":{"state":"ok","generation":42,"entries":84,"uncataloged":0},"external":{"state":"ok","generation":7,"entries":122,"writable":true},"rebuild":null}
```

`state` is `none`, `ok`, `loading`, `damaged`, `incompatible` or `absent`; a damaged one has
`detail`; `generation` and `entries` are present for `ok` and `loading`; `uncataloged` counts
the show's files whose size did not come from the catalog; `writable` is present when a
drive is plugged in. `rebuild` is `{"storage":"internal","read":12,"to_read":72}` while one
runs. The reply stays one line under 1,024 bytes.

### Seed 33's readiness

`readiness` is `checking` while a rebuild runs or a drive's catalog is loading, with
`checked`/`to_check` the rebuild's files read and to read, and `checking` the file the
rebuild is at or `catalog` while pages are read; otherwise as seed 33 says.

### Errors

New code `read-only`, in the order of the codes after `in-use`: `unknown-id, unavailable,
in-use, read-only, mapping-conflict, order-conflict, no-space`.

## The host interface

Three optional functions at the end of `odrig_host`:

```c
/* Lists the drive's folder `odrig` now, as drive_name describes it, for a drive without a
   catalog. A host that has this function lists the folder only when it is called. Returns
   the number of animation files, or -1. */
int32_t (*drive_list)(void *ctx, uint32_t drive);
/* Gives the place to the file of the drive's folder with this name: drive_name then
   reports the name and `drive/<place>` opens the file. Returns 1, or 0 when that drive is
   not plugged in any more or the name is not one a catalog may hold. */
int (*drive_bind)(void *ctx, uint32_t drive, uint32_t place, const char *name);
/* 1 when the core may write the drive with the storage functions, 0 otherwise. */
int (*drive_writable)(void *ctx, uint32_t drive);
```

`open`, `read_at`, `write_open`, `rename` and `remove` take `drive/<name>` for the file of
that name in the drive's folder, besides `drive/<place>`; a name of digits alone is a
place. A host without `drive_bind` keeps its drive legacy. The firmware's SD card backend
writes (`rename` there removes the target first, as FAT cannot rename onto a file; the
commit's finishing covers the cut between); its USB backend stays read-only. The test host
and the emulator write their drive folder unless `--drive-read-only`, list it only when
asked, and trace `drive_list` calls so that the tests see none.

## The PC tool: `odrig/catalog.py`

- `Storage(folder)`: `read(name)`, `write(name, data)` (whole, flushed), `rename(old,
  new)` (`os.replace`), `remove(name)`, `exists(name)`, `names()` (the legacy listing rule):
  the same calls as the core's host, so that a `Recording` storage can compare them.
- The format: `marker_text`, `page_text`, `do_text`, `parse_marker`, `parse_page`,
  `parse_do`, `page_of(name)`, `entry_of(name, data)` (the project's reader,
  `odrig.odrg.decode`, gives the canvas and the length; a rejection keeps its reason).
- The changes: `commit(storage, change)`, `finish(storage)`, `add(storage, name, data)`
  (writes `upload.part`, reads it back, checks it, commits `move upload.part <name>`),
  `remove(storage, name)`, `rebuild(storage, names=None, generation=None)`, `check(storage)`,
  `status(storage)`, `recover(storage)` (finishes, then removes `.new` files and a torn
  `catalog.do`).
- `python3 -m odrig.catalog <mount> status|import|add FILE…|remove NAME…|check|recover`,
  on `<mount>/odrig`; `--folder` takes the folder itself. Exit 0, 1 for a refused file or
  a damaged catalog, 2 for a usage error; one line of outcome per change.

`firmware/fwtool`: `storage.folder_files(folder, check=True)` adds the catalog of the
folder (`catalog.rebuild` on an in-memory storage, in the show's file order, the
generation one more than the board's catalog has, or 1); `with_show` writes it as any
other file, so seed 34's change writes only the pages that differ and the marker.

## The app

- `commands.js`: `catalog()`, `catalogRebuild(storage)`, `catalogCancel()`;
  `uploadBegin` takes `external`; `space()` keeps `read_only`.
- Upload: a choice `Store on: The card / This board` when `space` says the card can be
  written, the card chosen first; an upload to the card sends `upload begin external` and
  reads the new id from `upload end`.
- Settings: a panel `Catalogs` with a line for each storage (`Board: 84 animations,
  cataloged`, `Card: not cataloged yet`, `Card: catalog damaged`, …), `Rebuild` with a
  confirmation, progress (`Reading the animations: 12 of 84`) and `Cancel`; `catalog` is
  asked when Settings opens and every 2 seconds while it is visible.
- Animations: an external row's menu has `Delete` when the card can be written.
- The texts of `read-only` and the new lines of the table of commands in
  `docs/android-app.md`.

## odrigctl and the emulator

`odrigctl catalog [rebuild internal|rebuild external|cancel]` and `odrigctl upload
--external FILE`. The emulator's `--drive DIR` is written by the board's commands unless
`--drive-read-only`; the emulator documents it.

## Tests

- `tests/vectors/catalog/`: valid catalogs (empty, one page, all pages, long names) and
  malformed ones (each line form, CRC-32s, counts, names on the wrong page, twice, a torn
  `catalog.do`), with the outcome each must give.
- `tests/core/test_catalog*.py` (core), `tests/emulator/test_catalog.py`,
  `tests/firmware/test_catalog_install.py`, `tests/catalog/` (the PC tool, its CLI and the
  cross tests with the core through the test host), `tests/app/test_catalog.py`.
- The regression (task 1) as expected failures that later tasks turn into passes.
- Faults: the test host's `--cut-at` and `--store-fails-at` at every call of every change
  on both storages, then a start: the catalog before or after.
- Byte for byte: the same sequences of additions, replacements and removals through the
  core (test host, `--drive`) and through `odrig.catalog` on a copy leave the same files;
  `catalog rebuild` of a folder and `install-show`'s catalog of it are the same.
- Measurements (requirement 8.2) with `--trace-calls` and `--trace-store`.
