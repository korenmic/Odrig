# Requirements

Seed 73, `project-seeds/73-p2-an-archive-of-animations-uploaded-from-the-app/seed.md`,
built on seed 80's branch, whose run `app/www/batch.js` it feeds. The app's web code, its
tests and documents. No command, reply, core, firmware, converter or emulator change.

## 1. Reading the zip

1.1 A zip picked on the phone is read in the page: its central directory, and each entry
stored (method 0) or deflated (method 8), a deflated one through the converter's
`inflateRaw`; an entry's CRC-32 is checked.
1.2 An entry encrypted, in another method, in zip64, or damaged is listed as unreadable with
its reason.
1.3 At most 512 entries and 64 MB unpacked are read; beyond that the app says so.
1.4 The zip stays in the page's memory and is forgotten when the page reloads or another
zip is picked.

## 2. The entries

2.1 Entries whose names end in `.odrg` or `.odrgx`, in any folder, are the animations; other
entries are listed as passed over.
2.2 Each animation is checked as a ready-made upload is, for its kind, its canvas and its
length; one refused is listed with the reason and cannot be ticked.
2.3 Each row shows a checkbox, the name, the size, the kind and the length, or the reason.

## 3. The names

3.1 To the board's storage a file goes under the last part of its path; to the card under
its path from the archive's root, at most 100 bytes.
3.2 A name the destination cannot take is said in words, with a field to rename the file
before the upload.
3.3 A name the destination's list already has is said too; the upload replaces that file
only when the operator ticks `Replace` on its row.

## 4. The panel

4.1 A panel `Archive` on the Upload screen: `Choose an archive`, the list, `Tick all`,
`Tick none`, the destination (the board's storage, or the card while the target reports it
can be written), the sum of the ticked files against the destination's free space, and
`Upload ticked`.
4.2 The room for items is not shown, since no reply gives it.

## 5. The upload

5.1 The ticked files go one after another through seed 80's run: the same upload, lines,
pieces and refusals in words, the lowest free id for a new file of the board's storage, a
refusal said beside its file and the run going on, `Stop`, and the line on every screen.
5.2 A file ticked `Replace` replaces the destination's file of that name: the board's
storage by its item's id, the card by its path.
5.3 The board receives only the uploads it receives today.

## 6. One app

6.1 The Controller and the APK show the same panel from `app/www`.

## 7. The documents

7.1 `docs/android-app.md` with a step of "The check on a phone" and a bullet of "What is
open"; `agent/vocabulary.md` (`archive`); `docs/drifts.md`.
