# Design: previews at once, each as soon as it is known

## What this design relies on

- `app/www/client.js`, as seed 44 left it: `state.keys` of each storage, `{generation,
  entries, byName}` or null, and `state.keysVersion`; `reads`, the reads under way, the
  board's before the card's, each `{storage, generation, entries, pageGeneration, page,
  offset, tail, byName}`; `noteCatalog(reply)`, which starts a read of a storage that is
  `ok` with another generation or number of entries than its keys; `askPage()`, which
  parses each reply's whole lines into `read.byName` and sets `state.keys` after the last
  part of page 15; `keyOf(animation)`; `dropKeys()`, called by `heard()` after a silence
  and by `begin()` for another address; and `changed()`, which tells the watchers, the
  screens among them, after every reply.
- `app/www/previews.js`: `defaults`, imported from `./thumbnails/catalog.js`, each key
  with `{gif, names}`; `sourceOf(key)`; `start(factory)`, which opens IndexedDB
  `odrig-previews` at version 1 with its store `previews`, keeps the connection in
  `database`, and takes the phone's own previews; `makeOwn(bytes)`; `show(square,
  source)`.
- `app/www/screens/show.js`: `rowsState()` and `drawNow()` set each square with
  `previews.sourceOf(client.keyOf(animation))`, or null for a row with a `fault`; the
  screen draws on every change of the client and of the phone's own previews.
- `app/www/main.js` starts `previews` before it calls `client.begin()`.
- `app/www/target.js`: `address()`, the address in use, `host` or `host:port`, as the app
  keeps it.
- The app's suite: `tests/app/support.py`, whose `run()` starts Chrome with a profile of
  its own, so that every run starts with an empty IndexedDB, and serves the web code with
  `app/apptool/webserver.py`, the default catalog from `thumbnails/`; the stand-in targets
  of `StandIn`; `tests/app/test_keys.py` and its stand-in `Paged`, whose pages it gives a
  number of bytes at a time; the scenario `keys.js`, which follows a plan of steps; the
  driver's `app.reload()`, which loads the app again in the same profile.

## A preview by name and size

`app/www/previews.js`:

- `named`, a `Map` made once when the module is loaded: for each key of `defaults` and
  each of its `names`, the name to the list of its keys.
- `keyByName(file, bytes)`: null when `file` is not a string or `bytes` not a number.
  Otherwise the keys of `named.get(file)` that end in `-${bytes}`; when `named` does not
  hold `file` and `file` holds a `/`, those of the part after its last `/`. Exactly one
  gives that key, any other number null.

`app/www/screens/show.js`:

- `previewOf(animation)`: null for a row with a `fault`; otherwise
  `previews.sourceOf(client.keyOf(animation) ?? previews.keyByName(animation.file,
  animation.bytes))`.
- `rowsState()` and `drawNow()` set their squares with `previewOf`. Nothing else of the
  screen changes: a row's image is made, changed or taken out only when its source
  differs, as before.

## The keys of a read

`app/www/client.js`:

- `askPage()`: when a reply's whole lines have added at least one name to `read.byName`,
  `state.keysVersion` grows, so that the screens draw again after the reply. `state.keys`
  is still set only after the last part of page 15.
- `keyOf(animation)`: the read under way of the row's storage, if any, gives the name's
  key first, then `state.keys` of the storage; the key counts only when it ends in
  `-${animation.bytes}`. A read that has not reached its first page yet has an empty
  `byName` and gives nothing.
- What already holds stays: a read that starts again makes its `byName` anew, a read that
  ends without keys leaves `reads`, and `dropKeys()` empties `reads`, so that no line of
  an old read gives a key.

## The keys kept on the phone

`app/www/previews.js`:

- `VERSION = 2`; `opened(factory)` opens `odrig-previews` at that version, and its
  `onupgradeneeded` creates each of the stores `previews` and `keys` that the database
  does not hold. A database at version 1 keeps its store `previews` and gains `keys`.
- `kept`, a `Map` from `${address} ${storage}` to `{generation, entries, byName}`. In the
  store `keys`, a record has the same key and the value `{generation, entries, names}`,
  `names` the pairs of `byName`.
- `start()`: one transaction over both stores; the phone's own previews are taken as
  before, then every record of `keys` goes into `kept`, but for a key `kept` holds
  already, which a `keep` of this run wrote. A record of another shape is skipped. It
  resolves when this is done or has failed, and also, without the database, when the open
  is `blocked`. The connection closes, and `database` becomes null, on `versionchange`.
- `keeper`, the object `client.js` is given:
  - `kept(address, storage)`: the record, or null;
  - `keep(address, storage, keys)`: into `kept`, then into the store when `database` is
    open; a write that throws or fails changes nothing else;
  - `forget(address, storage)`: out of `kept` and out of the store, the same way.

`app/www/client.js`:

- `keeper`, at first one that keeps nothing, and `keepKeysIn(given)`, which replaces it.
  `keptUnder`, the address `begin()` read from `target.address()`, under which keys are
  kept and looked up.
- `noteCatalog(reply)`, for each storage:
  - shown `damaged`, `incompatible` or `none`: `keeper.forget(keptUnder, storage)`,
    besides what it does now; `loading` and `absent` do only what they do now;
    - shown `ok`, when `state.keys[storage]` is not of that generation and number of
      entries and `keeper.kept(keptUnder, storage)` is: it becomes the keys, `keysVersion`
      grows, and the read of that storage, if one is under way, leaves `reads`; otherwise
      as now, `pagesRefused` and the test of the read under way included.
- `askPage()`, after the last part of page 15: `keeper.keep(keptUnder, storage,
  state.keys[storage])`.
- `keptKeysReady()`: sets `keptTaken`, false until it is first called and never set back;
  each read in `reads` whose storage has a record of the read's generation and number of
  entries takes the record as its keys and leaves `reads`; then `changed()` and `next()`.
  `due()` gives `askPage` only while `keptTaken` is true, so that no page is asked before
  the kept keys are known.

`app/www/main.js`: `client.keepKeysIn(previews.keeper)` before `previews.start()`, and
`previews.start().then(() => client.keptKeysReady())`.

## The square

No change. `.thumb` keeps its black fill, and `show(square, source)` its rule; a row's
square takes its preview on the first draw after its key is known, by name and size, by a
reply or by the kept keys.

## Tests

- `tests/app/support.py`: `run(..., thumbnails=None)`; a folder given there is served
  under `/thumbnails/` in place of `thumbnails/`, its `catalog.js` and its GIFs, by
  `_Pages`.
- `tests/app/page/scenarios/keys.js`: its snapshot gains each row's file, the source of
  its square's image and the square's background colour; its plan gains `{"until":
  "rows"}`, rows drawn, `{"until": "some-keys"}`, a row with a key while the storage has
  no keys, and `{"reload": true}`, the app loaded again and its client taken again from
  the new frame.
- `tests/app/test_previews.py`:
  - rows named as files of the default catalog, with their sizes, show those previews
    while every `catalog page` is refused with `busy`, by `Paged.busy_always` of
    `test_keys.py`; a row of another size and an unknown one show none;
  - from a made-up catalog: a name of two keys of the row's size and a name of another
    size show none; a card row `night/deep.odrg` shows the key of `deep.odrg`; once the
    pages give a row another key, its square shows that key's preview or none; a square
    without a preview is black;
  - the show without a catalog shows by name and size the previews of its two files the
    default catalog knows before Settings' rebuild, and after it too.
- `tests/app/test_keys.py`:
  - with pages answered slowly, rows have their keys while the storage has none yet, the
    first page's names before the last page is asked;
  - with a made-up catalog holding some of the target's keys under other names, at
    `some-keys` those rows' squares have their image and the others none, on a black
    background;
  - after a reload of the app the keys come from the phone, with `catalog` sent and no
    `catalog page`; after a change of the generation before the reload, the pages are read
    and the kept keys replaced, and a second reload reads none;
  - `loading` and `absent` keep the kept keys, `damaged` forgets them;
  - another address does not take the keys of the first one;
  - the existing tests keep passing; the silence test now finds the keys back with no page
    read after the silence.
- `tests/app/page/scenarios/ownpreviews.js`: its helpers open `odrig-previews` without a
  version, at the one the database has.

## Pages and records

- `docs/android-app.md`: the square's sentence, "The keys of the animations" and its
  sentence on a show that `pack` makes, as the requirements say.
- `docs/drifts.md`, at its end, under "Seed 49": the lines of each reply used at once,
  finer than the page of the seed; the shape and the key of a kept record; the kept keys
  that come after a read has started; the test's own default catalog; the owner's words of
  2026-10-28 that the APK waits; and the measurement before and after, with the round trip
  to the board when it was measured.
- `project-seeds/49-p1-previews-at-once/state.json`: `in_progress` from task 1.
