# Miniature matrix debug mode — design

## Core boundary

Keep `odrig_host`, normal leg buffers and record formats unchanged. Allocate one fixed
miniature state at core startup for a 60x60 mapping; allocation failure leaves normal
playback usable and miniature unsupported. Public C helpers register host support,
read state/frame pointers and acknowledge an output-setup revision. Hosts which do not
opt in cannot accidentally advertise working hardware support.

State holds supported, active, requested, pending, failed and a nonzero request
revision. Boot is off. `debug mini` validates syntax, support and pending state; same
requests succeed idempotently and opposite pending requests return `busy`. A new
request clears failure, sets pending and increments revision. Only a matching pending
revision may be acknowledged. A failed acknowledgement sets active false and failed;
status exposes `on:null` until a later successful setup. Retry of either state is allowed.
The command's `ok` means accepted; `status.mini.pending` distinguishes completion.

Status adds `mini:{supported,on,pending,requested,error,brightness}`; `error` is null
or `output-setup-failed`. `on` is null when failed. Brightness is the effective capped
value (zero when power is off), independently of the normal requested brightness.

The shared renderer builds separate 180-byte row-major bottom-up preview and 180-byte
physical RGB buffers only while active. Thirty-six fixed 32-bit RGB accumulators
sum scaled source samples. For logical (x,y), cell=(x/10,y/10), preview column=cell.x+2.
Divide each sum by100, leaving side columns zero. Obtain raw colours from the same
palette/RGB/layer as normal output, not already-scaled or physically permuted legs.
Clear miniature buffers on off/invalid/blank playback and output transitions.

Manufacturer source: https://wiki.seeedstudio.com/rgb_matrix_for_xiao/ and its Eagle
archive https://files.seeedstudio.com/wiki/xiao-rgb-matrix/EAGLE_XIAO_MATRIX.zip
(SHA256 0095e346fbfe0f5f3315b010d4990827268dad60c50f481bd1cd8e2ac4c8efea).
Following DIN→LED116 through all60 DO→DI nets ends atLED39. In Eagle's component
view it is six-wide straight rows, descending Y. Landscape front view with IN edge
left rotates that grid90 degrees counterclockwise: physical index=x*6+y. This source
derivation is testable independently of the renderer; powered orientation remains open.

## Firmware transition

Retain the startup normal leg metadata/cache and use an alternate `OdrigLegSource`
for the one60LED GPIO1 bus. Pause the refresh requester through the existing ready
handshake during a transition. Poll transfer readiness in loop; dark/show the outgoing
bus first, wait for that transfer, then change source/apply the bus configuration.
Do not hold the core lock across WLED allocation/finalizeInit or transfer waits.
Check the resulting bus configuration and working count before acknowledging revision.
Clear pending copied frames at transitions, then resume decoding/refresh requests.
On failure, keep a dark source selected and keep normal frames from reaching any bus;
report failure through the core, allowing an explicit retry. Common core calls remain
serialized. Commands, network, SD worker and both USB routes remain serviced.

The existing output adapter's current limiting takes lengths/pins from the selected
source: miniature has60 active LEDs. Preserve global and per-snake budgets; do not
write WLED settings or change physical wiring. A standalone/custom host remains
unsupported unless it implements the transition contract.

## Emulator and app

Python binding declares the extra C helpers and state structure, opts into support,
and completes pending transitions immediately because it has no hardware buses.
The command reply still represents submission; the next status reflects completion.
The hub sends a separate `mini` event containing the core preview alongside normal
refreshes; the emulator draws it in a10x6 canvas with bottom-left coordinates.
Normal refresh/ODRR recording data keeps its installed geometry.

Shared app command/client modules route `debug mini` through the existing operation
machinery. A dedicated screen controller reads status and tracks request/readback with
the existing target epoch. Missing capability disables the checkbox as unsupported;
failed/disconnected/unknown state is visibly distinct. Pending and local in-flight
requests disable it. Read status after submission and retain pending until acknowledged;
polling reflects changes from other clients. No localStorage mode preference. A global
active indicator stays visible outside Settings. Older firmware needs no migration.

## Documentation and proof

README pin table repeats the settled intended circuit, with manufacturer links and
front/rear orientation. The documented part's2.8V high threshold at5V supports direct
3.3V data subject to actual-part/signal confirmation. Supply budget, USB paths, assembly,
corner/axis test, real-frame/SD playback, transition clearing, frame rate and phone
readback are later human acceptance; no flashing/build success is inferred.

Core public API/behavior docs, commands, emulator, mapping, app and firmware docs explain
state, preview and temporary routing. Record non-owner design choices in appended
drifts. Firmware build is expressly deferred to future seed60. APK release is once,
after seeds56–59 software; acceptance stays open until actually observed.

Review: requirements1–5 map to control, projection, host transition, app and operator
sections respectively. No new command beyond the owner-approved `debug mini on|off`.
