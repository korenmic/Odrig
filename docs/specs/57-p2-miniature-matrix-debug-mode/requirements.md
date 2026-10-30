# Miniature matrix debug mode — requirements

The approved seed has no unanswered product questions. The owner's later instruction
defers firmware compilation to seed 60; software implementation and verification remain
in scope. Electrical commissioning and board/phone observations remain open acceptance.

## 1. Shared temporary control

1.1 `debug mini on|off` is available through every existing command route. Status
reports support, acknowledged on/off, pending setup, setup failure and effective
miniature brightness. Invalid syntax is refused without changing state.
1.2 The mode starts off at every boot, lives only in RAM, and is shared by clients.
It never writes the mapping, show, catalogs, settings or animation files.
1.3 Repeated requests for the same state are idempotent. An opposite request during
setup is refused as busy. Success of command submission does not claim output setup.
Failed setup reports an unknown output state and keeps output dark until a successful
retry. An unsupported host or canvas refuses the mode honestly.

## 2. Shared logical projection

2.1 The original 60x60 canvas, animation decoding, timing, text, widgets, diagnostic
picture and internal/microSD playback stay intact. The normal leg API and recording
geometry remain unchanged.
2.2 A 10x6 miniature contains the square picture in its central 6x6 cells and black
columns at x=0,1,8,9. Each cell averages its 10x10 logical block with bounded integer
arithmetic. Coordinates start at the bottom left. Physical pin permutations and the
cross-wired snake cannot change this logical image.
2.3 Use the effective logical RGB picture, including palette and widget layers.
Scale each source channel using the existing brightness rounding, at no more than 40,
then floor its 100-sample average. Respect off and brightness zero without changing
the requested normal brightness. Normal-mode output is bit-for-bit unchanged.
2.4 All projection storage is fixed and allocated at startup; no second decoder or
per-frame allocation. Refreshes retain the accepted 20–50 FPS requirement on hardware.

## 3. Output isolation and preview

3.1 Firmware activates only one 60-LED GRB bus on GPIO1 while mini is on. Normal
outputs are cleared before switching; disabling clears mini and restores the saved
normal pin routing. Transition setup occurs outside the common core lock and waits
for in-flight transfers without blocking command replies.
3.2 Current limiting remains enabled, using the actual 60 active LEDs and existing
owner-set budgets. No change to the approved supply, current setting or circuit.
3.3 The documented landscape chain is derived from the manufacturer's schematic and
PCB, then checked later with a powered corner/axis test. Do not guess serpentine order.
3.4 Emulator and shared app expose the same acknowledged state and core-generated
projection. A miniature preview uses existing emulator events, with no frame command,
file-format change or APK-only app code.

## 4. App behavior

4.1 Settings contains `Miniature display debug mode`, a short 10x6 explanation and
a reference to root README wiring. Active mode is visible beyond Settings.
4.2 Checkbox values come from target status. Pending requests cannot stack. Refusal
retains confirmed state; timeout/lost connection is unknown until readback. Older
firmware is unsupported, not off. Target changes and reconnects never restore a local
enabled value; other clients' changes are reflected through polling.

## 5. Operator documentation and acceptance

5.1 Root README includes the approved ESP5V→matrix5V, GND→GND, GPIO1→IN table.
OUT, 3V3 and unused XIAO header pins remain unused. GPIO numbering is not XIAO numbering.
5.2 Explain orientation, assembly, power-off wiring, full-wall disconnection, supply
and USB-path/current verification, direct-data part correspondence, enabling/readback,
safe restoration and reboot returning to normal output. Do not claim measured power
readiness or silently add a supply or level shifter.
5.3 Document the temporary-output exception and all unperformed electrical, board,
frame-rate and phone checks. Software proof never completes human acceptance.

## Verification coverage

Vectors cover corners, axes, RGB/palettes/layers, averages, solids, asymmetric frames,
letterboxing, mapping permutations and bounds. Control tests cover syntax, routes,
boot/idempotence, unsupported/pending/failure/retry and no persistence. Host tests cover
pin/length, clearing, transfer/setup sequencing, safe failure, restoration and current
accounting. Browser/emulator tests cover state/readback, preview, target changes and
transport failures. Relevant suites are discovered by folder.
