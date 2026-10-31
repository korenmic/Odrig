# Upload ready-made animations into the folder being browsed

## Summary

Let the operator select an existing ODRG animation file and upload its original
bytes directly, without converting or re-encoding it. The upload belongs in the
folder the operator is currently exploring. Preserve the existing media import
workflow and the managed upload/catalog protections.

## Priority

`P2`.

## Product Context

On 2026-10-31 the owner requested support for uploading already ODRG-formatted
animation files that need no conversion, with uploads landing in the currently
explored folder. This also gives generated animations, such as the space scan,
a direct installation path from the operators' app.

The current media picker accepts video and GIF inputs for conversion. The app's
existing external byte upload uses `upload begin external <file> <bytes>` and
currently installs loose files at the SD root. Supporting ready-made files and
subfolder destinations therefore requires both an app entry point and compatible
managed destination handling. A changed file picker alone is insufficient.

The root browsing list combines internal animations and loose SD files. That
mixed view does not identify a unique storage destination; Q1 resolves it.

## Required Behavior

1. Offer a clear way to choose an already formatted `.odrg` animation. Accept the
   project's `.odrgx` containers through the same ready-made route when their
   validated contents are supported. Detect the actual format from its bytes,
   retaining existing extension/name rules and explaining invalid or unsupported
   content. Do not treat a renamed video as an animation.
2. Preserve the selected bytes exactly. Do not resize, crop, recolour, change
   timing, strip container content, decode-and-re-encode, or run media conversion.
   Format checking and generating a preview are permitted read-only operations.
   A canvas mismatch is explained and refused rather than silently converted.
3. Capture the destination storage and full relative folder path from the
   browsing context when the upload is prepared. Show the destination clearly
   before sending. An upload prepared in SD folder `a/b` must install
   `a/b/<filename>`, not the SD root, internal root or the current playback folder.
   Browsing context is separate from what happens to be playing.
4. Preserve that destination while the operator navigates elsewhere or reconnects.
   Resolve it against the current storage/catalog before sending; removed media,
   missing/changed folders, stale IDs and read-only storage must cause an honest
   refusal or renewed confirmation, never silent redirection to another folder.
5. Use existing managed upload validation, capacity accounting, incremental checks,
   CRC/readback, transaction recovery and atomic catalog/index publication. Keep
   existing files and metadata intact on cancellation, interruption or failure.
   Distinguish an acknowledged installed file from bytes merely sent.
6. Do not overwrite a same-name file silently. Reuse an explicit existing replacement
   flow with its stale-content guard where applicable, otherwise refuse the collision
   and allow another valid destination basename. A basename change must not alter
   the animation bytes or retarget an unrelated stored file.
7. Refresh the destination listing/catalog and app preview after acknowledged success.
   The file remains in its physical storage namespace with normal manual-play,
   inclusion, brightness and deletion behavior. Internal flat-name compatibility
   and SD path/index limits remain enforced.
8. Reuse the same shared app and core in the emulator and APK. Handle old firmware,
   refused paths, disconnects and uncertain completion honestly. Keep supported
   media conversion available for inputs that actually require it.

## Technical Constraints

- This is an ordinary content upload, not firmware flashing or a new animation type.
- Prefer extending the existing upload forms' validated destination path handling.
  Any actual addition to the command list still requires explicit owner approval
  before implementation and must be available through all transports.
- Reuse the converter's read-only format/preview capabilities and the target's
  authoritative managed checks; never introduce a second conversion implementation.
- Preserve bounded memory/work, storage containment, safe canonical relative paths,
  folder identity, catalog/index integrity and interrupted-write recovery. Refuse
  traversal, absolute paths and unsupported names without weakening old validation.
- Support the actual current browsing model. This seed does not require seed61's
  internal nested-clock paths or a general internal-folder redesign. If those are
  available when implemented, use their validated path model consistently.
- Test actual byte uploads against the emulator, including nested SD destinations,
  unchanged bytes, failures and storage/catalog changes. Native phone acceptance
  remains an owner check.
- The owner requested creating this seed only. Do not enqueue or implement it as
  part of seed62's animation work.

## Open Questions Requiring The Owner

### Q1. Which destination should the combined top-level list use?

- **A. Recommended:** upload to the SD root and refuse if it is unavailable or read-only.
- **B. Alternative:** upload to the internal root, under its existing naming/capacity rules.
- **C. Alternative:** ask the operator to choose SD root or internal root at that level.

An actual SD subfolder already determines its destination and needs no extra choice.
Exact wire forms and safe implementation details are specification work; no new
command spelling is approved merely by creating this seed.

## Definition Of Done

1. Q1 is resolved; requirements/design/tasks specify destination capture, validation,
   root behavior, compatibility, collision handling and interrupted uploads.
2. A valid ready-made animation is installed byte-for-byte in the explored folder,
   with an acknowledged catalog/list entry and usable preview; no conversion runs.
3. Discovered app/core/emulator/content suites cover nested folders, byte identity,
   malformed files, canvas mismatch, collisions, stale destinations, cancellation,
   disconnects, read-only/missing media and old-firmware behavior.
4. Relevant portable checks pass; any actual phone/board acceptance is reported
   separately. Seed creation leaves this feature planned and unimplemented.
