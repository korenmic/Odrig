# Requirements: previews of the animations in the app

Every animation gets a short looping GIF preview, named by its key, the CRC-32 and the
size of its file that every catalog line already keeps. The previews of every animation
known on the first computer are kept in the repository in `thumbnails/`, the default
preview catalog, which the emulator, `app.py serve` and the APK hold and the board never
does. The app learns the keys of the installation's animations by reading the catalogs'
pages with one new command, `catalog page`, and shows each row's preview; it makes the
previews of what this phone uploads itself and keeps them on the phone. Where these
requirements decide a point the seed leaves open, the decision is recorded at the end of
`docs/drifts.md` under "Seed 44".

## 1. The key

1.1. An animation's key is the CRC-32 of zlib and PNG of its whole file, as eight lowercase
hexadecimal digits, a dash, and its size in bytes in decimal: `1a2b3c4d-52340`.

1.2. Two files of the same bytes have one key and one preview, whatever their names.

1.3. A catalog line names the key of its file: its first word is the CRC-32 and its second
the size. The catalogs' format does not change.

## 2. The preview

2.1. A preview is a GIF89a of the animation's own canvas, its top row first, that loops
forever: an application extension `NETSCAPE2.0` with the loop count 0.

2.2. The loop `L` of an animation is, in milliseconds: for an ODRG file or an ODRGX
container of frames, the sum of its frame records' durations; for a text, its pass; for a
clock, a thousand times its seconds.

2.3. A preview holds `N` pictures, `N` being 24, else 12, else 6 (2.8). Picture `k`, for
`k` from 0 to `N - 1`, is the picture on screen at `floor(k * L / N)` ms from the
animation's start: for frames, the picture after the last record that begins at or before
that time; for a text or a clock, the picture the converter's library draws at that time,
a clock with the seed 1.

2.4. Every picture is shown for the same time, in hundredths of a second:
`floor((L + 5N) / (10N))`, at least 2 and at most `288 / N`: 12 with 24 pictures, 24 with
12, 48 with 6. The time is the picture's graphic control extension's delay; the extension
says no transparency and the disposal "do not dispose".

2.5. The palette is every colour of the `N` pictures when they hold at most 256. Otherwise
it is the 256 colours that cover the most pixels over the `N` pictures, a tie going to the
smaller colour read as one number of 24 bits, red highest. The palette is sorted by that
number, then filled with black to the next power of two, at least 2. It is the GIF's global
colour table; no image has a table of its own.

2.6. Each pixel takes the palette colour nearest it by the sum of the squares of the
differences of red, green and blue, a tie going to the lower index, without dithering.

2.7. Each picture is a whole image of the canvas at 0, 0, its indexes compressed by the
GIF's LZW with the minimum code size `max(2, b)`, `b` the bits of the palette's size, a
clear code first, a clear code again when the table would pass 4,096 codes, the end code
last, in data sub-blocks of 255 bytes and a last shorter one.

2.8. A preview of 24 pictures above 65,536 bytes is made again with 12, and one of 12
above 65,536 bytes again with 6; one of 6 above 65,536 bytes is no preview, and is refused
with the reason `preview-too-large`.

2.9. The same file gives the same preview, byte for byte, in Node.js and in a web page.

2.10. The preview is made while the file's records are read in order: what is kept is the
canvas's current picture and the sampled pictures, never every picture of the file. A
file the library's readers refuse is refused with their reason.

## 3. The converter

3.1. The converter's library gains the module `thumbnail.js`, the library's own code with
no package, offered by `index.js`, that makes a preview from the bytes of an ODRG file or
an ODRGX container, makes a key from bytes, and can make a preview in steps: each step
reads a bounded part of the file, so that a caller can let other work run between them.

3.2. The library's readers keep their behaviour: `odrg.decode` and the reader of ODRGX
containers decode, and refuse, as before, and the walk of 2.10 refuses the same files
with the same reasons.

3.3. The command line gains the sixth subcommand `thumbnail`:
`node converter/odrig.js thumbnail FILE --out OUT.gif` writes the preview of one file;
`node converter/odrig.js thumbnail FILE... --catalog DIR [--card ODRIG]` adds the preview of
each file to the preview catalog in `DIR`. `--out` takes exactly one FILE and is not given
with `--catalog`, and one of the two is given, else status 2 with the usage. Like every
option of the tool, an option given twice takes its last value.

3.4. `thumbnail` writes nothing on standard output and runs no separate check.

3.5. With `--out`, a file the readers refuse, or whose preview is too large, ends with
status 1, the one line `error: <reason>: <detail>`, and no file written.

3.6. With `--catalog`, every file is taken in the order given. A file whose key the
mapping holds keeps its GIF and gains its name. Any other file gets `DIR/<key>.gif` and a
line of the mapping. A file the readers refuse, or whose preview is too large, is passed
over and named on standard error by one line `passed over: <FILE>: <reason>: <detail>`.
The run ends with status 0 once the mapping is written. A folder `DIR` that does not exist
is made.

3.7. A name in the mapping is, for a FILE inside the folder `--card` names, its path from
that folder, its parts joined by `/`; for every other FILE its own file name. A mapping
entry holds each name once, its names in the order of their bytes. The subcommand never
guesses a card from a folder's name or contents.

3.8. The subcommand reads and writes `DIR/catalog.js` as text and never imports it, so
Node.js 20 runs it.

3.9. The table of exit statuses of `docs/converter.md` says that `thumbnail` with
`--catalog` ends with 0 after passing files over, and `docs/reasons.md` lists
`preview-too-large`.

## 4. The default preview catalog

4.1. `thumbnails/` at the top of the repository is tracked in git: `thumbnails/<key>.gif`
for each preview and `thumbnails/catalog.js`, the mapping, written by `thumbnail` only.

4.2. `thumbnails/catalog.js` is plain ASCII: the line `export default {`, then one line for
each key in the order of the key's bytes,
`  "1a2b3c4d-52340": {"gif": "1a2b3c4d-52340.gif", "names": ["foo.odrg"]},`, then the
line `};`. A name outside printable ASCII, or holding `"` or `\`, is written as JSON
writes it with every character above `~` as `\u` and four hexadecimal digits.

4.3. Every key of the mapping has its GIF in the folder, and every GIF of the folder has
its key; the folder holds nothing else.

4.4. No name of the mapping is a folder of the computer, a mount point or an account.

4.5. The firmware's build, `pack`, `fw.py install-show`, the card's catalog and every
lister of the board never read `thumbnails/`: it is in no show and on no storage.

4.6. The first default catalog is made from the animation files of the sources the seed
lists, read where they live and never copied or changed there: the two card copies each in
a run of its own with `--card`, every other source without it. The invalid vectors and
every file the readers refuse are passed over and named.

4.7. The report of the first default catalog gives the number of previews, their total
size, the APK's size and the sources that were not at hand.

4.8. The only GIF, MP4 or MOV files tracked in the repository are `thumbnails/*.gif`.

## 5. The command `catalog page`

5.1. `catalog page <storage> <page> <offset>`, `<storage>` being `internal` or
`external`, `<page>` 0 to 15 and `<offset>` 0 to 4,294,967,295; any other form is refused
with `bad-argument`.

5.2. The reply is `{"ok":true,"generation":<n>,"text":"<text>","next":<offset or null>}`.
`<n>` is the storage's generation as a number, as `catalog` gives it, or `null` when its
catalog is not `ok`. `<text>` is up to 512 bytes of the page from the offset, as the
inside of a JSON string. `next` is the offset plus the bytes given when the text is not
empty, and `null` only with an empty text.

5.3. The text is empty and `next` is `null` when the offset is at or after the page's end,
when the page cannot be read, as a page without entries has no file, and when the
storage's catalog is not `ok`.

5.4. The page's bytes are read into the chunk buffer with one `read_at` of the host a
call. The command asks for no memory: the core's memory and the core object keep their
sizes.

5.5. A host whose storage cannot be changed answers `storage-error`, as `read` does.

5.6. The command is refused with `busy` while a rebuild of that storage runs, the one
`catalog` names in `rebuild`; nothing else makes it `busy`, an open upload included.

5.7. The board, the emulator and `odrigctl` give the same: the emulator runs the core's
command as it is, and the command tool takes `catalog page internal|external PAGE OFFSET`.

## 6. The app reads the pages

6.1. The app asks `catalog` when the target first answers, when it answers again after a
silence, and after every complete `list`, besides Settings' occasions. Every reply of
`catalog`, Settings' included, counts for the previews.

6.2. When a reply shows a storage `ok` and the app has no read of it, or one of another
generation or another number of entries, the app reads that storage's sixteen pages, each
from offset 0 until `next` is `null`, one request at a time after the operator's own and
after `status`, an upload's lines, `list` and the saved order. It keeps, for that target,
each line's key by its name: the file's name on the board's storage, a card file's path
from `odrig`.

6.3. The keys of a read stand until the next read of that storage has ended. They are
dropped at once when `catalog` shows the storage in another state than `ok`, when the
target answers again after a silence, and when the target changes.

6.4. A page that answers another generation than the first page of the same read starts
the read again. A page refused with `busy` is asked again two seconds later. A page whose
generation is `null` ends the read without keys, and the storage counts as unread; any
other refusal but `busy` ends it the same way. Nothing of this is said to the operator.

6.5. A row takes the key of its storage and name only when the key's size is the row's
`bytes`. A row of a storage whose catalog is not `ok`, or whose file has no entry, has no
key: a show folder that `pack` makes has no catalog until Settings' rebuild, `catalog
rebuild internal`, has made one.

6.6. A target that answers any `catalog page`, of either storage, with `bad-argument` is
from before this seed: its rows have no preview, nothing is said, it is asked no page
again until the target changes, and it is asked `catalog` only on Settings' occasions.

6.7. A target that answers `catalog` with `unknown-command` or `bad-argument` is asked no
`catalog` again until the target changes, neither for the previews nor by Settings:
Settings says `This installation's software keeps no catalogs.` from that answer.

6.8. The table of command lines of `docs/android-app.md` gains these occasions of
`catalog` and the line `catalog page <storage> <page> <offset>`: thirty-five lines.

## 7. The app shows the previews

7.1. The default catalog reaches the app in its three hosts as the converter's library
does: the emulator serves `thumbnails/` under `/app/thumbnails/`, `app.py serve` under
`/thumbnails/`, both with `.gif` among their types, and the APK's build copies it to
`thumbnails/` beside the web code. The web code imports `thumbnails/catalog.js` and no
other file from outside `app/www` besides `converter/<file>`, and fetches no preview: an
image element's source is the GIF's path.

7.2. Each animation row, at every level of the explorer, has a square of 44 by 44 pixels
as the first part of its Play button, before the name; a tap on the square plays as a tap
on the name does, and the selection checkbox stays before the button.

7.3. The square shows the row's preview drawn with `image-rendering: pixelated` and not
draggable, its pixels square, scaled to fit in its own ratio, a 60-by-6 strip as a band
across the middle. It is an empty dark square when the animation has no preview or the
row has a `fault`.

7.4. A row's preview is the default catalog's for its key, else the phone's own (8.4).

7.5. At 320 px wide a row in selection mode keeps its Play button at least 44 px wide:
its `⊘ Ignored` or `Saving…` note stands under the name inside Play. Every control keeps
44 px, 8 px apart, and nothing scrolls sideways at 360, 320 and 740 px.

7.6. The now-playing panel shows the preview of the animation on the LEDs before its
words, in a square as a row's; the square is hidden while `status` names no animation,
while a test shows, and while the list does not hold the animation yet.

7.7. Folder rows and the Tests group have no square. The emulator's own page shows no
preview.

## 8. The phone's own previews

8.1. After an upload from the Upload screen, or from the form of a text or a clock, a new
one or an edited one, has ended with success and its message is shown, the app makes the
preview of the bytes it sent with the converter's library, reached through `convert.js`,
which stays the one script that imports the library, in steps that leave the screen
answering.

8.2. It keeps the preview on the phone in the web view's IndexedDB, in the phone's own
catalog of previews, under the key of the bytes it sent. The row keeps the empty square
until the preview is made.

8.3. A preview the readers refuse, or one too large, is not kept, and nothing is said.

8.4. The app looks a key up in the default catalog first and in the phone's own after.

8.5. At its start the app drops each phone preview whose key the default catalog has. The
phone's catalog has no other limit, never leaves the phone, and each phone has its own;
the Controller view and `app.py serve` have the one of the browser they run in.

8.6. When the web view has no IndexedDB or refuses a write, the preview is kept for the
run only, and nothing is said.

8.7. No plugin is added to the APK.

## 9. What stays

9.1. The catalogs' format, the board's memory, every other command and every reply stay
as they are; the board never holds a GIF.

9.2. The JSON source of every animation stays committed; a preview is no source.

9.3. The app keeps one body of web code: no file the APK's build adds is missing from the
emulator, and no behaviour is one in the APK and another in the Controller view.

## 10. The pages

10.1. `docs/converter.md` describes the subcommand, its options, its statuses and the
module; `docs/reasons.md` the reason `preview-too-large`; `docs/commands.md` the command;
`docs/catalog.md` the key; `docs/core.md` the command among the host rules and the
catalogs; `docs/android-app.md` the previews, the phone's catalog and its table of lines;
`docs/emulator.md` what it serves and the command tool's new form.

10.2. `agent/vocabulary.md` defines the preview, the GIF of `thumbnails/` beside a row,
told apart from the moving preview of the form of a text or a clock and from
`python -m preview`; `agent/animation-guide.md` has a row of its table of where things go
for the preview, committed, written by `thumbnail` in the commit of the animation's source.

10.3. `docs/decisions.md` gives a GIF its second role in the table of formats and has a
dated entry of its change log; `docs/drifts.md` has, at its end, that the tracked previews
are the media the repository holds besides the images it held, and the decisions these
requirements took.

10.4. `AGENTS.md` names seed 44 in "What is coming" as built with the owner's session
open.

## 11. The checks

11.1. Every suite that needs no board and no phone passes, with the tests the seed's
Definition of Done names for the converter, the core, the emulator, the app and the APK.

11.2. The firmware is built and not flashed. The owner's session flashes it, compares
`odrigctl catalog page external 0 0` with the card's `catalog-00.txt`, and looks at the
previews on a phone with the APK against the board, and at the preview of an animation
uploaded from the phone.
