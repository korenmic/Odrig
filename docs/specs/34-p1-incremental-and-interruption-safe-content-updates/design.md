# Design: incremental and interruption-safe content updates

## Overview

On the image route the firmware tool edits the board's storage image file by file instead
of building `/odrig` anew, finds which blocks the file system of the image before uses,
and writes the change in two parts: the free blocks, which the board's file system does
not read, and then the blocks in use, the commit. A journal in the work folder names the
change until it is finished, and `recover-storage` finishes or gives up a change that was
cut. On the live route the core remembers the file the last upload installed, so that the
same upload repeated is answered `unchanged` without a write, and a cleanup that a change
left unfinished is done at the next change. The format, the show file and the board's
firmware do not change.

## What this design relies on

Today's code, with seeds 28 to 32, 36, 38 and 39 in it:

- `fwtool/storage.py`: `with_show(image, files)` removes `/odrig` with everything in it and
  writes every file of the folder again; `runs(old, new, block_size)` gives the changed
  blocks joined into runs; `from_board` takes the newest kept image when the chip confirms
  its checksum (17 seconds on the board) and reads the partition otherwise (64 seconds);
  `pending`, `keep` and `discard` handle the new image `<time>-after.bin.part`.
- `fwtool/cli.py`: `write_storage(on_port, region, before, make)` writes every run in one
  esptool call, has the chip compare the whole partition and restart the board, and on a
  failure discards the new image and restarts the board. `install-show`, `set-wifi`,
  `set-limit` and `install-firmware` use it.
- esptool sorts the files of one call by their address, writes each by erasing its sectors
  and programming them, and resets the chip as `--after` says when its command ends, also
  after an error (esptool 5.4, the `teardown` of its commands).
- WLED mounts its file system with `WLED_FS.begin(true)` on the ESP32
  (`wled00/wled.cpp`): a file system it cannot mount is formatted, settings and show with
  it.
- The LittleFS library of the tool (`littlefs-python` 0.19) mounts an image in memory with
  a context whose `read` it calls for every block it reads; `used_block_count` traverses
  the file system.
- The core's live route (`core/src/storage.cpp`, `upload.cpp`, `content.cpp`): an upload
  is written as `upload.part` and checked through `read_at`, whose `FileSource` keeps a
  CRC-32 of what it read; `storage_install_upload` renames it onto its name, and for a new
  name writes `pending.txt` and the show file; a removal writes `pending.txt` and the show
  file and removes the file. A cleanup that fails sets `pending_cleanup`, and every change
  is then refused with `storage-error` until the next start settles `pending.txt`.
- The check after the start reads each file whole through the second source
  (`check_file_step`), and seed 32 marks a file read whole in this boot with `checked`.
- `odrigctl/content.py` `upload` sends `upload begin`, the pieces and `upload end`.
- Seed 36 keeps the saved playlist order in `order.txt` of `/odrig`, written through
  `order.part` when a command moves an animation and by nothing else; the core removes an
  `order.part` at its start. `storage.folder_files` does not take `order.txt` as a file of
  a show folder.

## The image: only what differs

`storage.change_of(present, wanted)` gives a `Change(kept, added, replaced, removed)` of
names. `storage.with_show(image, files)`:

1. returns the image as it is when `/odrig` holds exactly the files;
2. otherwise, on the mounted image: creates `/odrig` when it is missing; writes each added
   file under its name and each replaced file under a spare name `~<n>` that no file has;
   renames each spare onto its name, which replaces the old file in one commit of the
   file system; removes the files that go; removes a folder inside `/odrig` left empty.
   While the new bytes are written every old file is still there, so the allocator puts
   them into free blocks;
3. when the file system has no room for that, does it again from the image before with
   the files that go and the old files of the replaced ones removed first;
4. checks the result: the geometry is the same, `/odrig` holds exactly the files, every
   file outside it is the same, and every file outside `/odrig` and every kept file of it
   has the same blocks of its own (`blocks_of_files`); otherwise `verify-failed`.

`no-space` is raised when even the second way does not fit, before the board is written.

`folder_files` takes `order.txt` as a file of the show. `install-show` adds the board's
`order.txt` to the files of a folder that holds none, so that it is kept like any other
unchanged file; a folder's own `order.txt` replaces it.

## Blocks in use and the plan

```python
class _Watched(UserContext):     # notes each block the file system reads
def blocks_in_use(image):        # {0, 1} | blocks read by used_block_count and by reading every file
def blocks_of_files(image):      # path -> blocks its bytes are read from, less the records' blocks
Plan = namedtuple("Plan", "free in_use")
def plan(before, after):         # the runs of the change outside and inside blocks_in_use(before)
def run_bytes(runs):
```

`runs` takes an optional set of block numbers, `among`, and gives only the changed blocks
among them. The number of blocks in use equals the file system's own count of its used
blocks, which a test checks. Measured on a full storage (the tests'
`full_storage`): a removal changes 3 blocks, 2 of them in use; an addition of 120 KB 33
blocks, 2 in use; a replacement of 140 KB 37, 2 in use; the folder rebuilt as before
changed 2,046 to 2,732 blocks, 8.4 to 11.2 MB.

## The write

`write_storage(on_port, region, before, make, say)`:

1. makes the new image; a failure or an interrupt here restarts the board, nothing written;
2. nothing differs: the board is restarted, `storage: unchanged: nothing written`;
3. otherwise says the plan line, writes the new image as `<time>-after.bin.part`, writes the
   journal at the step `free`, and `apply_change`:
   - the runs of free blocks in one esptool call. A failure or an interrupt (the call is
     ended) removes the journal and the new image and restarts the board: the reason is
     esptool's, or `cancelled`; the detail ends `the change was not made: no block the
     board's file system uses was written, and the board holds its storage from before`.
   - under `held_interrupts()`: the step `commit` in the journal, the runs in use in one
     call, the step `compare`, and one `verify-flash` of every run. Every call has
     `--after no-reset`. A failure is `recovery-needed`, the journal and the new image
     stay, and the chip stays in its bootloader.
4. keeps the new image, removes the journal, restarts the board (`chip-id` with `--after
   hard-reset`) and says `storage: committed: N bytes written and compared; the board
   restarts`, with a note when an interrupt waited.

esptool runs in a session of its own (`start_new_session=True`), so that an interrupt
from the keyboard reaches the tool alone: the tool ends esptool by its `subprocess.run` when
the interrupt is not held, and lets it finish when it is. `held_interrupts()` sets a handler
of `SIGINT` that only notes it, and puts the one before back.

`Flasher.compare(files, regions, restart)` is `verify-flash` with several stretches.

## The journal

`fwtool/journal.py`, without the LittleFS library, so that every command can ask it:

```json
{"address": 6356992, "size": 10354688, "image": "20261024T210000-after.bin.part",
 "step": "free", "free": [[409600, 122880]], "in_use": [[8192, 8192]]}
```

`read()`, `refuse_open()`, `begin(region, image_path, plan)`, `step(change, name)`, `end()`,
`runs_of(change, image)` and `outside(plan, size)`. It is written to a spare file, flushed
to the disk and renamed over the journal. `cli.main` calls `refuse_open()` for every
command that touches the board's flash (`flash`, `restore-stock`, `big-storage`,
`install-show`, `set-wifi`, `set-limit`, `read-limit`, `install-firmware`, `read-show`,
`test-board`, `test-air`) before the command looks for the board.

## recover-storage

```
python3 firmware/fw.py recover-storage [--port P] [--whole] [--wait SECONDS]
```

1. No journal: `storage: nothing to recover: ...`, status 0, the board untouched.
2. Reads the table; a region other than the journal's is `layout-mismatch`.
3. Step `free`: the change was cut before its commit (the tool ended, the computer lost
   power). The journal and the new image are removed, the board restarted and its status
   printed: `storage: given up: ...`.
4. Otherwise, without `--whole`: the chip compares the board's storage outside the change
   with the new image (`journal.outside`); a difference is `storage-changed`, nothing
   written, the chip in its bootloader. Then the free runs and the runs in use, in two
   calls under `held_interrupts()`, the comparison of the runs, the new image kept, the
   journal removed, the restart, `storage: committed: the change was finished: ...`, and
   the board's status. With `--whole` the new image is written whole as one run in use.
5. A failure of its write keeps the journal: `recovery-needed`, `run ... recover-storage
   again`.

## What install-show says

```
layout: WLED's, storage 10354688 bytes
show: kept 56 files
show: added new.odrg, 120000 bytes
show: removed bad.odrg, 65262 bytes
storage: 33 blocks to write, 135168 bytes: 31 free first, then 2 in use
storage: committed: 135168 bytes written and compared; the board restarts
{"ok":true,...}
```

`show: replaced <name>, <bytes> bytes, was <bytes>`; nothing changed:
`show: kept 4 files; nothing added, replaced or removed` and `storage: unchanged: nothing
written; the board restarts`. `--dry-run` prints the show lines and the plan line,
`storage: dry run: nothing written; the board restarts`, and restarts the board.
`--keep-copies DIR` is checked before the board is touched (`output-not-empty`) and
written from the image before, with `kept copies: N files in DIR`. `set-wifi`, `set-limit`
and `install-firmware` keep their lines.

## The live route

### The file the last upload installed

`Upload` gains `uint8_t installed` in the padding after its name: `upload end` sets it when
it installed the file, and an `upload begin` that opens an upload clears it. The upload's
id, name, size and running CRC-32 stay as they were until the next upload opens. The core
grows by no byte. A CRC-32 for every file would take 8 bytes an entry of the file table,
1,056 bytes for the target file, which after seeds 31, 32 and 36 has about 370 bytes left
with a drive; so a file the check after the start read, or an older upload installed, is
uploaded again as before.

### upload begin with a CRC-32

`commands.cpp` takes 5 or 6 words for `upload begin`; the sixth is read by `crc_word`.
`upload_begin_known(core, now, id, name, bytes, crc, reply)` in `upload.cpp` answers
`{"ok":true,"unchanged":true}` when the upload is `installed` with this id, name, size and
CRC-32 and the item `id` is an animation item whose file has the name and no `fault`;
otherwise it calls `upload_begin`. An upload that began since, also one cancelled, makes
the file unknown. The order of the refusals of `upload begin` is kept.

### The cleanup at the next change

`storage_cleanup(core)` in `storage.cpp`: nothing to do when `pending_cleanup` is 0;
otherwise reads `pending.txt` with `read_at` into the chunk buffer (at most 1,500 bytes),
removes every file it names that no item names, and then `pending.txt`; true when all
went. A read that fails leaves it to the next start. `storage_install_upload`,
`storage_remove_item`, `storage_remove_many` and `content_ignore` call it where they now
refuse on `pending_cleanup`.

### `remove many` without a file that goes

When every removed animation's file is named by another item, `storage_remove_many` gives
the host a `write` of 0 bytes for `pending.txt`, which the host interface does not allow
(the test host stops with `file misuse`). It then writes no `pending.txt`, and has no
cleanup to do after the rename. The fault tests of `remove many` find it.

### odrigctl

`content.upload` sends `upload begin <id> <name> <bytes> <crc32>`; a reply `bad-argument`
to it sends the form without the CRC-32 once. A reply with `unchanged` ends the upload.
`odrigctl upload` writes one line to standard error after the upload: `upload: unchanged:
the target holds this file already; nothing was sent`, `upload: committed: <bytes> bytes
sent and checked by the target`, or `upload: not committed: <error>; the show is as it
was`; the reply is printed as today.

## Tests

- `tests/firmware/test_incremental.py`: the regression (task 1); a full storage of each
  layout, removal, addition, replacement and the same folder: changed blocks, the files,
  the settings, no file moved, the free part alone leaves the old file system, the blocks
  in use counted as the file system counts them; the replacement without room; no-space;
  `change_of`; a folder inside `/odrig`.
- `tests/firmware/test_recovery.py`: a stand-in board that keeps its storage, with a fault
  at one call (`fail`, `cut`, `interrupt`, `kill`): the order of the calls, each cut before
  the commit, in it and in the comparison, the interrupt held, every command refused while
  a journal is there, `recover-storage` from each step, `storage-changed` and `--whole`, a
  cut recovery run again, no journal, both layouts, `set-limit` the same way.
- `tests/firmware/test_storage.py`, `test_layouts.py`, `test_wifi_commands.py`,
  `test_limit_commands.py`, `test_flasher.py`: the lines and the calls as they are now; the
  dry run and the copies.
- `tests/core/test_incremental.py`: the bytes each live change writes with `--trace-store`
  in a show of 100 items; `unchanged` after an upload, not for a file the check read, not
  after another upload began, not for a removed item, not for another name, size or
  CRC-32; a power cut and
  a failure at every storage call of `remove many`, `ignore` and the start's cleanup; the
  cleanup at the next change.
- `tests/emulator`: `odrigctl upload` twice over the line port and HTTP: the second says
  `unchanged`; a target that refuses the CRC-32.

## Documents

`docs/firmware.md`: `install-show` as it is now, `recover-storage`, the reasons
`cancelled`, `recovery-needed` and `storage-changed`, and a section "Changing what the
board holds" that separates flashing, a change by command, a change by image, the
quarantine of seed 32, the board's check and the recovery of storage. `docs/commands.md`:
`upload begin` with a CRC-32, `unchanged`. `docs/core.md`: the CRC-32 of a file and the
cleanup. `docs/emulator.md`: `odrigctl upload`'s line. `docs/decisions.md`: a dated line.

## Combining with the other lines

Seed 33 (line A) reports readiness and keeps fault diagnostics, and may change what the
tool says after the board's restart: this seed adds lines before that reply and changes
nothing of `board.settled`. Seed 35 builds catalogs on the live route's storage: this seed
adds `storage_cleanup` and one condition in each change, and renames nothing. Seed 36's
saved playlist order is a file of `/odrig` the image route keeps or changes like any other.
