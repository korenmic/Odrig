# Requirements: previews at once, each as soon as it is known

Seed 49, `project-seeds/49-p1-previews-at-once/`. The operators' app shows a row's preview
as soon as the row is drawn, or as soon as its own key is known, without waiting for the
other rows, and keeps the keys it has read for its next start. On 2026-10-27 the owner saw
a long wait after opening the app before any preview, and asked for the previews to appear
sooner, "best effort show as soon as a preview has been loaded even before all previews
been loaded", with the box of a missing preview staying black. Nothing changes on the
board, in the commands or in the look of the square.

The words of seed 44's spec hold where these do not change them: the key, the default
preview catalog `thumbnails/`, the phone's own previews, the square and the reading of the
catalogs' pages.

## 1. A preview by name and size

1.1. When the app starts, it makes from the default catalog, `thumbnails/catalog.js`, a
map from each name of its `names` to the keys whose `names` hold it.

1.2. An animation row whose key the board has not given takes, from that map, the keys of
its `file` that end in `-<bytes>` of the row. When the map does not hold the `file` and
the `file` holds a `/`, it takes those of the part after the last `/`. When exactly one
key is found, the row shows that key's preview; when none or more than one is found, it
shows none.

1.3. Once the board has given the row a key (`keyOf`, 2.1), that key alone decides the
preview: the default catalog's for it, else the phone's own, else none, as seed 44's 7.4
and 8.4 say.

1.4. 1.2 and 1.3 hold for the rows at every level of the explorer and for the square of
the panel of what plays. A row with a `fault` has no preview, as before.

1.5. No request is added for it. The map is made once; the default catalog does not change
while the app runs.

## 2. The keys of a read used at once

2.1. While a storage's catalog is being read, the key of a row of that storage is the one
the lines of this read have given its name so far, else the one of the storage's keys
before this read, else none; in each case only when the key's size is the row's `bytes`,
as seed 44's 6.5 says.

2.2. The whole lines of each reply of `catalog page` are taken as soon as the reply has
come: the rows they name have their keys from then on, and the rows are drawn again.

2.3. The keys of a storage, `state.keys`, change only when its read has ended whole, as
before. A read that starts again for another generation forgets the lines it had taken; a
read that ends without keys forgets them too.

2.4. The rest of seed 44's reading is unchanged: when `catalog` is asked, the sixteen
pages from offset 0 until `next` is `null`, the board's storage before the card, `catalog
page` after every other request, `busy` asked again two seconds later, a `null` generation
and any other refusal ending a read, and a target that refuses `catalog page` asked for no
page again.

## 3. The keys kept on the phone

3.1. When a storage's read has ended whole, the app keeps its keys on the phone: the
generation, the number of entries and the key of each name, under the address of the
target, as the app keeps that address, and the storage.

3.2. They are kept in the web view's IndexedDB, in the database `odrig-previews` of the
phone's own previews, in a store `keys`. The database goes to version 2; going to it adds
the store `keys` and keeps the phone's own previews as they are.

3.3. When a reply of `catalog` shows a storage `ok` with the generation and the number of
entries of the keys kept for that target and that storage, and the app has no keys of that
storage of the same generation and number of entries, the kept keys become the storage's
keys at once, the rows are drawn again, and no page of that storage is read. A read of it
that was under way ends.

3.4. When it shows another generation or number of entries, the storage is read as before,
and its kept keys are replaced when the read ends whole.

3.5. A storage shown `damaged`, `incompatible` or `none` loses its kept keys. One shown
`loading` or `absent` keeps them. A target that keeps no catalogs, or that refuses
`catalog page`, keeps them too.

3.6. The kept keys are never used before a reply of `catalog` from the target, at a start,
after a silence or after another address, has shown the same generation and number of
entries. Every address has its own.

3.7. No page is asked before the kept keys have been taken from IndexedDB or found
missing; a read that a reply of `catalog` started meanwhile, of a kept record's generation
and number of entries, then ends and takes them. Keys kept during this run are not
replaced by older ones taken from IndexedDB.

3.8. A web view without IndexedDB, or one that refuses it, keeps no keys between two
starts, and reads the pages as before. A write that fails leaves the keys of this run.
Nothing of this is said.

## 4. The square

4.1. Each square shows its preview as soon as its own row has one, by 1, 2 or 3, and the
image is loaded, without waiting for any other row, page or storage.

4.2. A square whose preview is not known, or that has none, is the empty black square of
seed 44's 7.3, as before. The look of the square, of its image and of the row does not
change.

## 5. What stays

5.1. The board, the firmware, the core, the emulator and the command tool; every command,
reply, error code and member; the table of command lines of `docs/android-app.md`, its
thirty-five lines and their occasions.

5.2. `thumbnails/`, its GIFs and `catalog.js`, byte for byte; the phone's own previews,
how they are made and kept, and their rule against the default catalog.

5.3. The order of the app's requests in its queue, and how often each is asked.

5.4. No plugin is added to the APK, and the APK is not built by this seed's tasks: another
piece of work is changing it, and on 2026-10-28 the owner asked for it to be built after
that work: "do not rebuild apk, another agent is working on apk changes so only after they
finish we can rebuild apk, but you may test this on an emulator". The seed's Definition Of
Done 4 waits for that, and `docs/drifts.md` records it.

## 6. The pages

6.1. `docs/android-app.md`: "The keys of the animations" says how a row's preview is
found, in this order: the key the board gives, its read under way first; then the name and
size in the default catalog; then none; that the keys are kept on the phone by address and
storage, and used when `catalog` shows the same generation and number of entries; and
which states drop them. Its sentence that a show that `pack` makes has no key until
Settings' rebuild says that its rows show by name and size what the default catalog has
meanwhile.

6.2. `docs/android-app.md`, the square of a row: a row whose key is not known yet shows
the preview its name and size find in the default catalog; a file of other bytes with the
same name and size shows that preview until its own key is read.

6.3. `docs/drifts.md` gains entries at its end under "Seed 49": what was measured before
the change and after it, and what this spec decided beyond the seed.

6.4. The seed's `state.json` is `in_progress` from the first task; its line in `AGENTS.md`
stays until the owner's check has passed.

## 7. The checks

7.1. The app's suite and the onboarding suite pass, with tests of 1, 2, 3, 4.1 and 4.2;
the emulator's suite and the converter's pass as before.

7.2. In the emulator of the branch, with the show `scratch/seed-44-show` and the card copy
`scratch/all-card-local`, the app in a browser: the rows of files the default catalog
names show their previews with no `catalog page` before them, and at a second start no
`catalog page` is sent; the number of requests to the target before the first preview, and
at a second start the number of `catalog page` requests, both written in the drift beside
those of `master`.

7.3. The round trip to the board over Wi-Fi, as the median of 20 `status` requests of the
command tool, when the board is reachable from the computer, with the delay it gives for
86 requests. When it is not, the report says so, and this check waits for the owner's
session.

7.4. The owner's check, on a phone with an APK of the branch against the board and its
card, once the APK may be built: the previews show with the rows or one by one soon after;
a square stays black only for an animation whose preview is not known; at the second
opening of the app the previews show at once.
