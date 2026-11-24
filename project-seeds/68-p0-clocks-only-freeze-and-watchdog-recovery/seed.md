# Clocks-only freeze and watchdog recovery

## Summary

Track and close the owner's report that Only briefly plays a clock, then Wi-Fi,
app replies and output stop. Reuse the already implemented scheduler-starvation
candidate, establish whether the affected installation runs it, and investigate
any remaining freeze without assuming that a desktop test proves the board's cause.

## Priority

`P0`.

## Product Context

The owner repeated this report on2026-11-01 and requested a seed once a possible
fix was confirmed. The installed firmware revision and physical reset reason were
not provided; this seed must not assume the report uses an outdated image or that
the earlier repair has resolved the particular incident.

The issue is separate from seed67's root fallback and inventory revalidation.
Those can follow a restart, but do not prove what initially stopped the board.

## Confirmed Candidate And Existing Work

The actual `requestRefreshes` function previously blocked only when no refresh
was due. Continuously overdue rendering with immediate consumption, or an already
queued notification, permits uninterrupted execution with no idle opportunity.
The producer runs on CPU0, whose idle task is watched by the pinned SDK's enabled
five-second watchdog. A costly in-memory clock can exercise this path without
storage waits. This is a demonstrated possible reset mechanism, not an observed
physical Wi-Fi disconnect in an ESP32 emulator.

Fresh local tests compiled the original and repaired production function bodies
with a portable scheduler/consumer stand-in. For200 frames of32 ms, both original
consumer cases produced6400 ms uninterrupted work and zero blocking ticks. Both
repaired cases produced32 ms maximum uninterrupted work and200 blocking ticks.
See [evidence.json](references/evidence.json) and its
[replay instructions](references/README.md).

Existing candidate: commit `317eca0c23586038772f07936f3abddef6458a65` in
[PR39](https://github.com/korenmic/Odrig/pull/39). It blocks one scheduler tick after
every poll, outside the core lock, retaining notification/output gating. Its
delivery proof is d39bb35. The source image was built and inspected through fw.py;
SHA256 `9743c4e8432885408699676dba66ef96329ddb3f5e8799d841901d5681ec10bb`,
1888192 bytes, ESP32-S3 application image at `0x10000`.

Prior complete checks passed654 firmware cases(1 skip),671 emulator cases(19
skips) and88 onboarding cases; Windows/Linux CI passed at d39bb35. Two accelerated
300-second native clock/message collection runs stayed responsive and did not
reproduce a native-core hang. Reuse these proofs where source still matches;
do not reimplement the existing patch or relabel the scheduler model as a board trial.

## Required Behavior

1. Establish source/build identity before attributing a repeated failure to the
   original task. Use existing build metadata, status/host reset descriptions and
   available serial/fault logs. If the installed version or reset reason cannot be
   observed, record it as unknown rather than claim a confirmed physical cause.
2. Preserve a genuine blocking opportunity outside the core lock on every render
   path, including overdue frames and queued notifications. Retain suspension for
   update/output transitions, single-frame ownership and correct transfer handoff.
3. Keep the task watchdog enabled and unchanged. Do not disable/extend it, add blind
   watchdog feeding, increase task priority/stack or change hardware/power to hide a
   stall. Preserve the accepted20–50 fps range and current memory/work bounds.
4. Verify the complete symptom's recovery: sustained Only playback with clocks and
   messages, continued status/commands over existing HTTP/TCP/byte-feed routes,
   and responsive app state during delayed replies or reconnects. Test heavy
   in-memory rendering, late frames and storage delays; identify the layer each
   model actually exercises. The desktop core does not execute the FreeRTOS task.
5. If the same failure is reproduced after the candidate is present, retain its
   trace and investigate bounded rendering/decoding, IO/lock waits and task/output
   coordination before selecting another repair. Require an observed failing
   regression for any additional software fix. Do not invent a new cause from a
   timeout alone or replace a proven fault with speculative changes.
6. Keep the fix distinct from seed67's mode/inventory recovery and seed66's browsing
   policy. Do not duplicate their implementation or undo their desired invariants.
   No new command family, app transport, animation format or wiring is needed.
7. Use discovered relevant firmware/core/emulator/app suites for actual touched
   components. Build changed firmware only through fw.py, inspect source/image/ELF,
   and publish verified bytes using the existing artifact identity. Rebuild the APK
   only if its code changes. Preserve signing material and board settings.
8. S2S must first audit the existing candidate and proof commits, distinguishing
   already implemented work from new runnable tasks. A remaining seed state is not
   authorization to repeat completed implementation. Keep owner-only board/phone
   acceptance explicit; a merged software fix can be complete while those checks
   remain unperformed, according to repository policy.

## Technical Constraints

- Relevant producer: firmware/usermod/odrig_usermod.cpp requestRefreshes/refreshDue.
  Existing regression: tests/firmware/test_refresh_fairness.py in317eca0.
  Existing operating evidence: docs/fixes/clocks-only-stall in PR39.
- One core/app and all existing command routes remain intact. No configuration
  changes to Wi-Fi, bootloader, partitions, current limits, pins or power supply.
- A real reset/brownout/panic diagnosis requires its actual evidence; hardware
  changes remain with the owner. No board flashing is authorized by creating a seed.
- Keep physical acceptance and unknown installed-version facts separate from
  unresolved product-policy questions. Diagnosis may proceed on controlled hosts.

## Open Questions Requiring The Owner

None for specification. The desired stability and conservative fix constraints
are defined. Installed-version/reset evidence and a real-board trial are pending
observations, not answered product decisions and not permission to claim resolution.

## Definition Of Done

The existing candidate is correctly integrated/reused and its fail-first proof is
retained. Any demonstrated residual software fault has its own observed regression
and verified repair. Relevant suites, image provenance and artifact checks pass.
The handoff says exactly which failure was reproduced, whether the physical cause
was confirmed, and which board/phone observations remain open.
