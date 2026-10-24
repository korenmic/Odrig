# Design: playlist filters by storage and type

## What this design relies on

- Seed 36's Animations screen, `app/www/screens/show.js`, draws the rows from
  `shownOrder(state)`, the animations of the newest list in the saved order, and lets other
  modules add to a row's menu, draw with the screen and give the rows' order
  (`extend({menu, draw, order})`).
- `screens/selection.js` keeps the selected ids and offers Select all, Clear selection and
  Delete selected; `screens/reorder.js` says in `blocked()` why the order cannot be changed.
- `list` gives `external` on every animation item (seed 36) and, from seed 37 on, `type`,
  one of `"frames"`, `"text"` and `"widget"`; an item without `type` is frames.

## The filters

A new module, `app/www/screens/filters.js`, holds the two choices and their counts:

```js
const STORAGE = ["all", "internal", "external"];       // shown as All, Internal, External
const TYPE = ["all", "frames", "text", "widget"];      // shown as All, Normal, Text, Widget
export function kindOf(item);        // "frames" when the item has no type
export function storageOf(item);     // "external" or "internal", by isExternal of show.js
export function matches(item);       // both choices
export function filtering();         // a choice is not All
export function counts(animations);  // for each choice, the rows it would show with the other choice as it is
```

The choices are kept in `localStorage` under `odrig.filter.storage` and `odrig.filter.type`;
a missing or unknown value is All, and a storage that throws keeps them for the session.

`index.html` gains, between the list's heading and the list, a `div#filters` with two
groups (`role="group"`, `aria-label` Storage and Type), each a row of buttons with
`aria-pressed` and a count in a `span.count`, and a `p#filter-empty` with a `Show all`
button. The style sheet lays each group as a wrapping row of pill buttons of 44 pixels and
more.

## The list

`show.js` asks `filters.matches` of every animation after the saved order: the rows that do
not match are not drawn. `#none` says that no animation is installed when the list is
empty; `#filter-empty` that no animation matches when the list is not empty and no row
matches. The capacity lines and the Tests group draw as before.

## Reordering, selection and the menus

`reorder.blocked()` gains, before the selection mode, `filters.filtering()`: "Set both
filters to All to move animations: hidden rows would make the places unclear." That turns
off the long press, Move up and Move down, and writes the reason in the list's note.
`selection.js` takes `filters.matches` for Select all and drops, at every draw, a selected
id whose row does not match; the question of Delete selected names the selected rows only.

## Requests

The filters read the newest list and draw at every change of a choice; they ask the target
for nothing.

## Verification

`tests/app/test_filters.py` with a scenario `filters.js`: an emulator with internal
animations and a card of animations for Storage, and a stand-in target whose list has
`type` for Type (the core reports no `type` before seed 37 is merged); every combination,
the counts, the empty list and `Show all`, a reload, reordering off, Select all and a
filter change, the Tests group, the card pulled out and plugged in, and the lines sent
over a minute with and without filters.
