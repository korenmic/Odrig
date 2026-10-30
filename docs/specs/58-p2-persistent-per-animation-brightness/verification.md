# Persistent brightness verification

## Core preference and selection checks

Twenty-three focused core tests cover durable save/removal, zero as a present
override, runtime-default independence, blackout, miniature cap, first-frame
selection, text and widget rendering, clocks/messages and interrupted playback,
shared internal identities, restored/renamed paths, namespace/folder separation,
read-only external media, remount and reassigned ids, retained-entry capacity,
malformed settings, unchanged-save writes, each storage-call failure, temporary
file verification failure and power cuts during save/removal.

The initial four-case feature check first reported two `bad-argument` save
failures and a missing `dimming` field. During implementation the rename test
first observed saved values `[19,19]` instead of `[19,null]`: the runtime item kept
its old path's cached value. Refreshing preferences after a renamed upload and
the related indexed-file publication/move/removal boundaries corrected it. The
complete focused module then passed23 tests.

Each storage-cut recovery accepted only the complete old or new published
settings. Failed writes/close/rename or readback kept the prior published file
and active value. No-op saves made no writes. A full512-record file refused a
new preference without dropping unlisted paths; existing entries could change
or be removed. The32-external-record limit counts retained absent-card paths.

## Fixed memory and portability

The measured Windows host allocations are:

| Configuration | Requested bytes | Blocks |
|---|---:|---:|
| 100-item target show, writable internal storage | 125665 | 18 |
| Same show with a drive | 131069 | 21 |
| Same show without writable storage | 77869 | 13 |
| Bench example | 88954 | 17 |

The core object is3944 bytes, below4096. The drive case remains below131072.
Private fields were grouped to remove padding. Internal item metadata stays16
bytes. A compact repeat record retains its full32-bit position and16-bit count
in6 bytes; external brightness records use5 bytes each. Miniature flags now fit
in one byte, making its physical-image block188 bytes. No allocation is added
after startup, and no supported domain or existing bound is reduced/relaxed.

The compiler first caught oversized720/768-byte stack frames from a full local
file reader. The independent settings reader now uses a128-byte read buffer,
preserving the existing512-byte frame warning/error limit and decoder ownership.
Microsoft compilation first caught an implicit repeat-count conversion; its
existing validated16-bit range is now cast explicitly. A rewrite helper's Windows
line endings were corrected to LF. Both portability assertions passed in the
recorded nineteen-case recheck.

## Status compatibility

The first discovered core/emulator run covered981 core and647 emulator cases,
with19 failures and20 skips. The failures were additive status expectations,
unsupported-storage equivalence expectations, the compiler conversion and line
endings. All19 recorded cases passed after correction. Host equivalence checks
exclude only `dimming`, assert its unsupported value explicitly, and retain every
other old field/byte comparison. The reference and exact status examples include
the new field; ordinary default commands and rendered output retain their checks.
No clean initial aggregate result is claimed.

Final discovered run `20261030-130025-165968`, after the rename fix:

| Suite | Discovered tests | Result |
|---|---:|---|
| Core | 986 | Passed,1 skip |
| Emulator/command tool | 647 | All functional assertions passed;19 skips; two Windows socket-buffer cases passed unchanged in isolated rechecks |

The aggregate exited nonzero because `WinError10055` affected an invalid-show HTTP
startup and a TCP tool status exchange. Both cases then passed unchanged in
`seed58-task1-resource-recheck.log` and `seed58-task1-tcp-recheck.log`. The final
focused brightness module passed23/23 in `seed58-task1-brightness-final.log`.
No assertion or error case is left unverified; a clean aggregate exit is not claimed.

Local evidence is in `build/seed58-task1-*.log`; these are host/browser checks,
not firmware compilation, electrical measurements or board/phone acceptance.
Firmware tools, CLI integration and shared app controls are later queued tasks.
