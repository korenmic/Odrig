# Readiness progress and retained fault diagnostics

## Summary

Make startup, checking, readiness and degraded operation visible and truthful. Retain
enough bounded evidence to diagnose an animation rejection or reset retrospectively,
without deleting content or reflashing merely to discover what happened.

Do not declare success from an early null error, a flash command's exit status or an
FPS counter that also counts dark refreshes. Long checks must not hide the animation
list or prevent the app from controlling already usable content.

## Priority

- `P1`

## Depends On

- Seeds 31 and 32, for responsive work slices, file quarantine and available lists.
- Seeds 02, 03, 04 and 07, for shared commands, the emulator, firmware and tooling.
- Seeds 09, 17 and 23, for the shared app and permanent serial diagnostics.
- Coordinate installed/external counts with seed 28 without duplicating its UI scope.

## Product Context

The investigation observed valid original content and a real synthetic watchdog loop
as distinct phenomena. Historical error messages lack enough file/read/decoder context
to establish why otherwise valid files were rejected. Initial status can look healthy
before background validation later stops playback. Conversely, list can stay busy for
minutes while playback is already working: the 84-file board-only validation took
571.77 seconds. The default install-show wait is 300 seconds.

The firmware's dark-refresh counter can still report 50 FPS when no animation is
playing. space can report zero animations for an invalid show despite existing bytes.
Neither gives operators a reliable account of readiness or recovery needs.

## Technical Constraints

- Shared core state drives every client; the UI must not infer readiness solely from
  a timeout, list polling success or the absence of an error so far.
- Keep list/status reply limits and transport parity, updating client validators.
  Extend existing reporting where possible; no new command is approved by this seed.
- Bound diagnostic storage, memory, logging rate and retention. Never include Wi-Fi
  secrets, depend on an unavailable SD card, or wear flash with per-frame writes.
- Preserve enough evidence across relevant resets using a specified safe retention
  strategy. State honestly what cannot survive power loss or has been dropped.
- Do not introduce a full-body boot hash as a diagnostic shortcut. Persistent catalog
  ingestion and eliminating routine rescans are a separate proposal, not this seed.
- Keep accepted playback at 20-50 refreshes per second; address check starvation and
  control availability, not higher FPS within the accepted range.

## Required Behavior

1. Distinguish starting, checking, ready, degraded and metadata-recovery conditions.
   Report usable playback independently from whether all checks have completed.
2. Report progress with checked/remaining/failed counts and the current operation.
   Do not invent an ETA. Distinguish internal/external installed, usable, unavailable
   and operator-excluded entries; failed files must not disappear from physical counts.
3. Preserve the per-file status/reasons required by seed 32. Checking or degraded
   operation cannot globally hide lists or block ordinary controls and safe repair.
4. Include firmware/build identity, storage backend and available media identity,
   reset reason and a bounded fault context: file/content generation, operation,
   frame/offset, decoder reason and relevant read/checksum evidence when available.
   A decoder error alone must not be labelled confirmed on-disk corruption.
5. Preserve the last meaningful failure across watchdog/software resets sufficiently
   to diagnose repeated-boot incidents. Protect boot responsiveness if the diagnostic
   record is damaged or its storage is unavailable.
6. Keep background work making bounded forward progress at accepted playback rates.
   A temporarily late refresh must not create indefinite starvation. Measure check
   progress separately from command responsiveness and valid playback.
7. Firmware tools distinguish image-written, firmware-responsive, checking, healthy
   and degraded outcomes. A flash may report successful flashing without claiming
   content validation; a health check must wait for and verify its stated conditions.
   Expired waiting reports pending/unknown, never corruption or completed health.
8. The app shows actionable checking/degraded state and fault details while keeping
   usable controls available. FPS is labelled as refresh rate and not proof of light.
9. Define a repeatable evidence-capture procedure: identify app/show/media, capture
   logs without resetting, preserve affected bytes, then use one-variable trials.
   Do not alternate broad writes and deletions without a recorded hypothesis.

## Definition Of Done

1. Tests first demonstrate premature success, misleading counts and progress gating.
   Cover checks longer than tool timeouts, accepted slow playback, no content,
   quarantined files, absent media, all bad files and unusable metadata.
2. Protocol/client/browser tests cover the full state transitions, pagination and
   truthful counts on every route. Existing users can control healthy playback before
   unrelated validation finishes. Applicable suites pass.
3. Reset/fault injection verifies retained diagnostics and their integrity, bounded
   retention and drop reporting. Match captured firmware identity to the actual ELF.
4. On-board measurements record time to firmware response, first list, first usable
   playback and completed validation separately. Reproduce a controlled fault and
   diagnose it from the retained evidence, without removing the original payload.
5. Document both proved causes and remaining unknowns. Never claim that the synthetic
   watchdog reproduction established the original valid-file rejection's cause.

## The Owner's Answers

On 2026-10-24 the owner approved honest readiness/progress and retained fault evidence
as a separate seed. The shared app must expose the per-boot unavailable entries of
seed 32; this seed adds operational clarity rather than restoring a global boot gate.
