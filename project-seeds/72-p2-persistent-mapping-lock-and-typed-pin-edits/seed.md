# Persistent mapping checkbox and typed pin edits

## Summary

Make `Lock mapping edits` a directly accessible checkbox in the main Settings
page, with its confirmed value stored on the app and restored across app
restarts. Make the mapping's manual GPIO assignments directly editable through
text fields, alongside the existing drag and keyboard controls.

## Priority

`P2`.

## Product Context

The owner requested these changes on 2026-11-02. The existing mapping lock is a
button, and the app resets it when loading, leaving Settings, hiding the app or
changing target. GPIO values are plain text spans in the mapping editor.

This seed intentionally supersedes seed69's transient lock/reset policy. The
lock remains a local interaction preference; the board still owns its saved
mapping, and its existing validation and revision checks remain authoritative.

Seed 84, added on 2026-11-07 as a fix, delivers items 2 and 3, the kept lock
value, first, on the current toggle. This seed's checkbox shows and changes that
same stored value; it adds no second one.

## Required Behavior

1. Put a standard, labelled `Lock mapping edits` checkbox directly on the main
   Settings page near the mapping controls. It needs no submenu, overflow menu
   or expanded/collapsed section. Checked means locked; unchecked means unlocked.
2. Store one confirmed lock preference per app installation/browser profile.
   Restore both the locked and unlocked values across reloads and full app
   restarts. A fresh installation, missing/corrupt setting or unavailable local
   persistence starts locked; do not silently claim an unlock was saved.
3. Leaving Settings, backgrounding, reconnecting or changing the selected target
   must not silently replace the saved preference. Other phones and browser
   profiles have their own values. Do not store this lock on the board or add a
   firmware command for it.
4. Retain the owner's existing confirm/cancel protection for intentional lock
   changes. A cancelled, dismissed or stale confirmation changes neither the
   confirmed checkbox nor its saved value. The local checkbox can be configured
   without a connected board; that alone never sends a mapping write.
5. Persisting an unlock does not persist a draft, confirmation or pending edit.
   Target changes, app visibility loss and leaving the editor cancel unsent
   moves, typed drafts and confirmations. An already-sent save is reconciled
   against its original target. A disconnected, unsupported or stale target is
   never editable merely because the local checkbox is unchecked.
6. Give every current manual GPIO assignment a labelled, directly typeable text
   field with an appropriate numeric keyboard. These are real inputs, not
   read-only labels or fields accessible only through another menu. Keep the
   existing drag handles and keyboard moves available when editing is allowed.
7. A committed integer names a pin already present in the confirmed allowed
   assignment. Enter or leaving the field commits a valid change once. Move
   that pin into the edited snake's row using the same insert/shift behavior as
   dragging it there, maintaining the complete unique twenty-pin permutation.
   Do not invent pins, duplicate an assignment or change snake identities,
   canvas geometry, chain directions or per-strip custom starts.
8. Typing is a draft until committed. Empty, malformed, fractional, out-of-range
   or unavailable-pin input makes no write and gets a clear explanation. Escape
   cancels the draft. Committing an unchanged value is a no-op. Ordinary polling
   must not erase an active draft or move its focus; a changed target/revision
   invalidates stale drafts rather than applying them to new state.
9. Route typed edits through the same serialized, revision-checked durable save
   and confirmed readback path as existing mapping moves. Preserve existing
   conflict/storage-error handling and recovery after an uncertain reply; never
   silently retry a possibly completed mutation or apply it to another target.
10. While locked, disable text editing, dragging, keyboard moves, Restore defaults
    and photo Apply/Other reading, and guard their handlers as well as their
    appearance. Reads, Reload and diagnostics remain available. Relocking drops
    unsent edits without losing reconciliation of an already-sent save.

## Technical Constraints

This is shared app work: the Controller and Android APK behave alike and use
the same app-local preference mechanism. Preserve the existing mapping protocol,
board pin set, atomic mapping storage and current default assignment. No firmware,
hardware, power or cross-wire feature is required. Seed71's cleanup is separate;
neither change should reintroduce that retired option.

## Open Questions

None. The owner chose a directly accessible checkbox, app-side persistence and
typed manual edits. Persistence covers both confirmed checkbox states; existing
confirmation and target-write safety stay in place. Typed assignment follows
the established drag reorder operation rather than defining a second mapping
model.

## Definition Of Done

The direct checkbox restores its confirmed value after app restart, all mapping
mutations honor it, and GPIO fields can commit validated assignments through the
existing save path. Discovered affected app/emulator tests cover persistence,
cancelled/stale confirmations, drafts, invalid input, reorder parity, revision
conflicts, target changes and locked programmatic writes. Verify the shared
Controller and an installed APK in the Android VM where possible; real phone
interaction and physical LED/wiring acceptance remain the owner's checks.
