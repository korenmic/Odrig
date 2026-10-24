# Requirements: playlist and storage management

## 1. Persisted playlist inclusion

1.1 Existing show version 1 animations accept optional boolean `ignored`; absent is
false. Reject other types, duplicates and use on cycles. JS converter, packer,
Python library and core agree; explicit false survives rewriting.
1.2 `ignore <id> <0|1>` is an idempotent durable core mutation. Installed animation
list entries always include boolean `ignored`; cycles and external entries omit it.
Unknown ids use unknown-id, cycles/drive use in-use, invalid arguments bad-argument.
Startup, uploads and mapping diagnostic refuse mutations with busy.
1.3 Automatic start, play all and wrapping skip ignored animations, keeping order
and turn lengths. Explicit play of an ignored item plays one normal turn then
continues with included items. Explicit cycles ignore this playlist setting.
1.4 Ignoring the active playlist item advances immediately after commit. Changes
to other items preserve playback. All ignored with no drive yields black, null
playing/animation, unchanged power/brightness. Including while idle resumes that
item. Play all while empty returns unknown-id. Off stays off.
1.5 Replacement preserves inclusion; removal forgets it; a later new item defaults
included. Reboot and interrupted persistence leave a complete old or new setting.
1.6 Shared Show UI exposes confirmed Include in playlist toggles only for installed
animations. Pending disables its toggle; failure refreshes and explains the error.
Other-client changes appear on the normal refresh, without optimistic saved state.

## 2. Select and delete installed animations

2.1 `remove many <id,id,...>` accepts 1–32 distinct ids and validates all before any
mutation. Unknown, external, cycle and cycle-referenced items use existing refusal
reasons. Duplicate, out-of-range, empty or excess ids yield bad-argument. Existing
single removal retains its contract. All command routes share core implementation.
2.2 One batch commits atomic show metadata, then cleans unreferenced files. Restart
settles the pending journal. Shared files survive if any survivor references them;
cleanup debt cannot be overwritten by another transaction. Failure before rename
preserves metadata and playback. Surviving settings and cycles are preserved.
2.3 Current removed items advance to a surviving included animation or idle black;
removing a different item preserves current turn. No transient invalid show.
2.4 Shared Storage UI offers labelled checkboxes, select all, clear and delete.
Confirm count and names; external items remain read-only. Selections above 32 use
sequential batches with progress. Conflicting actions are disabled; failure reports
partial completion and re-reads authoritative list/space. No automatic retry of
uncertain deletions; retain only selection ids confirmed present. Target change
clears selection and rejects stale replies.

## 3. Capacity on each storage

3.1 Existing space free/total/animations fields retain meaning. Add external object
with present boolean, read_only true and nullable free/total byte counts. Mounted
unknown differs from absent; never substitute zero for unknown. Support capacities
over 4 GiB up to 2^53-1; invalid host values become unavailable.
3.2 Hosts provide capacity facts through optional drive_space callback; shared core
owns schema and protocol. Emulator reads folder filesystem usage; WLED reads FAT
free clusters without changing external files. Unsupported fallback reports absence.
3.3 Show dashboard and Storage show internal free/total and external capacity or
absent/unavailable. Query on startup/reconnection and upload/delete completion,
including failures, and within 10 seconds while relevant screens remain active.
Changes after boot or another client are reflected; target switches discard stale data.

## 4. Integration and delivery

4.1 Serial, HTTP Wi-Fi, emulator TCP, odrigctl, browser and Android share semantics.
Seed30 mapping save/diagnostic behavior remains intact. No flash or hardware change.
4.2 Keep fixed memory/no-runtime-allocation contracts, 1024-byte replies, bounded
stack and discovered suites. Preserve list pagination at the extra field boundary.
4.3 Run local suites, emulator verification, build both firmware variants and the
APK with project tools. Push combined branch and create one PR for seeds29+30.
Upload APK and WLED firmware to the usual Drive folder, preserving APK identity.
4.4 Phone and real LED acceptance stay explicitly deferred; both seeds remain in
progress until the owner makes those checks. Report automated evidence separately.
