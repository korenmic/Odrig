# Requirements: readiness progress and retained fault diagnostics

Seed: [`project-seeds/33-p1-readiness-progress-and-retained-fault-diagnostics/seed.md`](../../../project-seeds/33-p1-readiness-progress-and-retained-fault-diagnostics/seed.md).

After seeds 31 and 32 the board answers from its start, plays its usable animations, and
quarantines a bad one; `list` is answered during the check with `"bytes":null` for a file
not read yet. But nothing says whether the check is still going on, how far it is, what
the last fault was, which firmware runs or why the board last restarted, and the firmware
tool's `install-show` still waits for a `busy` list that no longer comes. This spec makes
the board's readiness and progress truthful on every route, keeps the last fault's
context for reporting, names the host, keeps the last fault across a restart of the
board, and has the tool and the app say what is so. The choices were made under the
owner's mandate of 2026-10-24 and are in `docs/drifts.md`, "Seed 33".

Words used here: **the check** is the check after the start of seed 14, of the installed
files and then of a drive's; **unavailable** is quarantined (seed 32) or left out.

## Requirement 1: readiness in `status`

1. `status` SHALL report `readiness`: `checking` while the check has files to read,
   `degraded` when it has ended and one or more animations are unavailable, `ready` when
   it has ended and none is, and `recovery` while the show is invalid.
2. `status` SHALL report `checked`, the files whose check has ended, `to_check`, the files
   it has still to read, `unavailable`, the animations unavailable now, and `checking`,
   the name of the file the check is at, or `null`. Installed files and a drive's count
   alike. Nothing is estimated: no time is given.
3. Usable playback SHALL be reported as today, apart from readiness: `playing` and
   `animation` say what plays while the check goes on.
4. A reply of `status` SHALL stay one line under 1,024 bytes on every route.

## Requirement 2: the last fault

1. A new command, `fault`, SHALL report the context the core keeps of the latest fault of
   a file (seed 31): the work, the file, the frame record, the bytes of its body read and
   the reason; or `null` before any fault.
2. The reply SHALL say a decoder's reason, not a cause: nothing in it claims damage on the
   storage.

## Requirement 3: the host's name

1. The host interface SHALL have an optional function `about` that gives a short text
   naming the host: its build, its storage and the reason of its last start.
2. `status` SHALL report it as `host`, or `null` for a host without it.
3. The firmware SHALL give its version, its build, its storage (internal, microSD or USB)
   and the reason of the last reset as ESP-IDF names it; the emulator SHALL give its name
   and the core's build.

## Requirement 4: the fault across a restart

1. The firmware SHALL keep the latest reason text its player logged (an invalid show, a
   quarantine, a file left out) in memory that survives a software or watchdog reset, and
   not a power cut, guarded by a check sum.
2. At its next start it SHALL write that text to its log as `before this start: <text>`,
   and nothing when the memory holds no sound record.
3. Nothing of it SHALL be written to flash or to the card; a damaged record SHALL not hold
   up the start.

## Requirement 5: the firmware tool

1. `install-show` and the tool's other waits for the board SHALL wait for `readiness` to
   leave `checking`, asking `status`, and fall back to the `busy` list of an older
   firmware without `readiness`.
2. They SHALL print the outcome as a line: `outcome: healthy`, `outcome: degraded: <n>
   unavailable` or `outcome: recovery: <reason>`; a wait that ends before the check
   SHALL be the failure `check-not-done`, which says the state is not known yet, and never
   health or corruption.
3. `flash` SHALL say that it wrote and that the firmware answers, and no more.

## Requirement 6: the app

1. The show screen SHALL show, while the check goes on, `Reading the animations: <n>
   read, <m> to read`, with the unavailable ones counted when there are any; when the
   check has ended with unavailable animations, `<n> animations unavailable; the others
   play.`
2. The target screen SHALL show the host's name and the last fault in words, when there
   are.
3. Every control SHALL stay usable meanwhile. The refresh rate is labelled as refreshes
   a second, as today.

## Requirement 7: progress under load

1. The check SHALL keep its floor of one step in ten refreshes at a host that is always
   late, as today, and the fault's context and the counts SHALL be kept without a second
   decode.

## Requirement 8: documents and tests

1. Tests SHALL first show the status that says nothing of the check and the tool's wait
   that ends before it.
2. The core's tests SHALL cover readiness and counts through the check, quarantines,
   drives, uploads during the check, invalid shows and hosts without storage, compared
   with the reference player; `fault` before and after faults; `host` with and without
   `about`.
3. The firmware's suite SHALL cover the tool's outcomes with a board that is checking,
   healthy, degraded and invalid, and the record that survives a reset, its check sum and
   its damaged forms.
4. `docs/commands.md`, `docs/core.md`, `docs/firmware.md` (with a procedure for capturing
   evidence: name the app, the show and the media, read the log without restarting,
   keep the affected bytes, change one thing at a time), `docs/android-app.md`,
   `docs/emulator.md` and `docs/decisions.md` SHALL say what holds.
5. Every suite that needs no board SHALL pass. The board session measures the time to the
   first reply, the first list, the first picture and the end of the check, and reads a
   retained fault after a reset.
