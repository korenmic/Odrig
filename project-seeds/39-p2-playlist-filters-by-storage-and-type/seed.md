# Playlist filters by storage and type

## Summary

The operators' app gets two filters over its list of animations: one by where an animation
is stored, internal or external, and one by its type, normal, text or widget. The filters
work in the app alone, on what the board already reports: no command, no reply member and
no change to the firmware, the core or the emulator's host.

## Priority

- `P2`

## Depends On

- Seed 36, for the Animations tab whose list the filters narrow, with its `in` / `ex`
  storage badges.
- Seed 37, for the three animation types, normal (frames), text and widget, and for the
  type of each item in `list`, which seed 37 adds.
- Seeds 35 and 38, for the external storage, a microSD card, and its catalog.

## Product Context

On 2026-10-24 the owner asked for a quick way to see only some of the board's
animations: only those of the card, only those in the board's own storage, or only the
text animations or the widgets once seed 37 brings them. With a full card the list holds
well over a hundred entries, and scrolling through it to find one kind wastes time at the
installation.

The owner asked for this in the app only. A filter changes what an operator sees, not
what the board plays.

## Technical Constraints

- Only the app's web code in `app/www/` changes, once for the APK, the browser and the
  emulator's Controller view. No command is added, no reply gains a member and nothing
  changes in `core/`, `firmware/` or the emulator's host.
- The storage of an item and its type come from what `list` reports after seeds 35 to 37.
  An item that reports no type, from a board or a file that predates seed 37, counts as
  normal.
- A filter is a view: it never changes the playlist, its order, an item's inclusion, what
  plays or what another controller sees.
- The app asks no more often than it does today.

## Required Behavior

1. Above the list of the Animations tab stand two filters, each a row of choices:
   Storage: All, Internal, External; Type: All, Normal, Text, Widget. Both start at All.
2. The two filters combine: a row is shown when it matches both.
3. Each choice shows how many rows it would show with the other filter as it is, for
   example `External 12`. A choice with 0 stays selectable and shows an empty list.
4. With no row to show, the list says that no animation matches, with a button that sets
   both filters back to All.
5. The choices are remembered on the device across a reload of the app, and are not
   shared with other controllers.
6. While a filter is not All, reordering by dragging is off and says why, because the
   positions of hidden rows would be unclear; the row menu, inclusion, play and deletion
   work as before.
7. Selecting rows for bulk deletion selects only shown rows; a row that a filter change
   hides leaves the selection.
8. The pinned Tests group of seed 36 is not filtered: it shows or hides by its own
   Settings checkbox only.
9. When the external storage is absent, External shows 0.
10. The page of the app describes the filters.

## Definition Of Done

1. All test suites that need no board and no phone pass, and the app's suite checks the
   filters in Chrome against the emulator: every combination, the counts, the empty list,
   the remembered choices, dragging off while filtered, selection of shown rows only, the
   Tests group left alone, and a card that is absent or pulled out.
2. A new APK is built, and the owner checks the filters on a phone against the board
   with the card in.

## Open Questions

None. The owner asked for this seed to be answered without a question pass.

## The Owner's Answers

On 2026-10-24 the owner asked for filters by storage, internal or external, and by type,
normal, text or widget, in the app only, and for any open question to be decided without
asking. Decided then: the filter row, the combining, the counts, the empty list, choices
remembered per device, dragging off while filtered, selection of shown rows only, the
Tests group outside the filters, and an item with no type counting as normal.
