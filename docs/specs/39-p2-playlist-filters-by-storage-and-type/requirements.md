# Requirements: playlist filters by storage and type

The seed is `project-seeds/39-p2-playlist-filters-by-storage-and-type/`. The owner asked
for it to be decided without a question pass; where these requirements decide a point the
seed leaves open, the decision is recorded in `docs/drifts.md`.

## 1. The filters

1.1 Above the list of Animations stand two filters, each a row of choices: Storage with
All, Internal and External, and Type with All, Normal, Text and Widget. Both start at All.

1.2 A row of the list is shown when it matches both filters. Storage matches by `external`
of `list`, and an older target's by the absence of `ignored`; Type matches by `type` of
`list`, and a row without `type` is Normal.

1.3 Each choice shows how many rows it would show with the other filter as it is, as
`External 12`. A choice with 0 stays selectable and shows an empty list.

1.4 When no row matches, the list says that no animation matches the filters, with a
button that sets both filters back to All. When the installation has no animation at all,
the list says so as before.

1.5 The choices are kept on the phone across a reload of the app, and not shared with
another controller. A target change keeps them.

1.6 While a filter is not All, reordering is off and the list says why: dragging lifts no
row, and Move up and Move down are off in the rows' menus. The rest of the menu, inclusion,
play and deletion work as before.

1.7 Select all selects only the shown rows; a selected row that a filter change hides
leaves the selection, and a bulk deletion names and deletes only selected rows.

1.8 The pinned Tests group is not filtered: it shows or hides by its own checkbox only.

1.9 While the external storage is absent, External shows 0.

## 2. What does not change

2.1 Only `app/www/` changes: no command, no reply member, nothing of the core, the
firmware or the emulator's host. A filter changes what the app shows, never the playlist,
its order, an item's inclusion, what plays or what another controller sees.

2.2 The app asks the target no more often than without the filters.

2.3 The APK, the browser and the emulator's Controller view run the same files.

## 3. Tests and delivery

3.1 The app's suite in Chrome checks every combination of the filters and their counts,
the empty list and its button, the choices kept across a reload, reordering off while
filtered, Select all and the selection with a filter change, the Tests group left alone,
a card absent, plugged in and pulled out, rows without `type`, and the requests the app
sends unchanged.

3.2 The page of the app, `docs/android-app.md`, describes the filters.

3.3 Every suite that runs without a board passes; the APK is built with
`python3 app/app.py build` and `tests/apk` passes on it.

3.4 Left to the owner: the filters on a phone against the board with the card in.
