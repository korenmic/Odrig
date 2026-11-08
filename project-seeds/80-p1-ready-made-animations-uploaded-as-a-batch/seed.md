# Ready-made animations uploaded as a batch

## Summary

On the app's Upload screen, `Choose ready-made animations` takes several `.odrg` and
`.odrgx` files from the phone's chooser at once. The app checks each one as it checks a
single file today, names it as a converted file is named, and lists them, with a reason
beside any file it refuses. One press of `Upload <n> animations` then sends them one after
another, through the upload the app already has, to one destination: the board's own
storage, or the card in the folder being browsed. The run goes on by itself while the
operator uses the app, and a line under the top of every screen shows how far it has come.

- A file that fails is marked with its reason, and the run goes on with the next.
- A pause of the link, or of the app, makes the run wait, not fail.
- `Stop` ends the run after the file in progress.
- `Try the failed again` sends the failed files once more.

Picking a single file keeps today's form exactly. Nothing changes on the board or in the
commands.

## Priority

- `P1`

## Depends On

- Seed 63, merged on `master`: ready-made `.odrg` and `.odrgx` files uploaded without
  conversion, to the board's storage or to the card in the folder being browsed. Also its
  preflight: the header, the canvas, the name rules, fresh observations of the target,
  the storage, the catalog and the folder before sending, and collisions refused, never
  overwritten.
- Seed 75, in pull request #48: the line under `Upload to the installation` that says why
  it is disabled (`upload-locked-reason`), and its lock holders. Pull request #48 is merged
  before this seed's branch is made, and this seed builds on it.
- Seed 17, the app's upload: one upload job at a time, `upload begin`, `upload data` and
  `upload end`, and the lowest free id for the board's storage.
- Related, not needed:
  - Seed 79, the preview of an upload made on the phone, makes each file's preview as its
    upload starts.
  - Seed 73, an archive of animations from a zip, plans the same kind of run. "The run"
    below says how the two share it.

## Product Context

On 2026-11-06 the owner asked, in their words, for "changing the upload ready animation to
ready animations, meaning add support for batch uploads, meaning I could multi-select and
not just select a single file and initiate a batch upload of multiple animations one after
the other by a single click and not attempt to manually re-upload each one at a time,
reiterating this, but only doing it once per multiple files and leaving it in the
background to finish by itself."

Today `Choose a ready-made animation` takes one file. Each file needs its own pick, its own
check, its own press of `Upload to the installation`, and a wait for its end before the
next one.

"In the background" is read here as: with the app open, on any of its screens, and the
phone left on the table. Switching to another app, or locking the phone, pauses the run
until the app is back. A run outside the app's page would need an Android service and a
permission, which this seed does not add. The owner is told so in words when the seed is
delivered.

## Technical Constraints

- **What happens today.** Read at `master` 390f47b7 on 2026-11-06.
  - The Upload screen's ready-made chooser takes one file. `prepareReady`
    (`app/www/convert.js:10-27`) reads it whole into memory and checks it. Its name is
    made by `fileName()` (`app/www/upload.js:29-39`) with no taken names, so it never gets
    `-2`. A collision is refused at the press, `A file already exists at this
    destination...` (`upload-destination.js:56`).
  - One upload runs at a time. The client holds one upload job (`app/www/client.js`,
    `upload()` and `contentBusy()`), and each screen's `locked()` disables its Upload
    button while one runs or is being checked. While a file is sent, the button gives way
    to `Cancel`.
  - Each form keeps the catalog generation it captured at the pick (`storage.js:66-68`).
    `validate` (`upload-destination.js:49-52`) refuses with `The storage catalog changed.`
    when it has moved. Every upload to a storage with a catalog moves it by one
    (`docs/catalog.md`).
  - Going off the screen cancels every waiting request (`client.js`, `cancelWaiting`),
    a preflight's too. The board drops an upload left without data for a minute, and the
    app then hears `no-upload` (`messages.js`).
  - The APK keeps the phone's screen on while the app is in front: `MainActivity` sets
    `FLAG_KEEP_SCREEN_ON` (`docs/android-app.md`, "the phone's screen stays on while the
    app is in front").
  - No reply gives the board's room for items. It is fixed when the player starts: 32
    items more than the show had then, and at least 128 (`docs/show.md`, `docs/core.md`).
- **1. The choice of files.**
  - The button reads `Choose ready-made animations`, and its input takes several files
    (`multiple`). The web view's chooser asks the phone's file app for several files,
    since Capacitor's chooser passes `EXTRA_ALLOW_MULTIPLE`. Whether several can be ticked
    is the file app's. The chooser may also offer files of other endings, since Android
    knows no type for `.odrg`. Such a file is listed as refused, with today's reason
    `Choose an .odrg or .odrgx animation file.`
  - One file picked opens today's form for one file, unchanged.
  - Two or more open the batch list. The list has `Add more`, which picks more files into
    it, and `Remove` on each row. `Add more` also serves a phone whose file app gives one
    file at a time. A list left with one row stays a list; with none, it closes.
  - A file picked twice, with the same name and size, is listed once.
  - At most 512 files are listed. Of a pick that would pass 512, the first files in the
    chooser's order are listed up to 512, and the app says `At most 512 animations are
    listed; <k> were left out.`
- **2. Each file's check.**
  - At the pick, each file has the checks of seed 63 that read only its start: its ending,
    its header, its canvas against the target's, and for a container the size of its
    payload. A file that fails is listed as `refused: <reason>`, in today's words, and is
    never sent.
  - A file is read whole only when its turn begins. Then every check of seed 63 runs again
    on the bytes read, those of the start too. That covers the length, and the full decode
    of a text or clock container: a damaged text or clock is refused only at its turn. A
    file that cannot be read, or that changed since the pick, fails with `The selected
    animation changed while it was read.`
  - The run reads a file whole only after the previous file's upload has ended. Each file
    gets the phone's own preview as a single ready-made file does: today after success
    when it is `previewSafe`, and with seed 79 as seed 79 says. A preview still being made
    keeps that one earlier file's bytes until it is made, at most one such preview at a
    time. So the phone holds at most two files of the batch. When a file's upload ends
    while the preview of the file before it is still being made, the run waits for that
    preview before it reads the next file. Otherwise it does not wait for previews.
- **3. The names.**
  - Each file's name is made by `fileName()`, as a converted file's is: the name without its
    ending, in lower case, every character other than `a`-`z`, `0`-`9`, `-` and `_` turned
    into `-`, an empty base made `animation`, with its own ending, `.odrg` or `.odrgx`, at
    most 32 characters.
  - A name the destination already has gets `-2`, `-3` and so on, and so does a name that a
    row above takes. The destination's names are those of the list the app holds of it at
    the time: the root's for `Internal storage`, the browsed folder's for `External
    storage`, and none when it holds no list. The names of unedited rows are made again
    when the destination's storage changes before the start.
  - On the card the path is the folder being browsed, then the name, at most 100 bytes,
    as seed 63 says.
  - Each name stays editable in its row until the start. A row whose name breaks the
    naming rule, makes a path of more than 100 bytes, or equals another row's name, says
    why under its name: in today's words, or `Another file of this batch has this name.`
    While any row says so, `Upload <n> animations` is disabled, and the line under it
    says `Mend the names marked in the list.`
  - From the press on, the names are fixed. An existing file is never replaced. A name
    taken at a file's turn fails that file as a collision.
- **4. One destination for the batch.**
  - The batch takes the storage and the folder that a single file's form would take at the
    first pick, with the same choice of `Internal storage` or `External storage` (seed
    63). The choice holds for every file of the batch. After the start the destination
    does not follow the card: a card found again does not move an Internal batch to it,
    and the batch never moves to Internal.
  - Before the start, the list shows `<n> animations, <a> KB.`, above the destination's
    capacity line as the Upload screen words it today. The files fit when `fits(sum,
    free)` of `upload.js` holds, where `sum` is the sum of the sizes of the rows that
    passed, and `free` is the destination's, from the last `space` reply. This is the
    one-file rule applied to the sum. It ignores blocks, and the target still decides for
    each file.
  - While they do not fit, `Upload <n> animations` is disabled, and the line under it,
    `id` `batch-locked-reason`, says `These animations need <a> KB and <the installation |
    the card> has <b> KB free.` When the space is not known, the run may start, and the
    target decides for each file.
  - The room for items is not shown, since no reply gives it. A file of the board's storage
    refused with `no-space` while the known free space would fit it fails with `The
    installation has no room for another animation until it restarts or one is removed.
    (no-space)`, and the run goes on.
  - The button reads `Upload 1 animation` for one file, and `Upload <n> animations`
    otherwise.
  - At the press, before the first file is sent, an absence fallback that the preflight
    finds changes the list's destination as the single form does. The run then starts only
    when the button is pressed again.
- **5. The run.**
  - The files go one after another, in the list's order. Each goes through the app's
    existing upload: its own preflight, the same lines and pieces, the lowest free id at
    its turn for a file of the board's storage, and the same refusals in words.
  - The catalog generation captured at the pick guards only the first file sent after the
    press of `Upload <n> animations`. A run of `Try the failed again` has no such guard.
    Every other file, the first of a retry run included, is guarded by its own preflight
    alone: `uploadSnapshot` reads the catalog before and
    after its lists, and fails that file in today's words when the generation moved
    between the two reads. The run's own uploads are therefore no change. A change another
    controller makes between two files fails only the file whose turn it is: its name check,
    `replacing:false` on Internal and `upload expect 00000000` on the card catch it.
  - A file whose preflight or `upload begin` is refused with `busy` waits 2 seconds, then
    runs its preflight and begin again, up to 30 times. After that it fails with today's
    words for `busy`. Its row says `waiting: the installation is busy (try <k> of 30)`.
    The 2 seconds count only while the app is on the screen. The `busy` of `upload end`,
    while the installation checks the file, is retried by the upload itself, as today, and
    does not count.
  - A file of the board's storage whose `upload begin` is refused with `stale`, its id taken
    meanwhile, starts its turn again once, with a fresh preflight and the lowest free id at
    that time. A second `stale` fails it.
  - A file whose upload is answered `no-upload` after the app was away from the screen
    during it starts its turn again once: a fresh preflight, then the file from its first
    byte. A second such `no-upload` fails it. Any other `no-upload`, such as the card taken
    out, fails the file at once in today's words.
  - A file whose `upload end` got no reply fails with today's words, `... not acknowledged
    as installed; check the destination before retrying.`, and is not sent again by this
    run.
  - When the destination no longer holds at a file's turn, that file fails in today's words
    and the run ends, with the files left `not sent`. That covers a card absent or
    read-only, a catalog no longer `ok` and writable, and a folder gone or changed.
  - A change of the target ends the run. The file in progress fails with `The target
    changed.`, and the files left are `not sent`.
  - A reason that tells the operator to select the file again, or to press Upload again,
    is said in a row without that clause.
  - Row states: `waiting`, `checking`, `sending 45%`, `waiting: the installation is busy
    (try <k> of 30)`, `uploaded as animation <id>` (on the card without an id, `uploaded
    to the card`), `failed: <reason>`, `not sent`, and `refused: <reason>` for a file
    refused at the pick.
  - From the press on, the list shows the run. `Add more`, `Remove` and the name fields are
    gone, and `Stop` is under the list. `Stop` lets the file in progress end and sends no
    more; a file waiting out a `busy` is not in progress and becomes `not sent` at once.
  - When the run ends, the list stays with its rows until a new pick replaces it.
    `Try the failed again` then starts a new run at once, with the rows that are `failed:`
    or `not sent`, the same names and the same destination. Rows `refused:` at the pick are
    never sent. A file that failed for a collision fails again; the operator picks it again
    to rename it.
  - The run holds the client's content lock, as a holder of its own, `batch`, from the press
    to its end, between files too. No other upload is queued behind it. Meanwhile:
    - `Upload to the installation` of the single form, and `Upload` or `Save` of the text
      and clock form (`author-upload`), are disabled. Each says `A batch upload is under
      way.`: under the single form in seed 75's line, in place of `An upload is under
      way.`; on the text and clock form in a line of its own under its button, `id`
      `author-locked-reason`.
    - Deleting and moving rows on Animations stay locked, with their sentences, as during
      one upload today.
    - Play, the brightness, the LEDs, browsing and Settings keep working. What the board
      refuses with `busy` while an upload is open, such as `repeat ... save` or the `clocks`
      lines, is refused in today's words.
  - During a run, `Choose ready-made animations` with one file opens today's form under the
    list, with its button disabled as above. With two or more files it lists nothing and
    says `A batch upload is under way. Choose these when it has ended.` The video and GIF
    chooser, `Make a text` and `Make a clock` work as today, with their uploads disabled.
  - The line on every screen is an element `id` `batch-line`, `role="status"`, under `#top`
    and above `#mini-indicator`. It stays in place when the content scrolls, and it is
    shown on Upload too. While the run lasts it says, for example, `Uploading 3 of 12:
    sunrise.odrg, 45%`. A tap on it opens Upload. When the run ends it says `<a> of <n>
    uploaded`, then `, <f> failed` and `, <s> not sent` where they are not 0, and a full
    stop, until it is tapped or another upload starts.
  - **Shared with seed 73.** This seed builds the run as a module of its own,
    `app/www/batch.js`. It takes items `{name, storage, folder, size, read(), replace}`,
    where `read()` gives an item's bytes at its turn and `replace` is false for every file
    of this seed. It runs them as this section and the next say. If seed 73 is built
    first and has a run of its own, this seed adds to it what it lacks: the retries, the
    one new start, the line, the lock and `Try the failed again`. Seed 73's own needs,
    replacing a file when ticked, a path per file and its panel, stay seed 73's.
- **6. In the background.**
  - The run needs no further press. It goes on while the operator uses any screen of the
    app.
  - While the app is in front, the APK keeps the phone's screen on, as today. The run asks
    for no wake lock.
  - While the installation does not answer, the run starts no file's preflight and fails
    nothing, and the line says `Waiting for the installation to answer.` It goes on when
    the installation answers. A file whose bytes had begun is started again, once, as a
    dropped one is.
  - While the app is not on the phone's screen, the run sends nothing and starts no file's
    preflight, as today. A preflight that leaving the screen cancels does not fail its
    file: that file's turn starts again when the app is back. The line then says `Paused
    while the app was not on the screen.` until the next file's turn.
  - No plugin, service or permission is added. A run does not outlive the app's page:
    closing or reloading the app ends it. The files are not kept, and the phone keeps no
    record of the run.
- **7. What stays.**
  - The board, the firmware, the core and the emulator, every command and every reply.
  - The single form of a ready-made file, a converted video or GIF, a text and a clock.
    Converted media stays one file at a time.
  - Seed 63's rules of names, folders, collisions and preflight, for a single file.
  - Each uploaded file goes last in the list of Animations and in the playlist, as today.
- **The pages.**
  - `docs/android-app.md`: the chooser, the batch list, the run, its row states and its
    line, its waits, and a step of "The check on a phone" with a bullet of "What is open".
  - `docs/drifts.md`: an entry at its end, "Seed 80: ...".
- **Tests.** In `tests/app`, in Chrome against the emulator and stand-ins:
  - three files picked at once go into the list, and `Add more` adds a fourth;
  - a file of another ending, and one of another canvas, are listed as refused and never
    sent;
  - names made and suffixed against the destination's list and one another, an edited
    name that breaks the rule disabling the button with its line, and a storage change
    making unedited names again;
  - the sum against `space` disables the button with its line;
  - a run of ten files to the board's storage, and to a card folder whose catalog moves at
    each file, every file uploaded;
  - a refusal in the middle, after which the run goes on;
  - `busy` of `upload begin` tried again, and `busy` of `upload end` not counted;
  - `stale` started again once with a new id;
  - a stand-in that drops an upload while the page is hidden, after which that file is
    started again once; and a `no-upload` with the page shown, which fails the file;
  - a stand-in that stops answering in the middle: the run waits and goes on;
  - a card taken out at a file's turn ends the run, the rest `not sent`;
  - a change of target ends the run;
  - `Stop`, then `Try the failed again`;
  - the line on another screen, its tap, and its end sentence;
  - the single form and the text form disabled with `A batch upload is under way.`, and
    deleting on Animations locked, during a run;
  - one file picked opens today's form;
  - the look rules at 320, 360 and 740 pixels.
- **Where it lands.** A branch from `master` after pull request #48 is merged, as a pull
  request of its own.

## Required Behavior

1. The phone's chooser gives the app several ready-made files at once, and `Add more` adds
   more of them.
2. Each file is checked as a single file is, and named as point 3 says. A refused one is
   listed with its reason and is never sent.
3. One press sends every listed file that passed, one after another, to one destination,
   with no further press.
4. The run goes on while the operator uses the rest of the app; deleting and moving
   animations, and other uploads, wait for its end. Every screen shows how far the run
   has come, and how it ended.
5. A file that fails is marked with its reason, and the run goes on. A pause of the link
   or of the app makes the run wait, not fail. `Stop` ends the run after the file in
   progress, and `Try the failed again` sends the rest once more.
6. The run reads a file whole only at its turn, and the phone holds at most two files of
   the batch. No command, reply or byte of the board changes.

## Definition Of Done

1. The app's suite with the tests above, and the onboarding suite with the pages. The
   converter's suite is unchanged.
2. The APK is built from the branch.
3. The owner's check, on a phone with that APK:
   - in the phone's chooser, ten ready-made files ticked at once;
   - `Upload 10 animations` to the board's storage, then the Animations screen opened while
     the run goes on, with the line showing its progress;
   - all ten play;
   - the same to the card, in a folder;
   - the phone left on the table with the app open until the run ends;
   - during a run, another app opened for two minutes and the app brought back: the line
     said `Paused while the app was not on the screen.`, and the run went on to its end.

## Open Questions

None. The owner described what is wanted. Decided here:

- one file keeps today's form; two or more open the batch list, with `Add more`;
- at most 512 files are listed;
- each file is read whole only at its turn, and at most two are held;
- names follow a converted file's rule, with suffixes, and never replace a file;
- one destination for the batch, the space checked as one sum, and the room for items not
  shown, since no reply gives it;
- each file after the first is guarded by its own preflight;
- `busy` and `stale` tried again, a dropped file started again once, and a pause of the
  link or the app waited out;
- `Stop`, `Try the failed again`, and one line on every screen;
- the content lock held through the run, and seed 75's line saying so;
- "in the background" read as the app open on any screen; no wake lock, service or
  permission;
- the run built as a module that seed 73 can feed;
- converted media stays one file at a time;
- no command, reply or firmware change, and a pull request of its own from `master` after
  pull request #48.
