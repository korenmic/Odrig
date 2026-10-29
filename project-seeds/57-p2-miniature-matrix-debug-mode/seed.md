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

The owner subsequently selected the ESP board's **5 V pin**, not 3V3, for miniature
matrix power. Normal snake 1 uses GPIO1 for data and a separate external supply
reported at about 4.3 V. Those are separate functions: GPIO1 is not a power pin,
and successful operation of the snake does not establish the miniature matrix's
power budget. For miniature testing the normal wall is disconnected; do not join
its external positive supply to the ESP's USB-derived 5 V rail.

## Sources And Current Boundaries

- Manufacturer: https://wiki.seeedstudio.com/rgb_matrix_for_xiao/ . The product
  has VCC, GND, DIN and DOUT pads, uses XIAO D0 for its data, and requires assembly.
  The XIAO header layout is not the ESP32-S3-N16R8 development board's header.
- Purchase: https://www.4project.co.il/product/6x10-rgb-ws2812-matrix-for-seeed-studio-xiao .
  SKU 4P-7304 / SE-104030107; the retailer specifies 5 V operation.
- Owner's rear-board photograph: `references/1000317545.jpg`, supplied on
  2026-10-29. It visibly identifies `seeed studio 6x10 RGB MATRIX for XIAO`.
  In that photograph the right-side three pads read `5V`, `GND`, `IN`; the
  left-side group reads `5V`, `GND`, `OUT`. The XIAO header has D0-D10, 3V3,
  GND and 5V labels. Use the labelled **IN** pad for incoming ESP data, never OUT.
  Do not treat matrix D1 as the target merely because the ESP output is GPIO1:
  the manufacturer's XIAO data connection is D0. Prefer the dedicated IN/5V/GND
  group in the README to avoid confusing the two boards' header numbering.
  The photograph establishes visible labels, not a silicon revision, current
  rating, electrical continuity, solder quality or a powered functional test.
- Owner's ESP32-S3 pinout reference: `references/esp32s3-pinout.png`, supplied on
  2026-10-29. It labels a separate 5V power pin, GND and GPIO1. The owner explicitly
  confirmed the board's 5V pin exists, selected its use and instructed that this
  settle the seed's remaining hardware planning question. Treat that as owner
  approval of the intended wiring, not a measured current rating or proof that
  every board pictured online has the same power circuitry. Read the actual board's
  silkscreen; do not substitute a pin position from a differently oriented image.
- Manufacturer-linked LED datasheet:
  https://files.seeedstudio.com/wiki/xiao-rgb-matrix/WS2812B-1010-DATASHEET.pdf .
  Its parameter table specifies a 2.8 V minimum high-input threshold at VDD=5 V,
  supporting direct 3.3 V data for that documented part. Do not carry forward the
  unsupported assumption that a 3.3-to-5 V buffer is mandatory for this matrix.
  Confirm the supplied board corresponds to that documentation and that the
  signal at DIN meets the requirement under the intended short-wire connection.
- The board's normal data pins are GPIO1-18, GPIO21 and GPIO47. GPIO39-42 are the
  microSD SPI pins; GPIO19/20 are native USB and GPIO43/44 are UART. Do not borrow
  these storage/USB/UART pins for the matrix.
- `firmware/usermod/odrig_leds.cpp` currently builds and fills twenty physical
  output buses from the core's leg buffers. The app is shared web code in
  `app/www/`, served by the emulator and packaged into the APK unchanged. Commands
  are shared across HTTP and serial, never an APK-only firmware endpoint.
- Hardware/power and additions to the command list require the owner's explicit
  approval under AGENTS.md. Approved choices and remaining electrical verification
  are distinguished below; the photograph alone is not a safe-power certification.

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
    wall disconnected for this mode. The owner selected ESP **5V -> matrix 5V**,
    **ESP GND -> matrix GND**, and **GPIO1 -> matrix IN** as the intended arrangement.
    Do not connect matrix 3V3, OUT or its unused XIAO header signals for this setup.
    As an implementation/commissioning acceptance check, establish this exact ESP board's
    5 V rail/USB protection/current capability and remaining budget after the ESP
    and microSD load, against the matrix demand at the enforced debug cap. Check
    startup and failure states as well as typical animation demand; pin availability
    is not proof of current capacity. Verify simultaneous USB power paths if both
    board sockets remain attached. Direct data is supported by the linked part's
    threshold, subject to the correspondence/signal checks above, not by snake
    stability at 4.3 V. If extra supply or signal components prove necessary,
    identify the concrete part/circuit and obtain owner approval before substituting
    it; do not silently require a buffer or connect positive supply rails together.
    Never assume an ESP GPIO supplies matrix power or that 5 V is safe on a GPIO.
    These acceptance checks do not reopen the owner's settled 5V-versus-3V3 choice
    or block specification. Keep the intended wiring explicit while distinguishing
    approved planning from electrical measurements still to be recorded before use.
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

On 2026-10-29 the owner explicitly approved the shared command `debug mini on|off`,
GPIO1 with the wall disconnected, and choosing the ESP's 5 V pin rather than 3V3
for matrix power. The photograph resolves which labelled matrix pads are intended.
These choices are settled; do not repeatedly ask the owner to choose the voltage.

None requiring an owner answer before S2S. The owner supplied the ESP pinout,
confirmed the 5V pin and explicitly instructed that the selected 5V arrangement
close the remaining planning question on 2026-10-29. The intended circuit is
GPIO1 -> IN, ESP 5V -> matrix 5V and shared GND, with the normal wall disconnected.
The documented LED threshold supports direct GPIO data for that part; verify the
correspondence rather than assuming a mandatory level converter. The seed is ready
for specification with zero open product questions.

Current budget, USB power-path compatibility, assembly and the powered acceptance
test remain required execution checks, not completed measurements and not open
voltage-choice questions. Do not claim that a labelled 5V pin alone proves those
checks. If implementation evidence requires changing the approved circuit or
adding a part, report the concrete finding and obtain approval before that change.

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
