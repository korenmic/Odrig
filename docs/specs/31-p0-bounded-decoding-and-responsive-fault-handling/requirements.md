# Requirements: bounded decoding and responsive fault handling

Seed: [`project-seeds/31-p0-bounded-decoding-and-responsive-fault-handling/seed.md`](../../../project-seeds/31-p0-bounded-decoding-and-responsive-fault-handling/seed.md).

On 2026-10-24 Codex reproduced a reset loop on the board: a 65,262-byte animation, compressed,
with a bad palette index in its first frame and 64 MB of inflated body after it. The
decoder's `settled` reads the whole rest of the stream, under the core's lock, to report
the reason a reader holding the whole file reports first; commands wait for the lock, and
the five-second task watchdog restarts the board. This spec bounds every piece of work
the core does in one call, keeps the reasons exactly as they are, and never disables a
watchdog.

The owner made a responsive start with bad animations mandatory on 2026-10-24; per-file
skipping is seed 32's. Further choices were made under the owner's mandate of 2026-10-24
and are in `docs/drifts.md`, "Seed 31".

In this document "a call" is one call of the core's interface by its host
(`odrig_core_poll`, a command, `odrig_core_begin`); "settling" is what the decoder does
after it found a defect inside a compressed body: it inflates on to the end of the stream
to find the defect a whole-file reader meets first; "the reproducer" is the file above,
made by a generator of the repository; "a slice" is the work one call may do on one task.

## Requirement 1: settling in slices

1. Settling SHALL inflate at most `kSettleSliceBytes` bytes in one call of the decoder, and
   then give the internal result `pending`, keeping where it was.
2. The next call of the same decoder SHALL go on settling from there, before anything else.
3. The reason settling ends with SHALL be the reason it ends with today, whatever the
   slices: the same for every file of `tests/vectors` and the reproducer.
4. `pending` SHALL never be reported as the reason of a file, in a reply, a log line or a
   document of reasons: it means "go on later".
5. No new limit SHALL be set on the size of a body: the format and its readers in the
   converter and the Python library do not change.

## Requirement 2: playback in slices

1. Bringing an animation to the picture of a time SHALL decode at most `kCatchUpBytes`
   bytes of its body in one refresh, and always at least one whole frame record; what is
   left is decoded at the next refresh, from where it stopped.
2. While a file settles, the refresh SHALL show the picture before, and the player SHALL
   act on the file's reason when settling has ended, as it acts on a reason today.
3. Valid animations SHALL play as today: the same pictures at the same times.

## Requirement 3: the checks in slices

1. A step of the check after the start, of the check of an uploaded file, and of the
   check of a drive's file SHALL decode at most one frame record or one slice of
   settling.
2. A step that ends `pending` SHALL be taken up again at the next step; it is no fault.
3. The check at the start of a host that cannot change its storage MAY read a whole file
   in one call, as today, going on through `pending` until settling ends.

## Requirement 4: what stays responsive

1. With the reproducer installed, a command SHALL be answered within the latency budget of
   the design, during the start, while the file plays and while it is checked.
2. The firmware's task watchdog SHALL stay on with its five seconds and panic, and no task
   SHALL feed it while it waits for the core's lock.
3. A bad file present at every start SHALL not lead to a reset: the start reaches a state
   that answers every command; seed 32 makes the healthy animations play on.

## Requirement 5: the fault's context

1. When a file's check or playback ends with a reason, the core SHALL keep the file, the
   work (the check at the start, playback, an upload's check or a drive's check), the
   record it was at, the bytes of its body read so far, and the reason, in a bounded
   record that seed 33 reports.
2. Keeping it SHALL need no second decode.

## Requirement 6: budgets

1. The design SHALL state `kSettleSliceBytes`, `kCatchUpBytes`, the longest a call may take
   on the board, and the longest a host's read may take, with their reasons.
2. The emulator's suite SHALL measure the longest call while the reproducer is settled,
   played and checked, and compare it with the budget.

## Requirement 7: tests and documents

1. A generator in the repository SHALL make the reproducer; no test depends on a file under
   `build/`. The reproducer is never installed on the board as an ordinary animation.
2. A test SHALL show the unbounded call before the change: one call of the core taking the
   whole settling.
3. The core's tests SHALL cover the reasons of every vector unchanged with settling in
   slices of a few bytes, truncation, a huge body, bad records, failed reads, a drive
   that goes, the start, and repeated playback and checks.
4. `docs/core.md`, `docs/reasons.md` and `docs/firmware.md` SHALL say what the slices are,
   that `pending` is no reason, and the budgets.
5. Every suite that needs no board SHALL pass.
6. On the board: the reproducer on the card, no watchdog reset and no command waiting
   longer than the budget; the firmware's identity and reset reasons recorded; when the
   board cannot be used, what is missing is said.
