# Requirements

Seed 80, `project-seeds/80-p1-ready-made-animations-uploaded-as-a-batch/seed.md`, built on
seed 75's branch, pull request #48. The app's web code, its tests and documents. No command,
reply, core, firmware or emulator change.

## 1. The choice of files

1.1 The Upload screen's button reads `Choose ready-made animations`; its input takes several
files.
1.2 One file picked opens today's form for one file, unchanged.
1.3 Two or more open the batch list, with `Add more`, which picks more files into it, and
`Remove` on each row. A list left with one row stays a list; with none, it closes.
1.4 A file picked twice, by the same name and size, is listed once.
1.5 At most 512 files are listed; of a pick that would pass 512, the first in the chooser's
order are listed, and the app says `At most 512 animations are listed; <k> were left out.`

## 2. Each file's check

2.1 At the pick, the checks of a ready-made file that read only its start: its ending, its
header, its canvas against the target's, and a container's payload size. A file that fails
is listed `refused: <reason>` in today's words and is never sent.
2.2 At its turn a file is read whole and checked again with every check of a single file;
a file that cannot be read, or changed, fails with `The selected animation changed while it
was read.`
2.3 The run reads a file only after the previous file's upload has ended. A successful
file's preview is made as a single ready-made file's is; a preview still being made keeps
that one file's bytes, at most one at a time, and the run waits for it before it reads the
file after the next.

## 3. The names

3.1 Each name is made as a converted file's: `fileName()` of its name, with its own ending,
`-2`, `-3` and so on for a name the destination's list has or a row above takes. The
destination's names are those of the list the app holds: the root's for Internal storage,
the browsed folder's for External storage, none without a list. Unedited rows are named
again when the storage changes before the start.
3.2 On the card the path is the browsed folder, then the name, at most 100 bytes.
3.3 Each name is editable in its row until the start. A row whose name breaks the naming
rule, makes a path of more than 100 bytes, or equals another row's says why under it; while
one does, `Upload <n> animations` is disabled and the line under it says `Mend the names
marked in the list.`
3.4 From the press on, the names are fixed; an existing file is never replaced; a name taken
at a file's turn fails that file as a collision.

## 4. One destination

4.1 The batch takes the storage and folder a single form would take at the first pick, with
the same choice; it holds for every file, and after the start it does not follow the card.
4.2 Before the start the list shows `<n> animations, <a> KB.` above the destination's
capacity line.
4.3 While `fits(sum, free)` does not hold for the destination's free space of the last
`space` reply, the button is disabled and `batch-locked-reason` says `These animations need
<a> KB and <the installation | the card> has <b> KB free.` Without a known free space the run
may start.
4.4 A file of the board's storage refused `no-space` while the known free space would fit it
fails with `The installation has no room for another animation until it restarts or one is
removed. (no-space)`.
4.5 The button reads `Upload 1 animation` or `Upload <n> animations`.
4.6 At the press, an absence fallback that a preflight finds changes the list's destination
as the single form does, and the run starts only at the next press.

## 5. The run

5.1 The files go one after another in the list's order, each through the existing upload:
its own preflight, its lines and pieces, the lowest free id at its turn, and today's
refusals in words.
5.2 The catalog generation captured at the pick guards only the first file sent after the
press; every other file is guarded by its own preflight.
5.3 A preflight or `upload begin` refused `busy` waits 2 seconds while the app is on the
screen and tries again, up to 30 times, the row saying `waiting: the installation is busy
(try <k> of 30)`; then the file fails in today's words. The `busy` of `upload end` is the
upload's own.
5.4 A `stale` `upload begin` of the board's storage starts the file's turn again once.
5.5 A `no-upload` after the app was away from the screen during the file starts its turn
again once; any other `no-upload` fails the file.
5.6 An `upload end` without a reply fails the file with today's words and is not sent
again.
5.7 A destination that no longer holds at a file's turn (a card absent or read-only, a
catalog not `ok` and writable, a folder gone or changed) fails that file and ends the run,
the rest `not sent`. A change of target ends the run, the file in progress failing with
`The target changed.`
5.8 A reason that tells the operator to select the file again or press Upload again is said
in a row without that clause.
5.9 Row states: `waiting`, `checking`, `sending 45%`, `waiting: the installation is busy
(try <k> of 30)`, `uploaded as animation <id>` or `uploaded to the card`, `failed:
<reason>`, `not sent`, `refused: <reason>`.
5.10 From the press on `Add more`, `Remove` and the name fields are gone and `Stop` is
under the list; `Stop` lets the file in progress end and sends no more, and a file waiting
out a `busy` is `not sent` at once.
5.11 When the run ends the list stays until a new pick; `Try the failed again` starts a new
run of the `failed:` and `not sent` rows with the same names and destination.
5.12 The run holds the content lock, `batch`, from the press to its end. The single form's
`Upload to the installation` and the text and clock form's upload are disabled, saying `A
batch upload is under way.` (the single form in `upload-locked-reason`, the text form in
`author-locked-reason`); deleting and moving on Animations stay locked; play, brightness,
browsing and Settings work.
5.13 During a run, one file chosen opens today's form under the list with its button
disabled; two or more list nothing and the app says `A batch upload is under way. Choose
these when it has ended.`
5.14 The line `batch-line`, `role="status"`, under `#top` and above `#mini-indicator`, stays
in place while the content scrolls, on every screen: `Uploading 3 of 12: sunrise.odrg,
45%` during the run; a tap opens Upload; at the end `<a> of <n> uploaded`, then `, <f>
failed` and `, <s> not sent` where not 0, and a full stop, until it is tapped or another
upload starts.
5.15 The run is a module of its own, `app/www/batch.js`, taking items `{name, storage,
folder, size, read(), replace}`.

## 6. In the background

6.1 The run needs no further press and goes on on any screen of the app.
6.2 While the installation does not answer it starts no preflight and fails nothing; the
line says `Waiting for the installation to answer.`; a file whose bytes had begun is started
again once.
6.3 While the app is not on the screen it sends nothing and starts no preflight; a preflight
cancelled by leaving does not fail its file; the line says `Paused while the app was not on
the screen.` until the next file's turn.
6.4 No plugin, service or permission; closing or reloading the app ends the run.

## 7. What stays

7.1 Every command and reply; the single form of a ready-made file, converted media, texts
and clocks; seed 63's rules; each uploaded file last in Animations and the playlist.

## 8. The documents

8.1 `docs/android-app.md`: the chooser, the list, the run, its row states, its line and its
waits, a step of "The check on a phone" and a bullet of "What is open"; `docs/drifts.md`.
