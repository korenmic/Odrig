# Manage playlist inclusion, bulk deletion and storage capacity

## Summary

An operator can exclude an uploaded animation from the automatic playlist without
removing it, then include it again. A toggle labelled "Include in playlist" appears
beside each installed animation in the shared web app used by Android and the
emulator's Controller view. The same setting is available over serial and HTTP and
survives a restart. Operators can also select and delete multiple installed animations,
and see free space in internal and external storage after startup, uploads and deletions.

## Priority

- `P1`

## Depends On

- Seeds 02, 03 and 04, for the shared player, emulator and firmware.
- Seed 07, for installed animations, uploads, removal and durable show changes.
- Seed 09, for the shared operators' web app and Android package.
- Seed 16, for the automatic playlist and explicit cycles.
- Seed 17, for the app's upload and animation list.

## Product Context

The owner requested this control on 2026-10-23 for the Android app, emulator and
serial tool. Today every installed animation joins the playlist. Removing a file
just to stop its automatic playback loses a useful animation and requires another
upload to restore it. The setting belongs to the target's show, so every connected
controller sees the same choice.

This is an extension of the default playlist behavior: existing shows still play
everything, while an operator can explicitly exclude selected animations. This seed
plans that change; it does not implement it or change the board's installed files.

## Technical Constraints

- Playback, persistence and command handling belong to the shared C++ core. Every
  firmware hosting that core and the emulator have identical behavior.
- Implement the UI once in `app/www/`, including the animation list in
  `app/www/screens/show.js`. The Android APK, browser app and emulator's Controller
  view use it. Do not build another toggle in the emulator's LED or Mapping view.
- Add one command, `ignore <id> <0|1>`: 1 excludes an animation, 0 includes it.
  Use an explicit value rather than a flip operation so retries are safe. This is
  the command for the owner's requested serial control, and it exists on every
  route, including the emulator's TCP line port. Extend `odrigctl` to send it.
- Add an optional boolean `ignored` to installed animation items in `show.json`,
  version 1, defaulting to false. Existing shows keep their behavior. Cycles do not
  accept it. The JavaScript converter, Python library and core agree on validation,
  and packing preserves it. Older players may reject shows using the new field;
  document that those shows require the updated player and tools.
- `list` reports `ignored` as a boolean on installed animation items. Drive items
  remain distinguishable by the existing installed-item boundary, not an id range;
  they do not gain this setting. Keep replies within their existing size limit and
  paginate accordingly. Update clients that validate list replies.
- Show changes use the existing durable transaction mechanism. A power cut leaves
  the complete old setting or the complete new one, never a broken show. Preserve
  all other item members when rewriting the show.
- Keep existing memory constraints and the accepted board refresh range of 20 to
  50 a second. No wiring, power, USB or microSD work is part of this seed.

## Required Behavior

1. The setting applies to every animation item installed in the writable show,
   whether initially packed or uploaded later. New animations are included by
   default. Removable-drive animations and cycles have no toggle in this seed.
2. Automatic playback, playlist wraparound and `play all` visit only included
   animations, in their original order. Existing turn lengths are unchanged.
   At startup, an ignored animation named by `start` is skipped for the next
   included animation, wrapping as necessary. A cycle named by `start` is unchanged.
3. Ignored animations remain listed, stored, counted by `space` and available to
   `play <id>`. An explicit play of an ignored animation plays its usual turn once,
   then continues with the next included animation. It does not clear the setting.
4. Cycles continue to play every animation they explicitly name, including ignored
   ones. The setting controls the automatic playlist only.
5. Excluding the currently playing animation while in playlist mode advances to the
   next included animation from its first frame as soon as the command commits.
   This also applies during a turn begun by explicit play. Excluding another item
   does not restart or interrupt the current turn. A playing cycle is unaffected.
6. With no included animation and no available drive animation, the automatic
   playlist shows black and reports `playing: null` and `animation: null`, without
   invalidating the show or changing `on` or brightness. `play all` then returns
   the existing `unknown-id` reason. Explicit play and cycles still work. Including
   an animation while idle resumes the automatic playlist from that animation;
   if `on` is false, the timeline resumes but the LEDs remain off.
7. Including an animation while another plays preserves the current turn and the
   original show order. Drive animations retain their existing playlist behavior.
8. A successful `ignore` returns `{"ok":true}` only after persistence succeeds.
   Repeating the same setting succeeds without restarting playback or rewriting
   unchanged storage. Unknown ids return `unknown-id`; cycle ids and drive ids
   return `in-use`; malformed arguments use the existing command-argument reason.
   Existing `busy` and invalid-show restrictions for show mutations also apply.
9. Uploading a replacement for an installed item preserves its ignored setting.
   Removing an item removes the setting with it. A later new upload reusing its
   removed id defaults to included. Unrelated uploads and removals preserve settings.
10. The shared animation list shows an accessible, labelled "Include in playlist"
    toggle, on for included and off for ignored. It remains possible to play or
    remove an ignored animation under the existing removal rules. Show a clear
    ignored state without relying on color alone. Hide the toggle for drive items.
11. While a change is pending, disable that toggle. Apply the confirmed target state
    after success; on refusal, timeout or disconnection, show a readable error and
    refresh from the target rather than presenting an unconfirmed change as saved.
    The next normal list refresh reflects changes made by another client or serial.
12. Update the relevant format, command, app, emulator and firmware documents,
    `docs/decisions.md` with its append-only change log, and the shared firmware
    additions list as part of implementation. Describe how the default playlist
    decision is extended and that explicit cycles are unaffected.

## Bulk deletion and capacity (resolved extension)

The owner added these features before implementation began. They belong to this
seed and use the same shared command implementation and web app as the toggle.

- Add `remove many <id,id,...>` alongside unchanged `remove <id>`. A batch contains
  1–32 distinct installed animation ids. Validate the whole batch first: unknown ids
  return `unknown-id`; cycles, drive entries and animations referenced by a cycle
  return `in-use`; malformed or duplicate ids return `bad-argument`. No item is
  removed on validation failure. Startup, upload and diagonal-test busy rules apply.
- Commit one complete show change per batch, using the existing atomic rename and
  pending-file recovery mechanism. Power loss leaves all or none of its metadata
  removed; unreachable files are cleaned after commit or on recovery. Shared files
  survive while another item references them. A later mutation must not overwrite
  an unresolved cleanup journal. Playback continues from surviving items without
  invalidating the show. Settings of surviving items are preserved.
- Storage provides accessible checkboxes for installed animations, Select all,
  Clear selection and Delete selected. Confirm count and filenames before sending.
  External media remains read-only and has no deletion or inclusion controls.
  Arbitrary selections are sent in batches of at most 32. Disable conflicting
  actions while working; report progress and partial completion on failure. Refresh
  list and space after every outcome. Never automatically retry an uncertain delete.
  Preserve selection only for items confirmed still present; clear it on target change.
- Extend `space` without removing its legacy `free`, `total` and `animations` fields.
  Add `external: {present, free, total, read_only: true}`. No mounted external media
  reports `present:false` and null capacities. Mounted media whose capacity cannot
  be queried reports `present:true` and null capacities. Known free and total are
  byte integers (up to the JavaScript exact-integer limit), including volumes above
  4 GiB. Internal capacity still describes the writable animation filesystem.
- Query external capacity through an optional host callback; command processing and
  JSON schema stay solely in the shared core. Firmware queries the mounted FAT
  volume without writes or formatting; emulator queries its mounted folder's
  filesystem. Unsupported hosts explicitly report unavailable external capacity.
- Show internal free/total and external free/total (or absent/unavailable) on Storage
  and the Show dashboard. Fetch on app startup and reconnection, after deletions and
  uploads (including uncertain outcomes), and at most every 10 seconds while either
  screen is active, so another client's changes and a target reboot are reflected.
  Ignore replies from an earlier target and clear stale values on target change.
- Document and test both commands on serial, HTTP, TCP, odrigctl and the shared web
  controller. No transport may implement its own playlist or deletion semantics.

## Definition Of Done

1. Requirements, design and tasks cover all behavior above without owner questions.
2. All suites that need no board pass. Shared-core tests cover exclusion, restoration,
   persistence and interrupted transactions, old shows, invalid values, idempotent
   commands, startup, explicit play, cycles, all excluded, replacements and removals.
3. The converter and Python suites agree on the new show member and packing. Core
   and emulator tests verify identical commands over HTTP, serial and TCP where
   available, and list pagination with the extra field.
4. Browser tests exercise the shared controller against the emulator: toggle off
   and on, reload and restart, another client changing the setting, and command
   refusal or disconnection. Confirm drive entries lack the toggle.
5. Build the updated APK and both firmware variants through the repository tools.
   Board checks use those tools, one program at a time and brightness at most 40.
   Record the actual firmware and show left on the board. A person checks the
   Android toggle against the board and confirms the LEDs skip and restore the
   selected animation. Pending hardware or phone checks are reported explicitly.

## Open Questions

None. Use the resolved behavior in this seed. The remaining work is specification,
implementation and verification, not another product decision. The owner authorizes the new command forms and the
playlist decision extension by requesting their implementation. External media remains
read-only; no new hardware behavior is assumed.
