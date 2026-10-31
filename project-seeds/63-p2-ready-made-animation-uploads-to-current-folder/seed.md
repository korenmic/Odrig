# Upload ready-made animations into the folder being browsed

## Summary

Let the operator select an existing ODRG animation file and upload its original
bytes directly, without converting or re-encoding it. The upload belongs in the
folder the operator is currently exploring. Storage is selectable, defaulting
to External whenever detected. If External is disconnected or not detected,
select Internal automatically and gray out External. Preserve the existing
media import workflow and the managed upload/catalog protections.

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

The root browsing list combines internal animations and loose SD files. On
2026-10-31 the owner resolved its destination choice: storage is selectable,
External is always the default when detected, and absence/disconnection selects
Internal while graying out External. This is an upload destination choice,
separate from what is playing and from list filters.

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
   Large encoded files must not require expansion of every frame on the phone
   merely to create a preview. Keep preflight and preview work bounded and use
   the target's authoritative managed validation, with an honest preview fallback.
3. Capture the chosen destination storage and full relative folder path when
   the upload is prepared. Show both clearly before sending. With External
   selected, an upload prepared in SD folder `a/b` installs `a/b/<filename>`;
   browsing and playback are separate. At the combined top level, use the root
   of the selected storage. Current Internal storage has a flat root: selecting
   or falling back to Internal from an SD subfolder must show `Internal /` and
   explain the destination change before sending. Do not invent matching internal
   folders or claim the SD path was retained. This adds no general internal-folder
   model; existing valid internal path support may be reused where available.
   Apply the explored-folder destination consistently to new ready-made uploads
   and new converted-media uploads prepared from that context. Explicit edits or
   replacements remain anchored to their original stored file and its stale guard.
4. Navigation must not silently change a prepared destination. Revalidate storage,
   folder and catalog identity before sending. The approved absence fallback
   applies before an upload starts and must update the visible destination.
   A missing/changed folder, stale ID, read-only card, full storage or other write
   refusal is not absence and must not silently redirect the upload. Once bytes
   have started, freeze the transaction's storage/path. A disconnection stops
   that attempt safely; a new attempt may use the visibly selected Internal
   fallback, never continue or replay the active transaction into another storage.
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
9. Provide a Storage selector with the named choices `External storage` and
   `Internal storage`. Every new upload form defaults to External when detected;
   the operator may choose Internal for that form. Do not persist an earlier
   Internal choice as the next form's default. When External is disconnected or
   not detected, select Internal automatically, disable/gray the External choice
   and explain why. Re-detection re-enables External and restores the automatic
   default if the operator has not explicitly chosen Internal for the current
   form; revalidate the destination first and never retarget an active upload.
   Derive presence from the target's storage detection/capability, not an empty,
   filtered or still-loading file list. Report detected-but-read-only separately.
   Internal fallback still obeys capacity and naming rules: an oversized file is
   refused with an explanation, without conversion, truncation or overwrite.

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
  unchanged bytes, selectable storage/defaults, absent/not-detected External,
  disabled choices, re-detection, explicit Internal selection, preflight versus
  in-flight removal, insufficient internal capacity and storage/catalog changes.
  Native phone acceptance remains an owner check.
- The owner requested creating this seed only. Do not enqueue or implement it as
  part of seed62's animation work.

## Open Questions Requiring The Owner

None. The owner resolved the storage choice on 2026-10-31: selectable storage,
External as the default whenever detected, and automatic Internal fallback with
External grayed out when disconnected or not detected. Folder display, safe
transaction boundaries, capacity checks and re-detection behavior are specified
above. The seed is ready for S2S with zero open product questions. Exact wire
forms remain specification work; any actual new command spelling still needs
explicit owner approval before implementation, as the repository requires.

## Definition Of Done

1. Requirements/design/tasks preserve the owner's resolved choice and specify
   the selector, External default, disabled absent External, visible Internal
   fallback, re-detection and safe behavior before/during an upload.
2. A valid ready-made animation is installed byte-for-byte in the displayed
   destination folder, preserving the explored SD path when External is selected
   and explicitly showing the Internal root when storage is switched or falls back.
   It has an acknowledged catalog/list entry and usable preview; no conversion runs.
3. Discovered app/core/emulator/content suites cover nested folders, byte identity,
   malformed files, canvas mismatch, collisions, stale destinations, cancellation,
   disconnects, read-only/missing media and old-firmware behavior.
4. Relevant portable checks pass; any actual phone/board acceptance is reported
   separately. Seed creation leaves this feature planned and unimplemented.
