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

## Command tool and settings transfers

The CLI now accepts `brightness ID VALUE save` and `brightness ID default`, with
all forms in its help. The ordinary one-value command still sends values as typed
and retains the target's refusal/exit status. Malformed forms and line breaks are
usage errors. The new transport regression first failed with CLI exit2 instead
of0 because the saved form was rejected. It now passes through the existing HTTP
and line transports, including saved zero, default restoration, unknown IDs and
out-of-range values. Every original animation/show/catalog byte is unchanged.

`brightness.txt` joins the firmware tool's preserved settings. A show folder may
explicitly replace it, an ordinary install keeps the board's copy, and read-show
copies it back. Before the change, folder validation rejected the file and an
ordinary install dropped the saved values. The new round-trip fixture also needed
its second write applied atop the first installed image; after that fixture
correction, preservation, explicit replacement, readback and unchanged outside
files all pass. These are memory images and a recorded esptool stand-in, with no
board write or firmware build.

Verification: focused CLI/transport8 tests passed. The pure firmware storage
module ran59 tests:58 passed in the full run, and the corrected new round-trip
case passed in isolation. Discovered emulator run `20261030-132015-4012` passed
649 tests with19 platform skips, exit0. Logs are `build/seed58-task2-*.log`.
Existing firmware/emulator host filename access already accepts both brightness
settings names; no host protocol or transport is added. Shared app controls and
the final documentation/integrated proof remain queued.

## Shared app controls

The shared Controller/APK code has one slider/number/checkbox controller. The
shortened slider and labelled checkbox remain adjacent at320px and landscape
sizes, with48px touch room, no horizontal overflow and the unchanged pinned-panel
threshold. Labels distinguish the default from this animation's brightness and
name the current file. Zero remains editable while power is off. Missing/null
capability, malformed/unknown status, no animation and damaged settings explicitly
disable override changes; old targets retain ordinary default controls.

Edits capture target epoch, animation ID, full file and mode. Identity transitions
cancel unsent work, and queued mutations validate the capture before sending.
Sent commands retain their target/file; late replies cannot repaint another one.
Valid dirty text is committed and read back before mode changes, invalid text
blocks them, and an already-entered numeric command is also confirmed first.
Override drags save once on release; default controls retain200ms throttling and
queue coalescing. Replies acknowledge commands, while subsequent status confirms
the setting. Communication failure invalidates status freshness; another command's
reply cannot restore it. Recovery reads status without automatically resending.

The first browser regressions failed because the controls were absent. Further
observed faults were: entering default0 and immediately capturing saved128;
releasing the same override value after a fast external change sent onlyone
command instead oftwo; another command's reply briefly re-enabled malformed-status
controls; and at320px the checkbox wrapped beneath the slider. Each case passed
after its correction. The core still makes unchanged durable saves write-free.

Discovered run `20261030-134205-199536` ran394 app and649 emulator tests. Four app
failures were the old full-width-slider/pointer-file contracts, an ASCII source
check and the allowed command list. The layout contract now checks the exact8px
gap, shared row, field alignment and panel edges; the focus coordinator remains
usable by ordinary change/Enter handlers. A Unicode escape preserves ASCII source
with the same displayed label, and only the approved save/default forms were
added to the command allowlist. The emulator failure was Windows socket exhaustion
(`WinError10055`) during an existing upload test's emulator startup.

All five failed cases were covered by passing final rechecks:51 tests for all19
brightness cases, the20 existing controls, Look/Touch and the unchanged upload
case; plus7 web-scope tests. The brightness cases include dirty/entered text,
queued identity changes, stale target replies, refusal, lost replies/reconnect,
other controllers, unsupported/error states, reload, off/zero, narrow/landscape
layout and the real emulator. No clean aggregate exit is claimed: its recorded
five failures were corrected/rechecked, and all other assertions passed with19
emulator platform skips. Logs are `build/seed58-task3-*.log`. Final cumulative
verification and documentation remain task4; board/phone acceptance stays open.
