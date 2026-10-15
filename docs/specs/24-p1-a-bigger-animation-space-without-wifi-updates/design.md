# Design: a bigger animation space without Wi-Fi updates

## Overview

The firmware tool learns a second partition table, the bigger layout, which it makes
itself. A new command, `big-storage`, moves a board to it, keeping the settings; the way
back is `restore-stock --full`, which on a board of the bigger layout also writes WLED's
storage with the settings. Every command that reads the board's table says which layout
it found. The firmware refuses an update over Wi-Fi when the board has no second slot,
with a message of its own, and the layout itself makes such an update unable to write:
its one firmware slot is a factory slot, for which the update library finds no slot to
write. The emulator's default storage follows the board's new size.

## What this design relies on

From the sources on 2026-10-15:

- `firmware/fwtool/partitions.py` reads a table and checks only that it has an
  application partition at `0x10000` that the image fits in and a data partition named
  `spiffs`; `storage_of` writes the storage where the table puts it, at its size.
- `storage.from_board` reads the whole storage and keeps it in the work folder, eight
  images at most for each size; `write_storage` writes the blocks that changed.
- WLED's update over Wi-Fi, `POST /update`, and ArduinoOTA both start with
  `Update.begin`, which takes `esp_ota_get_next_update_partition(NULL)`. With one
  application slot of the kind `ota_0` that call answers the slot that runs, and the
  update would erase the running firmware; with a slot of the kind `factory` and no
  `ota_` slot it answers none, and `Update.begin` fails with `Partition Could Not be
  Found` before it writes anything.
- WLED calls the usermods' `setup` before it registers its own pages, and the web server
  takes the first handler that matches a request.
- littlefs-python 0.19.0 of the work folder has `fs_grow`.
- Stock WLED and this firmware mount the storage at the size of the partition, and the
  file system's own record of its size must match it.

## The layouts

`partitions.py` gets the two layouts as lists of entries, `WLED` and `BIGGER`, a function
`table(entries)` that makes the bytes of a table with its MD5 entry, and `layout_of(found)`,
which names a parsed table `WLED's layout` or `the bigger layout` by its entries, or
refuses it with `layout-mismatch`.

| Name | Type, kind | WLED's layout | The bigger layout |
|---|---|---|---|
| `nvs` | data, nvs | `0x9000`, `0x5000` | the same |
| `otadata` | data, ota | `0xE000`, `0x2000` | the same |
| `app0` | app, `ota_0` in WLED's, `factory` in the bigger | `0x10000`, `0x300000` | the same place and size |
| `app1` | app, `ota_1` | `0x310000`, `0x300000` | none |
| `spiffs` | data, spiffs | `0x610000`, `0x9E0000` | `0x310000`, `0xCE0000` |
| `coredump` | data, coredump | `0xFF0000`, `0x10000` | the same |

`table(WLED)` gives the bytes of the stock `partitions_s3_16m.bin`; a test of the suite
checks it with the table of its stand-in board, and with the stock file when the stock
folder is there.

Every command that reads the board's table prints, before anything else it prints, one
line: `layout: WLED's, storage 10354688 bytes` or `layout: bigger, storage 13500416
bytes`. `flash`, `install-firmware`, `install-show`, `set-wifi`, `set-limit`,
`read-limit` and `read-show` print it.

## The move: `big-storage`

```
python3 firmware/fw.py big-storage [--port P] [--wait SECONDS]
```

1. The tool reads the board's table. A table of the bigger layout: it prints
   `layout: bigger, storage 13500416 bytes` and `nothing to do`, writes nothing and ends
   with 0. A table that is neither: `layout-mismatch`.
2. It reads the board's storage, keeps it in the work folder and prints the path.
3. It makes the new storage: a LittleFS file system of the disk version of the old one,
   with 4,096-byte blocks, made at 768 blocks, the size of the second slot, holding the
   settings: every file of the old storage outside `/odrig`. Then `fs_grow` takes it to
   3,296 blocks, 13,500,416 bytes. Everything it holds lies in its first 3,145,728 bytes,
   which are the second slot's on WLED's layout. The tool checks the result: its size,
   its files equal to the settings, and no `/odrig`.
4. It writes, in a first esptool call without a restart, the new storage's first
   3,145,728 bytes at `0x310000`, and verifies them. The board still has WLED's layout
   whole: nothing of it lies there.
5. In a second esptool call it erases the boot selection, writes the bigger layout's
   table at `0x8000`, verifies it and restarts the board. Then the storage's blocks
   beyond the first 3 MB are those of WLED's old storage; the file system knows them as
   free, and erases a block before it writes it.
6. It waits for the reply to `status`, as `flash` does, and prints it.

The regions the move may touch are the table, the boot selection and the bigger layout's
storage. A failure in step 4 leaves WLED's layout as it was. A failure in step 5, the
writing of one 4 KB sector, can leave a table that the bootloader refuses; the board is
then brought back with `restore-stock --full`, and the settings with `set-wifi` and
`set-limit`, or from the kept image.

## The way back: `restore-stock --full`

As today, it writes the stock bootloader, table and application. On a board whose table
is the bigger layout, the tool first reads the board's storage, keeps it, and makes
WLED's storage: a file system of 2,528 blocks holding the settings, written at `0x610000`
in the same esptool call. The show is not kept: it may not fit, and installing it again
is the owner's. On a board of WLED's layout nothing changes: storage is not written.

## The firmware: an update over Wi-Fi

A new source of the usermod, `odrig_update.cpp`, with `OdrigUpdate::begin()`, called in
`setup()`. When the board has no slot an update could write,
`esp_ota_get_next_update_partition(NULL)` is none or is the slot that runs, it registers
a handler of its own for `POST /update`, ahead of WLED's: it takes the upload and throws
it away, and answers with WLED's message page, status 501, `Update refused` and

> This board has no second firmware slot: that room holds animations. Its firmware is
> updated over the USB cable with python3 firmware/fw.py flash.

The usermod's `onUpdateBegin` is not called, so the LEDs go on playing. On WLED's layout
it registers nothing, and WLED's update works as before. ArduinoOTA, when it is on, fails
at `Update.begin` on the bigger layout, with its own message.

## The emulator and the core's host

`emulator/host.py` `STORAGE_BYTES` and the core's test host `kBoardStorage` become
13,500,416, and the tests that state the default with them.

## Tests

- `tests/firmware/`: the two tables, `table(WLED)` against the stand-in's table and the
  stock file; `layout_of` for each and for a table that is neither; the layout line of
  each command on a stand-in board of each layout; `big-storage`: the order of its two
  calls, the regions, the settings kept, no `/odrig`, the grown file system mounted at
  13,500,416 bytes with every block it uses in the first 3 MB, nothing written on a board
  of the bigger layout; `restore-stock --full` on each layout; the update handler's
  source: the check of the slot, the handler registered before WLED's, the message, no
  call of `onUpdateBegin`.
- `tests/emulator/`, `tests/core/`: the default storage.
- `tests/board/`: the storage total that `space` reports is the board's partition size.

## Documents

`docs/firmware.md`: the two layouts, why, what was given up, `big-storage`, the way back,
the regions, the layout line, and the refused update. `docs/decisions.md`: "What fits"
and a line in its change log. `docs/format.md`, "What fits". `docs/emulator.md` and
`docs/core.md`: the default storage. `docs/firmware-prerequisites.md`. `AGENTS.md`.

## What needs the owner

- The board: the move, the settings and `status` afterwards on the serial chip's port and
  over Wi-Fi, the show of 113 animations, the way back and the move again, and the board
  left playing at a brightness of 40 or less.
