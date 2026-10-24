# Boot-local animation quarantine and recovery

## Summary

One corrupt, missing or unreadable animation must not stop the whole show or prevent
boot from completing. Keep its entry visible but unavailable and grayed out with a
reason in the app, skip it in every playback route, and remember that failure for the
rest of the current boot. Keep healthy animations and safe repair operations available.

This is quarantine, not deletion and not a permanent operator playlist exclusion.
Preserve the original bytes and fault evidence for diagnosis.

## Priority

- `P0`

## Depends On

- Seed 31, for bounded decoding and I/O even before a fault can be reported.
- Seeds 02, 04, 07, 14, 16 and 20, for the shared player, content transactions,
  startup checking, playlist and external animations.
- Seeds 09 and 17, for the shared operators' app and its animation list.
- Coordinate with seed 29's persistent playlist toggle without changing its scope.

## Product Context

The current core makes the entire installed show invalid after one file fails.
Playback goes dark, list and remove are refused, and replacement can be blocked.
External bad files are instead omitted, so an operator cannot consistently see which
animation failed. Repeated broad storage rewrites were used to work around this trap.

The owner explicitly requires startup to finish despite corrupt animations, the app
to gray those animations out rather than hide them, and the booted instance to remember
to skip any unchanged animation that failed once. The saved original files later
validated successfully; quarantine must not pretend a decoder rejection proves physical
corruption or destroy the evidence needed to distinguish the causes.

## Technical Constraints

- The shared core owns eligibility and fault state. The emulator and every firmware
  use the same policy; app, serial and HTTP clients receive authoritative state.
- Implement the shared UI in app/www once for the APK, browser and emulator Controller.
- Keep mapping/show-metadata errors, individual animation errors and whole-medium
  loss distinct. Never guess unsafe paths from malformed metadata.
- This seed changes the current all-or-nothing installed-file policy, with owner
  approval. Reconcile show/core/command documents, the relevant decisions and the
  contradictory firmware-additions claim during implementation.
- Per-boot quarantine is separate from seed 29's persisted ignored setting. An
  intentional exclusion is not corruption; changing it cannot revive a failed file.
- Existing external media stay read-only on the board. No external-write protocol,
  new retry command, wiring change or power decision is implied by this seed.
- Preserve reply limits with pagination and update strict reply validators. Report
  file state/reason through existing list/status routes; propose any new command to
  the owner before adding it.

## Required Behavior

1. File-open, header, canvas, body, integrity and read failures discovered during
   startup, validation or playback cannot invalidate otherwise usable content.
   Complete boot into a responsive degraded state and continue healthy animations.
2. Retain a boot-local failed state and bounded reason for each affected content
   identity/generation. After a failure is established, do not retry that unchanged
   content on every playlist turn, list refresh, explicit play or automatic remount.
   Any ambiguity-resolving retry is bounded and precedes quarantine, not an endless
   attempt to re-enable the file.
3. Skip failed files in the automatic playlist, startup selection and explicit cycles.
   If a cycle has no usable members, fall back to the usable ordinary playlist; if
   nothing is usable, idle dark while commands and recovery remain responsive.
   Explicit play of a quarantined item is refused without decoding it again.
4. List known failed animations as well as healthy ones, including external entries
   that previously vanished on rejection. Give them stable, unambiguous identities
   before validation; an id collision or card swap must not transfer another file's
   quarantine. Preserve known entries as unavailable if their medium disappears.
5. Gray unavailable entries in the app, add a readable non-color-only reason and
   disable Play. Do not gray or disable the entire app: valid content and applicable
   repair actions remain usable, including when every animation has failed.
6. Keep list, status and safe internal removal/replacement available while unrelated
   checks are pending or files have failed. Retain genuine transaction and reference
   safety checks, but avoid a global full-scan prerequisite for these operations.
   Explain read-only external repair limitations rather than offering a false Remove.
7. Quarantine does not delete, rename or rewrite the original artwork. A successful
   validated replacement establishes a new content generation and can become eligible
   without restarting. A mere client reconnect or same-content media remount does not.
8. A new boot may check content again under seed 31's bounded policy. Automatic
   quarantine does not persist as a permanent playlist choice. Operator exclusions
   survive independently under seed 29 and remain in effect after a repair.
9. Separate a file failure from a whole-card failure. Do not automatically unmount
   usable external storage because one animation is bad. Real disconnection or
   diagnosed medium-wide failure remains bounded and does not block internal playback.
10. With unusable mapping/show metadata, expose a safe responsive recovery state and
    the fault; do not claim there is a usable show or blindly operate on guessed ids.

## Definition Of Done

1. Regression tests first show the old global invalidation and repair lockout.
   Cover bad headers/bodies, missing files, all files bad, invalid metadata, cycles,
   startup selection, explicit play and a failure after initially successful playback.
2. Instrument file opens/reads to prove a failed unchanged file is not repeatedly
   retried during one boot. Test restart, replacement, same-content remount, different
   media, identity collisions and independent persistent playlist exclusions.
3. Browser tests against the emulator show failed entries grayed out with reasons,
   disabled Play, functioning healthy playback and available safe repair operations.
   Shared protocol behavior and pagination agree on every supported transport.
4. Storage/medium-fault tests distinguish isolated failures from removal of a whole
   card. No quarantine test deletes the payload; retained bytes match the originals.
5. Applicable suites pass. Board fault trials complete boot and remain responsive at
   brightness at most 40 through repository tools. A person verifies the app and real
   LEDs; report any outstanding physical check and exactly what was left installed.

## The Owner's Answers

On 2026-10-24 the owner approved this seed and explicitly made graying out failed
animations, skipping them for the current boot and preventing corrupt-file boot stalls
its purpose, not optional enhancements. New managed-catalog ingestion is a separate
proposal, not a prerequisite for this fault-isolation fix.
