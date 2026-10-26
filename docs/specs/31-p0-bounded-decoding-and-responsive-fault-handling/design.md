# Design: bounded decoding and responsive fault handling

## Overview

The decoder learns to stop in the middle of settling and go on at its next call, giving
the internal result `kPending` in between. Every caller treats `kPending` as "not yet":
the player keeps the picture before and tries again at the next refresh, the steps of the
checks take the same step again. Playback's catch-up gets a budget of body bytes per
refresh. Nothing about what a file means changes, so the converter, the Python library and
the vectors do not change.

## What this design relies on

- `OdrgDecoder::settled` (`core/src/odrg_decoder.cpp`) is the only place where a file's
  decode can do work not bounded by one frame record: a record holds at most `n + 1` data
  bytes and the palette 768 bytes, but settling inflates to the end of the stream.
- The players' catch-up loops, `first_loop_to` and `show_at` (`core/src/player.cpp`),
  decode records until the frame of the time; with short frames after a long pause they
  decode many records in one refresh.
- The check after the start (`check_file_step`, `core/src/core.cpp`), the upload's check
  (`core/src/upload.cpp`) and a drive's check take one step per refresh, a step being a
  header, one record or the end.
- A host's `read_at` returns or fails; the core cannot interrupt it.

## The decoder

```cpp
const uint32_t kSettleSliceBytes = 32768;   // inflated bytes of settling in one call

// in OdrgDecoder:
uint8_t settling;          // 1 while a settling is under way
Reason settle_found;       // the defect that started it
uint32_t settle_missing;   // data bytes of the record still owed
uint32_t settle_slice;     // bytes this call may still inflate
uint64_t body_read;        // bytes of the body taken so far, for the fault's context
```

`settled(found, left)` keeps `found` and `left`, sets `settling`, and goes on in
`settle_more()`, which inflates up to `kSettleSliceBytes` bytes and gives `kPending` when
the slice ends first. `next()` and `finish()` begin with `if (settling) return
settle_more();`. `open()` clears the fields. The uncompressed case settles in the same
way, by bytes of the file. `kPending` is a value of `Reason` after `kReasonCount`'s
documented names, with no name in `reasons.cpp`'s table; `reason_name` of it is never
asked for, and a test checks that no reply or log line holds it.

The constant can be set at build time (`-DODRIG_SETTLE_SLICE=…`), so that the core's tests
build a second host with slices of 7 bytes and compare every vector's reason with the
usual build's.

## The player

```cpp
const uint32_t kCatchUpBytes = 131072;      // body bytes the player decodes in one refresh
```

The catch-up loops take `core.decoder.body_read` at their start and stop at a record's
boundary once it grew by `kCatchUpBytes`; the stream keeps its place (`frame_end`,
`stream_records`), so the next refresh goes on. A `kPending` from the decoder ends the
loop the same way. `advance` returns false for a refresh that brought no picture yet, so
the LEDs keep the picture before. When the decoder gives a reason, the player acts on it
as today.

## The checks

`check_file_step` and the upload's and the drive's steps return "going on" for `kPending`
without counting a record, and take the same step again at the next refresh. The record
counter goes down only for a record that was decoded. `check_file`, the whole-file check
of a host without writable storage, calls the decoder again while it gives `kPending`.

## The fault's context

```cpp
struct FaultContext {          // in Core
    uint8_t present;
    uint8_t work;              // kWorkStart, kWorkPlay, kWorkUpload, kWorkDrive
    char name[kNameRoom];      // the file
    uint32_t record;           // the frame record it was at, from 0
    uint64_t body_bytes;       // the body read so far
    Reason reason;
};
```

`core_fail`, the upload's refusal and a drive's left-out file write it, replacing the one
before. Seed 33 reports it.

## Budgets and their reasons

| Budget | Value | Reason |
|---|---|---|
| `kSettleSliceBytes` | 32,768 bytes | The decoder inflates about 30 MB a second on the board's chip (seed 05's dense clip: 10,800 bytes a frame decoded in 9 to 17 ms with its other work); 32 KiB is about a millisecond, below a refresh of 20 ms. |
| `kCatchUpBytes` | 131,072 bytes | Twelve dense 60 x 60 records, enough to catch up a pause of a quarter second at 50 refreshes a second; a few milliseconds of inflating. |
| A call on the board | 50 ms at most | A command waits for one call; 50 ms keeps a session of commands quick and is two and a half refreshes. |
| A host's read | 250 ms at most | The microSD driver's and the USB driver's own timeouts are shorter; a read that fails is `read-error`, as today. |

The emulator's suite measures the longest call on the Mac; the board session measures it
on the board.

## The reproducer

`tests/core/huge_tail.py` writes the reproducer (`python3 -m tests.core.huge_tail OUT`): a compressed ODRG file on a 60 x 60
canvas with a palette of two colours, whose first frame record holds the index 255, and
whose stream inflates 64 MiB of zeros after it, made with Python's `zlib`. The core's tests
and the emulator's tests make it into a temporary folder; it is not tracked as a file, and
no tool installs it on the board.

## Tests

- `tests/core/test_bounded.py`, with the test host's `--trace-calls`, which prints what each
  call read of files (the host has no clock): before the change, one `poll` of a show with
  the reproducer reads the whole file; after it, no call reads more than 4 KiB, and the file's
  reason is `bad-palette-index` in the end, as `found_in` gives it. Every vector of
  `tests/vectors` gives its reason through the host built with slices of 7 bytes. A clip
  of frames of 1 ms after a pause of ten seconds catches up over several refreshes and
  then shows the picture of its time. Failed reads and a drive pulled out in the middle of
  settling end with `read-error` and the drive's dropping.
- `tests/emulator/test_bounded.py`: with the reproducer installed, `status` over the line
  port during the start, the playback and the check is answered within 50 ms each.
- The fault's context after each kind of work.

## Documents

`docs/core.md` (the slices, `pending`, the budgets), `docs/reasons.md` (`pending` is no
reason), `docs/firmware.md` (the watchdog stays on; the budgets on the board).
