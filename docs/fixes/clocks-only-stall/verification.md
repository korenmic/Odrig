# Clocks-only stall investigation

The owner reported a short period of clock playback, followed by a lost Wi-Fi
connection, an unresponsive app and stopped output. The delivered firmware source
was74eb4ac; its final documentation-only proof was9b64f48.

## Demonstrated fault

`requestRefreshes` previously delayed only when no refresh was due. If rendering
took longer than the20-ms grid and the consumer took each frame immediately, every
poll was due and the task never blocked. A queued task notification also returns
immediately; it does not guarantee an opportunity for idle to run. This permits
idle starvation beyond the enabled five-second task-watchdog interval.

The portable regression compiles the actual production task function with a
scheduler/consumer stand-in. With200 continuously overdue32-ms frames (about31
frames/s), both immediate consumption and queued notifications first failed:
`6400 not less than 5000`, with zero blocking ticks. The same cases pass after
an unconditional blocking tick after each poll, outside the core lock; the longest
modeled uninterrupted period is32 ms. Idle polls and update/output suspension
also pass. No watchdog is disabled, extended or manually fed, and no clock format,
shuffle, schedule, power, output configuration or app behavior changes.

## Native player evidence

Two accelerated300-second native-emulator runs mounted the actual shipped clock
and message collection. One selected clocks only; the other additionally enabled
messages. They remained responsive and advanced through clock/message turns with
no logged fault. These runs did not reproduce a native-core hang. They narrow the
demonstrated defect to the firmware producer's scheduling, which the desktop
player does not execute. They sample the collection rather than claim every file
was played.

The scheduler fixture is a portable model, not instruction-level ESP32 emulation.
The starvation condition is proven; identifying it as the owner's particular reset
still needs the actual board's reset reason and a trial with the repaired image.
No board was flashed, erased, reconfigured or observed by this investigation.

## Verification and delivery

Discovered run `20261101-000633-37676` passed all three relevant suites:
654 firmware cases(1 skip),671 emulator cases(19 skips),88 onboarding cases.
It ran with four workers and completed in295 seconds. The focused scheduler/task
contract run adds eight passing checks after the two observed red cases.
The clean fix commit is the build source for the separate delivery proof.

Physical acceptance remains open: run clocks only on the
installation, confirm continuing playback and Wi-Fi/commands, and inspect `host`
or the serial reset log if the symptom returns.
