# SD capacity without blocking playback

## Summary

The first request for the microSD card's free space must not freeze playback or
commands. The firmware reports mounted presence independently of whether capacity
is known, answers `space` from a bounded cache, and obtains capacity without a long
hold of any lock needed by the player. The app distinguishes an unknown or stale
storage report from a current report that a card is absent. No command is added.

## Priority

- `P1`

## Depends On

- Seeds 29 and 38: the external capacity callback and the microSD host adapter.
- Seeds 31 and 33: bounded work, responsiveness and readiness diagnostics.
- Seeds 35 and 50: the external catalog and index; they must remain usable while
  capacity is unknown and must not be rebuilt to obtain free space.

## Product Context

The owner saw “No answer” and “External storage: absent” after installing current
firmware and a current card catalog. Investigation on 2026-10-29 found the card
mounted, with all 348 external animations across 16 folders and 78 internal
animations listed, zero listed faults, and both catalogs OK. This does not explain
the earlier absence; it establishes a separate, reproducible responsiveness fault.

After each of two resets, `status` and `catalog` answered normally. The first
`space` command over the UART bridge then took 10.5881 and 10.5958 seconds. A `status`
command sent 250 ms later on native USB waited 10.4899 and 10.3269 seconds, and
reported 0 FPS. Subsequent `space` commands took 0.0646 and 0.0221 seconds. No reset,
catalog failure, unmount or animation fault occurred during those pauses; playback
recovered afterward. The app's request deadline is five seconds.

The board identified itself as `odrig_ESP32-S3_16MB_opi Oct 28 2026 22:28:52
internal+microsd`. Claude's flash record names commit `a8be36c`, a 1,859,920-byte
image with SHA-256
`463493e6ebbd978643da9860228c8bfa817530c013d484d71058b729b5091092`.
The implementation remains in master `1cd0430` as this seed is written.

Evidence on the first computer is in
`build/sd-investigation-20261029/`: `findings.md`, `baseline.jsonl`,
`cold-1-probe.jsonl`, `cold-2-probe.jsonl`, `final-state.jsonl` and `diagnose.py`.
These ignored artifacts are supporting evidence, not a prerequisite for another
checkout: the measurements and reproduction above are preserved here.

## Technical Constraints

- `firmware/usermod/odrig_usermod.cpp` holds the common core lock around commands
  and refreshes. `core/src/content.cpp` calls the host's `drive_space` callback
  synchronously. `firmware/usermod/odrig_drive.cpp` takes the SD mutex and calls
  `SD.totalBytes()` and `SD.usedBytes()` inside that callback.
- Both calls in the pinned Arduino SD library call `f_getfree`. A cold free-cluster
  calculation can walk the allocation table. The cold/warm timings support this
  explanation; no instrumented build has separately measured time inside it.
- Moving the same monolithic calculation to a worker that holds the SD or FatFs
  lock is not a solution: playback reads need those resources too. Neither delaying
  publication of a mounted card nor increasing the app's timeout is a solution.
- Existing `space` permits `present:true` with `free:null` and `total:null`.
  Capacity not yet known is not absence, corruption, zero free bytes or read-only.
- Keep the external storage generation checks, correct 64-bit counters and cache
  invalidation on removal, remount and changes. No old card's capacity may describe
  a newly mounted card. Do not present an estimate as exact available capacity.
- Keep upload safety when capacity is unknown: no invented available byte count,
  no damaged catalog or partial animation published on out-of-space or removal.
- Use existing commands, catalog formats, partitions and dependencies where possible.
  No hardware, power, mapping, watchdog or Wi-Fi setting changes; no whole-flash
  erase. Follow the repository's board tools and approval rules.

## Required Behavior

1. A request for `space` never begins or waits for an unbounded FAT scan under the
   player/core, SD or filesystem critical paths. Its capacity callback is bounded
   within the existing 50 ms per-call budget, including when the cache is cold.
2. A mounted card is reported present immediately, independently of capacity. Its
   catalog, lists and animations remain accessible while capacity is unknown.
3. Capacity becomes available through bounded, interleavable work, or existing
   trustworthy volume metadata, without stalling playback or other commands.
   The design must account for the filesystem's own locks, not just the outer one.
4. Cache publication is generation-safe and reconciles successful writes,
   replacements and removals, errors, removal and remount. Accuracy and the bounds
   are documented and tested. An unknown value stays explicitly unknown.
5. The app displays unknown capacity and stale/disconnected storage information
   honestly; it must not turn either into a fresh “absent” claim. A genuine absent
   reply remains distinguishable. Browser and APK share the same behavior.
6. Regression coverage first reproduces a slow first capacity calculation and
   proves that concurrent status and refreshes are delayed on the old path. It
   covers warm queries, capacity failure, card generation changes and writes too.

## Definition Of Done

1. The regression is seen failing before the fix and passes afterward. Relevant
   firmware, core and app suites pass by discovery; shared command behavior stays
   compatible. The firmware builds through `firmware/fw.py`.
2. An approved board session repeats the cold first-space test after at least two
   resets, at brightness no greater than 40, with the same card or an equally
   adversarial volume. The first and subsequent `space` and concurrent `status`
   replies arrive within 500 ms on the local USB route. Playback stays within
   the agreed 20–50 FPS after startup, with no multi-second gap or watchdog reset.
3. The mounted card's complete catalog and listing remain available, no animations
   or catalogs are lost or rewritten to calculate capacity, and unknown capacity
   converges safely or reports failure without blocking. Removal/remount and a
   controlled mutation/out-of-space test demonstrate cache and publication safety.
4. The owner checks the phone's unknown/stale/absent states. Anything requiring
   hardware or a person's observation that was not checked is explicitly left open.
5. The documents describe capacity freshness and the bounded implementation; the
   board report records firmware identity, cold/warm timings, rates and outcomes.

## Out Of Scope

Finding the cause of the historical pre-restart absence or brownout; changing power
or wiring; Android USB flashing/serial support; miniature diagnostic displays;
new commands; unrelated decoder or catalog changes; optimizing rates already
inside 20–50 FPS. Those require separate approval and, if wanted, separate seeds.

## Open Questions

None requiring an owner choice before specification. The bounded capacity strategy
is an implementation design decision, justified against the pinned filesystem and
the reproduction. A strategy that cannot meet these bounds must be raised before
weakening them, not hidden by a longer request timeout.

## The Owner's Approval

On 2026-10-29 the owner asked for a seed implementing the fix after receiving the
confirmed two-run diagnosis. This creates planned work; no implementation or
flashing is performed by creating this seed.
