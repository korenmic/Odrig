# Design: readiness progress and retained fault diagnostics

## Overview

The core knows the state of its check, its quarantines and the context of its last fault
(seeds 14, 31, 32); this design reports them. `status` gains the readiness and the
counts, a new command `fault` gives the context, and an optional host function `about`
names the host in `status`. The firmware names its build, storage and last reset, keeps
its last reason text across a reset, and the firmware tool and the app read `status`.

## What this design relies on

Today's code, with seeds 28 to 32 and 38 in it:

- `check_complete`, `check_at`, `FileInfo.checked` and `.fault`, `DriveEntry.state` and
  `.fault`, `drive_check_at` (`core/src/core.cpp`, `core_state.h`).
- `FaultContext` and `note_fault` of seed 31.
- `status` in `core/src/commands.cpp` writes one line; `ODRIG_REPLY_MAX` is 1,024.
- `odrig_host` in `core/include/odrig_core.h` ends with `drive_space`; the emulator's
  `HostRecord` (`emulator/binding.py`) and the test host mirror it; the firmware builds
  it in `OdrigFiles::host()` and wraps it in `OdrigDrive::withDrive` and
  `OdrigLog::withLog`.
- The firmware tool's `board.settled` waits for a `list` that is not `busy`; since seed
  32 `list` is never `busy` for the check, so the wait ends at once.

## `status`

After `height`:

```
"readiness":"checking","checked":12,"to_check":72,"unavailable":1,"checking":"dense7.odrg","host":"..."
```

- `readiness`: `recovery` while `core.invalid`; else `checking` while `to_check` is above
  0; else `degraded` while `unavailable` is above 0; else `ready`.
- `checked`: the show's files with `checked` or `fault`, and the drive's places that are
  not `kDriveToCheck`. `to_check`: the rest. `unavailable`: the files with `fault` and
  the drive's places left out. A file two items name counts once.
- `checking`: while the check is not complete, the name of the file at `check_at`; then,
  while a drive's file waits, its name as the drive gives it, cut to 32 characters; else
  `null`.
- `host`: the text of `about`, at most 95 bytes, as a JSON string; `null` when the host
  has no `about` or it gives none.

The longest reply: 130 bytes of today's members, 70 of the counts, 45 of `checking`, and
`host` with every byte escaped, 576: under 1,024.

## `fault`

```
fault
{"ok":true,"fault":{"work":"play","file":"b.odrg","record":3,"bytes":1234,"reason":"truncated"}}
{"ok":true,"fault":null}
```

`work` is `start`, `play`, `upload` or `drive`. Answered on an invalid show too. A new
command of the list, approved in advance by the owner.

## `about`

```c
/* Optional: a text that names the host, at most capacity - 1 bytes of printable ASCII, with
   a 0 after it. Returns 1, or 0 when it has none. */
int (*about)(void *ctx, char *buffer, size_t capacity);
```

The member goes after `drive_space`, so hosts that set the members they know by name and
clear the rest keep working. The core asks it at each `status`, with room for 96 bytes.
The test host gives the text of its option `--about TEXT`. The emulator gives
`odrig emulator, core <date of the library's build>`. The firmware gives
`<release> <build date> <storage> reset <reason>`: WLED's release name, the build's date
and time, `internal`, `internal+microsd` or `internal+usb`, and `esp_reset_reason()` as
`power-on`, `software`, `panic`, `task-watchdog`, `interrupt-watchdog`, `brownout`,
`deep-sleep` or `other`.

## The fault across a restart (firmware)

`OdrigLog` keeps, in `RTC_NOINIT_ATTR` memory, a record:

```cpp
struct Kept { uint32_t magic; uint32_t crc; uint16_t length; char text[96]; };
```

Each line the player logs that names a reason (an invalid show's text, `file … unavailable:
…`, `drive file … left out: …`) is written into it, with the CRC-32 of length and text.
`OdrigLog::begin()` reads it once: a record with the magic, a length up to 95 and the
right CRC is logged as `before this start: <text>` and cleared; any other is cleared
silently. The test host of the firmware's suite runs the same functions on a plain
buffer.

## The firmware tool

`board.ready(port, wait)` asks `status` every half second until its `readiness` is not
`checking`; a status without `readiness` falls back to the `busy` list of the firmware
before. `board.outcome(reply)` gives the line `outcome: healthy`, `outcome: degraded: <n>
unavailable` or `outcome: recovery: <error>`. `install-show` and the settings commands that
wait print the status and the outcome; `install-show` ends with 0 for healthy and
degraded and 1 for recovery; a wait that runs out is `check-not-done`, as before, saying
the check has not ended.

## The app

`commands.status` keeps the new members; `screens/show.js` writes the line `#readiness`;
`screens/target.js` the host's name and the last fault, asked with `fault` when the target
screen is shown. `messages.js` has the sentences.

## Tests

- `tests/core/test_readiness.py`: first the status without readiness (expected failures
  in task 1); then every state with the reference player, which counts as the core does;
  `fault`; `host` with `--about`.
- `tests/firmware`: the tool's outcomes with the board stand-in of its suite; the kept
  record with its check sum, damaged, too long and absent.
- `tests/app`: a scenario of a target that checks, then is degraded.
- `tests/emulator`: `host` and `fault` over HTTP and the line port.

## Documents

`docs/commands.md` (`status` members, `fault`), `docs/core.md` (`about`, readiness),
`docs/firmware.md` (`about`, the kept record, the outcomes, "Capturing evidence"),
`docs/android-app.md`, `docs/emulator.md`, `docs/decisions.md`.
