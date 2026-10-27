# More than 256 files on a drive

> **DRAFT. Do not run seed-to-spec on this seed.** It is a whiteboard for the owner's
> decision, not planned work. Its state stays `suspended` until the owner chooses a way
> below, rewrites it as a seed, removes this note and sets it to `remaining`.

## Summary

A drive, the board's microSD card or the emulator's `--drive` folder, shows at most 256
animation files in all, however they are spread over its sub-folders. The owner's
collection, `E:\artifacts\odrig\collection`, holds 359, so 103 of them are never listed.
This draft records why the limit exists and two ways to lift it.

## Priority

- `P2`

## Depends On

- Seed 20, a USB drive's animations, and seed 38, the microSD card.
- Seed 35, the internal and external catalogs, for the second way.
- Seed 41, sub-folder playlists, which groups the same 256 places into folders.

## Product Context

Why the limit exists. The core takes no memory beyond one fixed budget, 131,072 bytes for
the 60 x 60 installation (`docs/core.md`). It keeps a table of every file of a drive: 12
bytes for each place (its state, size, length and id), and 4 more for each place in the
saved order. `kDriveMost = 256` in `core/src/core_state.h` sets the places. With 256 of
them the target file takes 130,509 bytes, 99 percent of the budget. Each more place costs
16 bytes, so 256 more places would need about 4 KB that the budget does not have.

Seed 41 made the drive's sub-folders browsable and playable as playlists, but it gave them
no memory of their own: the folders are a tree over the same table, so the limit is on
the whole drive, not on a folder.

## The two ways (to be decided)

1. **A bigger budget.** Raise the core's budget for a host with a drive, and `kDriveMost`
   with it: about 4 KB for each 256 places more. Small in code: one constant, the budget
   and the tests that measure it. It holds only if the board has the room: the ESP32-S3's
   internal RAM is shared with WLED and the Wi-Fi, and its PSRAM, if fitted, would have to
   be where the core's memory comes from. The limit moves; it does not go.
2. **No table of every file in memory.** The card already has a catalog (seed 35). The core
   would keep only a window of places and read the rest of the catalog a page at a time
   when `list`, the playlist or the explorer reach it, as seed 44 reads the previews' pages.
   The number of files is then bounded by the card. More work in the core, the hosts and
   the saved order, and a drive without a catalog (the emulator's `--drive` folder, a stick)
   needs one made, or keeps a limit.

## Technical Constraints

- Whatever is chosen, the core keeps one fixed budget and takes no other memory.
- Nothing changes for a drive of 256 files or fewer.

## Required Behavior

To be written once a way is chosen.

## Definition Of Done

To be written once a way is chosen.

## Open Questions

1. Which way: a bigger budget, how big and in which memory of the board; or a window over
   the card's catalog? This is the owner's decision, and it changes a decision of
   `docs/decisions.md`, the core's memory budget.
2. Does the emulator's `--drive` folder keep a limit, or is a catalog made for it?
