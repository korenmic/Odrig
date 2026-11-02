# An archive of animations uploaded from the app

## Summary

The operators' app takes one zip archive of animation files, opens it on the phone, lists
the animation files it holds, and uploads the ones the operator ticks, one by one, to the
installation's own storage or to its card, through the upload the app already has. Nothing
of the archive reaches the board: the board's commands are unchanged. The zip is read in
the app's own JavaScript with the converter's inflate, the one converter of seed 18.

## Priority

- `P2`

## Depends On

- Seed 17, the app's converting and uploading: the upload flow, its request queue, its
  refusals said in words, and `upload begin <id> <file> <bytes>` with the lowest free id.
- Seed 35, the catalogs, for `upload begin external <path> <bytes>` to a card the board can
  write, and seed 61 as planned, for the choice of internal storage or card.
- Seed 18, one converter: `converter/lib/inflate.js` reads a raw DEFLATE stream, which is
  what a zip entry is, and `check` says whether a file is an animation for the canvas.
- Seed 24, the bigger animation space: the board's storage is 13,500,416 bytes, and each
  file takes whole blocks of 4,096 bytes of it.

## Product Context

On 2026-11-02 the owner asked, in their words, for "a way to upload an entire zip to the
APK and have the APK self-extract it internally and then upload wirelessly or wired to the
ESP an entire archive of animations", "one by one file is fine also if it does so
internally in the Android before it uploads them", because "the APK needs to receive just
one file and we don't have that feature yet"; and for "a zip extraction management
interface that just reuses the existing upload interfaces", in which, "once a zip is
loaded, I can select specific animations to upload to the internal storage or external
storage, however I want".

The first archive is ready: `clocks_rotated_right.zip`, the 112 clocks of seed 52 and the
message of seed 54 turned a quarter turn to the right by pull request #46, 113 files of
1,255,654 bytes, 1,268,334 bytes zipped, on the share and on the owner's Drive. Twelve of
its names were shortened to at most 32 characters, the longest the board's own storage
takes: `time-original-5-every-row-another-time.odrg` is `t-orig-5-every-row-time.odrg`.
The board holds 116 animations today with 139,264 to 258,048 bytes free of 13,500,416;
with those removed, the 113 take about 1.45 MB in whole blocks, and 11 MB stay free.

## Technical Constraints

- **Reading the zip.** In `app/www`, a reader of the zip format's local file headers and
  central directory: entries stored (method 0) or deflated (method 8), the deflated ones
  through `converter/lib/inflate.js`; entries encrypted, in other methods, or in zip64 are
  listed as unreadable with the reason. A zip is read from the phone's picker, as a media
  file is for converting; it stays in the page's memory and is forgotten when the page
  reloads. At most 512 entries and 64 MB unpacked are read; beyond that the app says so.
- **The entries.** The files whose names end in `.odrg` or `.odrgx`, in any folder of the
  archive, are the animations; other entries are listed as passed over. Each animation is
  checked as an upload is, with the converter's `check`, for its kind, its canvas and its
  length; a file the check refuses is listed with the reason and cannot be ticked.
- **The names.** A file goes to the board's own storage under the last part of its path,
  which must be 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_` and `.`, as `show.json`
  names them; to the card, under its path from the archive's root, at most 100 bytes, as
  the card's paths are. A name the destination cannot take is said in words, with a field
  to rename the file before the upload; a name the destination already has is said too,
  and the upload replaces the file only when the operator ticks that it may.
- **The interface.** A panel `Archive` on the Animations screen, beside the upload: a
  button that picks a zip; the list of its entries with a checkbox, the name, the size,
  the kind and the length, or the reason it is not an animation; `Tick all` and `Tick
  none`; a choice of destination, the installation's own storage or the card, offered
  only while the target reports it can be written; the sum of the ticked files against
  the destination's free space from `space`, and against the room for items, 32 more
  than the show had at the start and at least 128, from `list`; and `Upload ticked`.
- **The upload.** The ticked files go one after another through the app's existing upload,
  the same queue, the same `upload begin`, `upload data`, `upload end` and `upload begin
  external` lines, the same pieces of 1,500 bytes and the same refusals said in words; the
  panel shows the file in progress, the count done, and a refusal beside the file it was
  for, and goes on with the next file. `Stop` ends the run after the file in progress. A
  file uploaded to the board's own storage takes the lowest free id, as today.
- **One app.** The emulator's Controller view and the APK show the same panel from the
  same `app/www`; the emulator takes the uploads as the board does, to its storage and to
  a card given with `--drive`.
- **Where the work goes.** `app/www/screens/archive.js`, a zip reader of its own in
  `app/www/`, `index.html`, `style.css`, `main.js`, `upload.js` where the run of several
  files needs a hook; `tests/app/test_archive.py` with a zip fixture made by the test from
  the test animations; `docs/android-app.md`; `agent/vocabulary.md` (`archive`). No change
  to the board, the core, the converter or the command list.

## Required Behavior

1. The app takes one zip from the phone's picker and lists its animation files with their
   kind, size and length, and its other entries with why they are passed over.
2. The operator ticks files, chooses the installation's own storage or the card, sees the
   ticked sum against the free space and the room for items, and starts the upload.
3. The files are uploaded one by one through the app's existing upload, each refusal said
   beside its file, the run going on with the next; the operator can stop it.
4. A name the destination cannot take is renamed in the panel before the upload; an
   existing name is replaced only when the operator allows it.
5. The board receives only the uploads it receives today; no new command.

## Definition Of Done

1. The app's suite, in Chrome against the emulator and stand-ins: a zip of stored and
   deflated entries read; an encrypted, a zip64 and a broken entry listed as unreadable; a
   non-animation passed over; a refused animation listed with its reason; names too long
   renamed; the sums against `space` and the room for items; ten files uploaded in a row
   to the emulator's storage and to a card, one refused in the middle, the run going on;
   `Stop`; the look rules at 320, 360 and 740 px.
2. The converter's suite unchanged; the onboarding suite with the pages.
3. The owner, on a phone, loads `clocks_rotated_right.zip`, ticks a selection, uploads it
   to the installation's own storage, and sees the clocks play.

## Open Questions

None. The owner asked for this seed with the interface described above; what is decided
here beyond their words is the reuse of the converter's inflate and `check`, the limits
of 512 entries and 64 MB, the names shortened before an upload, and the replacement of an
existing name only when allowed.
