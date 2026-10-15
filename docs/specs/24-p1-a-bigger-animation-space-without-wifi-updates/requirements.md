# Requirements: a bigger animation space without Wi-Fi updates

Seed: [`project-seeds/24-p1-a-bigger-animation-space-without-wifi-updates/seed.md`](../../../project-seeds/24-p1-a-bigger-animation-space-without-wifi-updates/seed.md).

The board's flash holds two firmware slots of 3 MB each and a storage of 10,354,688 bytes.
The second slot is only for updates over Wi-Fi, which this project does not use: the
firmware is updated over the USB cable with `firmware/fw.py`. This spec gives the second
slot's room to the storage, which grows to 13,500,416 bytes, and teaches the firmware tool
the new layout, the move to it, and the way back.

The owner answered the seed's questions on 2026-10-15:

1. Moving a board to the new layout need not keep the animations it holds: installing
   them again is the owner's.
2. An update over Wi-Fi may fail, as long as its message says the reason correctly, so
   that no time goes into finding it out.

In this document "WLED's layout" is the partition table of WLED's 16 MB build, with two
firmware slots; "the bigger layout" is the table this spec makes, with one; "the
settings" are every file of the storage outside the folder of the installed show,
`/odrig`: WLED's settings, among them the network's name and password and the limit of
the LED current; and "the move" is the change of a board from WLED's layout to the bigger
one.

## Requirement 1: the bigger layout

1. The bigger layout SHALL keep WLED's partitions `nvs`, `otadata` and `coredump` where
   they are, and the first firmware slot at `0x10000` with its 3,145,728 bytes.
2. It SHALL have no second firmware slot, and its storage, `spiffs`, SHALL begin at
   `0x310000` and hold 13,500,416 bytes.
3. On the bigger layout no update over Wi-Fi SHALL be able to write any part of the
   flash: not the firmware that runs, not the storage.

## Requirement 2: the move

1. A command of the tool SHALL move a board of WLED's layout to the bigger one: it writes
   the bigger layout's partition table and a storage of 13,500,416 bytes that holds the
   settings as they were and no show.
2. Until the new partition table is written, the board SHALL keep its old layout whole:
   nothing the move writes before the table lies in a partition that WLED's layout uses.
3. The command SHALL keep a copy of the board's storage as it was in the work folder
   before it writes, and say where.
4. On a board that has the bigger layout already, the command SHALL write nothing and say
   so.
5. Afterwards the board SHALL answer `status` on the serial chip's port with its show
   empty, and its settings SHALL be as they were.

## Requirement 3: either layout

1. `flash`, `install-firmware`, `install-show`, `set-wifi`, `set-limit`, `read-limit` and
   `read-show` SHALL work on a board of either layout, and SHALL say which layout they
   found.
2. A layout that is neither SHALL be refused as today, with `layout-mismatch`, before
   anything is written.
3. `space` on a board of the bigger layout SHALL report the bigger total and free space;
   the firmware reports the storage it finds, whatever its size.

## Requirement 4: the way back

1. `restore-stock --full` SHALL put WLED's layout back, with stock WLED, on a board of
   either layout.
2. On a board of the bigger layout it SHALL also write WLED's storage, holding the
   settings as they were and no show, so that stock WLED starts with its settings.
3. `restore-stock` without `--full` SHALL go on writing only the first firmware slot, on
   either layout.

## Requirement 5: an update over Wi-Fi

1. On a board without a second firmware slot, an update sent to WLED's page SHALL be
   refused before anything is written, with a message that says why: the board has no
   second firmware slot, and its firmware is updated over the USB cable with
   `firmware/fw.py`.
2. The board SHALL keep playing through the refusal, and its firmware and its storage
   SHALL stay as they were.
3. On WLED's layout an update over Wi-Fi SHALL work as it does today.

## Requirement 6: the emulator

1. The emulator's default storage, the total that `space` reports when `--storage` is
   not given, SHALL be 13,500,416 bytes, and so SHALL the default of the core's host
   program of the tests.

## Requirement 7: tests and documents

1. The suite of the firmware tool SHALL cover both layouts: the commands of Requirement 3
   on each, the move, the way back, a layout that is neither, and the order of the
   move's writes.
2. Every suite that needs no board and no phone SHALL pass.
3. The documents SHALL say what the layout is, why, what was given up for it, how a board
   is moved and moved back, and what the firmware answers to an update over Wi-Fi.
4. On the board: after the move the settings are as they were and `status` answers on
   the serial chip's port and over Wi-Fi; the owner's show of 113 animations of
   2026-10-15 installs whole and `list` names all of them; the way back and the move
   again are tried; and the board is left playing with its settings as they were, at a
   brightness of 40 or less. Only the board can show these.

## Left out on purpose

- Keeping the installed show through the move or the way back.
- Updates over Wi-Fi on the bigger layout.
- Changing the bootloader, the `nvs` partition or the first firmware slot.
