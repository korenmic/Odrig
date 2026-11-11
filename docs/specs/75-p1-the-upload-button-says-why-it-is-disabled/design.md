# Design

## Boundaries

Three files of the web code change what they say, and two tests files and one
scenario grow. The client, `app/www/client.js`, names the holder of its content lock
and stops forgetting the capacity on a failed request. The destination module,
`app/www/upload-destination.js`, tells a missing reply from a reply that names no card.
The Upload screen, `app/www/screens/storage.js` with `index.html` and `style.css`, puts
the reason of a disabled button in words. Nothing is sent to the installation that is
not sent today, and no reply is read that is not read today.

## The client

- `contentLocked` becomes the holder of the content lock: `"preflight"` while the
  Upload screen's preflight runs, `"deletion"` while the selection's deletion runs,
  or null. `setContentBusy(holder)` takes the holder's name or `false`; the two
  callers name themselves. `contentHolder()` gives `"upload"` while an upload job of
  any screen is under way, else the holder, else null; `contentBusy()` is
  `contentHolder() !== null`, so every screen that reads it is as before. `begin()`
  clears the holder as it clears the lock today.
- `failed()` sets the link, the failure and `statusFresh` as today and leaves
  `state.space` as it was. `begin()` still sets it to null for a new address, and
  `askSpace()` still sets it to null on a `storage-error` refusal, a reply that said
  the capacity is unknown. `uploadSnapshot()` is unchanged: its own `space` request
  fails in words when no reply comes.

## The destination module

- `present(space)` is unchanged: true only for a reply with `"present":true`.
- `absent(space)`, new: a reply came and named no present card, `space !== null &&
  !present(space)`; an older target's reply without `external` counts.
- `synchronize(form, space)` moves the form to Internal when it was chosen
  explicitly or when `absent(space)`, to External when `present(space)` and Internal
  was not chosen explicitly, and nowhere when `space` is null. It still returns
  whether the storage changed.
- `select()` and `capture()` are unchanged: External is taken only while
  `present(space)`, and a new form starts External only while a reply says a card is
  present, else Internal, and moves to External when such a reply comes, as the
  redetection of seed 63 does today.
- `reason(form, space)` says `Storage not known yet: the installation has not
  answered.` while `space` is null, and the sentence about the card only while
  `absent(space)`; the read-only, flat-root and staying-put sentences follow as
  today.
- `validate()` is unchanged; it reads the preflight's fresh replies.

## The Upload screen

- `index.html`: `<p id="upload-locked-reason" class="small" hidden></p>` right after
  `upload-made`, and `aria-describedby="upload-locked-reason"` on the button. The
  class `small` gives the line the colour and the size of `upload-space`; no new rule
  of `style.css` is needed unless the line needs its margin, which the look test
  decides.
- `storage.js`: `lockReason(state)` gives the first reason that holds, in the order
  of requirement 1.2: the link (`checking` → `The installation has not answered
  yet.`; `no-answer` → `The installation does not answer. ` + `messages.ofFailure(
  state.failure)`), then `preparing` or the holder `"preflight"` → `Checking the
  destination with the installation.`, then `sending !== null` or the holder
  `"upload"` → `An upload is under way.`, then the holder `"deletion"` → `A deletion
  is under way on Animations.`; null when nothing holds, which `locked()` makes
  impossible while the button is disabled. `draw()` shows the line with
  `lockReason()` while the button is on the screen and disabled, and hides it
  otherwise, through `say()`. `locked()` itself is unchanged.
- The capacity lines keep the class `stale` by the link, as today; with `space` kept
  they now show the last numbers dimmed instead of `-`.

## The tests

- `tests/app/page/scenarios/ready-checks.js`: `reason_no_reply`, `reason_absent`,
  `reason_older_target`, `no_reply_moves_nothing` (an External form stays External
  through `synchronize(form, null)`), `external_refused_without_reply`; the existing
  `flat_root_explanation` passes an absent reply instead of null.
- `tests/app/page/scenarios/upload-lock.js`, new: waits for Animations, opens Upload,
  hands the ready-made file of `settings.file` to `ready-file` as `ready-upload.js`
  does, and reads a snapshot: the button's `disabled` and `hidden`, the lock line's
  text or null, the destination line, the storage select's value and whether External
  is disabled, the capacity line's text and whether it is stale, and the line's
  computed colour, font size and right edge against the view's width and
  `scrollWidth`. Then, as `settings.flow` says: `status-fails` steps the test, waits
  for the lock line to name a failure, reads, steps again, waits for the button
  enabled, reads; `space-silent` waits for the lock line to say the installation
  does not answer, reads, steps, waits for the button enabled, reads; `deletion`
  goes to Animations, starts the selection, selects all, deletes and confirms, goes
  to Upload, waits for the lock line to name the deletion, reads, waits for the
  button enabled, reads; `preflight` steps, presses the button, waits for the lock
  line to name the check, reads, waits for the message, reads. The snapshots come
  back keyed by moment.
- `tests/app/test_upload_lock.py`, new, with stand-ins from `test_upload.target()`
  whose replies are callables reading a flag the test's steps flip: `status` answering
  502 after the step; `space` giving no answer, `None`, until the step and then a reply
  with `"external":{"present":false}`; `remove many` sleeping three seconds; `space`
  sleeping two seconds after the step with `begin`, `data` and `end` answering. One
  test runs `status-fails` at 320, 360 and 740 pixels and checks the look facts. Each
  test fails on `master` because the page has no element `upload-locked-reason`, and
  the `space-silent` test also because the destination line says the card is absent.
- `tests/app/test_ready_upload.py` is unchanged; its emulator test of the Internal
  fallback still passes. `tests/app/test_docs.py` counts 25 steps and 27 `*Seen:*`.

## The documentation

`docs/android-app.md`: a paragraph of `Ready-made files and upload destinations`
says what the line under the button says and when, that the card sentence waits for
a reply, and that a lost reply keeps the capacity dimmed and the form where it is;
the check on a phone gets step 24, `The reason under Upload`, before `Note`; `What is
verified` gets its bullet; `What is open` says the owner's phone has not seen it.

## Delivery

Task 4 runs after the pull request is open. It builds the APK from the pushed head
on Windows as the earlier deliveries did: `npm ci --prefix app`, the staged web code
through `app.apptool.stage`, Capacitor's `sync android`, Gradle without its daemon
with a build-local user home, then `apksigner` with the persistent key of
`C:\Users\koren\.codex\signing\odrig\` whose password is loaded from its JSON into
the environment and never printed, `apksigner verify --print-certs` against the
certificate SHA-256 of `odrig-signing-README.txt`, `zipalign -c 4`, and the APK
suite. The APK, its SHA-256 and a README go to the Drive as `odrig archive/seed-75/`,
a new folder, nothing overwritten. The APK and its SHA-256 are published as the
assets of a pre-release of `korenmic/Odrig` tagged `apk-seed-75-<short sha>`, so
that the phone downloads it by a link; the link, the commit, the hashes and the
checks go into `verification.md` of this spec, and the pull request's description
gets the link. The seed's `state.json` goes to `completed`; the `AGENTS.md` line of
seed 75 names the open pull request.
