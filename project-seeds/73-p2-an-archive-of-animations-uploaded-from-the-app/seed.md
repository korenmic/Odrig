# An archive of animations uploaded from the app

## Summary

The operators' app opens one ZIP picked on the phone, lists all its entries, and lets
the operator select all eligible animations or a manual subset. The archive contains
already formatted `.odrg` and `.odrgx` files: extract them on the phone and upload their
original animation bytes in a batch, one file at a time, without media conversion.
Before Upload, show the selected Internal or External destination, every resulting
path, and the projected storage use, free space and capacity as the selection changes.
Reuse seed 63's explored-folder and managed upload protections. The board receives
ordinary animation uploads, never the ZIP.

## Priority

`P2`.

## Depends On

- Seed 63, completed: byte-preserving ready-made upload, captured explored-folder
  destinations, selectable storage, safe new-file guards and compatibility refusals.
- Seeds 17, 18, 24 and 35: the shared upload queue, one JavaScript converter and its
  read-only format tools, managed storage accounting, catalogs and incremental checks.
- Seed 74's separate storage explorer work, only where installing a preserved archive
  subpath needs a folder that does not already exist. Current upload creates no folder;
  this seed does not add general folder management, backup, moving or storage migration.
  It can upload into supported existing destinations without that folder dependency.

## Product Context

On 2026-11-02 the owner requested one archive received by the APK, opened there, and
its chosen animations uploaded to Internal or External storage using the existing
upload interface. Selecting specific animations and uploading them one by one within
the app is sufficient; the board does not need an archive extractor.

The initial example is `clocks_rotated_right.zip`, the 112 clocks of seed 52 and the
message of seed 54 turned a quarter turn right by pull request #46. The recorded
example has 113 files, 1,255,654 animation bytes and a 1,268,334-byte ZIP. Twelve names
were shortened for the internal name limit. These are historical example measurements,
not a live inventory or a promise that a connected target has enough free space.
The owner's later estimate of approximately 3 MB for the final pre-rotated clocks
is a different reported measurement; inspect the chosen archive and query each
connected target rather than assuming either size or a particular partition capacity.

The operator needs to know what will be installed and where before starting a batch.
A small ZIP can expand into large animation files; the ZIP's download size is not the
required installation space. Folder names and duplicate basenames also make a list of
filenames alone insufficient. The panel therefore prepares a visible destination and
collision plan and keeps confirmed successes distinct from files merely sent.

## Required Behavior

1. **Open and inspect.** Offer an Archive panel beside the existing upload workflow.
   The phone picker accepts one ZIP. For an accepted archive, list every central-directory
   entry, including folders, non-animation files and unsupported or invalid entries.
   Show its original relative name, ZIP-compressed and extracted byte sizes, and its
   eligibility or reason it cannot be selected. Identify `.odrg`/`.odrgx` from their
   actual supported bytes, not just a suffix. Explain damaged content, unsupported
   containers and canvas mismatches. Checking must not convert the animation or expand
   every encoded frame on the phone merely to build a preview. Reuse the ready-made
   upload preflight and its honest unavailable-preview fallback; the target's managed
   full check remains authoritative.
2. **Select and plan.** Start with no entries selected. Provide `Select all`, `Select
   none` and per-entry selection. Select all selects only valid, currently eligible
   animation files; it does not authorize overwrites or hide excluded entries. Show
   selected and excluded counts and the reason for each exclusion. Keep selection,
   destination-name edits and per-file outcomes visible. Recompute the destination
   plan and capacity projection whenever selection, storage, names or collision choices
   change; no bytes are sent until the operator presses Upload.
3. **Choose the destination.** Use seed 63's named `External storage` and `Internal
   storage` selector. A new archive form defaults to detected External; absent External
   is disabled and gray and visibly selects Internal. An operator may choose Internal
   explicitly. A detected read-only card remains identifiable as External and refuses
   writes rather than silently falling back. Presence comes from target capabilities,
   not an empty, filtered or loading file list. Capture the browsed base folder when
   preparing the archive, independently of playback. Show both storage and full planned
   paths before Upload. Later navigation does not retarget the prepared archive.
4. **Map paths visibly.** In External, map a safe archive path below the captured
   explored folder: archive `clocks/a.odrg` prepared in `night` becomes
   `External /night/clocks/a.odrg`. At the combined top level the base is the chosen
   storage's root. Internal currently has a flat namespace: use the entry's basename
   at `Internal /`, explicitly show that archive folders and the explored SD path are
   not retained, and resolve any resulting collisions. Do not invent internal folders.
   Every required External parent must already be a supported indexed folder, or be
   created through the separately approved seed 74 workflow before this plan is
   revalidated. Otherwise the entry is blocked with the missing folder named; do not
   silently flatten it, create folders ad hoc, or redirect it to another storage.
   A seed 74 backup's animation entries are relative to its captured source base;
   its separate JSON manifest is listed as a non-animation and skipped. Importing
   the ZIP does not apply source storage names, settings or restore instructions.
5. **Resolve collisions before sending.** Show original name, final destination and
   the planned action for every selected file. Detect duplicates within the ZIP,
   basename collisions caused by Internal flattening, renamed entries that collide,
   and existing target files using the destination's actual name-comparison rules.
   Default to no overwrite: skip the conflicting entry or enter a different valid
   basename and revalidate it. An explicitly requested replacement must name the
   existing destination and use a compatible managed replacement with a stale-content
   guard. Where that safe operation is unavailable, explain and block replacement;
   allow skip or rename. A checkbox alone is not a safe replacement protocol. Never
   delete the existing file to make a later upload fit, or silently turn a replacement
   into a new file at another path. A name edit changes no animation bytes.
6. **Project space before Upload.** Show the selected extracted animation bytes and
   the connected destination's current reported used, free and total capacity, plus
   projected use/free after the planned batch and the peak extra room needed while it
   runs. Update the projection with the selection. Account for destination allocation
   units where known, catalog/show/index growth, temporary upload and publication files,
   item/ID limits, and the managed upload reserve. For a replacement keep the old file
   allocated until the new transaction commits: its eventual net saving cannot pay for
   its own peak. Use the planned sequential order for batch peak calculations, and
   count each temporary allocation once rather than adding the same staging file twice.
   Never use ZIP-compressed size, a historical board inventory, or a fixed partition
   size as a substitute for the connected target's report.
7. **Be honest about unknown space.** If a report, allocation unit or metadata bound
   is unavailable, stale or refused, say which part is unknown; show known selected
   bytes and reported totals without presenting an exact projected free number.
   Label conservative estimates and their assumptions. Known insufficient space or
   item capacity blocks Upload until the selection or destination changes. Unknown
   capacity is not zero and is not proof that a batch fits: allow only the existing
   managed per-file admission when its protections are supported, with the uncertainty
   visible. Refresh target, storage presence/writability, catalog/folder identity and
   capacity immediately before sending and after each confirmed file. A projection is
   advisory; every upload must still pass the target's authoritative checks.
8. **Upload sequentially.** Freeze the reviewed selection, order, storage and paths
   for the run. Extract and upload one selected animation at a time through the existing
   request queue and managed begin/data/end flow, preserving the exact extracted ODRG
   or ODRGX bytes. Respect the target's acknowledged chunk limit and keep one upload
   transaction open at a time. Show per-file and batch progress and distinct pending,
   checking, installed, skipped, refused, cancelled and uncertain outcomes. Mark installed
   only after acknowledged managed publication or successful authoritative reconciliation.
   Refresh the destination catalog/list/preview after success, using normal namespace,
   inclusion and playback behavior. No archive conversion or automatic playback change
   is added by this workflow.
9. **Handle partial success safely.** The batch is a sequence of per-file transactions,
   not one atomic archive transaction. An isolated content refusal may be recorded and
   the run may continue with the next eligible file. Update the expected inventory
   after each of this batch's acknowledged managed commits and revalidate remaining
   entries against it. Pause on insufficient space, unexpected storage/folder/catalog
   changes, a collision discovered after preflight, read-only or missing media,
   connection loss, or an uncertain commit. Keep earlier confirmed
   successes; do not roll them back or silently retry them. `Cancel` stops scheduling
   new files and cancels an uncommitted active upload through the existing managed
   cancellation path. If publication may already have happened, reconcile first and
   report its actual outcome. Pending files stay distinguishable from failures.
10. **Recover explicitly.** On disconnect, stop the run; no entry in an active batch
    automatically switches storage, path or target. After reconnect, compare destination
    identity and authoritative catalog/content keys before offering retry of refused,
    cancelled, pending or uncertain files. Re-read state rather than treating bytes sent
    as success. If completion cannot be established, keep it uncertain and require a
    reviewed decision; never blindly replay an upload that may already have committed.
    An absence fallback before any bytes are sent must change the visible destination,
    rebuild the entire plan and require a fresh Upload click. There is no background
    resume after page reload: the ZIP session is local to the page, and reopening it
    requires a new review against current inventory.

## Technical Constraints

- **ZIP bounds and integrity.** The safe defaults remain at most 512 entries and
  64 MiB aggregate extracted bytes; bound the picked ZIP itself to 64 MiB as well.
  Count all entries, including ignored files, toward entry and declared extracted-size
  limits. Enumerate archive metadata before extracting candidate animation data, then
  preflight candidates with bounded reads and visible validation status. Support
  stored (method 0) and raw-DEFLATE (method 8) entries; reuse the shared converter's
  inflate implementation only with a hard output bound enforced before allocation
  and during decoding. Declared sizes alone are not trusted. Check actual extracted
  length and ZIP CRC-32, local-header/central-directory agreement and safe byte ranges;
  reject contradictory, overlapping or truncated records. Use bounded decoding work
  and output limits to stop ZIP bombs, including when headers lie. Reject an archive
  whose structure or limits prevent safe complete inspection; do not present a partial
  entry list as the whole archive. Encrypted entries, ZIP64, unsupported methods and
  unsupported multipart archives are explained and never selected; do not implement
  passwords or recursively open nested archives. Safe directory entries and unrelated
  files remain visible but are not uploaded. Resource-limit failures are said in words.
- **Contained paths and names.** Treat ZIP names as untrusted input, displayed as text
  rather than markup. Reject absolute, drive-letter and UNC names, traversal (`..`),
  empty/dot components, control/NUL characters, symlink or other special-file entries,
  ambiguous separator/encoding forms and names that could escape the captured base.
  Never extract ZIP paths directly to a phone filesystem or let percent decoding turn
  a safe displayed name into another destination. Canonicalize once under the same
  destination validation used by seed 63 and verify containment after joining base
  and entry path. External basenames follow the existing 32-byte upload rule; the
  full path remains within the catalog's 100-byte/three-folder limit. Internal keeps
  its flat 1–32-character `a`–`z`, `0`–`9`, `-`, `_`, `.` name rule. Show valid basename
  renaming for an otherwise safe entry; do not repair unsafe paths silently.
- **Bounded phone and core work.** Keep the archive as picker-backed data and read
  bounded slices where supported. Do not retain extracted copies of every selected
  file or decode all animation frames. Hold at most one bounded entry's encoded bytes
  plus bounded metadata/working buffers; release them between files. Bound any
  validation/preview work and keep cancellation and the UI responsive. The 64 MiB
  extracted limit means ZIP entry output containing encoded animation bytes, not an
  allowance to expand all ODRG frames. The board/core receives only one ordinary
  incremental upload and never buffers or extracts an archive. Any missing bounded
  decoder support must be resolved in the shared implementation during specification,
  not by introducing a second converter or trusting unbounded inflate.
- **Capacity model.** Reuse current managed accounting and documented allocation rules.
  Internal's known 4,096-byte allocation is an input where applicable, not a universal
  External assumption. The specification must identify metadata and reserve bounds
  from the actual upload/publication behavior and avoid fake precision where `space`
  has nullable External counts. Keep storage bytes and show/catalog/item capacity as
  separate constraints. Do not reclaim existing content merely to satisfy preflight.
- **Compatibility and approval gates.** Reuse documented commands; this planning seed
  authorizes no new command spelling or changed command behavior. Current seed 63
  protects new Internal files with CRC-bearing begin and explicit `replacing:false`,
  and new External files with `upload expect 00000000`. Existing Internal edit guards
  are limited to files of at most 16,384 bytes; External nonzero expectations are not
  supported. Therefore arbitrary safe replacement is not an existing capability.
  Specification must resolve those cases through a supported guarded path or expose
  a blocked replacement with skip/rename. If meeting a requirement needs a new command
  or command-list addition, obtain the owner's explicit approval before implementation
  and provide it across all transports under repository rules. Similarly, a missing
  External folder is not something current upload creates; coordinate with seed 74
  rather than claim otherwise. Older firmware lacking required new-file guards must
  refuse safely, not fall back to unguarded upload.
- **One app and bounded scope.** Use the same `app/www` in the emulator's Controller
  view and APK and the same managed core behavior on emulator and board. Preserve
  ordinary single-file ready-made upload and media conversion. This seed supplies ZIP
  selection, inspection, planning, extraction and batch orchestration; seed 74 owns
  the wider storage explorer, folder management, backup and move workflows. No firmware
  flashing, general filesystem tool, show import or archive supplied to the board is
  part of this seed. Implementation paths and discovered tests are specification work.

## Open Questions Requiring The Owner

None about the product workflow. The safe defaults above settle selection, archive
limits, path mapping, collision handling, capacity uncertainty and partial success
without expanding the requested feature. Current replacement and missing-folder
limitations are explicit compatibility/dependency gates, not assumed capabilities.
Any actual command-list addition still needs the owner's approval before implementation.
Physical phone and board acceptance remains an owner check, not something an agent
can declare from emulator results.

## Definition Of Done

1. Requirements/design/tasks preserve the ZIP-only scope, exact animation bytes,
   complete accepted-archive listing, Select all/manual subset, explicit storage and
   captured explored-folder destinations, live selection-dependent projections and
   the compatibility/approval gates. This hardening adds no implementation or queue task.
2. The discovered app suite exercises stored/deflated ZIPs containing ODRG and ODRGX,
   directories and non-animations; manual selection and Select all; invalid content,
   unsupported/encrypted/ZIP64 entries; malformed records, CRC/length mismatches,
   unsafe paths, duplicate destinations, ZIP bombs and limits. The UI exposes reasons,
   original/final paths and per-file outcomes at the project's phone widths.
3. Capacity cases cover selection changes, extracted rather than compressed bytes,
   current Internal/External reports, allocation rounding, metadata/staging reserve,
   replacements' peak rather than only net change, item/ID exhaustion, unknown/null
   or stale counters and capacity changing between files. No estimate promises a fit
   the existing managed admission cannot establish.
4. Emulator-backed tests install a selected batch byte-for-byte in Internal and in
   supported existing External folders, including a browsed base plus archive subpath.
   They cover flat Internal collisions, missing folders, guards against concurrent
   creation, unsupported safe replacement, read-only/absent cards and old firmware.
   No skipped or unselected entry is uploaded, converted or overwritten.
5. Exercise an isolated refusal mid-batch, cancellation during extraction/upload/check,
   disconnect before and after publication, a lost success reply, reconnect with a
   changed card/target/catalog and insufficient remaining space. Confirm retained
   successes, paused uncertain cases, explicit reconciliation/retry and no silent
   retargeting, duplicate replay or damage to existing files/metadata. Verify bounded
   phone buffers/work and the core's existing incremental upload behavior.
6. Run the discovered relevant portable app/converter/core/emulator suites and
   documentation/onboarding checks when implementation changes their covered areas.
   The owner then opens `clocks_rotated_right.zip` on a phone, selects a subset and
   all eligible entries, reviews both storage choices and changing space projections,
   uploads a reviewed selection, and confirms its installed animations play. Record
   actual phone/board checks separately from automated evidence.
