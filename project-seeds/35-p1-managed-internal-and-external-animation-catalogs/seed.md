# Managed internal and external animation catalogs

## Summary

Replace routine animation discovery and full-library validation at startup with two
persistent catalogs: one for internal storage and one carried by the external medium.
Managed ingestion validates an affected animation and commits its metadata when content
is added, replaced or removed. Boot loads catalog metadata, not every animation body.

The ESP checks a bounded publication marker for external-catalog changes. A change
reloads only external metadata in bounded work slices; it neither rebuilds the internal
catalog nor reopens every external animation. Cross-platform Python tools manage cards
mounted on a PC, and C++ manages runtime operations. The owner explicitly permits
these two implementations, governed by one contract and cross-implementation tests.

## Priority

- `P1`

## Depends On

- Seeds 02, 03 and 04, for the shared core, emulator and firmware.
- Seeds 07, 14, 16 and 20, for durable content updates, startup, playlist and external
  animations; the current microSD backend uses the external-animation interface.
- Seeds 09 and 17, for the shared app and upload workflow.
- Seeds 31-34, for bounded work, per-boot quarantine, honest readiness and incremental
  interruption-safe updates. This seed replaces routine rescanning, not those safeguards.
- Coordinate catalog identity and metadata with seeds 28-30 without changing their
  scope or losing counts, playlist exclusions or mapping assignments.

## Product Context

The installed show already names internal files in show.json, but byte sizes, loop
durations and successful body checks are learned again in RAM after each startup.
list is refused until every installed file has been checked. External discovery lists
the folder and validates every file before admitting it to the playlist. A managed
upload already validates its payload, yet this knowledge is not reused on the next boot.

The board-only investigation measured 571.77 seconds until installed validation
completed for 84 animations. Firmware can respond and play earlier; this is primarily
an app/list/library-readiness delay, not nine minutes before the processor starts.

The owner wants one logical admission/update funnel across the app, serial, USB-C
command transfers and PC-mounted storage. A plain file copy must not silently install
an animation. A detached SD card needs its own catalog because a PC cannot update the
catalog inside a disconnected ESP. Each catalog must remain authoritative for its
own storage, while the operator sees one combined library.

## Technical Constraints

- Define one versioned, compact catalog and transaction contract, implemented in
  cross-platform Python on PCs and portable C++ on the ESP/runtime. Duplication of
  catalog-management implementation is explicitly approved, not accidental divergence.
- Share schemas, fixtures and behavioral vectors; test Python-written catalogs and
  transactions in C++ and C++-written results in Python. Keep the JavaScript converter
  as the only converter. Catalog scripts manage existing ODRG payloads, not a second
  media-conversion implementation.
- Catalog references use storage/content identity and relative paths, not Mac mount
  paths or physical flash addresses. Specify coexistence with show.json so playlist
  configuration and catalog metadata cannot become competing authorities. mapping.json
  remains the authoritative geometry/pin mapping.
- Persist the metadata needed for listing and playback selection: identity, location,
  size, canvas/format compatibility, duration, content generation/integrity information
  and the validation-contract version. Set exact fields/layout during specification.
- Define a fixed-size publication header/marker containing a generation and digest
  or equivalent change token. Writers update it as part of a committed transaction.
  Comparing this marker is not the same as hashing the whole catalog on every poll.
- O(1) per refresh means a fixed upper bound on scheduled metadata work, independent
  of library size. A complete N-entry reload remains O(N) total and is sliced across
  refreshes. I/O needs bounded timeouts/handoffs as well as bounded byte counts.
- Normal catalog mutations must avoid library-wide enumeration, payload validation
  or index rewrites. Target constant or amortized-constant metadata work per changed
  entry; explicitly account for any incremental checkpoint/compaction work outside
  the boot-critical path. Copying/validating S payload bytes remains O(S), and listing
  all N entries remains O(N). Do not claim these are constant-time operations.
- Registration targets supported writable internal/external storage through the
  available command/transfer routes and PC-mounted media. This plans the controlled
  extension of today's read-only external-content policy where runtime writes are
  supported; it does not add arbitrary filesystem writes or change hardware/power.
- USB-C is a transport, not a new storage type. Do not imply USB mass-storage gadget
  access, hub support or a new physical transport that the repository does not provide.
- The owner requested an explicit app action to force rebuilding. Specify its common
  command/protocol form and storage target, and expose it consistently on all routes;
  do not add an app-only settings endpoint. Document the command-list extension.
- Preserve core memory/allocation constraints and the accepted 20-50 refresh range.
  Board work uses firmware/fw.py and odrigctl only, brightness at most 40, one program
  at a time, no whole-flash erase and no changes to hardware, power or Mac Wi-Fi.

## Required Behavior

1. Maintain an internal catalog in internal storage and a separate external catalog
   on the external medium. Publish one logical library without rewriting or rescanning
   internal content because the external catalog changed or the card disappeared.
2. Route all supported animation additions, replacements and deletions through the
   same logical registration rules, regardless of transport or writer implementation.
   Validate only affected new/replacement payloads and derive their required metadata
   before publication. Preserve unchanged payloads and their validation records.
3. Provide cross-platform Python commands/scripts for preparing and modifying a card
   mounted on macOS or Windows. The same medium is not concurrently mounted by the PC
   and ESP. Runtime C++ applies the same transaction and catalog rules for supported
   uploads/removals; transports only carry the request/data.
4. Files copied without registration remain uninstalled and absent from automatic
   playback until explicit managed import or forced rebuild. Do not discover them
   through a hidden directory walk or full-file scan on every boot.
5. Boot reaches responsive control and useful catalog-backed listing/playback without
   opening all animation payloads, hashing all content or waiting for external media.
   Use bounded mounting and compact indexed/paged metadata; the first useful list
   page and first playable selection must not depend on reading the whole library.
6. Stream the selected animation when its turn arrives, using saved duration and
   compatibility metadata instead of decoding unrelated files to rediscover them.
   Opening and decoding still follow seed 31's bounded rules; do not promise literal
   zero-latency media access or load whole animations into RAM.
7. Detect external changes on mount and by bounded marker checks at a specified cadence.
   If storage identity and committed external marker are unchanged, do not reload the
   catalog or start catalog-induced payload validation. Ordinary playback retains its
   runtime checks. Do not calculate a full catalog hash every refresh.
8. On an external-marker change, stage/verify the new external metadata incrementally
   with a fixed per-refresh budget and atomically publish a coherent generation.
   Keep the internal catalog, validation state and internal playback untouched.
   Do not mix external records from two generations or retain usable references to
   media that has actually disappeared.
9. Add/replace/remove transactions make content and catalog publication recoverable
   through power loss, transfer failure and cancellation. Content must be complete
   before it becomes referenced. Prevent stale writers and interrupted copies from
   publishing partial entries; define old-reader lifetime and cleanup boundaries.
10. A missing, incompatible or corrupt catalog yields a responsive diagnosed state,
    not an automatic full-library rebuild, boot loop or loss of healthy other-storage
    playback. Provide explicit one-time migration/import for legacy uncataloged media.
11. Forced rebuilding is a deliberate operation on the selected storage, using the
    same bounded validation/registration pipeline. Show progress, support safe
    cancellation and keep usable controls/other-storage playback available. Ordinary
    restart, reconnection or app refresh does not imply rebuilding.
12. Catalog metadata is not proof that payload bytes cannot change afterward. Retain
    bounded runtime decoding/integrity checks and seed 32's grayed-out, boot-local
    quarantine. Detect unmanaged payload changes when content is accessed or during
    an explicit check; do not restore a full boot-time hash scan to detect every edit.
13. A metadata-only catalog reload cannot revive an unchanged file quarantined in the
    current boot. A successfully registered replacement has a new content generation
    and may become eligible. Preserve independent persistent operator exclusions,
    cycle references, ordering, mapping and brightness across catalog transactions.
14. Measure and report firmware response, first useful app/list page, first playback
    and completion of an external metadata reload separately. Set concrete readiness,
    polling, slice-size and timeout budgets during specification using board baselines.

## Definition Of Done

1. Regressions first show repeated installed validation/list gating and external
   enumeration/body admission. After the change, traced ordinary boot and unchanged
   refreshes perform no directory enumeration or full-library payload reads.
2. Growing the library and payload sizes demonstrates that per-refresh scheduled
   catalog work stays within the same budget, and first useful readiness no longer
   waits for total payload validation. A changed external catalog reads only external
   metadata; counters prove internal state and unrelated payloads remain untouched.
3. Measure single-entry addition/replacement/removal at several library sizes. Account
   separately for payload work, bounded/amortized metadata work and compaction; do not
   disguise full-catalog rewrites or global hashes as O(1) updates.
4. Python scripts run on macOS and Windows. Shared golden and malformed fixtures,
   transaction/recovery tests and bidirectional compatibility tests keep Python/C++
   behavior identical, including format versions, integrity and publication markers.
5. Fault injection covers every durable update stage, failed/absent/swapped media,
   stale markers, corrupt/truncated catalogs, invalid payloads, legacy migration,
   concurrent/stale writers, interrupted reloads and cancelled forced rebuilds.
   Recovery never silently starts a full scan or loses healthy internal playback.
6. Core, emulator, tooling, protocol and shared-app suites pass by discovery. The app
   remains useful during mounting/reload/rebuild and shows accurate library state,
   progress and seed 32's unavailable entries without overriding quarantine.
7. Board checks use cataloged internal storage and a PC-prepared external card,
   compare readiness against the existing measured baseline, verify fixed-budget
   work and a changed-catalog reload without rereading animations. A person confirms
   the app and LEDs; unavailable hardware/phone/Windows checks remain explicitly open.
8. Update the format, core, show, command, firmware, microSD, app and PC-tool documents
   and relevant decisions during implementation, explaining the managed-copy contract,
   read-only/write capabilities, explicit migration/rebuild and exact complexity claims.

## The Owner's Answers

On 2026-10-24:

1. Use two independent catalogs: internal and external. Reload only external metadata
   when its committed hash/generation changes, not external animation payloads.
2. Cross-platform Python on a PC and runtime C++ are approved separate implementations
   of catalog management. One format and compatibility contract govern both.
3. All supported copy/upload paths must use managed registration. Plain copies do not
   add playable animations, and routine boots must not rediscover/revalidate the library.
4. Per-refresh work is bounded independently of library size; a complete catalog reload
   may take multiple refreshes. Payload copying/validation is not claimed to be O(1).
5. A full rebuild is an explicit app/command action, not an automatic startup task.
6. This is a new seed, separate from the already approved corruption, diagnostics and
   update-safety seeds 31-34. Creating it does not implement or flash any firmware.
