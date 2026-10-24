# Incremental and interruption-safe content updates

## Summary

Make adding, replacing and removing content change only the necessary payload and
metadata. Do not recreate every installed animation for a one-file change. Keep
updates recoverable through failures, cancellation and power loss, and distinguish
content maintenance from firmware flashing and filesystem repair.

## Priority

- `P1`

## Depends On

- Seeds 04, 07 and 24, for firmware tooling, durable content changes and both layouts.
- Seed 32, for safe repair when another animation is bad or still being checked.
- Coordinate stored playlist choices and mapping with seeds 29 and 30, preserving
  their data without requiring those features to be implemented first.

## Product Context

The invalid-show gate prevented ordinary removal during the investigation. The
fallback rebuilt /odrig in a local filesystem image: one deletion changed 6,705,152
bytes and the next changed 6,676,480. The tool writes differing blocks, not necessarily
the whole partition, but unrelated animation payloads are still relocated. It then
verifies the full 13.5 MB partition. Cancellation has no general rollback guarantee.

Reflashing the app alone preserves animation storage and cannot remove a bad file.
The owner needs precise, small recovery operations, not repeated broad writes whose
scope and completion are unclear.

## Technical Constraints

- Preserve all settings outside /odrig, mapping, item identities/order, brightness,
  timing and stored playlist choices unless the requested operation changes them.
- Board access remains through firmware/fw.py and odrigctl; one program at a time,
  brightness at most 40, no whole-flash erase, eFuse or factory-backup writes.
- Use normal transactional filesystem/content operations where they can meet the
  safety requirement. Changed raw blocks alone do not make an update atomic.
- If an offline/raw-image fallback cannot safely cancel at a particular point,
  identify that point and complete or recover deliberately. Do not promise rollback
  merely because a backup file exists.
- Require sufficient transaction space before mutation. Refuse without damage when
  a recoverable old/new outcome cannot be provided; do not overwrite live data to fit.
- Keep external media read-only on the board under the current product policy.
  This seed does not add SD/USB writes or the separately proposed shared ingestion
  catalog. PC-mounted-media workflows must remain compatible with that future work.
- No new operator command is implied. Preserve existing command safety and propose
  any protocol addition to the owner first.

## Required Behavior

1. Single-file removal, addition and replacement do not rebuild the animation folder
   or rewrite unchanged payloads. Bound metadata changes and document filesystem
   overhead; do not claim literal constant physical writes under garbage collection.
2. Prefer live scoped recovery where safe, including when unrelated items are bad.
   A malformed animation never requires a firmware rewrite merely to remove it.
3. Publish a change only after its content and metadata meet the transaction's checks.
   Failures leave a complete old or new committed state or a clearly diagnosed,
   deterministic recovery path; never silently expose a partial update as playable.
4. Define safe cancellation boundaries and restart recovery for live updates and
   any raw-storage fallback. Interrupted cleanup is idempotent and preserves content
   still referenced by a committed show.
5. Preserve an affected file for diagnosis before destructive recovery when requested,
   and verify the exact target. Quarantine itself never deletes payloads.
6. Scope progress and outcome messages precisely: what changed, bytes transferred,
   verification performed, whether a restart is needed and whether the operation is
   committed, pending, cancelled or requires recovery.
7. Unchanged requests are idempotent and do not rewrite content unnecessarily. A
   routine content operation preserves firmware, settings and unrelated artwork.
8. Keep full-show installation available as an explicitly broad operation, but avoid
   replacing unchanged content needlessly. Whole-filesystem repair is a separately
   identified last resort, not an automatic one-file maintenance step.

## Definition Of Done

1. A regression first demonstrates the existing excessive one-file update. Tests
   record logical payload preservation and changed/transferred byte counts for
   removal, addition, replacement and unchanged retries at representative capacities.
2. Fault-injection tests interrupt every durable transaction step, including writes,
   rename/publish, cleanup, out-of-space, transport loss and user cancellation.
   Restart always has the documented old/new or recoverable state.
3. Test both flash layouts, preserve settings and mapping byte-for-byte where
   unchanged, and cover bad/quarantined content without disabling safe repair.
4. Applicable suites pass. On-board trials show one-file maintenance without app
   reflashing or relocation of unrelated payloads. Record elapsed time and bytes,
   compare before/after manifests, and report exactly what remains on the board.
5. Documentation clearly separates flashing, content updates, quarantine, validation
   and filesystem recovery, including cancellation limitations and backup recovery.

## The Owner's Answers

On 2026-10-24 the owner approved incremental, interruption-safe storage maintenance
as a separate seed. Planning this work does not authorize removing any animation or
rewriting the currently healthy board during seed creation.
