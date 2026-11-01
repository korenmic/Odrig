# Confirmed mapping edit lock

## Observed failure and implementation

Before repair, `seed69-task2-red-observed.log` showed enabled Settings handles and
Restore defaults, an accepted direct photo-save handler, and a changed native pin
assignment when the expected state was protected. The regression uses the actual
shared browser app and production native core, not a duplicated mapping implementation.
After repair the same default-lock check passed in2.989s, with unchanged native pins.

Mapping editing now starts locked. Its toggle requires explicit confirmation in both
directions; Cancel/Escape preserve the state. The native HTML dialog fits the browser
viewport and initially focuses Cancel. Mutation guards cover pointer/held-row/key
entry, defaults, photo handlers and the send queue. Local cancellation happens before
transport and does not fabricate a board reply. An already-sent save is reconciled.
Leaving Settings, visibility loss, target changes and link loss relock and close any
pending prompt. Mapping reads, photo analysis and diagnostics remain available.

Six browser/native-core cases pass: default protection, confirmed real save and
cancel/Escape/relock, session/visibility reset, stale confirmation on target change,
photo preview with protected Apply/Other reading, cancellation behind a held status
reply, and reconnect remaining locked. The session case combines several assertions.
Five initial cases passed in14.586s; the link-loss case passed in4.967s. The complete
discovered mapping suite subsequently passed all42 tests, including the dialog-width
assertion and the existing focus/drag/photo behaviors after deliberate unlock.

## Discovered verification

The corrected single-run gate is `build/tests/20261101-051401-115372`, logged in
`build/seed69-final-all.log`. Compiler/interpreter selection uses existing compatible
tools: MSVC for the core and the pinned firmware Python with GNU firmware fixtures.
The orchestration changes only interpreter/compiler selection and uses default local
cache paths. It does not suppress tests or rewrite assertions.

| Suite | Result |
| --- | --- |
| App | 446 passed |
| Mapping | 42 passed |
| Core | Pass:1050 tests,7 compiler-specific skips |
| Firmware | Pass:647 tests,1 Windows symlink-privilege skip |
| Firmware-host | Pass:28 tests,1 local PlatformIO package-integration skip |
| Converter/reference | 552 passed |
| Converter JavaScript | 1602 passed |
| Onboarding | 88 passed |
| Runner | 26 passed |
| Emulator | Pass:657 tests,20 Windows platform skips;353s |

The combined run exited unsuccessfully due to two emulator checks. An existing real
message fixture assumed its required asset was in the first listing as soon as a
clock played. It now collects pages and waits boundedly for that asset before making
the same playback/inclusion assertions; the corrected case passed in1.161s. Another
emulator could not bind even port0 because Windows reported socket-buffer exhaustion
under the parallel load. The full emulator suite is rechecked separately with two
workers and passed all657 checks (20 platform skips) in353s, logged in
`build/seed69-final-emulator.log`. The final runner report retains the other nine
passing suites. No production clock, networking or OS settings changed for these
incidents.

An earlier static app check needed its input-event allowlist to include the dialog's
standard cancel/close events; its updated class passed. Earlier concurrent test-runner
attempts shared a retention folder and one pruned the other's completed records.
Those underreported totals are not accepted as complete evidence. The corrected
combined run's full records/report are preserved under `build/seed69-combined-proof/`.
Only one runner at a time is used for final evidence.

Exact-head Windows/Ubuntu firmware builds, source/image inspection and supported CI
checks are a merge gate for the focused PR. No board was flashed, no APK/FW was
published by this master change, and actual phone/LED acceptance remains open.
