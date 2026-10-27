# Previews of the animations in the app

## Summary

Every animation the installation has ever been given gets a short miniature preview, a
small looping GIF made from the animation's own frames, kept in the repository in a
catalog of its own, the default preview catalog. The previews are named by the
animation's checksum, the CRC-32 and the size of its file, which the catalogs of the
board's storage and of the card already keep for every file. The operators' app, in the
APK, the browser and the emulator's Controller view, shows each animation's preview
beside its name; it learns the checksums from the board's catalogs through one new
command, and finds the preview in the default catalog that comes with the app. The board
and the firmware never hold, send or read a preview. An animation the default catalog
does not know has no preview, unless this phone uploaded it: the app then makes the
preview itself and keeps it on the phone, in the phone's own catalog of previews.

## Priority

- `P2`

## Depends On

- Seed 35, for the catalogs of the board's storage and of the card, whose every line
  keeps the file's CRC-32 and size, `python3 -m odrig.catalog` and `fw.py install-show`
  that write them on a computer, and `catalog` that reports their state.
- Seed 36, for the Animations tab and its rows, and seed 41, for the folder explorer
  whose levels list the rows and for the paths of a card's files.
- Seed 37, for texts and clocks, drawn by the converter's library at any time.
- The converter, `converter/`, the one tool that converts, whose library runs alike in
  Node.js and in the app's web view.

## Product Context

On 2026-10-27 the owner, having looked through a presentation of every conversion with a
preview of each, asked for previews in the app itself. The owner's words: the
pre-scanned catalog should keep a checksum of all the animations; a tracked file maps
checksums to animation preview thumbnail GIFs, available only to the emulator and the
APK app; the firmware and the board never transmit those to the app, they are
pre-cached by the git repository; any uncached animation simply has no preview, unless
it was uploaded by the phone, the APK, the app itself, in which case it updates the
phone's personal hash-to-preview; all animations' short miniature previews are kept
tracked in the repository in a special, different catalog that is invisible to the
firmware and tracked only in git, the default preview catalog; and the sources for the
animations are all the paths where animations are known to live.

An operator scrolling a card of two hundred animations reads file names like
`science-in--de0d1ywfhak_fit.odrg`. A preview tells them apart at a glance.

## Technical Constraints

- **The checksum.** An animation is known by its key: the CRC-32 of its whole file, as
  eight lowercase hexadecimal digits, a dash, and its size in bytes, for example
  `1a2b3c4d-52340`. The CRC-32 is the one of zlib and PNG that the catalogs already keep,
  and the size is the catalog line's too, so the key is in every catalog line of today and
  the catalog's format does not change. Two files of the same bytes are one animation and
  share one preview. A storage without a catalog that is `ok`, and a file of it without an
  entry, have no key, and so no preview. The installation's storages are cataloged on a
  computer before they are used: the board's own by `fw.py install-show`, the card by
  `python3 -m odrig.catalog <card> import`. A show folder that `pack` makes for the
  emulator has no catalog; Settings' rebuild, `catalog rebuild internal`, makes one, after
  which its rows have keys.
- **The command.** The core keeps no checksum in memory and has only some hundreds of
  bytes left with a drive, so no reply member can carry one. The app reads the catalogs
  themselves, page by page, with one new command, `catalog page <storage> <page>
  <offset>`, `<storage>` being `internal` or `external`, `<page>` 0 to 15 and `<offset>` 0
  to 4,294,967,295, as `read` takes an offset, else `bad-argument`. Its reply is
  `{"ok":true,"generation":<n>,"text":"<up to 512 bytes of the page from the
  offset>","next":<offset or null>}`, `next` being the offset plus the bytes given when
  the text is not empty and `null` only with an empty text, `<n>` the storage's generation
  as a number, as `catalog` gives it, or `null` when its catalog is not `ok`. The bytes
  are read into the chunk buffer through the host's `read_at`, as `read` reads a file, so
  the command asks for no memory and takes one host read a call; a host whose storage
  cannot be changed answers `storage-error`, as `read` does. An offset at or after the
  page's end, a page that cannot be read, as a page without entries has no file, and a
  storage whose catalog is not `ok` answer `"text":""` and `"next":null`. It is refused
  with `busy` while a rebuild of that storage runs, the one `catalog` names in `rebuild`;
  nothing else makes it `busy`, an open upload included, since every other change of a
  catalog is made whole within the command that makes it. A change whose finishing a
  failed call left is not looked for: the storage's pages are answered as they are until
  its next change, or the next start, finishes it. The command tool `odrigctl` takes it as
  `catalog page internal|external PAGE OFFSET`. This is the one addition to the command
  list; the owner gives it by accepting this seed.
- **When the app reads the pages.** The app asks `catalog` when the target first answers
  and after every complete `list`. It reads a storage's sixteen pages, one request at a
  time after the operator's own, when `catalog` shows the storage `ok` and the app has no
  read of it, or only one of another generation or number of entries, and keeps the keys,
  by the file's name, a card file's by its path from `odrig`, for that target. The keys of
  a read stand until the next read of that storage has ended, so that a row keeps its
  preview while its storage is read again after an upload or a removal; they are dropped
  at once only when `catalog` shows the storage in another state than `ok`, when the
  target answers again after a silence, and when the target changes. A generation alone
  names no catalog: every first `import` of a card writes 1, and so does `fw.py
  install-show` on a board without a catalog it can read. A page that answers another
  generation than the first page of the same read starts the read again, and one refused
  with `busy` is asked again two seconds later. A row takes the key of its storage and
  name only when the key's size is the row's `bytes`. A target that answers any `catalog
  page`, of either storage, with `bad-argument` (the app never sends an argument out of
  range), or `catalog` with `unknown-command` or `bad-argument`, is one from before this
  seed: its rows have no preview, nothing is said, and the app asks it for no page again
  until the target changes. A page whose generation is `null` ends the read without keys,
  and the storage then counts as unread; any other refusal but `busy` ends it the same
  way, and nothing is said. A target that answers `catalog` with `unknown-command` or
  `bad-argument` is asked no `catalog` again until the target changes, neither for the
  previews nor by Settings: Settings uses that same answer and says `This installation's
  software keeps no catalogs.` without asking, so such a target is still asked `catalog`
  once, as today. A target that answers `catalog` but refuses `catalog page` is asked
  `catalog` only on Settings' occasions. The app's table of command lines gains these
  occasions of `catalog` and the line `catalog page`: one line more than the table holds
  then, thirty-three when no seed between has added one.
- **The preview.** A GIF89a that loops forever, of the animation's own canvas, 60 by 60 on
  the installation, the top row first. It holds 24 pictures taken evenly over the
  animation's first loop, picture `k` being the one on screen at `k` twenty-fourths of the
  loop, each shown for a twenty-fourth of the loop rounded to 10 ms, at least 20 ms and at
  most 120 ms: an animation of up to three seconds plays at its own speed, a longer one as
  a summary of about three seconds, a group of 15 minutes included. A text or a clock is
  drawn by the library at the same times over its pass or its seconds, a clock with the
  seed 1. The palette is every colour of the pictures when they hold at most 256;
  otherwise the 256 colours that cover the most pixels over all the pictures, a tie going
  to the smaller colour read as one number of 24 bits, red highest. Each pixel takes the
  palette colour nearest it by the sum of the squares of the differences of red, green and
  blue, a tie going to the lower index, without dithering; the palette is sorted by that
  number and filled with black to the next power of two, at least 2. A preview above
  65,536 bytes is written again with 12 pictures at twelfths, each at most 240 ms, and one
  still above with 6 at sixths, each at most 480 ms; one above even then gets no preview,
  and is named. The same file gives the same bytes in Node.js and in a web view.
- **The converter makes previews.** The library gains a module that walks the records of
  an ODRG file or an ODRGX container with the readers the library's `odrg.decode` and its
  reader of ODRGX containers use, refusing what they refuse, keeping only the pixel buffer
  and the sampled pictures, chooses the palette and writes the GIF: the library's own
  code, with no package, as its DEFLATE compressor is. The command line gains a sixth
  subcommand, `node converter/odrig.js thumbnail FILE... --catalog DIR [--card ODRIG]`,
  which adds the preview of each file to the preview catalog in `DIR`, a key it already
  holds gaining only the file's name, and `node converter/odrig.js thumbnail FILE --out
  OUT.gif` for one file; `--out` takes exactly one FILE and is not given with `--catalog`,
  else status 2; it runs no separate check. `--card` names a card's folder `odrig`; like
  every option of the tool, given twice it takes its last value. `thumbnail` writes
  nothing on standard output. With `--catalog` it goes through every file: each file it
  passes over is named on standard error by one line `passed over: <FILE>: <reason>:
  <detail>`, and the run ends with status 0 once the mapping is written; the table of
  statuses of `docs/converter.md` says so. With `--out`, a file the reader refuses ends
  with status 1 and the reader's reason, and no file is written. A preview still above
  65,536 bytes at 6 pictures has the new reason `preview-too-large`, listed in
  `docs/reasons.md`: status 1 with `--out`, a passed-over line with `--catalog`. The key's
  CRC-32 is computed by the library's own code, and the subcommand reads and writes
  `thumbnails/catalog.js` as text and never imports it, so Node.js 20 runs it. In the app
  the module is reached through `convert.js`, which stays the one script that imports the
  library.
- **The default preview catalog.** A folder at the top of the repository, `thumbnails/`,
  tracked in git and nowhere else: `thumbnails/<key>.gif` for each preview, and
  `thumbnails/catalog.js`, the mapping, written by the `thumbnail` subcommand only:
  `export default {`, then one line for each key in the order of its bytes, `
  "1a2b3c4d-52340": {"gif": "1a2b3c4d-52340.gif", "names": ["foo.odrg"]},`, then `};`,
  plain ASCII. A name is, for a FILE inside the folder `--card` names, its path from that
  folder, its parts joined by `/`, as a card's file is named in its catalog; for every
  other FILE its own file name; each once, in the order of their bytes: never a folder of
  the computer, a mount point or an account. The subcommand never guesses a card from a
  folder's name or contents. The names are for people: the app finds a preview by its key
  alone. The firmware's build, `pack`, `fw.py install-show`, the card's catalog and every
  lister of the board never read the folder: it is in no show and on no storage. The first
  catalog is some 400 previews of 25 to 36 KB each, 10 to 13 MB: the repository's pack
  grows from 14 MiB to about 25 MiB and the APK from 4.3 MB to about 15 to 17 MB.
- **The sources of the first default catalog.** The animation files of the first computer
  in the places listed here, read where they live and never copied or changed there: in
  the owner's checkout `/Users/koren/src/odrig`, `scratch/all-card-local/odrig` with its
  folders, the show folders of `scratch/new-animations/`, `scratch/seed-41-card/odrig`,
  `scratch/board-2026-10-25`, and `build/` with its folders, among them
  `build/owner-show-full`, `build/owner-show` and the demo show `build/demo-20/show` that
  `agent/getting-started.md` packs; the mirror of Google Drive, `My
  Drive/artifacts/odrig/animations`; the share `/Volumes/192.168.0.1/artifacts/odrig/`,
  its root and `animations/new animations/` with its sub-folders; and of the repository,
  `test-animations/` and the valid vectors of `tests/vectors/`. The two card copies are
  each given in a run of their own, with `--card scratch/all-card-local/odrig` and with
  `--card scratch/seed-41-card/odrig`; every other source, the share's and the Drive's
  sub-folders, `build/` and the checkout's other folders included, is given without
  `--card`. The invalid vectors and every file the reader refuses are passed over and
  named. When the share is not mounted while the catalog is made, it is made from the
  rest, and the report says in words that the share's files are not in it yet; the same
  subcommand adds them in a commit of their own when it is mounted next. A later
  conversion adds its previews the same way, in the commit that records it.
- **The app shows them.** The default catalog reaches the app in each of its hosts as the
  converter's library does: the emulator and `app.py serve` serve `thumbnails/` beside the
  app, `.gif` among the types they serve, and the APK's build copies it into the APK,
  which holds the web code, the library and `thumbnails/` byte for byte. Besides
  `converter/<file>`, the web code imports one file from outside `app/www`,
  `thumbnails/catalog.js`, and it shows a preview with an image element whose source is
  the GIF's path, so that it fetches nothing itself. Each animation row of the Animations
  tab, at every level of the explorer, has a square of 44 by 44 pixels as the first part
  of its Play button, before the name, so that a tap on it plays as the name does, the
  selection checkbox staying first: the preview drawn with `image-rendering: pixelated`
  and not draggable, as the Upload screen's preview is, its pixels kept square, scaled to
  fit in its own ratio, a 60-by-6 strip as a band across the middle; or an empty dark
  square when the animation has none or the row has a `fault`. At 320 px a row in
  selection mode keeps its Play button at least 44 px wide: its `Ignored` or `Saving` note
  stands under the name inside Play. The now-playing panel shows the preview of the
  animation on the LEDs before its words, the same way, hidden while `status` names no
  animation, while a test shows and while the list does not hold the animation yet. Folder
  rows and the Tests group have none.
- **The phone's own previews.** When the app has uploaded an animation, from the Upload
  screen or from the form of a text or a clock, a new one or an edited one, after `upload
  end` succeeded and its message is shown, it makes the preview of the bytes it sent with
  the converter's library, in steps that leave the screen answering, and keeps it on the
  phone in the web view's IndexedDB, in the phone's own catalog of previews, keyed by the
  CRC-32 the upload computed and the size; the row keeps the empty square until it is
  made. The app looks a key up in the default catalog first and in the phone's own after,
  and at its start drops each phone preview whose key the default catalog has; the phone's
  catalog has no other limit. It never leaves the phone, each phone has its own, and the
  emulator's Controller view and `app.py serve` have the one of the browser they run in.
  When the web view has no IndexedDB or refuses a write, the preview is kept for the run
  only and nothing is said. No plugin is added to the APK.
- **What stays.** The catalogs' format, the board's memory, every other command, and every
  reply; the board never holds a GIF. The emulator's own page shows no preview; it serves
  them to the app. The decision that the JSON source of every animation is committed
  stays: a preview is no source and stands in for none.

## Required Behavior

1. `node converter/odrig.js thumbnail FILE --out OUT.gif` writes the preview of an ODRG
   file or an ODRGX container as the constraints say; the same file always gives the same
   bytes, in Node.js and in a web page.
2. `node converter/odrig.js thumbnail FILE... --catalog thumbnails` adds each file's
   preview under its key and its name as the constraints say to the mapping; a key it
   holds keeps its GIF and gains the name; a file the reader refuses or that has no
   preview within the size rule is passed over and named.
3. `thumbnails/` holds the default preview catalog made from every source the constraints
   list, one GIF per distinct key, and `thumbnails/catalog.js` maps every key to its GIF
   and every GIF has its key.
4. `catalog page <storage> <page> <offset>` answers the lines of a page of the board's own
   catalog or the card's, 512 bytes at a time with the next offset, alike on the board, in
   the emulator and through `odrigctl`.
5. The app asks `catalog` and reads the pages as the constraints say, matches each row to
   its key, and shows each row's preview or an empty square, and the preview of the
   animation on the LEDs in the now-playing panel; a target from before this seed shows no
   preview and is asked for no page.
6. After an upload from the phone to a storage whose catalog is `ok`, the uploaded
   animation's row shows the preview the app made, and so it does after the app restarts;
   on one without, the row keeps the empty square and the phone still keeps the preview.
7. The emulator, `app.py serve` and the APK hold the same default catalog; the board, the
   firmware's build and the card hold none of it.
8. The pages of the project describe it: `docs/converter.md` the subcommand and the
   module, `docs/commands.md` the command, `docs/catalog.md` the key, `docs/core.md` the
   command: in its rules for hosts, that `read` and `catalog page` are the commands whose
   `read_at` begins at the offset it is given, and in its catalogs, that `catalog page`
   reads one page of the board's catalog, or of the card's through `drive/`, into the
   chunk buffer with one `read_at` a call, asks for no memory, and is `busy` while a
   rebuild of that storage runs, `docs/reasons.md` the reason `preview-too-large`,
   `docs/android-app.md` the previews, the phone's catalog and its table of lines,
   `docs/emulator.md` what it serves and the command tool's new form,
   `agent/vocabulary.md` the preview, the GIF of `thumbnails/` beside a row, told apart
   from the moving preview of the form of a text or a clock and from `python -m preview`,
   `agent/animation-guide.md` a row of its table of where things go, the preview in
   `thumbnails/`, committed, written by the `thumbnail` subcommand in the commit of the
   animation's source, `docs/decisions.md` a GIF's second role in the table of formats and
   a dated entry of its change log, and `docs/drifts.md`, at its end, that the tracked
   previews are the media the repository holds besides the images it held.

## Definition Of Done

1. All test suites that need no board and no phone pass. The converter's suite checks the
   preview of frames, of a text and of a clock, the walk of a long file without keeping
   every picture, the palette, the size rule's steps, the same bytes in Chrome as in
   Node.js, the mapping's shape and its folder, and that the only GIF, MP4 or MOV files
   tracked are `thumbnails/*.gif`. The core's suite checks `catalog page` on both
   storages, its offsets, its empty answers, its refusals and that it asks for no memory.
   The emulator's suite checks the served folder, the command and the command tool's form.
   The app's suite checks, in Chrome against the emulator on a show and a drive with
   catalogs and on one without, the rows with and without a preview at every level of the
   explorer, a faulty row, folder rows and the Tests group without a square, the
   now-playing panel, the pages read again after an install, a card put back and a change,
   a target from before this seed, an upload's preview, and that of a text saved from its
   form, kept on the phone across a reload, and a row in selection mode at 320 px. The
   APK's suite checks that the APK holds `thumbnails/` as the repository does.
2. The default catalog is made from every source the constraints list, and the report
   gives the number of previews, their total size, the APK's size, and the sources that
   were not at hand.
3. The firmware is built, and in a session with the owner it is flashed, `odrigctl catalog
   page external 0 0` is compared with the card's `catalog-00.txt`, and the owner sees the
   previews on a phone with the APK against the board, and the preview of an animation
   uploaded from the phone.

## Open Questions

None. The owner asked for this seed at once; the decisions it needed are taken in the
constraints: the key as the catalogs' CRC-32 and size, so that no catalog changes; one
command that reads the catalogs' pages, since the core has no memory for a checksum
member; when the app reads them, and what makes it read them again, since a generation
names no catalog; a GIF of 24 pictures over the first loop at the canvas's size, its
palette rule and its size steps; the converter's library as the one maker of previews,
on the computer and on the phone; `thumbnails/` as the default catalog's folder, served
and packed as the converter's library is, and its mapping's shape; the square at the
start of each row's Play button; IndexedDB for the phone's own catalog, the default
catalog before it.

## The Owner's Answers

On 2026-10-27 the owner asked for the pre-scanned catalog to keep a checksum of all the
animations, for a tracked file mapping checksums to preview GIFs that only the emulator
and the APK app have and the board never transmits, pre-cached by the repository, an
uncached animation having no preview unless the phone uploaded it, which updates the
phone's own hash-to-preview, and for all the animations' short previews to be tracked in
the repository in a catalog of their own that the firmware does not see, the default
preview catalog, made from every path where the animations live. The owner's acceptance of
this seed is the owner's word on the one addition to the command list, `catalog page`, and
on the change it makes to what is decided, a GIF's second role in the table of formats;
the answer of `docs/drifts.md` that no media file is tracked gives way, in a new entry at
its end, to the folder of previews. Later on 2026-10-27 the owner asked for this seed to
be specified, built and opened as a pull request without a question pass: that is the
acceptance. A review of the seed against the code before the specification found no
question for the owner and closed seven gaps an agent may decide: the `--card` option and
the names, what `thumbnail` prints and its statuses, `catalog` asked once of a target that
keeps no catalogs, `busy` only during a rebuild, a refusal of either storage's page and a
`null` generation, `docs/core.md` among the pages, and the offset's range.
