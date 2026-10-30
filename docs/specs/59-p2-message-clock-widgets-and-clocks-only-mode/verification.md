# Message clock verification

## Format and renderer

The initial feature checks failed with `unknown-widget` in the shared core and a
missing Python reader. The implemented subtype now passes independent Python/core
validation and exact converter/core pixel comparison for all seven timeline roles,
two extreme seeds, fades, countdown, random rolling, stops, square freeze, loop
restart and out-of-order seeking. Malformed records, UTF-8, offsets, reserved
fields, text limits, truncation and trailing bytes are rejected before rendering.
The largest legal payload is 29,976 bytes, within the existing 32,768-byte window.

The real-emulator app regression first timed out waiting for an explanatory message
and showed the ordinary clock editor for a generated message clock. The app now
opens no form, explains the restriction, and leaves the uploaded bytes unchanged.

The broader core run also exposed an undersized test-host payload allocation: it
used the text limit rather than the already-supported widget window. Correcting
both decoder/render host callers avoids a Windows heap-corruption exit. The
production player already used the full widget window. Unknown-widget fixtures
now use the still-unassigned subtype 7 rather than the assigned subtype 6.

The C++ build retains warnings as errors and its 512-byte per-function frame limit.
The renderer adds no Core fields, heap allocation or persistent playback state.
Compiled masks are top-down alpha4; output RGB uses the existing bottom-up order.
The public format documents both layouts and deterministic timing math.

The full core suite passed 991 tests with one expected skip. The emulator suite
passed 649 tests with 19 expected skips. The JavaScript converter suite passed
1,586 checks (one skipped); the Python converter/library suite passed all 552.
Onboarding (88), runner (22), and mapping (43) passed. Six additional focused
core/emulator checks covered the gradual-stop boundary and standalone procedural
preview. A real Chrome test also generated and decoded the new widget's GIF using
the app's existing preview pipeline; the decoded image was 60 by 60 pixels.

Host memory remained 125,665 bytes in 18 blocks for the 100-item target show and
131,069 bytes in 21 blocks with a drive. No supported limits were relaxed.

The app suite ran all 398 tests: 397 passed and one existing storage-count test
captured `animations not known yet` before its list finished. That unchanged test
passed when rerun alone. Both new app checks passed, including preview generation.
The final converter reruns resolved all initial format-number, module-export,
module-inventory and documentation-contract failures. The aggregate first-run log
retains those failures rather than being presented as an entirely green run.
After the final documentation entry, all 38 documentation checks passed again.

## External inclusion

The initial external Ignore checks observed `in-use` refusals and missing folder
inclusion fields. The implementation stores exclusions in internal `ignored.txt`,
independently of the external medium and show file. Tests cover own/inherited folder
choices, ancestor removal preserving a child's own choice, remount and reassigned
IDs, retained absent paths, full capacity, no-op writes, malformed settings and
manual play. Every failed write/close/rename/readback keeps published bytes and
active choices; each storage cut recovers only a complete old or new settings file.

The manual-turn check first observed an explicit jump being replaced by the next
automatic file. Explicit-turn provenance now keeps that manual playback available.
The cold-start exclusion regression also observed animation 60001 starting while
all files were excluded; the newly-checked-file entry now uses shared eligibility.
Clock and message selection use the same own/ancestor exclusion helper.

The pure firmware storage-tool suite passed all 60 tests, including preserving,
explicitly replacing and reading back the new settings file. The new regression
first observed the file omitted before it joined the preserved settings list.
No real board, serial port, flash or external-medium write was used.

Measured host allocations are 125,153 bytes/18 blocks for the 100-item target show,
130,941/21 with a drive, 77,613/13 without writable storage, and 88,442/17 for the
bench example. Core is 3,688 bytes, Checker 2,208 and DriveIndex 716. The 640-byte
exclusion cache shares the existing order allocation. Two source caches and the
index cache each save 256 bytes; public reads and full 512-byte quarantine
fingerprints retain their domains. The 128 KiB, 4,096-byte Core and 512-byte stack
frame limits are unchanged.

Compatibility checks exposed old external-row and fixed-pagination assumptions.
Fixtures now include the additive flags, and catalog listing probes cover every
item with closer page starts rather than lowering expected catalog counts.
The procedural preview smoke waits for a nonnull rendering seed, rather than
assuming the URL is published only after the first complete drawing.

The final rebuilt-code run passed both discovered suites: core 1,008 tests
(one expected skip), emulator 651 (19 expected skips), with no failures.
The focused 19-case run passed the cold-start, clock/message exclusions,
HTTP/TCP persistence, manual-turn and preview checks. Onboarding passed all 88
checks and public documentation all 38. Task 2 is software-verified; physical
board/phone acceptance remains open.


## Exclusive mode and complete message bags

The initial mode checks observed `clocks only` rejected as `bad-argument` and
missing mode metadata. The implemented mode now passes 25 focused core tests and
four real-emulator HTTP/TCP/CLI tests. These cover durable restart, strict legacy
migration, no-op writes, every failed save/readback and storage cut, missing or
excluded faces staying dark, re-inclusion, remount with changed IDs, quarantine
and runtime media failure. The exclusive scheduler retains the normal playlist
path and window, refuses outside playback and output-taking diagnostics, permits
inside manual files and folders, and cannot escape through content cleanup.
Entering Only also ends an existing mapping diagnostic without later restoring it.

A further remount regression observed the saved `night` playlist becoming root
after an intermediate card lacked that folder, even when a later card restored it.
Tree publication now retains the saved normal path and held window while Only is
active. On exit it resolves that path on the current card; a folder still missing
then correctly falls back to root. Both the restored and missing cases are covered.

Independent face and message permutations exhaust their eligible direct children
before reshuffling in both enabled modes. Nested unrelated files are not automatic
candidates. A procedural message with a 54.9-second loop completes that whole loop
in Between and Only; the existing message remains supported. Ignored manual messages
remain explicitly playable with the message flag off. The read-only-card emulator
test verifies that mode/inclusion changes do not alter external media bytes.

Version-1 settings are read without eager rewriting; changed settings write
version 2, close and verify the full part, then rename. All 61 pure firmware-storage
tests passed, including preservation and readback of the new settings form.
All 88 onboarding and 72 focused documentation/settings compatibility tests passed.

Status retains its 1,024-byte bound with complete supported 99-byte ASCII file and
deep folder names, escaped host descriptions and Only metadata. Escaped control
descriptions use the reserved 160-byte budget; ordinary 95-byte ASCII descriptions
remain complete. No UTF-8 filename or new language support is introduced.

The warnings-as-errors build retains its 512-byte stack-frame guard. Core is
3,712 bytes, Checker 2,208 and DriveIndex 716. Actual allocations are 125,177 bytes
in 18 blocks for the target, 130,965 in 21 with a drive, 77,637 in 13 without a
store, and 88,466 in 17 for the benchmark. No allocation block, per-frame state,
public 512-byte quarantine fingerprint, supported domain or memory limit changed.

The first full compatibility run exposed expected old version-1 write assertions,
status-key/reference normalization, the prior escaped-host budget and command/help
inventories. Those fixtures now reflect the approved additive mode contract while
retaining legacy reads and their strict malformed-file checks. Final complete-run results are recorded below.


The final discovered core run completed all 1,033 tests successfully (one expected
skip), and the emulator completed all 655 successfully (19 expected skips), after
the remount fix and all compatibility-fixture updates. Its combined result has
1,668 passing checks and 20 skips with no failures. The earlier failed runs and
the 20 successful emulator rechecks remain separately identified in local logs.
All 130 focused mode, status, command and folder checks also passed. No board was
flashed or used, and physical output/phone acceptance remains open.


## Shared app controls and inclusion

The first browser checks observed an INPUT instead of the required mode SELECT,
missing normalized mode metadata and command form, and rejected external folder
inclusion fields. Further fail-first checks found no folder inclusion menu, no
external file Ignore action, and outside Play still enabled. The shared app now
validates explicit mode metadata, maps legacy booleans to Off/Between with Only
unavailable, and preserves own/inherited flags for external files and folders.

Both settings controls wait for fresh target confirmation after acknowledgement.
Tests exercise refusal, contradictory status, reconnect, another controller,
pending target changes and late old-target replies. A lost-ack regression first
stayed on Settings after fresh status confirmed Only; recovery now opens the
resolved folder while retaining explicit unconfirmed wording, without a false
Saved message. Navigation occurs once per target/mode transition, and later
browsing stays where the operator chooses. Outside Play is disabled and explained;
the global action restarts Clocks even from an unrelated browsed folder.

The UI/runtime integration review also caught raw `play all` accepted contrary to
the seed's explicit rule16. A regression observed success instead of `in-use`.
Raw all is now refused; global restart sends `play` with the currently resolved
Clocks folder ID. Core and HTTP/TCP checks distinguish the two requests and
retain the saved normal playlist. This corrects the earlier runtime interpretation.

External file and folder menus save the same Ignore setting on the target even
with read-only media. Inherited exclusions stay visible and distinct; including
an ancestor preserves the child's own choice, and explicit inside play remains
available. Refused saves keep the previous choice until an explicit retry.
Narrow and landscape layouts retain full-width controls and 48-pixel new actions.

A real browser against the actual emulator selected Only, manually played a message
with automatic messages off, ignored the message folder, browsed outside with Play
disabled, and restarted through the resolved folder ID. The event stream verified
the requests and raw-all refusal; external card bytes were identical before and
after. The first combined trial timed out during its initial browser connection;
an isolated trial completed the UI and found a recorder fixture that incorrectly
relied on proxy capture for localhost. The corrected test uses the emulator's
authoritative event stream and checks current status before opening the browser.
No APK was built at this stage and no phone or physical board was used.

An outside-play refusal initially said the animation could not be removed. Its
regression now checks that both Play and display-test refusals explain Clocks only,
including when another controller changed mode before the app's next status.


The discovered app run executed 418 checks: 412 passed, including all 19 new mode
cases present at discovery. Six old documentation/action expectations and the
ASCII-source constraint initially failed. Documentation/drive rechecks (13), the
two folder/order regressions within a six-test correction run, and all seven
source-scope checks passed after their updates. Literal display symbols now use
JavaScript Unicode escapes, preserving visible text while keeping app source ASCII.
The additional outside-play/display-refusal regression and existing message table
passed all six checks after the new explanation was added.

The discovered emulator run executed 655 checks with 19 expected skips; its sole
failure was the old assertion that raw all succeeds. All four mode transport checks
passed after that assertion was corrected, within the six-test correction run.
All 25 current core mode tests passed again, including explicit inside restart,
raw-all refusal and held normal-path/window restoration. The real-emulator,
narrow/landscape and refused-external-inclusion checks also passed together.
No observed failure remains unresolved. These logs distinguish the initially
failed complete runs from their successful focused rechecks; the integrated asset
task performs the next fresh all-supported-suite pass.
