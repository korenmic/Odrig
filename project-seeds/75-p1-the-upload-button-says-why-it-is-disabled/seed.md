# The Upload button says why it is disabled

## Summary

On the Upload screen, `Upload to the installation` is disabled by a check that has no
words: an upload or a deletion under way, the destination being checked, or the
installation not answering. The only sentence under the form then is the destination
line, and it says `External storage is disconnected or not detected. Using Internal /.`
also when the real reason has nothing to do with the card: that sentence is shown
whenever the app holds no `space` reply, which is so after any request that failed. The
operator reads that the card blocks an upload to the board's own storage. This seed puts
the reason of a disabled button in words beside it, keeps the destination line to the
destination, and never lets the card's absence disable an upload to Internal. The board is
not changed: the app sends nothing before the button is enabled.

## Priority

- `P1`

## Depends On

- Seed 17, the app's converting and uploading: `app/www/screens/storage.js`, whose
  `locked()` disables the button, and `app/www/upload.js`.
- Seed 63, ready-made animations and their destinations: `app/www/upload-destination.js`,
  whose `reason()` writes the destination line and whose `present()` reads `space`.
- Seed 66, the clocks-only boundary of open pull request #43, which adds its own reason
  to `locked()` and shows it in the destination line; its rule is kept as it is.
- The client, `app/www/client.js`: `contentBusy()`, `link`, and `failed()`, which sets
  `space` to null after a request that failed.

## Product Context

On 2026-11-04 the owner, at the installation with the spare board and no card, chose
`time-standalone-6-melting-clock.odrg` with `Choose a ready-made animation`, saw the
form with `Internal storage` selected, the filename `time-standalone-6-melting-c.odrg`,
the destination `Internal /time-standalone-6-melting-c.odrg`, the line `External storage
is disconnected or not detected. Using Internal /.`, and `Upload to the installation`
grayed, and reported: "upload to internal is grayed out saying external is unavailable
even when internal was selected". The APK was the one on the Drive, built from `edf96d8`
on the branch of pull request #41; the app of `master` has the same check and the same
sentence.

What the code does, read on 2026-11-04:

- `draw()` of `app/www/screens/storage.js` sets the button disabled while `locked()`
  holds: `preparing`, `sending`, `client.contentBusy()` (a lock set by this screen's
  preflight and by the deletion of Animations, or an upload job of any screen), or
  `client.state.link !== "answers"`. None of these is said anywhere on the screen. The
  APK of pull request #41 adds the clocks-only boundary to the same check; that one is
  said in the destination line, and it was not in force in the report.
- The destination line comes from `reason()` of `app/www/upload-destination.js`, whose
  first test is `!present(space)`, and `present()` is false both for a `space` reply that
  says `"present":false` and for no reply at all. `failed()` of the client sets
  `state.space = null` after a request that failed, so the sentence about the card
  appears whenever the last request failed, and `synchronize()` then moves the form to
  Internal and disables the External option, whatever the card.
- The firmware takes no part: the app sends no line until the button is pressed, and a
  board without a card answers `space` with `"present":false`, as documented. Pull
  request #44's firmware and the firmware of `master` behave the same here.

So the fault is the app's: a disabled button without a reason, and a sentence that
blames the card for a state of the link or of the app. Which condition held on the phone
cannot be told from the screen, which is the fault itself; the emulator without a drive
passes the existing test of an Internal fallback upload, so the ordinary case works.

## Technical Constraints

- **The reason beside the button.** A line under `Upload to the installation`, `id`
  `upload-locked-reason`, hidden while the button is enabled, and while it is disabled
  one of these, the first that holds, in this order: `The installation does not answer.`
  with the kind of the failure as the Target screen words it (`no-wifi`: the phone is
  not on the installation's network; `bad-address`; `no-answer`; `bad-reply`: what
  answered is not the installation); `Checking the destination with the installation.`
  while the preflight runs; `An upload is under way.` while this screen sends, or while
  a text or a clock is being saved; `A deletion is under way on Animations.` while the
  selection's deletion holds the lock; and, in the apps that have it, the clocks-only
  boundary's own sentence, unchanged. The button has `aria-describedby` of that line.
  Every reason comes from the client's state: the lock of `client.js` names its holder
  (`preflight`, `upload`, `deletion`), so that the screen can word it and the client's
  reset on a new address clears it, as it does today.
- **The destination line speaks of the destination only.** `External storage is
  disconnected or not detected. Using Internal /.` is shown only after a `space` reply
  with `"present":false`. While the app holds no `space` reply the line says `Storage not
  known yet: the installation has not answered.` and the form does not change.
- **A failed request moves nothing.** The last `space` reply stays through a failure,
  shown stale as the capacity lines are today; the form's storage changes only on a
  reply, so that a lost reply does not turn an External form into an Internal one and
  back. `present()` keeps its meaning; `failed()` stops nulling `space`, and what read
  `space === null` as "no answer" reads `link` instead. The preflight at the press still
  asks for fresh replies and fails in words when they do not come.
- **Internal is never disabled for the card.** With Internal selected and no lock
  holding, the button is enabled whether a card is present, absent, read-only or
  unknown. The External option stays disabled while no reply said a card is present.
- **Where the work goes.** `app/www/screens/storage.js`, `app/www/upload-destination.js`,
  `app/www/client.js`, `app/www/index.html`, `app/www/style.css`, `app/www/messages.js`
  for the words of a failure's kind; `tests/app/` with scenarios in
  `tests/app/page/scenarios/` and stand-in targets as `tests/app/test_upload.py` makes
  them; `docs/android-app.md`, the Upload section and its check list. No change to the
  board, the core, the converter, the emulator's commands or the command list.
- **Where it lands.** On a branch from `master`, as a pull request. The open pull
  requests #41, #43, #44 and #45 carry the same check and sentence and take the change
  when they are brought up to date with `master` before their merge, as rule 11 asks.

## Required Behavior

1. While `Upload to the installation` is disabled, the line under it says why, in words,
   one reason at a time in the order above; while it is enabled, the line is hidden.
2. The destination line blames the card only after a reply said the card is absent;
   without a reply it says that the storage is not known yet, and the form keeps its
   storage.
3. A request that fails leaves the last capacity known, shown stale, and leaves the form
   as it was; the next reply refreshes both.
4. With Internal selected, the button is enabled whenever no lock holds, whatever the
   card; External is offered only after a reply said a card is present.
5. The app sends nothing new to the installation; no command and no firmware change.

## Definition Of Done

1. The app's suite, in Chrome against stand-ins and the emulator, each seen failing
   before the change where it tests a fault: a stand-in whose `status` answers and whose
   `space` never answers, then a stand-in whose `status` fails, each showing the button
   disabled with `The installation does not answer.` and the destination line `Storage
   not known yet`, the form's storage unchanged, and the button enabled with the External
   sentence once a reply with `"present":false` comes; a stand-in that delays `remove
   many` while a deletion of Animations runs, the Upload screen saying `A deletion is
   under way on Animations.`; the preflight sentence while a stand-in delays `space`
   after the press; `ready-checks` with `reason()` for no reply and for an absent card;
   the existing Internal fallback upload against the emulator without a drive, unchanged;
   the look rules at 320, 360 and 740 pixels with the new line.
2. The onboarding suite with the pages; the converter's and the emulator's suites
   unchanged.
3. The owner, on the phone with no card: a ready-made file, Internal, `Upload to the
   installation` enabled and `Uploaded as animation <id> <file>. It plays in the
   playlist.`; with the installation off, the line under the button says that it does
   not answer.

## Open Questions

None. The owner asked for a fix seed with no open questions; what is decided here is the
four reasons and their order, the sentence for an unknown storage, that a failed request
keeps the last capacity and moves the form nowhere, that the clocks-only boundary of seed
66 stays as it is, and that the change lands on `master` and reaches the open pull
requests when they are brought up to date.
