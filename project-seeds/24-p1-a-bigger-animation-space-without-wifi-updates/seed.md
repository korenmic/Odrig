# A bigger animation space without Wi-Fi updates

## Summary

The board's space for animations grows from 10.35 MB to about 13.5 MB. The room comes from
the second firmware slot, which only updates over Wi-Fi need: from now on the firmware is
updated over the USB cable only. The firmware tool learns to make the bigger space, to
fill it, and to put the old layout back.

## Priority

- `P1`

## Depends On

- Seed 04, for the firmware tool that flashes the board and installs a show.
- Seed 08 and seed 15, for the settings that the tool keeps in the board's storage.

## Product Context

The board's chip has 16 MB, split by WLED's layout into parts: two firmware slots of 3 MB
each, the storage of 10,354,688 bytes that holds WLED's settings and the installed show,
and small parts for WLED's own use. Two slots let WLED take a new firmware over Wi-Fi
while the old one runs. This project updates the firmware over the USB cable only, with
`firmware/fw.py`, which writes the first slot; the second slot is never used.

On 2026-10-15 the owner installed a show of 113 animations for the 60 x 60 canvas, 10.1 MB
of files. It did not fit: the storage holds the files in blocks of 4,096 bytes with
the file system's own records, and was short by about 0.2 MB. Six of the smallest
animations were left out, and 107 were installed and play. The owner gave up updates over
Wi-Fi so that the space of the second slot can hold animations.

The second slot lies right before the storage on the chip: from address `0x310000` to
`0x610000`. With the storage starting there instead of at `0x610000`, it grows by
3,145,728 bytes, to 13,500,416.

The tool checks the board's partition table before it writes anything, and builds the
image of the storage at the size the table gives. It refuses a layout that is not
WLED's, as a safety check. That check has to learn the new layout, and a board has to be
moved to it once.

## Technical Constraints

- The whole flash is never erased, and no eFuse is written. The bootloader stays as it is.
- WLED's settings in the storage, the network's name and password and the limit of the
  LED current, are kept through the move to the new layout.
- The move does not keep the installed show: the owner installs it again afterwards.
- The first firmware slot stays at `0x10000` with its 3 MB, so every firmware the tool
  builds still fits.
- WLED's update over Wi-Fi does not work on the new layout. It fails without harm to the
  firmware that runs, the board keeps playing, and the message it shows says why: the
  board has no second firmware slot, and its firmware is updated over the USB cable with
  `firmware/fw.py`.
- The tool can put WLED's own layout back, with stock WLED, as `restore-stock` does today.
- The emulator reports the size of the storage it is given; its default follows the new
  size of the board's storage.
- The firmware is built only as the tool builds it. On the board the brightness stays at
  40 or less.
- Tests that need the board are kept apart from those that need none.

## Required Behavior

1. A command of the tool moves a board to the new layout: the partition table without the
   second firmware slot, and a storage of 13,500,416 bytes that holds the board's settings
   as they were and no show.
2. `install-show`, `set-wifi`, `set-limit`, `install-firmware`, `flash` and `read-show`
   work on a board of either layout, and say which layout they found.
3. `space` on the board reports the bigger total and free space.
4. An update over Wi-Fi on WLED's page is refused with a message that names the reason
   and the way that works: the USB cable and `firmware/fw.py`.
5. A show that did not fit before fits now: the show of 113 animations of 2026-10-15
   installs whole.
6. A command of the tool puts WLED's own layout back, with stock WLED.
7. The documents say what the layout is, why, and what was given up for it.

## Definition Of Done

1. All test suites that need no board pass, and the tool's suite covers both layouts.
2. On the board, after the move, the network's name and password and the limit are as
   they were, and `status` answers on the serial chip's port and over Wi-Fi.
3. On the board, the show of 113 animations of 2026-10-15 is installed whole, and `list`
   shows all of them.
4. Putting WLED's layout back and moving to the new one again are tried on the board.
5. Afterwards the board is left playing with its settings as they were, at brightness 40
   or less.

## The Owner's Answers

On 2026-10-15:

1. Moving a board to the new layout need not keep the animations it holds: installing
   them again is the owner's.
2. An update over Wi-Fi may fail, as long as its message says the reason correctly, so
   that no time goes into finding it out.
