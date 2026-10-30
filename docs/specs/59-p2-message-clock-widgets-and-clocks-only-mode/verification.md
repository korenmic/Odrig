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
