# Miniature matrix debug mode

## Summary

Add a temporary miniature-display debug mode for the owner's Seeed Studio 6x10
RGB WS2812 Matrix for XIAO, SKU 104030107. A checkbox in the operators' app enables
and disables it on the board. The firmware plays the same installed and microSD
animations, but projects their logical picture onto the 60-pixel matrix instead
of sending the normal twenty-snake display. No animation conversion is needed.
The root README must explain the exact board-to-matrix wiring, input and output
directions, any required signal-conditioning components and the safe procedure
for entering and leaving the mode. This seed includes the APK, firmware, shared
command/core behavior, tests and documentation; not just the checkbox.

## Priority

- `P2`

## Depends On

- Seeds 30 and 43: saved pin assignments, diagnostics and the cross-wired snake.
- Seeds 35, 37, 38 and 50: catalogs, frame/text/widget playback and microSD files.
- Seed 45: brightness and current limits must not be bypassed by debug output.
- Seed 56 fixes the independently confirmed SD-capacity stall. Do not reimplement
  that fix here or mistake its pause for the miniature projection's cost.

## Product Context

The installation has a logical canvas of 60x60 pixels, driven by twenty independent
data outputs, each carrying a three-column snake of 180 LEDs. The owner bought the
small matrix at 4Project on 2026-10-29 to see the installation's actual playback
without connecting the full wall. The purchased matrix has 60 WS2812 LEDs in ten
columns and six rows, on a board of approximately 21x18 mm. It has one serial DIN,
not twenty independent data inputs, and cannot verify all twenty physical outputs,
full-wall wiring, current demand or long-cable signal integrity.

The owner's request explicitly includes a checkbox in the APK, the firmware that
makes it work, and exact ESP32-S3/matrix pin instructions in the README. Creating
this seed is the only work authorised now: do not generate its spec, implement,
build, flash, change a board or instruct the owner to wire an unapproved circuit.

## Sources And Current Boundaries

- Manufacturer: https://wiki.seeedstudio.com/rgb_matrix_for_xiao/ . The product
  has VCC, GND, DIN and DOUT pads, uses XIAO D0 for its data, and requires assembly.
  The XIAO header layout is not the ESP32-S3-N16R8 development board's header.
- Purchase: https://www.4project.co.il/product/6x10-rgb-ws2812-matrix-for-seeed-studio-xiao .
  SKU 4P-7304 / SE-104030107; the retailer specifies 5 V operation.
- The board's normal data pins are GPIO1-18, GPIO21 and GPIO47. GPIO39-42 are the
  microSD SPI pins; GPIO19/20 are native USB and GPIO43/44 are UART. Do not borrow
  these storage/USB/UART pins for the matrix.
- `firmware/usermod/odrig_leds.cpp` currently builds and fills twenty physical
  output buses from the core's leg buffers. The app is shared web code in
  `app/www/`, served by the emulator and packaged into the APK unchanged. Commands
  are shared across HTTP and serial, never an APK-only firmware endpoint.
- Hardware/power and additions to the command list require the owner's explicit
  approval under AGENTS.md. The proposals below are not approved instructions.

## Required Behavior

### App And Shared Control

1. Settings has one clearly labelled checkbox, `Miniature display debug mode`,
   with a short explanation naming the 10x6 matrix and the wiring instructions.
   The app visibly indicates the mode while active. Do not confuse it with the
   packaged diagonal or individual-snake tests.
2. The checkbox reflects the board's acknowledged state, not a phone-only flag.
   Pending requests cannot be stacked. A refusal leaves the confirmed value; a
   timeout leaves state unknown until read back. Reconnecting or changing targets
   reads that target's state and never enables a mode automatically from a stored
   checkbox. Older firmware is shown as unsupported, not silently treated as off.
3. Approved shared command: `debug mini on|off`, with an explicit miniature-mode
   state/capability in the status reply. The owner approved this command on
   2026-10-29. The same semantics reach the board and emulator through every existing
   route and `odrigctl`; no new transport or command family beyond this proposal.
4. Mode is off at boot, held only in RAM and shared by all clients. Losing the app
   connection does not change it; disabling or rebooting does. No mode setting is
   written into the show, mapping, WLED settings or animation storage.

### Firmware And Projection

5. Keep decoding and playing the original logical 60x60 show. Installed animations,
   microSD animations, text and widgets all use the same runtime picture and time.
   Do not rewrite ODRG/ODRGX, catalogs, previews, saved mapping, pin assignments,
   playlist order, clock settings or files to obtain the miniature picture.
6. Preserve aspect ratio and orientation by default: a square 60x60 picture fits
   into the central 6x6 pixels of the landscape 10x6 matrix, with two black columns
   on each side. Downsample with bounded integer box averaging; for this source,
   each visible miniature pixel represents a 10x10 logical block. No stretching,
   rotation, cropping or new user-adjustable projection controls are needed.
   The matrix's physical chain order must be verified against its schematic and
   a corner/axis test, not guessed from the front photograph.
7. Project from logical canvas coordinates, not the first sixty bytes/pixels of a
   snake. The projection uses the effective logical picture regardless of saved
   physical pin permutation and cross-wired snake settings. Normal output off-mode
   remains bit-for-bit unchanged for the same inputs.
8. While active, only the miniature output carries the projected frame; the other
   full-wall outputs are cleared and not fed the normal show. The normal logical
   mapping remains in memory for decoding and is restored to physical output when
   the mode is disabled. Clear outgoing display data at transitions; do not latch
   a partial frame or claim success when output setup failed. A setup failure must
   leave a clearly reported safe state, not an optimistic checked checkbox.
9. The display follows on/off and brightness, including brightness zero. Effective
   miniature brightness is capped at 40 without raising a lower setting or changing
   the normal brightness saved or chosen by the operator. Existing current safety
   is not bypassed; account for the actual active miniature hardware rather than
   treating it as 3,600 physical LEDs. Report any distinction between requested and
   effective miniature brightness honestly. Hardware power limits remain owner-set.
10. USB commands, UART logs, Wi-Fi, microSD playback, fault quarantine and catalogs
    continue working. Projection uses bounded work and fixed memory without a
    second decoder or per-frame allocation. Meet the existing 20-50 FPS range;
    do not optimise rates already in that range.
11. The emulator and shared app expose the same mode state and projection, so a
    deterministic miniature preview and the checkbox can be tested without the
    board. No APK-only copy of app code, hardware-only projection algorithm or
    separate interpretation of animation formats is introduced. The specification
    chooses the appropriate shared API boundary without adding a frame-export
    command or changing the installed canvas.

### Exact Wiring And Operator Documentation

12. Root `README.md` includes a concise `Miniature display debug mode` section,
    with the final approved pin-to-pin table, signal direction and labelled board
    orientation. A diagram may be linked from it, but the essential table is in
    the README itself. Update the related app, firmware and mapping documentation
    and record the approved temporary-output exception to the normal mapping rule.
13. The table must name the actual ESP32-S3 GPIO label, matrix DIN, matrix VCC and
    common GND, plus each intermediate level-shifter connection and its verified
    supply, enable pins and part/package when required. Matrix DOUT is an output
    for chaining and stays unused here; it is not connected to an ESP input. Do
    not present a XIAO header pin number as an ESP32-S3 header pin number.
14. Approved data output is GPIO1, temporarily replacing snake 1, with the full-size
    wall disconnected for this mode. Proposed power/signal arrangement is an
    owner-approved regulated 5 V source and an appropriate 3.3-to-5 V data buffer.
    The command and GPIO1 arrangement are approved; power/signal conditioning
    still needs verification and the owner's informed approval below. Determine the actual component
    and its pin numbers from primary documentation before publishing the table.
    Never assume an ESP GPIO supplies matrix power or that 5 V is safe on a GPIO.
15. Instructions explicitly cover power-off rewiring, required assembly, verified
    supply/data compatibility, which normal display connections must be removed,
    how the checkbox is enabled and checked, and how to return to the wall. Warn
    that reboot disables the mode and normal output resumes; do not advise live
    rewiring or promise that software detects the attached matrix. No unrelated
    board or reader rewiring is required or permitted.

## Verification

- Projection vectors prove orientation, corners, RGB order, letterboxing, box
  averages, solid colours, asymmetric shapes and bounds, with frames, text and
  widgets. Mapping permutations must not scramble the logical miniature image.
- Shared command tests cover idempotent switching, reboot defaults, failures,
  invalid arguments and parity across routes. App tests cover acknowledgement,
  timeout/readback, unsupported firmware, target changes and another client changing
  the mode. Emulator tests show the same projection/state as the firmware uses.
- Host tests show correct active output pin/length, cleared unused outputs, normal
  routing restored, no changes to persisted files, brightness zero/cap and safe
  output reconfiguration. Test coexistence with microSD and both USB interfaces.
- A later approved board/phone session verifies the assembled circuit, original
  animations from internal storage and microSD, orientation and transitions,
  responsive controls and the accepted refresh rate. A person's observation of
  actual pixels and power readiness is required, not inferred from a serial reply.

## Out Of Scope

Implementation or flashing during seed creation; a 20-input diagnostic fixture;
simultaneous full-wall and miniature output; Android USB flashing/serial features;
animation reconversion; new file/catalog formats; arbitrary miniature hardware;
user-configurable projection effects; solving electrical or long-wire faults of
the full installation. Seed 56 remains separate.

## Open Questions Requiring The Owner

On 2026-10-29 the owner explicitly approved the shared command `debug mini on|off`
and GPIO1 with the full wall disconnected. These are settled.

The earlier third question was unclear: the owner asked whether to use the ESP's
5 V pin or its 3V3 pin and said either is acceptable. The matrix's specified power
is **5 V at VCC**, not the ESP's 3V3 output. GPIO1 is the separate data signal.
The owner's statement does not prove available supply current, safe simultaneous
USB power paths or the matrix's input-high threshold, and is not approval to buy
or require an unidentified signal-level converter.

One hardware item remains before zero-question S2S: establish the exact matrix
revision's data-level requirements and this board's safe 5 V source, then obtain
approval of the concrete circuit based on the parts the owner actually has. Prefer
the existing hardware when supported by primary specifications; do not require a
level shifter by assumption. If an additional component is necessary, identify it
and ask the owner plainly before fixing it into the wiring plan. Never suggest
putting 5 V onto an ESP GPIO. Assembly remains a separate owner check.

## Definition Of Done

1. Owner-only command and hardware choices are resolved and recorded before S2S
   claims zero open questions. The scope stays APK plus firmware plus exact README
   wiring, rather than a checkbox-only change or a plan that hides hardware unknowns.
2. The checkbox enables and disables the real firmware mode and reads its state;
   browser/emulator and APK use the same app and shared mode/projection behavior.
3. Existing 60x60 animations play in miniature without conversion, storage changes
   or permanent remapping; disabling restores normal twenty-snake operation.
4. The tested, approved README wiring table names every actual pin and component
   needed by this board and matrix, including safe transitions and reboot behavior.
5. Relevant discovered suites pass, APK and firmware build through the repository
   tools, and the board/phone acceptance evidence is recorded. No unchecked human
   or hardware acceptance is called complete; any remaining check is told to the
   owner explicitly. This seed's creation alone does none of that implementation.
