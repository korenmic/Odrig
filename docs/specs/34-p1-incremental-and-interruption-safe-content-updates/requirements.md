# Requirements: incremental and interruption-safe content updates

Seed: [`project-seeds/34-p1-incremental-and-interruption-safe-content-updates/seed.md`](../../../project-seeds/34-p1-incremental-and-interruption-safe-content-updates/seed.md).

Two routes change what the board holds. **The live route** is the commands `upload`,
`remove`, `remove many` and `ignore`, which the core carries out on the board's own file
system: each writes one animation file and the small show file through a temporary file
and a rename, and seed 07 made each survive a power cut at every storage call. **The image
route** is the firmware tool: `install-show`, `set-wifi`, `set-limit` and
`install-firmware` read the board's storage partition into an image on the computer,
change the image with the LittleFS library, and write the blocks that differ.
`install-show` removes the folder `/odrig` and writes every file again: on 2026-10-24 one
deletion this way changed 6,705,152 bytes, and the test of this spec measures 8.4 MB of
WLED's storage and 10.9 MB of the bigger one for the removal of one animation. The tool
then compares the whole partition, and a write that is cut leaves storage in a state
nobody named; WLED formats a file system it cannot read when the board starts.

This spec makes the image route change only what differs and write it in an order with
one named step that cannot be cancelled, kept in a journal and finished by a recovery
command; it makes an unchanged upload write nothing, finishes an interrupted cleanup at
the next change, and says what each operation did. External media stay read-only, and no
animation is removed or rewritten on the board while the spec is written. The choices
were made under the owner's mandate of 2026-10-24 and are in `docs/drifts.md`, "Seed 34".

Words used here:

- **a block in use**: a block of the storage partition that the file system of the image
  the board holds reads: its superblock, its metadata pairs and the blocks of its files.
  Every other block is **free**.
- **the change**: the blocks in which the new image differs from the one the board holds,
  joined into runs of neighbouring blocks.
- **the commit**: the writing of the blocks of the change that are in use. Before it the
  board's file system is the one before; after it and the comparison, the new one.
- **the journal**: the file `build/firmware/storage/change.json`, which names a change
  from before its first write until it is finished or given up.
- **a full storage**: the storage partition of a layout, 10,354,688 or 13,500,416 bytes,
  with WLED's settings and a show whose animations of 50 to 250 KB fill 80 % of it.

## Requirement 1: the image route changes what differs

1. `install-show` SHALL remove from `/odrig` only the files the folder does not hold, write
   only the files that are new or whose bytes differ, and leave every other file of the
   storage where it is: no unchanged file is written or moved.
2. A new or changed file SHALL be written while every file of the image before is still
   there, so that its bytes go into free blocks, and SHALL then take the place of the old
   file; the files that go SHALL be removed last. When the room does not allow that, the
   files that go and the files that change SHALL be removed first, and the plan says that
   more blocks in use are written.
3. In a full storage of either layout, removing, adding or replacing one animation SHALL
   change at most the blocks of the files written and 4 blocks more, of which at most 4 are
   in use; installing the same folder again SHALL change no block.
4. Every file outside `/odrig`, the mapping when it is unchanged, and every unchanged file
   of `/odrig` SHALL stay byte for byte and in its blocks; the new image is checked for
   this before anything is written.
5. A file that is quarantined on the board, or is not a valid animation, SHALL be removed or
   replaced like any other. The folder is checked as today; `--no-check` stays.
6. The saved playlist order, `order.txt`, SHALL be a file a show folder may hold. When the
   folder holds none, `install-show` SHALL keep the one the board holds: the order is the
   operator's choice, and installing animations does not change it.

## Requirement 2: the order of the write

1. The tool SHALL write a change in two esptool calls: first the runs of free blocks, then
   the runs of blocks in use. Either call is left out when it has no run.
2. A failure or an interrupt before the second call SHALL leave the board's file system as
   it was before.
3. From the second call to the end of the comparison the tool SHALL hold an interrupt from
   the keyboard, finish, and then say that it came.
4. After the write the chip SHALL compare every written run with the new image in one
   call, and the board SHALL be restarted only when all are equal; no call of the write
   resets the chip. The rest of the partition is not compared: it is the image the chip
   confirmed, or that was read whole, before the write.
5. When nothing differs, nothing SHALL be written or compared, and the board is restarted.
6. `set-wifi`, `set-limit` and `install-firmware` SHALL write their changes the same way.

## Requirement 3: the journal and the recovery

1. Before its first write the tool SHALL write the journal: the region, the name of the new
   image, the runs of each part and the step reached; each later step SHALL be recorded
   before it begins.
2. A failure before the commit SHALL end with its reason, an interrupt with the reason
   `cancelled`; the journal and the new image are removed, the board is restarted, and the
   message says that the change was not made and the board holds its storage from before.
3. A failure in the commit or in the comparison SHALL end with the reason
   `recovery-needed`: the journal and the new image stay, the chip is left in its
   bootloader, and the message names `python3 firmware/fw.py recover-storage`.
4. While a journal is there, every command that reads or writes the board's flash SHALL
   refuse with `recovery-needed` before it looks for the board.
5. `recover-storage` SHALL, for a journal whose change was cut before its commit, remove
   the journal and the new image and restart the board; otherwise have the chip compare the
   board's storage outside the change with the new image, write the change in the order of
   requirement 2, compare it, make the new image the board's, remove the journal and
   restart the board. When the storage outside the change differs it SHALL refuse with
   `storage-changed` and write nothing; `recover-storage --whole` SHALL then write the new
   image whole, the last resort. Without a journal it SHALL say so and touch nothing.
6. A recovery that is cut SHALL keep the journal, so that `recover-storage` can be run
   again with the same outcome.

## Requirement 4: what the tool says

1. Before it writes, `install-show` SHALL print how the show changes: the number of files
   kept, and each file added, replaced or removed with its bytes; and the blocks and bytes
   to write, free first and then in use.
2. One line SHALL then say the outcome of the write: unchanged, committed with the bytes
   written and compared, and that the board restarts; a failure is the error line of
   requirement 3.
3. `install-show --dry-run` SHALL print the same plan, write nothing and restart the board.
4. `install-show --keep-copies DIR` SHALL copy every file it removes or replaces, as the
   board holds it, into `DIR`, a new or empty folder, before anything is written.
5. What the board says after its restart is printed as today.

## Requirement 5: the live route

1. `upload begin <id> <file> <bytes> <crc32>` SHALL answer `{"ok":true,"unchanged":true}`
   and open no upload when the last upload of this boot installed `<file>` as the file of
   the animation item `<id>`, with `<bytes>` bytes and the CRC-32 `<crc32>`, no upload has
   begun since, and the item names it still, usable; otherwise it SHALL act as `upload begin
   <id> <file> <bytes>`. Nothing is written for an unchanged file.
2. The core SHALL remember the id, the name, the size and the CRC-32 of the file the last
   upload installed, until another upload begins or the core starts again, in the memory it
   has already: the target file leaves no room for a CRC-32 of every file.
3. `odrigctl upload` SHALL send the CRC-32, send the form without it again when a target
   answers `bad-argument`, and print one line of outcome: `unchanged`, `committed` with the
   bytes sent, or `not committed` with the error. Run again after a reply that did not
   arrive, the same upload finds the file unchanged when it was installed.
4. A cleanup that a change left unfinished, a file to remove or `pending.txt`, SHALL be
   tried again at the next change, before the change. While it still fails the change is
   refused with `storage-error`, as today, and the next start tries it. A cleanup never
   removes a file the show names.
5. Removing one animation SHALL write only `pending.txt` and the show file; adding one the
   file, `pending.txt` and the show file; replacing one under its name the file; an
   unchanged upload nothing. No other file is written, renamed or removed.

## Requirement 6: faults

1. A power cut and a failure at every storage call of `remove`, `remove many`, `ignore` and
   `upload` SHALL leave the old show or the new one whole after the next start.
2. A power cut at every storage call of the start's cleanup SHALL leave a folder whose next
   start finishes it; cuts one after the other come to the same folder.
3. An upload whose sender goes away is discarded after 60 seconds, and `upload cancel` in
   each state of an upload leaves the show as it was.
4. On the image route, a failure, a cut write and an interrupt at each step of the write
   SHALL end as requirement 3 says, at both layouts, and `recover-storage` SHALL then bring
   the board to the new image.
5. A change that does not fit SHALL be refused with `no-space` before anything is written,
   on both routes.

## Requirement 7: tests and documents

1. A test SHALL first show the excessive one-file update: removing one animation from a
   full storage changes megabytes.
2. Tests SHALL record the bytes changed and written for a removal, an addition, a
   replacement and an unchanged retry, on both routes, and on the image route at both
   layouts with a full storage, and that unchanged files keep their blocks.
3. `docs/firmware.md` SHALL separate flashing, content changes by command and by image,
   quarantine, the board's check and the recovery of storage, with the step that cannot be
   cancelled, `recover-storage`, and what the kept images can and cannot bring back;
   `docs/commands.md` the new form of `upload begin` and the member `unchanged`;
   `docs/core.md` the CRC-32 of a file and the cleanup at the next change; `docs/decisions.md`
   a line.
4. Every suite that needs no board SHALL pass. The board's trials stay for the board
   session: one animation removed and one added by command and by `install-show`, timed,
   with the bytes written and the manifests before and after, without flashing the app;
   what remains on the board said.
