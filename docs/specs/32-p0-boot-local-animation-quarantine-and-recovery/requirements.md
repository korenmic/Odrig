# Requirements: boot-local animation quarantine and recovery

Seed: [`project-seeds/32-p0-boot-local-animation-quarantine-and-recovery/seed.md`](../../../project-seeds/32-p0-boot-local-animation-quarantine-and-recovery/seed.md).

Today one installed `.odrg` file that is missing, has a bad header, another canvas, a bad
body or cannot be read makes the whole show invalid: the LEDs go dark, `list`, `remove`
and `upload` are refused with `show-invalid`, and the operator cannot repair anything
without new firmware or a new show. A bad file of the drive (the USB stick or the microSD
card) is left out and disappears from `list`. This spec makes a bad animation
unavailable for the current boot, keeps it listed with its reason, plays the healthy
ones, and keeps every safe repair open. The owner approved the change of the
all-or-nothing policy on 2026-10-24; the other choices were made under the owner's
mandate of 2026-10-24 and are in `docs/drifts.md`, "Seed 32".

Words used here:

- **a file fault**: a reason that belongs to one `.odrg` file: `file-missing`,
  `size-mismatch`, `read-error` while the file is read, or a reason of "ODRG files" in
  `docs/reasons.md`;
- **a show fault**: a reason of the mapping file or the show file, `duplicate-id`,
  `undefined-id`, `nested-cycle`, or `out-of-memory`;
- **quarantined** (unavailable): an animation whose file had a file fault in this boot;
- **this boot**: from the core's start until the next start of the core.

## Requirement 1: a file fault is the file's, not the show's

1. A file fault of an installed file, met at the start, by the check after the start, by
   the whole-file check of a host that cannot change its storage or by the player, SHALL
   quarantine that file's animations and SHALL NOT make the show invalid.
2. The start SHALL end in a show that plays its usable animations and answers every
   command, also when every animation is quarantined; then nothing plays and the LEDs are
   dark.
3. A show fault SHALL make the show invalid as today: `status` reports it, and the
   commands that need a show are refused with `show-invalid`. No id is guessed.
4. Each quarantine SHALL write one log line, `file <name> unavailable: <reason>`, and keep
   the fault's context of seed 31.

## Requirement 2: what plays

1. The playlist, the start's choice and every cycle SHALL skip quarantined animations.
   A cycle whose turn names a quarantined animation SHALL play its next usable member in
   that turn; a cycle without a usable member SHALL give way to the playlist; with no
   usable animation nothing plays.
2. When the player meets a file fault, that refresh SHALL keep the picture before, and the
   next refresh SHALL play the animation after it, from its first frame. When the check
   meets a file fault in the animation that plays, the next refresh SHALL do the same.
3. `play <id>` of a quarantined animation, and of a cycle without a usable member, SHALL
   be refused with the new error code `unavailable`, without reading the file.
4. Valid shows SHALL play exactly as before.

## Requirement 3: remembered for the boot

1. A quarantined installed file SHALL not be opened again in this boot: not by the
   player, the check, `list` or `play`.
2. A quarantined file of a drive SHALL be remembered by its name and the CRC-32 of its
   first read: when a drive is taken up again in this boot, a file with the same name and
   the same first read SHALL be left out again with its reason, after that one read and
   without decoding its body. Another file of the same name, and every file of another
   drive, SHALL be checked anew.
3. A new boot SHALL check every file again. Quarantine SHALL write nothing to storage and
   SHALL be independent of `ignored` (seed 29): changing `ignored` does not revive a
   quarantined animation, and quarantine does not change `ignored`.
4. An upload that replaces a quarantined animation, and passes its check, SHALL make it
   available at once.

## Requirement 4: listed with its reason

1. `list` SHALL list a quarantined animation in its place, with the new member `fault`,
   the reason's name. A usable animation has no `fault`.
2. A file of a drive SHALL get its id when the drive is taken up, before it is checked,
   in the order of the drive's list; a file that is left out keeps its id and is listed
   with `fault`. Ids of one drive SHALL never pass to the files of another.
3. `bytes` of a file that has not been read whole SHALL be `null`.
4. Replies SHALL keep their limit of 1,024 bytes; `next` pages as today.

## Requirement 5: repair stays open

1. `list`, `remove`, `remove many`, `ignore` and `upload` SHALL be answered while the
   check after the start goes on, for every item, and while files are quarantined.
2. An upload during the check SHALL take the second decoders; the check SHALL go on after
   the upload with the file it was in, from its start. A file an upload installed SHALL
   not be checked again.
3. A removal during the check SHALL keep the check at its file.
4. A drive's file SHALL stay read-only: `remove` and `upload` of its id are refused with
   `in-use` as today.
5. The quarantine SHALL never remove, rename or write an animation's file.

## Requirement 6: a file is not the medium

1. A file fault of one drive file SHALL leave the drive's other files in the playlist.
2. A drive pulled out SHALL drop its files from the playlist and `list` as today, and SHALL
   not stop the installed animations.

## Requirement 7: the app

1. The operators' app SHALL show a quarantined animation in its list, grayed, with its
   reason in words beside it, and its Play button disabled.
2. The rest of the app SHALL stay usable, also when every animation is quarantined.
3. For a drive's unavailable file the app SHALL say that it is fixed on a computer, and
   SHALL offer no removal.
4. The app's checks of replies SHALL accept `fault` and a `bytes` of `null`.

## Requirement 8: tests and documents

1. Tests SHALL show first the old global invalidation and the refused repair.
2. The core's tests SHALL cover bad headers, bad bodies, missing files, files that cannot
   be read, all files bad, show faults, cycles, the start's choice, `play`, a fault after
   good playback, the opening counts of quarantined files, replacement, remounts of the
   same and of other content, and `ignored` beside quarantine.
3. The emulator's and the app's tests SHALL show a quarantined animation grayed with its
   reason, Play disabled, and the healthy ones playing.
4. `docs/show.md`, `docs/core.md`, `docs/commands.md`, `docs/reasons.md`,
   `docs/android-app.md`, `docs/decisions.md` and `docs/firmware-additions.md` SHALL say
   what holds now.
5. Every suite that needs no board SHALL pass. The board's trials stay for the board
   session: a bad file installed and on the card, boot completes, the board answers and
   plays the rest, brightness 40 or less; a person looks at the app and the LEDs.
