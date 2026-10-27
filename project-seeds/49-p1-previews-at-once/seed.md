# Previews at once, each as soon as it is known

## Summary

In the operators' app, each animation row shows its preview as soon as the row is shown,
or as soon as its own preview is known, without waiting for the others. Today a row's
preview is found by the key of its file, and the app learns the keys only by reading the
catalogs of the board, 512 bytes a request, after the whole list and after every other
request, and uses the keys of a storage only once all 16 pages of its catalog are read.
Every start of the app reads them again. In between, every square is the empty black
square. In the emulator, with the card of 2026-10-27 and a show of 116 animations, the app
sent 86 requests before the first preview, and then all of them appeared at once. This
seed shows a preview from what the app already holds: the default preview catalog names
the files of each key, so a row whose name and size match one key shows its preview at
once. The phone keeps the keys it has read, and uses them at its next start when the
board's catalog has not changed. The keys of a page are used as soon as that page is read.
A square whose preview is not known yet, or that has none, stays the black square of seed
44. Nothing changes on the board or in the commands.

## Priority

- `P1`

## Depends On

- Seed 44, merged on `master`, for the keys of the animations, `<crc32>-<bytes>`; the
  default preview catalog that comes with the app, `thumbnails/catalog.js`, which the app
  imports from beside its own files and which maps each key to its GIF and to the names
  the file was given; the phone's own previews,
  kept by key in the web view's IndexedDB, database `odrig-previews`; the square of 44 by
  44 pixels of each row; and the command `catalog page <storage> <page> <offset>`.
- Seed 35, for the catalogs of the board, their generation and their number of entries,
  which the reply of `catalog` gives for each storage.
- Seed 41, for the card's sub-folders, whose files the list names by their path from the
  card's folder `odrig`.

## Product Context

On 2026-10-27 the owner checked seed 44 on a phone against the board and said, in their
words: "the previews worked well on my phone, however I confirm that there was an
unreasonable delay between the time I opened the app and till the previews started
rendering and till then there was a black box in their previews icon area which is
unacceptable and probably a bug that can be fixed in a continuation seed if you can
detect it." The owner confirmed that the previews work well otherwise.

Then, in their words: "if the preview is missing the box should remain black, the fix
shouldn't be able replacing a blank preview with a transparent/row's own color, it is
about making the preview appear faster without delays even when not 100% of them are
loaded (best effort show as soon as a preview has been loaded even before all previews
been loaded)".

The cause was found the same day, in the code and in a measurement, and is set out in
"What happens today". It is not a fault of one line: the app was built to learn every key
from the board before it shows any preview, and the board answers in small parts.

## Technical Constraints

- **What happens today.** Read and measured at `master` eb4f5de on 2026-10-27.
  - A row's square shows `previews.sourceOf(client.keyOf(animation))`
    (`app/www/screens/show.js:221` and `:386`). `keyOf` (`app/www/client.js:457-465`) is
    null until `state.keys` of the row's storage is set. `askPage` sets it only after the
    last part of the last of the 16 pages of that storage's catalog is read
    (`client.js:412-418`, `PAGES = 16`). Until then no row of the storage has a key.
  - A reply of `catalog page` holds at most 512 bytes (`docs/commands.md`). The card's
    catalog of 2026-10-27, 235 files of generation 2, is 19,096 bytes in 16 pages: 45
    requests. The board's own storage takes at least 16, one for each page, an empty page
    too.
  - `due()` (`client.js:545-590`) sends, in this order: what the operator asked for, a
    `status` that is due (every second), the next line of an upload, the next part of
    the list, the saved order, the space, `catalog`, and only then the next part of a
    catalog's page. The internal storage is read before the external one. A page refused
    with `busy` waits 2 seconds (`PAGE_AGAIN_MS`).
  - The keys live only in memory. Every start of the app reads every page again.
  - Until a preview is known, the square is `.thumb` with `background: #000000`
    (`app/www/style.css:299-309`): the empty dark square of seed 44's requirement 7.3, and
    of `docs/android-app.md`.
  - The measurement: the emulator of `master` eb4f5de, with the show of
    `scratch/seed-44-show` (116 animations) and the card copy of
    `scratch/all-card-local` (235 animations, catalog generation 2), and the app opened
    at `/app/` in a browser. The list took 44 parts. The app sent 86 requests to the
    target before the first GIF was asked for, and every GIF it showed was asked for
    within 5 ms of the first. Each request took about 1 ms there. On the board each is a
    round trip over Wi-Fi, whose time has not been measured; that time, about 86 times
    over, is the delay the owner saw. The time of a round trip to the board is to be
    measured by this seed (see "Definition Of Done").
- **1. A preview at once, from the default catalog.**
  - When the app starts it makes, from `catalog.js`, a map from each name to the keys
    whose `names` hold it. The names are those `thumbnail` wrote: a file's own name, and
    for a file given with `--card`, its path from the card's folder `odrig`
    (`converter/cli/thumbnail.js:77-85`). The list names a card's file by that path, and a
    file of the board's own storage by its name.
  - A row whose key the board has not given yet takes the keys of its `file` that end in
    `-<bytes>` of the row. A card row whose path is not named takes those of the last part
    of its path, its file's own name. When there is exactly one, the row shows that key's
    preview at once. When there is none or more than one, the square shows none until the
    board's key is known.
  - Once the board gives the row's key, that key alone decides: the default catalog's
    preview, else the phone's own, else none, as seed 44 says.
  - A file with the same name and size as a file of the default catalog, and other
    bytes, shows that file's preview until its key is read. `docs/android-app.md` says so.
  - No request is added. The map is built once; `catalog.js` does not change while the app
    runs.
- **2. The keys kept on the phone.**
  - When the keys of a storage have been read whole, the app keeps them in IndexedDB, in
    the database `odrig-previews`, which goes to version 2 and gains a store `keys`. The
    one open of `previews.js` goes to version 2, its upgrade creates only the stores that
    are missing, and the keys use that connection. Its
    record is named by the target's address, as `target.js` keeps it, and the storage,
    and holds the generation, the number of entries and the map from each name to its
    key.
  - At a start, whenever the target changes, and when it answers again after a silence
    (`client.js:103-110`), the kept record of each storage of that target is read. When a
    reply of `catalog` gives that storage the same generation and number of entries, the
    kept keys are the storage's keys at once, and none of its pages is read. Otherwise its
    pages are read as today, and the record is replaced when they are read whole. A
    storage whose catalog is `damaged`, `incompatible` or `none` loses its record;
    `loading` and `absent`, as after each boot and while the card is out, keep it.
  - The kept keys are not used before that reply. A card changed on the board gets a new
    generation and does not take them. Another card with the same generation and number
    of entries does, for a file of the same name and size: every new catalog starts at
    generation 1 (`docs/catalog.md`), and `catalog` gives only those two numbers.
  - A web view without IndexedDB, or one that refuses it, works as today, and nothing is
    said. The store of the phone's own previews keeps its records.
- **3. The keys of a page used at once.**
  - When the last part of a page has been read, the names of that page are added to the
    storage's keys at once, `keysVersion` grows and the rows are drawn again. A page of
    another generation than the first drops what was read, as today.
  - While a storage is read, `keyOf` gives a name's key from the pages read so far, else
    from the storage's keys before this read (they stand meanwhile, `client.js:313-315`),
    else null; a row with null keeps what point 1 gives it.
  - `catalog page` keeps its place in `due()`, after every other request.
- **4. Each square on its own, and the black square kept.**
  - Each square shows its preview as soon as its own row's key is known, by point 1, 2 or
    3, and its GIF is loaded, without waiting for any other row, page or storage. A
    preview that is known is never held back until the others are.
  - A square whose preview is not known yet, or that has none, stays the empty black
    square of seed 44's requirement 7.3, `.thumb` with `background: #000000`, as today.
    The look of the square does not change.
- **What stays.** The board, the firmware, the core, the emulator, every command and every
  reply, `thumbnails/` and `catalog.js`, the phone's own previews, a tap on the square
  that plays, and the folder rows and the Tests group, which have no square.
- **The pages.** `docs/android-app.md`: the keys and the three ways a preview is found, in
  that order: the board's key, then the name and size in the default catalog, then none;
  and its sentence that rows have no key until Settings' rebuild (`:557-558`), which no
  longer holds for a file the default catalog names. `docs/drifts.md` gains an entry at
  its end, "Seed 49: the previews at once", with the measurement above and the round trip
  measured on the board.
- **Tests.** In `tests/app`, with the fake targets the suite has:
  - a row of a file the default catalog names, with one key of its size, shows its
    preview before any `catalog page` is answered, with a target that answers no page;
  - from a made-up catalog the test's server serves in place of `thumbnails/`: a name
    with two keys of the same size, and a name of another size, show none until the key
    is read;
  - a key read from the board that differs from the one of point 1 replaces it;
  - keys kept from one start of the app are used at the next, with no `catalog page`
    sent, when `catalog` gives the same generation and entries; and are not used, and the
    pages are read, when it gives another;
  - after the first page of a storage is read, the rows of that page have their keys
    while the other pages are still unread;
  - while one storage is read, a row whose key is read shows its preview while other rows
    still have none; a square whose preview is not known stays black, as today.
  The suite's existing tests of the keys and the previews keep passing, changed only
  where they pinned the keys arriving whole, no preview without a key
  (`test_previews.py:93`), or the database at version 1 (`ownpreviews.js:30` and `:47`).

## Required Behavior

1. A row of a file that the default catalog names, with exactly one key of the row's
   size, shows that key's preview as soon as the row is drawn, before any page of a
   catalog is read.
2. The board's key of a row, once read, decides the row's preview.
3. The phone keeps the keys of each storage of each target and uses them at its next
   start, without reading a page, when `catalog` gives the same generation and number of
   entries.
4. The keys of a page are used as soon as the page is read.
5. Each square shows its preview as soon as its own is known, before the others are. A
   square whose preview is not known, or that has none, stays black.
6. No command, reply or byte of the board changes.

## Definition Of Done

1. The app's suite and the onboarding suite pass, with the tests above.
2. In the emulator, with the same show and card as the measurement above, the rows of
   files the default catalog names show their previews with no `catalog page` request
   before them; and at a second start of the app, every preview shows with no `catalog
   page` request at all. The counts are written in the drift.
3. The round trip to the board is measured with the command tool over Wi-Fi, from the
   computer, as the median of 20 `status` requests, when the board is reachable. It goes
   into the drift with the delay it gives for 86 requests. When the board is not
   reachable, the report says so, and this point waits for it.
4. The APK is built from the branch.
5. The owner's check, on a phone with that APK against the board and its card: the
   previews show with the rows or each soon after, without waiting for all of them; a
   square stays black only for an animation whose preview is not known; and at the
   second opening of the app the previews show at once.

## Open Questions

None.

## The Owner's Answers

On 2026-10-27, after the seed was first pushed with the square drawn in the row's own
background: the black square stays for a preview that is missing, and the seed is about
showing the previews sooner, each one as soon as it is loaded, before all of them are
(see "Product Context").
