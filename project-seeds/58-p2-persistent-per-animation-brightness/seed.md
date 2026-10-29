# Persistent per-animation brightness

## Summary

Add a checkbox beside the existing brightness slider for the animation playing
now. Unchecked, the slider and numeric field edit the shared default brightness.
Checking it captures the value currently set and saves that value as this
animation's brightness override. While checked, adjusting brightness changes and
saves that override instead of the default. Unchecking removes the override and
immediately uses the default again. Overrides live on the installation, survive
restarts and later default-brightness changes, and apply whenever that animation
plays. Include shared app/APK, core, firmware integration, emulator, commands,
durable storage, tests and documentation. This is not a phone-local preference.

## Priority

- `P2`

## Depends On

- Seeds 09 and 36: the shared app, acknowledged command queue and Animations panel.
- Seed 47: the synchronized brightness slider and numeric field.
- Seed 48: current-animation identity/status and durable per-file repeat settings,
  whose storage namespace and interruption-safe update pattern are precedents.
- Seeds 35, 37, 38 and 50: catalogs, animation types and large indexed microSD media.
- Seed 45: existing brightness/current safety remains effective.
- Coordinate with seed 57 if both are implemented: miniature output must use this
  same selected animation brightness and retain its own safety cap. Neither seed
  needs the other to begin; do not add miniature functionality here.

## Product Context

The existing brightness controls set one value for everything. Different animations
can need different settings, and the owner does not want to retune them each time.
On 2026-10-29 the owner requested a persistent per-animation override checkbox
beside the brightness bar, shortening the bar only enough to fit it. A later
default-brightness change must never replace a checked animation's saved value.

The owner also explicitly approved these command forms in this conversation:

- `brightness <id> <value> save`: save an animation override.
- `brightness <id> default`: remove that override.
- Existing `brightness <value>` remains the default-brightness command.

This request creates the seed only. Do not generate its spec, implement, build,
install, flash or change animation/storage contents during seed creation.

## Required Behavior

### Default And Override

1. Keep two distinct values: a global default brightness, 0-255, and an optional
   saved brightness for each animation, also 0-255. Zero is a valid override, not
   the absence of one. An animation with an override uses that value in place of,
   not multiplied by, the default. Otherwise it uses the default.
2. Checking the box snapshots the brightness currently in force as confirmed by
   the target, without a jump in light output. A typed but uncommitted edit must
   be committed through the existing field rules first or discarded explicitly;
   do not silently save stale, invalid or partially typed text.
3. While checked, the slider and numeric field display the override; committed
   edits save it and take effect immediately without restarting playback. While
   unchecked, the controls display and edit the default through the existing
   command. Keep their existing synchronization and input validation.
4. Unchecking durably removes the override, switches the controls to the current
   default and applies it immediately. It does not overwrite the default with the
   former override. Checking again captures the value then in force; it does not
   secretly restore an override the operator removed.
5. Changing the default never changes any saved override, even for the animation
   playing now. When the next animation starts, its own override or the default
   is applied before its first visible frame. Manual play, cycles, root/folder
   playlists, text, widgets and inserted clocks/messages follow the same rule.
   A clock interruption uses that clock's value, then restores the resumed
   animation's override or the latest default, not a stale pre-interruption value.
6. The power switch remains an unconditional blackout; overrides cannot turn an
   `off` display on. Default brightness zero affects only animations using the
   default; an explicit nonzero override still overrides it. Label the default
   as a default, not as a master safety dimmer. All hardware/current limits and
   any active miniature-display safety cap still apply after brightness selection.
7. Default startup/lifetime behavior stays as today: `show.json` supplies the
   startup default and `brightness <value>` changes the runtime default. This seed
   makes animation overrides persistent; it does not add default-brightness
   persistence or rewrite the show. No override means existing playback behavior.

### UI And Shared Command Contract

8. Put a labelled checkbox, `Override for this animation`, immediately beside the
   brightness slider. Shorten the slider only enough to fit the checkbox and its
   accessible label. Preserve the numeric field, the pinned panel and the shared
   app's touch targets; no overlap, off-screen control or horizontal overflow at
   320 px or in landscape. Browser/emulator Controller and APK are the same code.
9. Show the current file identity and clearly distinguish editing `Default
   brightness` from `This animation's brightness`. The checkbox follows the
   target's reported saved state, including after reconnect, another client's
   change and automatic animation transitions; it is never stored on the phone.
   With no current animation, unknown state or unsupported firmware, disable or
   mark the override unavailable rather than claiming it is unchecked.
10. Capture the target and animation identity when an edit begins. A transition
    while dragging/typing must not save its value onto the next animation. Cancel
    unsent stale edits, reconcile from status and clearly report uncertain results.
    Do not retarget queued commands using whichever animation is current later.
    A late reply must not change the controls of another target or animation.
11. The approved save form takes a listed animation id and value 0-255; default
    removes its entry. They act on that file even if it is not currently playing,
    and affect current playback immediately when it is. Unknown ids, malformed
    values, cycles and folders are refused without changes. Use existing refusal
    categories, report storage failures and keep the prior setting on failure.
12. Implement the forms once in the shared core, carried unchanged over HTTP and
    serial and supported by `odrigctl` and the emulator. Never add an APK-only
    endpoint. The target reports the global default, effective animation brightness
    and nullable saved override distinctly, without breaking existing `status`
    clients or the 1,024-byte reply bound. The specification defines additive field
    names, capability detection and refusal precedence; the command forms above
    are already owner-approved. Old firmware retains ordinary brightness controls
    and is clearly shown not to support overrides.

### Persistent Storage And Identity

13. Save overrides in the board's own storage, including overrides for external
    animations. No SD write permission is required to save a preference, and the
    preference is not lost on eject/remount, id reassignment, app restart, firmware
    flash that preserves storage or a later default change. Files, animation CRCs,
    catalog generations and image contents are unchanged by a brightness setting.
14. Follow saved-repeat identity: namespace plus full file path, not volatile numeric
    id or basename alone. Internal and external files are separate; same-named
    files in different folders are separate. Items naming the same internal file
    share one override. Replacing a file at the same path keeps its preference;
    renaming creates a different identity. A different card using the same external
    path inherits that path's preference, as the project's saved path-based settings
    do; no new card-identity scheme is introduced.
15. Retain saved entries until explicitly unchecked/removed by the override command
    or storage is deliberately reset. Removing an animation or temporarily losing
    a card must not silently evict its brightness preference. Document that a file
    later restored at that path gets its override again. No age-based expiration,
    automatic eviction or turn-scoped fallback is allowed.
16. Use the existing bounded, atomic settings-file pattern: temporary write, verify
    as required, rename to publish; a cut leaves the complete old or new settings.
    Saving an unchanged value writes nothing. Coalesce slider traffic and persist
    committed edits, not every rendering event or status poll. The acknowledged
    final value must be durable, not waiting on an unreported debounce timer.
17. Missing settings mean no overrides. Damaged settings must not block boot or
    animation indexing: log/report the problem and use defaults safely. Preserve
    the prior usable state on a failed update. Finite storage limits are explicit:
    refuse a new entry with `no-space` rather than evicting another or pretending
    it was saved. Lookups and storage updates remain bounded with indexed media;
    never rescan animation bodies or inflate startup work for this preference.
18. Firmware tools preserve/read back the settings alongside existing saved repeats
    and playlist settings; ordinary show installs without explicit replacement
    settings must not erase them. Respect current storage/board safety rules.

## Technical Constraints

- Select brightness in the shared runtime before colour scaling; do not apply
  global and override brightness twice or duplicate the rule in JavaScript/WLED.
- Preserve playback time, decoder state, repeat counts, random clock seeds,
  quarantine and mappings when a setting changes. Diagnostic output with no
  animation identity uses the default and existing safety rules, not the last
  animation's override.
- Keep on-wire compatibility, fixed memory/bounded work and command serialization.
  Do not weaken watchdogs, current limits or the accepted 20-50 FPS contract.
- No new animation/container/catalog format, hardware wiring, power decision,
  permanent remapping or Android USB feature belongs to this seed.

## Open Questions

None. The owner approved the command forms on 2026-10-29. The request establishes
permanent animation overrides and checkbox placement; the rules above settle UI
editing, default/override precedence, identity, persistence and recovery. File
layout, additive status field names and implementation decomposition are normal
S2S design work, not unanswered owner choices. Human acceptance and later flashing
approval remain required execution checks, not open product questions.

## Definition Of Done

1. Checkbox, slider and numeric field behave identically in APK and Controller.
   Tests cover enable/capture, override edits, zero, disable/restore, changing the
   default while an override exists, target/animation transitions, late replies,
   failures, unsupported firmware and narrow/landscape layouts.
2. Core/command tests demonstrate default fallback and persistent overrides for
   internal and external frames, texts and widgets, including cycles, clock breaks,
   resumed animations, remount with new ids, missing cards, duplicate basenames,
   replacing/restoring paths, power off, limits and no-animation diagnostics.
3. Persistence tests restart the runtime, cut each storage step, corrupt/truncate
   the settings and exhaust its capacity. No boot stall, silent eviction, phantom
   successful save, unrelated file mutation or global-default overwrite occurs.
4. Firmware tool tests prove preferences survive normal show/firmware operations.
   Relevant suites pass by discovery, firmware/APK build through repository tools,
   and documentation describes checkbox semantics, default-zero behavior, file
   identity, storage limits and recovery. No existing animation needs conversion.
5. A later approved board/phone session saves A at one brightness, changes the
   default while B plays, returns to A, restarts board and app and confirms A's
   override remains; unchecking A immediately restores the default and persists.
   Hardware brightness remains at most 40 during bench checks. Record human
   observations separately from automated proof; never call an unperformed check
   complete. Creating and pushing this seed performs none of the implementation.
