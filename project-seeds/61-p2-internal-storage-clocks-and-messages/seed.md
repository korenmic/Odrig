# Internal-storage clocks and messages

## Summary

Let the clock modes find clock faces and message animations by their relative
paths in either the board's internal storage or the SD card. In particular, files
at `clocks/message/<file>` in internal storage must be usable as messages alongside
clock faces on the card, without requiring a second copy of those messages there.
Preserve the existing `clocks/message/` name; do not introduce a parallel `msgs/`
or `msg/` convention.

Implementation also includes attempting to deploy the seven approved message
widgets to the board's internal storage through the project's managed content
tools, verifying the stored bytes and their selection/playback. Creating this
seed does not upload content, change firmware or operate the board.

## Product Context

On 2026-10-31 the owner successfully flashed the new firmware from an Android
phone and reported that only the old message appeared in the message folder.
The seven new widgets existed in the repository and configured shared collection,
but had not been installed onto the physical card by the agent. The firmware
update itself preserves animation storage and does not deploy those files.

The seven widgets together are 79,235 bytes before filesystem/catalog overhead:
`v7-consciousness.odrgx`, `v7-symmetry.odrgx`, `v7-temperature.odrgx`,
`v7-the-time.odrgx`, `v7-countdown.odrgx`, `v7-the-clock.odrgx` and
`v7-mistakes.odrgx`. They are tracked at `collection/card/clocks/message/`, with
their sources, previews and provenance. Reuse those exact approved files; this
request adds storage support, not new captions, Hebrew glyphs or animation variants.

The owner requested that an internal file with the same full relative path as an
SD file be recognized by the corresponding clock setting. The owner also explicitly
requested trying to place the messages in internal storage during this seed's
implementation. A physical installation attempt must distinguish an uploaded file
from a collection copy, an archive or an emulator fixture.

Related work:

- Seed 35: managed internal/external catalogs and interrupted-write recovery.
- Seed 37: ODRGX text/widgets and the shared renderer.
- Seed 41: folder playback and browsing for external storage.
- Seeds 54 and 59: Between/Only clock modes, complete message turns and exclusions.
- Seed 58: persistent brightness by animation identity.
- Seed 60: the firmware can be built locally on Windows; Mac access is not a prerequisite.

## Required Behavior

1. Recognize the logical paths `clocks/<face>` and `clocks/message/<message>`
   relative to each storage's animation root. Internal storage must be able to
   represent, persist, list and resolve these paths through its catalog/content
   model. Current internal names are flat, so filename substring matching or a
   clock-type test is not a substitute for adding real path support. The physical
   representation and compatible schema migration are specification work.

2. Retain every currently valid internal flat name, show, animation id, catalog,
   saved order, mapping and operator preference. Firmware updates and normal show
   installs must not silently erase the new path metadata or deployed messages.
   A missing, damaged or interrupted metadata update must recover safely. Do not
   change flash partitions, format storage or replace the whole installed show
   merely to add these files.

3. Use the effective clock/message paths across both storages in Between animations
   and Clocks only. The important mixed case is an SD clock face followed by an
   internal message. Preserve complete message loops and shuffled exhaustion,
   message on/off, mode persistence and the acknowledged state shown in Settings.
   A message file must not become a clock face because its storage differs.

4. If eligible internal faces exist, clock playback must remain available without
   an SD card. If only internal messages exist and no eligible face is available,
   retain the existing no-clock behavior: Between continues ordinary playback,
   while Only stays selected, dark and responsive with an explanation. Do not use
   ordinary non-clock animations or messages as an implicit face fallback.

5. Apply the logical clock boundary to every playback entry point in Only mode,
   including manual play, folder play, automatic next, restart, resume and cleanup
   after storage/catalog changes. Internal clock/message files belong inside that
   boundary; an unrelated internal file does not. Browsing remains unrestricted.
   Leaving Only restores ordinary playback according to the existing rules.

6. Resolve duplicate paths explicitly rather than weighting identical copied
   messages twice or binding a selection to whichever transient numeric id appears
   first. Detect the same relative path with different bytes and apply the approved
   precedence policy. Preserve storage identity for reads, edits, brightness,
   inclusion, quarantine and deletion; merging playback eligibility must not make
   an operation target the other storage's file. Settle the precedence question
   below before completing S2S.

7. Preserve own/inherited Ignore semantics, saved brightness, quarantine and
   availability when selecting from either storage. Card insertion/removal,
   catalog refresh, restart and changed ids must re-resolve candidates without
   stale selections, duplicate turns or playback outside the clock boundary.
   Read-only or missing external storage must not prevent reading internal messages.

8. Keep the shared core authoritative for selection and playback, with the emulator,
   command tool, firmware and shared app agreeing. Extend existing listing/upload/
   catalog paths compatibly and make the effective source/path understandable in
   the app. Preserve old-firmware handling. Prefer existing command forms; any new
   command spelling needs the owner's explicit approval before implementation.

9. Retain the fixed-memory, bounded-work and incremental catalog protections.
   Do not add a boot-wide animation-body scan, unbounded in-memory path union,
   blocking filesystem traversal or an independent renderer. Internal path metadata
   and any cache must have stated bounds and fit the current memory limits.

10. During implementation, query the actual internal free capacity and account for
    catalog/transaction overhead. Attempt the requested managed upload of all seven
    existing widgets into their internal `clocks/message/` paths using `firmware/fw.py`
    and/or `odrigctl` through an available approved connection. Keep existing content,
    perform the catalog transaction and read every uploaded file back for byte/hash
    verification. Record internal source/path, catalog state and observed selection
    in both clock modes; do not report a NAS copy as deployment.

11. No additional permission is needed merely to attempt that later content upload:
    the owner requested it with this seed. Existing board protections still apply:
    one board client at a time, no whole-flash erase, no GPIO/power/wiring changes,
    and no unapproved Wi-Fi connection or display/current-limit changes. The owner's
    LED/phone checks remain human acceptance. If access, capacity or a person-only
    step prevents completion, preserve existing data and report the exact unperformed
    deployment/check rather than marking it successful.

## Technical Constraints

- The internal catalog currently follows the show's flat filename rule; external
  catalogs already support relative paths. Address validation, indexing, migration
  and content operations together instead of weakening a single validator.
- No redesign of unrelated internal playlists, new message variants, time-sync
  feature, display mapping or firmware build platform is requested.
- Reuse the approved ODRGX payloads, converter, seeded timing, fonts and previews.
- Keep code portable across Windows, macOS and Linux. Use discovered regression
  suites and the actual emulator wherever possible; do not wait for Mac access.
- Record the owner's extension of clock-mode storage behavior in the appropriate
  specification and append-only decision/drift history when implementing it.
- Any necessary firmware/APK delivery must state its source, preserve the persistent
  APK signing key and verify the actual bytes. Do not rebuild artifacts just to
  create this seed or imply that flashing alone installs message content.

## Open Questions Requiring The Owner

1. When an eligible internal file and an SD file have the same relative path but
   different contents, which copy should automatic clock/message playback prefer?
   Options are internal-first or SD-first. Identical copies should contribute one
   logical automatic candidate; manual browsing must retain their storage identities.
   This precedence is not established by the request and must not be silently
   invented during implementation.

## Definition Of Done

1. The owner has settled duplicate precedence, and requirements/design/tasks state
   the compatible internal-path model, effective clock set, persistence and bounds.
2. Core/emulator regressions demonstrate SD faces with internal messages, internal
   clocks without SD, both modes and message toggles, complete-loop exhaustion,
   Only boundaries, duplicates, Ignore/brightness/quarantine and storage changes.
3. Catalog/content tests demonstrate old internal data compatibility, path validation,
   atomic updates/recovery, preserved unrelated files and accurate stored-byte reads.
   App/command tests demonstrate consistent source/path and acknowledged mode state.
4. Relevant discovered suites pass on Windows, and needed artifacts are built from
   the completed software through the repository pipeline with explicit provenance.
5. The requested seven-file internal deployment has been attempted through managed
   tools. Success includes actual path/catalog and readback evidence; blocked or
   unperformed work is named. No physical-card change is required merely to use
   the internal messages.
6. The owner confirms the actual LED/phone result, including a mixed SD-face/internal-
   message turn. Unperformed physical checks remain explicit. Creation of this seed
   stops at the seed files; S2S, implementation and upload follow separately.
