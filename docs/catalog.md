# Catalogs

Each storage of animations keeps a catalog of what it holds: the board's own storage, and
the folder `odrig` of the card or USB drive in it. A catalog says, for each animation file,
its size, CRC-32, canvas, length and type, so that the board does not read the animations
to learn them again at every start. This page states the format, how a change is made and
finished, who writes catalogs, and what each operation costs.

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

### The pages: `catalog-00.txt` to `catalog-15.txt`

One line for each animation:

```
1a2b3c4d 52340 60 60 12000 frames sunrise.odrg
```

The file's CRC-32, its size in bytes, its width and height, the sum of the durations of
its frame records in milliseconds, its type (`frames` for an ODRG file), and its name. The
page of a name is the low four bits of the FNV-1a hash of its bytes. A page's lines stand
in the order their entries came in: a rebuild writes them in the storage's order, an
addition puts its line last on its page, a replacement keeps its line's place, a removal
takes its line out. A line is at most 161 bytes.

A name is 1 to 100 bytes of printable ASCII other than `/ \ : * ? " < > |`; it does not
begin with `.` or a space, does not end with a space or `.`, is not made of digits alone,
and ends in `.odrg` in any case. A name of the board's own storage follows the show's rule
too: 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_` and `.`.

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
step comes to the catalog before the change or the one after it. A `catalog.do` that is not
whole, and `.new` files without one, are traces of a change that was not committed: they
are never read.

An upload adds or replaces with the action `move upload.part <name>`: the file is checked
as `upload.part` and becomes the animation in the same commit as its entry. A removal takes
the entry out with `remove <name>`.

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
| A start | none of a cataloged file | the marker and the pages, once |
| A drive with a catalog plugged in | none | the marker and the pages, in steps of at most 512 bytes |
| An unchanged drive | none | one read of the marker, 409 bytes, in 10 seconds |
| An addition or a replacement | S written and S read back by the check | one page of P lines read and written, the marker, the commit record |
| A removal | the file removed | one page, the marker, the commit record |
| A rebuild or an import | every file read whole | every page and the marker written |

No change lists the storage, reads another animation or writes another page; a rebuild is
the one operation that reads the whole library, and it is a command.
