# The preview of an upload, made on the phone as it starts

## Summary

When the operators' app starts an upload, it starts making the preview of the bytes it
sends at once, beside the upload, and keeps it on the phone alone. It keeps the preview by
the key of those bytes, as today, and also by the place the upload puts them: the target,
the storage, and the file's name as the list names it. As soon as the upload has ended
with success and the preview is made, the row of that animation and the panel of what
plays show it. They do not wait for the board's catalog to give the row its key, and they
show it on a storage that has no catalog at all. A ready-made animation of any size gets
its preview, compressed or not: a compressed body is read as a stream, so the preview
never holds the whole inflated animation, only the file's bytes, which the upload holds
anyway. The preview never leaves the phone. Nothing changes on the
board or in the commands.

Today a row finds the phone's own preview only by the key the board's catalog gives it,
and a storage without a catalog never gives one. A ready-made frames file gets a preview
made on the phone only when it is small and not compressed. So after an upload the owner saw no preview in the
playlist.

## Priority

- `P1`

## Depends On

- Seed 44, merged on `master`: the phone's own previews, kept by key in the web view's
  IndexedDB, database `odrig-previews`, store `previews`, made with the converter
  library's `thumbnail` maker a step at a time; the key `<crc32>-<bytes>`; the square of
  44 by 44 pixels of each row and of the panel of what plays. This seed replaces the last
  clause of seed 44's Required Behavior 6, "on one without, the row keeps the empty
  square"; the rest of it stands.
- Seed 49, merged: the order in which a row's preview is found, and the keys kept by the
  target's address and the storage in the store `keys`, database version 2.
- Seed 63, merged: the upload of ready-made files to the board or the card, into the
  folder being browsed, and its bounded preflight. Its rule was that a large or compressed
  file is never inflated on the phone, so such a file got no preview. This seed keeps the
  rule's purpose, bounded memory on the phone, and gives those files a preview.
- Seed 37, merged: the texts and the clocks the app's forms make and upload.
- Related, not needed: seed 73, an archive of animations, and seed 80, uploads of several
  ready-made files at once. Both send each animation through the same upload, and each
  one then gets its preview by this seed.

## Product Context

On 2026-11-06, after the spare board took its first uploads from the phone, the owner
said, in their words: "once an upload is taking place and completes, there is no preview
thumbnail animation in the Android app. What I think should be is that once an upload is
initiated from the phone itself creates in-place preview that is only stored on the phone
and not uploaded to the board, and would be used by the phone's playlist browser to
preview the specific animation."

The phone already makes previews of what it uploads (seed 44), but a preview reaches a row
only through the board's catalog, and the ready-made files the owner uploads mostly get
none. "What happens today" sets out why.

## Technical Constraints

- **What happens today.** Read at `master` 390f47b7 on 2026-11-06.
  - A row's square shows `previews.sourceOf(client.keyOf(animation) ??
    previews.keyByName(animation.file, animation.bytes))` (`app/www/screens/show.js:237`).
    - `keyOf` (`app/www/client.js:615-625`) gives a key only from the catalog of the
      row's storage: its pages read now, or the keys of an earlier read that the phone
      kept (seed 49). It gives it only when the key's size is the row's `bytes`.
    - `keyByName` (`app/www/previews.js:49-57`) looks a name and size up in the default
      catalog only.
    - The phone's own previews (`previews.js:19`, `sourceOf` at `:61-69`) are found by key
      alone.
  - The list carries no key (`docs/commands.md`, `list`). A storage without a catalog, or
    with one that is not `ok`, gets no line from a change (`docs/commands.md:661-667`).
    Two kinds of storage have none: a board that was only ever flashed, as the spare board
    on 2026-11-06, and a show folder that `pack` makes. There a row never gets a key, and
    the phone's preview of its upload is never shown. Seed 44's Required Behavior 6 said so
    in words: on a storage without an `ok` catalog the row keeps the empty square. An
    installation whose firmware refuses `catalog page` gives no key either. With a catalog,
    the upload changes its generation. The row shows the preview only after the next
    complete list has asked `catalog` again and the app has read the changed catalog's
    pages up to the one that names the file. Pages are the last of its requests.
  - No person has seen a preview made on the phone in a row of the board. Seed 44's check
    on a phone was ticked on the owner's word that the previews worked well, and those came
    from the board's catalog pages. The app's test of the phone's own previews,
    `tests/app/test_own_previews.py`, runs only against a show whose catalog was rebuilt
    first.
  - The preview of a converted animation, a text or a clock is made only after its upload
    has ended with success: `makeOwn` in `app/www/screens/storage.js:224`, and in
    `app/www/screens/author.js:334` and `:338`. A ready-made file's preview starts when the
    file is picked (`storage.js:145`, in `showMade`), but only when it is `previewSafe`. It
    is written to IndexedDB as soon as it is made, even if the file is never uploaded
    (`previews.js:253-259`).
  - `previewSafe` (`app/www/convert.js:25`) holds for every text or clock container. It
    holds for a frames file only when all of these hold:
    - it is not compressed;
    - the whole file is at most 65,536 bytes;
    - it has at most 256 frames;
    - `n`, the bytes of one picture (width times height, times 3 without a palette),
      times its frames is at most 262,144.

    Any other frames file gets a preview only when the default catalog holds its key. The
    reason is that `odrg.reader` inflates a compressed body whole
    (`converter/lib/odrg.js:113`, `inflated` at `:220-226`, with `inflateRaw` of
    `converter/lib/inflate.js`), and seed 63 asked for bounded work on the phone
    (`docs/android-app.md:593-598`). An uncompressed frames file of the full canvas, 3,600
    LEDs, is `previewSafe` only up to 72 frames with a palette, or 24 without, and only
    while it is at most 65,536 bytes. No compressed frames file is.
- **1. The preview starts with the upload.**
  - The making of the preview starts as soon as the operator starts any of these uploads:
    - `Upload to the installation` on Upload, of a converted video or GIF or of a
      ready-made file, to the board or to the card;
    - the upload, or the Save, of a text or a clock form;
    - every upload that goes through the same upload, as seeds 73 and 80 will.

    It is made from the exact bytes sent, a step at a time between the app's other work,
    beside the upload. A ready-made file still starts its preview when it is picked, as
    today, now for every file.
  - The phone makes one preview at a time, in the order the uploads started. A preview
    whose key the phone already holds, in its own catalog or in the default catalog, is
    not made again.
  - A preview, once made, is the phone's for this run at once, as `own` is today, so the
    form of a ready-made file shows it.
  - It is written to the phone's own catalog in IndexedDB only when an upload of those
    bytes has ended with success. An upload that is refused, fails or is cancelled writes
    nothing. The making of its preview stops unless another upload of the same bytes is
    still waiting for it. A preview already made by then stays for this run alone.
  - A ready-made file's making, started when it is picked, takes its place in the order
    then, as an upload's does. The form that holds the file waits for it as an upload does.
    Its making stops when the form lets the file go, because another file is picked, media
    are made or the form is forgotten, and no upload of those bytes waits for it. A
    refused, failed or cancelled upload of a file the form still holds does not stop it.
  - A file the maker refuses keeps no preview, as today, and nothing is said. Examples are a
    damaged body, and a file whose preview is still above 65,536 bytes at sixths.
- **2. The place of an upload, kept on the phone.**
  - When an upload ends with success, the app keeps, beside the key, the place it put the
    bytes:
    - the target's address the upload was sent to, as `target.js` keeps it. A change of
      target ends an upload under way as a failure (`client.begin`), and a failed upload
      keeps nothing;
    - the storage, internal or external;
    - the file's name as the list names it. That is a file of the board's own storage by
      its name, and a file of the card by its path from the card's folder `odrig`,
      including the folder being browsed (seed 63).
  - The place is the name, not the id. The board reuses the id of a removed animation, and
    the reply that ends an upload to the card may carry no id.
  - When an upload to a name ends with success, that name's key is taken out of the keys of
    that storage's last read, and of a read of it under way, for this run. Step 1 below
    then gives the row a key only from a page read after the success, and until then step
    2 finds the kept place. A Save of a text or a clock keeps its name and often its size,
    and without this the row would show the old bytes' preview until the pages are read.
  - The places are kept in `odrig-previews`, which goes to version 3 and gains a store
    `uploads`. The one open of `previews.js` goes to version 3, and its upgrade creates
    only the stores that are missing. A record is named `<address> <storage>`, as those of
    `keys` are, and holds the pairs of each file name and its key. A later upload to the
    same name replaces that name's key.
  - A web view without IndexedDB, or one that refuses the write, keeps the places for the
    run alone, and nothing is said.
- **3. The order in which a row's preview is found.**
  1. The key the board gives the row, from the read under way first, as today. Its
     preview comes from the default catalog, else from the phone's own.
  2. Else the key this phone kept for the row's place: this target's address, the row's
     storage and its `file`. It is taken only when that key's size is the row's `bytes`.
     Its preview comes from the default catalog or the phone's own.
  3. Else the default catalog, by the file's name and size (seed 49).
  4. Else none: the square stays the empty dark square of seed 44.

  - A key found at step 1 or step 2 decides. When neither the default catalog nor the
    phone's own has its preview, the square stays empty, and the later steps are not
    tried. So a kept place whose preview was never made, because the maker refused it or
    the app ended before the making did, keeps the empty square. Nothing makes it again,
    since the bytes are gone.
  - Step 2 comes before step 3 because the kept place names what this phone put there. A
    key the board gives later decides, as step 1 says.
  - The panel of what plays finds its preview in the same order.
  - A row whose size is not read yet (`bytes` null) takes no kept place.
- **4. A ready-made file of any size.**
  - The converter's library gains a reader of a raw DEFLATE stream. It takes its input in
    parts, is told when the input has ended, and gives its output a part at a time, with a
    window of 32,768 bytes. Its verdicts on a damaged stream are those of `inflateRaw`,
    reason and detail. `truncated` comes only after the end of the input is told, and the
    output it gave before a verdict is a prefix of what zlib gives of that input. It
    reports `held`, the bytes of output it holds.
  - The preview maker reads the frame records of an ODRG file, and of an ODRGX container
    of frames, from that stream, in two passes instead of inflating the body whole.
    - The first pass inflates the whole stream, keeping only the window and the record
      start being read. It gives the stream's verdicts, `bad-deflate`, `truncated` and the
      `trailing-bytes` after the stream, before any record is judged. It also sums the
      durations of the record starts for the loop, stopping where `loopMs` stops today.
      An ODRGX container of frames gives its loop in its header, and its first pass only
      checks the stream.
    - The second pass reads the palette and the records, and takes the pictures.

    Every verdict and its order therefore stay as `docs/reasons.md` gives them, and the
    maker's refusals stay those of the reader. `odrg.reader`, `odrg.decode`,
    `odrgx.decode`, `check` and every other user of the library keep inflating whole,
    unchanged.
  - Besides the file's bytes, which the upload holds anyway, the preview maker then holds
    at most the window, the inflate state, one frame's buffer and picture, and its 24
    pictures, whatever the inflated body's size. It reads every record to the end of the
    body and makes the checks after the last record, as today.
  - A step of either pass reads at most 256 records, as `RECORDS_A_STEP` already holds,
    and, new, at most 1,048,576 bytes of inflated body. The first step no longer inflates
    the body or sums the durations at once: it reads the header only. An uncompressed
    body is read in place, in the same two passes and the same steps.
  - `previewSafe` no longer limits previews. The preflight stays as seed 63 made it.
  - The same animation, compressed or not, gives the same preview, byte for byte.
  - The form of a ready-made file names where its preview comes from. Under a preview of
    the default catalog the note keeps its sentence, `Preview from the animation catalog.
    The original animation bytes are kept.` Under one this phone made it says `Preview
    made on this phone. The original animation bytes are kept.` Today the first sentence
    stands under both.
- **5. What a kept place is not.**
  - A place is dropped when a complete list of the level that holds the file names no
    file of that storage at that name. The list must have been asked from its first part
    after the upload that kept the place ended. That is the root's list for a file of the
    board's own storage or at the card's root, and the folder's list for a file in a
    folder of the card. A place under a folder whose list is not read again stays until a
    later upload or a deletion by this app at its name replaces or drops it; the row's
    size check guards it meanwhile.
  - A place is also dropped when this app deletes the file, and replaced by a later upload
    to the same name. The GIFs stay by key, since the phone's catalog has no other limit,
    as today.
  - Two boards that answer at one address share their places, as the spare board and the
    installation both do at `4.3.2.1` on their own networks (`docs/wifi.md`). A complete
    list of one drops the places of the files it does not name, the other board's too. A
    row of one may show this phone's preview of a file of the other with the same name and
    size, until a board key is read. Telling two boards apart needs an identity that no
    reply gives, and that would be a new command: it is not this seed's.
  - Another phone does not see the preview, and neither does the Controller view or
    `app.py serve` in another browser. They show what their own catalog or the default
    catalog has for the board's key, as today: each phone has its own.
  - Another controller may replace a file with one of the same name and size. This phone
    then shows its own preview until the board's key is read, as a name and size in the
    default catalog already may (`docs/android-app.md` says so).
- **What stays.**
  - The board, the firmware, the core and the emulator, every command and every reply.
    Nothing is sent for a preview.
  - `thumbnails/` and `catalog.js`, and the keys kept by seed 49.
  - The square's look, and the black square of a missing preview.
  - Seed 63's preflight, and the form's sentence for a preview that is not known yet.
  - A tap on the square, which plays.
- **The pages.**
  - `docs/android-app.md`:
    - "The phone's own previews": made as the upload starts, written on success, and the
      place kept;
    - the order of a row's preview (`:86-91` and `:769-772`);
    - the ready-made section's sentence that a compressed body is never inflated for a
      preview (`:593-598`);
    - a step of "The check on a phone", and a bullet of "What is open".
  - `docs/converter.md`: the library's DEFLATE stream, and that the preview maker reads a
    compressed body from it in two passes. `docs/reasons.md` is unchanged.
  - `docs/drifts.md`: an entry at its end, "Seed 79: ...", with the measurement.
- **Tests.**
  - In the converter's suite:
    - The stream reader against `inflateRaw`, on the library's DEFLATE vectors and on the
      compressed ODRG files of the tests' vectors, fed in parts of 1, 7 and 4,096 bytes.
      It must give the same output, and the same reason and detail.
    - Every invalid vector gets the same reason and detail from the maker as from
      `decode`, as before.
    - The maker's GIF of a compressed file equals that of its uncompressed twin.
    - On a file whose body inflates to more than 16 MB, the reader's `held` never exceeds
      32,768 bytes plus one record of `n` + 5 bytes.
    - `thumbnails/` made again by `thumbnail --catalog` is unchanged.
  - In `tests/app`, with the fake targets the suite has, and the emulator with a show folder
    that `pack` makes, which has no catalog:
    - An upload to a board's storage whose catalog is `none` shows its preview in its row
      after success, with no `catalog page` asked.
    - So does one to a target that refuses `catalog page`.
    - An upload to the card shows its preview before the changed catalog's pages are read.
    - The preview of a slow upload is made before the upload ends, and is written only
      after success.
    - A refused, a failed and a cancelled upload keep no place and write nothing.
    - A Save of a clock, whose size does not change, shows its new preview in its row on a
      storage whose catalog is `ok`, before the changed catalog's pages are read.
    - A list whose parts began before the upload ended does not drop its place.
    - After a restart of the app, the kept place shows the preview.
    - A complete list without the file drops its place.
    - A board key that differs from the kept one decides.
    - A row whose size differs from the kept key's takes none.
    - A ready-made compressed file gets its preview.
    - A version 1 and a version 2 database each go to version 3 with their records kept.
    - A web view without IndexedDB keeps the places for the run.

    The suite's existing tests of the previews keep passing. They change only where they
    pinned a preview made after success alone, `previewSafe` limiting the previews, or the
    database at version 2.
- **Where it lands.** A branch from `master`, as a pull request of its own.

## Required Behavior

1. An upload started from the phone starts making the preview of its bytes at once. The
   preview is written to the phone's own catalog only when the upload has ended with
   success.
2. After an upload has ended with success, the row of the uploaded file and the panel of
   what plays show its preview as soon as it is made. This holds on a storage with a
   catalog or without one, with no catalog page waited for.
3. The phone keeps where it uploaded each file. At the next start the row still shows the
   preview, once it was made. A file that leaves the list leaves its place.
4. A key the board gives a row, from a page read after this phone's last upload to it,
   decides its preview.
5. Every ready-made file the app accepts gets a preview, whatever its size and
   compression, with the phone's memory bounded as point 4 says, unless the maker refuses
   it as it refuses a file today: a damaged body, or a preview still above 65,536 bytes
   at sixths.
6. The preview never leaves the phone. No command, reply or byte of the board changes.

## Definition Of Done

1. The converter's suite, the app's suite and the onboarding suite pass, with the tests
   above.
2. Measured in Chrome against the emulator: the time from the press of `Upload to the
   installation` to the preview in the row, for a converted GIF and for two compressed 60 x
   60 ready-made files whose keys the default catalog does not hold, both put on the Drive
   under `odrig archive/seed-79/`:
   - a large one, of at least 16 MB, made from `collection/card/space/space-scan-10x.odrg`
     by the converter's library without its last frame record;
   - a small one, of at most 4 MB, made by the converter's library from the first records
     of the same file, compressed, so that it fits the spare board's storage of 5.1 MB.

   The drift names each file, its size, its key and its times.
3. The APK is built from the branch.
4. The owner's check, on a phone with that APK, against the spare board, whose storage has
   no catalog, and against the installation with its card, finishing each before going to
   the other:
   - upload a converted GIF, a compressed ready-made animation of `odrig archive/seed-79/`
     whose preview the default catalog does not hold, and a text: the small file to the
     spare's storage, and the large one to the installation's card;
   - each row shows its moving preview within seconds after the upload's success message
     (`Uploaded as animation ...`, `Uploaded to the card ...` or `Uploaded <file> to the
     card.`), and so does the panel of what plays when it plays;
   - after the app is closed and opened again, the previews are still there;
   - after one is deleted, no preview stays at its name for a new file of another size.

## Open Questions

None. The owner described what is wanted. Decided here:

- the preview starts with the upload, and is written to the phone only on success;
- one preview is made at a time, in upload order;
- the place is kept by target address, storage and the list's name, never the id, in a
  store `uploads` at database version 3, and two boards at one address share places;
- a name just uploaded loses its old read key for the run, and a key found decides;
- places are dropped by a complete list of the file's level asked after the upload;
- seed 44's Required Behavior 6 and the outcome of seed 63's requirement 1.3 are replaced,
  and no decision of `docs/decisions.md` changes: the previews stay named by their key and
  kept in the phone's IndexedDB;
- the form of a ready-made file names where its preview comes from;
- the kept place is looked up after the board's key and before the default catalog's
  name and size;
- a compressed or large ready-made file is previewed through a DEFLATE stream in two
  passes with bounded memory, every reason unchanged, and `previewSafe` no longer limits
  previews;
- another phone sees nothing of it;
- no command, reply or firmware change, and a pull request of its own from `master`.
