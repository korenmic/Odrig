# Requirements

## 1. Ready-made bytes

1.1 Upload accepts `.odrg` and `.odrgx` separately from video/GIF conversion. The
converter's header readers determine actual content, never the suffix alone.
Unsupported headers, malformed bounded containers, missing canvas and mismatched
canvas are explained before sending; the target validates the complete payload.
1.2 Sending preserves every selected byte. Renaming changes only the basename.
There is no conversion, resizing, timing change or decode/re-encode.
1.3 Preflight reads bounded headers and bounded drawn payloads. A compressed or
large frames file never inflates on the phone for validation or preview. A known
preview is reused by content key; otherwise the form explains its preview is
unavailable and the target will check the file. Small safe inputs may use the
existing preview maker. Success means managed commit acknowledgement.

## 2. Storage and destination

2.1 Each new selection/form defaults to `External storage` when detected; the
other choice is `Internal storage`. An explicit Internal choice lasts for that
form only. External absence/unknown detection disables its option, explains why,
and visibly selects Internal. Redetection restores automatic External unless
Internal was explicitly chosen. Empty/loading/filtered lists do not imply absence.
Detected read-only External stays distinct and refuses uploads without fallback.
2.2 Capture the browsed `{path,id}` when preparing either ready-made or converted
media. External uses that relative folder, combined root uses its root. Internal
uses its existing flat root, with an explanation when switching from an SD folder.
Show storage, full destination path and editable valid basename before sending.
Navigation cannot change a prepared destination. Playback cannot select it.
2.3 Revalidate target identity, storage detection, catalog generation and exact
folder identity before beginning. Stale/missing folders, unsupported older
firmware, read-only/full storage and collisions refuse visibly, without root or
cross-storage redirection. A preflight absence fallback updates the form and
requires another explicit upload click if discovered during preflight.
2.4 Once begun, storage/path are frozen. Removal or communication failure stops
that attempt; uncertain completion is reported honestly. A later manual attempt
may use visibly selected Internal; the active job never retries into it.

## 3. Managed integrity

3.1 External paths obey the existing catalog limits (100 bytes, at most three
folder levels, valid safe components); Internal remains flat and at most32 bytes.
Only an existing indexed folder can receive a nested upload. No folder creation,
absolute paths, traversal or new runtime command spelling is introduced.
3.2 Reuse begin/data/expect/end/cancel, chunk acknowledgements, capacity reserve,
CRC readback, incremental full-content checks and atomic catalog/index recovery.
New app uploads require an absent destination; collisions offer a new basename.
Existing explicit internal edit flows retain their original file and stale guard.
3.3 Failure/cancellation/interruption preserves unrelated files, catalog, ids,
playlist position and metadata. Nested additions update folder counts, ordinal
positions and id map atomically, including after restart.
3.4 After acknowledgement refresh list/catalog/keys and preview. The new file
supports play, read, ignore, brightness and removal in its physical namespace.
Preserve the core's131072-byte arena,4096-byte Core,512-byte stack warning,
128-animation minimum and32 upload spares.

## 4. Proof and delivery

4.1 Discovered suites exercise valid ODRG/ODRGX, fake extensions, mismatch,
bounded large-file handling, defaults/redetection, explicit Internal, root/nested
paths, destination staleness, collisions, read-only/full storage, cancel/removal,
catalog recovery and old-firmware refusal. Actual emulator commands prove byte
identity, acknowledged indexing and normal playback; include the space-scan file.
4.2 Use the same `app/www` and core in emulator, APK and firmware. Rebuild firmware
because destination handling changes the core, using the Windows firmware tool.
Build APK with the existing persistent Odrig key, verify signer and native Android
install/update/launch, then overwrite the existing Drive artifact files in place
and verify bytes and file identity. Never print or commit signing secrets.
4.3 Push one reviewed PR, report CI and notify the finished feature and uploaded
artifact names. Physical board and owner-phone acceptance remain explicitly open.
