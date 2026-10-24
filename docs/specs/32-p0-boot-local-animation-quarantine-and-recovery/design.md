# Design: boot-local animation quarantine and recovery

## Overview

The core keeps a file fault in the file's entry of the file table and in the drive's
entry of a drive's file, instead of making the show invalid. Every route that chooses an
animation asks whether it is usable. `list` reports the fault, `play` refuses the
animation, and the commands that repair the show no longer wait for the check after the
start. The app grays what `list` marks. Nothing of the format, the show file or the
storage changes.

## What this design relies on

Today's code, with seeds 28, 29, 30, 31 and 38 in it:

- `core_fail` (`core/src/core.cpp`) makes the show invalid; `fail_file` calls it for every
  file fault: from `open_file` at the start, `check_file` (a host without writable
  storage), `check_step` (the check after the start) and `advance`
  (`core/src/player.cpp`).
- A drive's file has a `DriveEntry` with `kDriveToCheck`, `kDriveInPlaylist` or
  `kDriveLeftOut`; it gets its id from `free_drive_id` when its check passes, and
  `content_list` lists only the files in the playlist.
- `list`, `remove`, `remove many`, `ignore` and `upload begin` answer `busy` until
  `check_complete`; the upload's check and the check after the start share the second
  decoders (`Checker`); `drive_check_yields` hands them from a drive's check to an
  upload.
- `FileInfo` is 48 bytes: `name[33]`, then three bytes of padding before `bytes`.
- Seed 31: the decoder settles in slices; `note_fault` keeps the fault's context.
- Seed 36 (line B) will add `external` and seed 37 (line C) `type` to `list` items;
  this seed adds `fault` beside them and renames nothing.

## The file table

```cpp
struct FileInfo {
    char name[33];
    uint8_t fault;      // a Reason: kNone while usable
    uint8_t checked;    // read whole by a check in this boot
    uint32_t bytes;
    uint64_t total_ms;
};
```

The two bytes take the padding: the table does not grow. `set_file` (an upload's file)
sets `checked` and clears `fault`: a passed check is a new content generation.

`quarantine_file(core, index, reason, work)` sets `fault`, writes the log line
`file <name> unavailable: <reason>`, keeps the fault's context, closes the player's
stream when it holds the file, and calls `player_file_failed`. `fail_file` calls it for a
file fault; a show fault still calls `core_fail`. `usable(core, item)` is true for an
animation item whose file has no fault, and for a cycle with a usable member.

## The player

- `plays()` is false for a quarantined animation, so the playlist, `next_animation`,
  `player_first_animation` and `player_start` pass over it.
- A cycle's turn: the entry of the turn, or the first usable entry after it in the
  cycle's order. `advance` takes it; with none the player calls `player_play_all` from the
  first usable animation, or halts.
- `player_file_failed(core, file)`: when the playlist's turn is an animation of the file,
  the playlist goes on with the next usable animation, from its first frame at the next
  refresh, or halts. A cycle goes on at the next refresh, with the rule above.
- When `advance` meets a file fault it quarantines the file and returns
  `kShowsBefore`: the refresh keeps the picture before.
- `play <id>`: an animation that is not usable, or a cycle without a usable member, is
  refused with `unavailable` before anything is opened.

## The checks

- `check_step` skips a file that is quarantined or `checked`. On a file fault it
  quarantines and goes on with the next file. `check_done` is set when every file was
  passed.
- `check_file` (a host without writable storage) quarantines and goes on with the next
  file; so does `open_file` at the start.
- The check after the start takes no step while an upload is open. `check_yields`
  (in place of the body of `drive_check_yields`, which stays as its name for a drive)
  closes the file the check is in and has the check begin it again; `upload_begin` calls
  it. `content_take_out` keeps `check_at` at the same file: one lower when a file before
  it left the table, and the file begins again when it was the one that left.

## A drive

- `drive_touch` gives every place of a new drive its id at once, with the rule of today
  (the lowest from 60001 up that the show and the drive's places before it do not use),
  so an id stands for one file of one drive.
- A `DriveEntry` gains `uint8_t fault`. `drive_left_out` sets it. `content_list` lists
  the places in the playlist and the places left out, in place order; a place still to
  be checked is not listed yet, as today.
- The boot's memory of left-out files, in a block taken at the start beside the drive's
  table:

```cpp
struct Remembered {           // 16 of them
    char name[33];            // the drive's name of the file, cut to 32 characters
    uint8_t reason;
    uint16_t first_read;      // the bytes of the file's first read
    uint32_t crc;             // their CRC-32
};
```

  When a drive's file is left out with a file fault, its name, the bytes of its first read
  and their CRC-32 (the second source keeps both) are written into the next of the 16
  places, the oldest giving way. At the header step of a drive's file, a remembered entry
  with its name, the same bytes and the same CRC-32 leaves the file out at once with the
  remembered reason. 16 entries are 704 bytes; a file pushed out of the memory is
  checked again, in slices.

## Commands and replies

- `list`: an animation item `{"id":3,"file":"a.odrg","bytes":null,"ignored":false,"fault":"bad-code"}`;
  a drive's file `{"id":60002,"file":"b.odrg","bytes":null,"fault":"read-error"}`.
  `bytes` is `null` until the file was read whole. `fault` comes last among the members
  this seed knows, so that the members of seeds 36 and 37 can follow it.
- `list`, `remove`, `remove many`, `ignore` and `upload begin` no longer answer `busy`
  for the check after the start. `upload begin` still answers `busy` while an upload is
  open, and `mapping set` and `mapping test on` keep their rules.
- New error code `unavailable`: `play <id>` of a quarantined animation or of a cycle
  without a usable member.
- `status` and `space` keep their members; `space`'s `animations` counts quarantined
  animations too: they are installed.

## The app

`app/www/commands.js`: `list` accepts an optional string `fault` and a `bytes` of `null`,
and keeps both. `app/www/screens/show.js`: a row with `fault` gets the class
`unavailable` (grayed in `style.css`), a text `Unavailable: <reason in words>` and a
disabled Play button; a drive's row adds `Fix it on a computer: the card is read-only
here.` `app/www/messages.js` gives the words of a reason. The storage counts of seed 28
count quarantined animations as installed.

## The reference player

`tests/core/support.py`'s `ReferencePlayer` states the rules a second time: a file fault
quarantines, the playlist and cycles pass over quarantined animations, the refresh that
meets a fault keeps its picture, `play` refuses with `unavailable`, `list` reports
`fault` and `bytes` of `null`, and the commands of repair answer during the check.

## Tests

- `tests/core/test_quarantine.py`: first the old global invalidation and refused repair
  (expected failures in task 1); then every rule above with sessions compared with the
  reference player; `--trace-files` counts the openings of a quarantined file over many
  turns; replacement by upload; remounts with the same content, with another file of the
  same name, and of another drive; `ignored` beside quarantine; every animation bad; show
  faults still invalid.
- The existing tests that expected the global invalidation of a file fault expect the
  quarantine.
- `tests/emulator/test_quarantine.py`: the emulator starts with a bad file and plays the
  others; `list` over HTTP and the line port reports `fault`.
- `tests/app`: a page scenario with a quarantined animation: grayed, its reason, Play
  disabled, and the healthy ones play.

## Documents

`docs/show.md` ("When a show is invalid" becomes show faults only; a new section "An
animation that cannot be played"), `docs/core.md`, `docs/commands.md` (`fault`,
`bytes` null, `unavailable`, the commands during the check), `docs/reasons.md`,
`docs/android-app.md`, `docs/firmware-additions.md` (row 5 states what holds),
`docs/decisions.md` (the change of the policy, dated).
