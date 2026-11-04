# Requirements

Seed 75, `project-seeds/75-p1-the-upload-button-says-why-it-is-disabled/seed.md`. The
app only: no command, no core, no emulator and no firmware change.

## 1. The reason beside the button

1.1 A line under `Upload to the installation`, `id` `upload-locked-reason`, is shown
while the button is on the screen and disabled, and hidden while the button is
enabled or hidden. The button names it with `aria-describedby`.
1.2 The line says one reason, the first of these that holds, in this order:
- the installation does not answer: `The installation has not answered yet.` while
  the link is still `checking`, and `The installation does not answer.` followed by
  the failure's sentence as the target screen and Animations word it, ending in the
  kind in brackets, `(no-wifi)`, `(bad-address)`, `(no-answer)` or `(bad-reply)`,
  while the link is `no-answer`;
- `Checking the destination with the installation.` while this screen's preflight
  runs;
- `An upload is under way.` while this screen sends, or while a text or a clock is
  being uploaded or saved from its form;
- `A deletion is under way on Animations.` while the selection's deletion holds the
  content lock.
1.3 Every reason is read from the client's state and from this screen's own state:
the client's content lock names its holder, `preflight`, `deletion` or `upload`, and
the client's reset on a new address clears it, as it clears the lock today.
1.4 The line has the look of the small lines of the screen: the colour and the size
of `Internal storage:` above the form, inside the screen at 320, 360 and 740 pixels,
with nothing scrolling sideways.

## 2. The destination line speaks of the destination only

2.1 `External storage is disconnected or not detected. Using Internal /…` is shown
only after a `space` reply said that no card is present: a reply with
`"external":{"present":false,…}`, or a reply of an older target that names no
external storage.
2.2 While the app holds no `space` reply the line says `Storage not known yet: the
installation has not answered.`, and the form keeps its storage.
2.3 The other sentences of the line are unchanged: read-only card, the flat root of
Internal, and the destination staying put.

## 3. A failed request moves nothing

3.1 A request that fails leaves the last `space` reply in the state. The capacity
lines of Upload and Animations keep their numbers and are shown stale, dimmed as
they are today while the installation does not answer. The next reply refreshes them.
3.2 The form's storage changes only on a reply: a lost reply does not turn an
External form into an Internal one and back. `present()` keeps its meaning. A new
address still forgets the capacity, and a `space` reply refused with
`storage-error` still leaves it unknown.
3.3 The preflight at the press still asks for fresh replies, and fails in words when
they do not come.

## 4. Internal is never disabled for the card

4.1 With Internal selected and no lock holding, the button is enabled whether a card
is present, absent, read-only or unknown.
4.2 The External option is offered only after a reply said a card is present; without
a reply, and after a reply that names no card, it stays disabled.
4.3 The clocks-only boundary of seed 66, pull request #43, is not in `master`; where
it is merged, its own sentence follows the four reasons above, unchanged.

## 5. Proof and delivery

5.1 The app's suite, in Chrome against stand-in targets, each new test seen failing
before its change: a target whose `status` fails after the form is shown, with the
failure named under the disabled button, the destination line and the form's storage
unchanged and the capacity kept stale; a target whose `space` never answers, with
`Storage not known yet` and the form unchanged, and the button enabled with the
External sentence once a reply without a card comes; a target that delays
`remove many` while the selection's deletion runs, Upload naming the deletion; a
target that delays `space` after the press, Upload naming the preflight, and the
upload then acknowledged; the destination invariants of `ready-checks` for no reply,
an absent card and an older target; the look of the line at the three widths. The
existing Internal fallback upload against the emulator without a drive is unchanged.
5.2 The converter's, the emulator's, the app's and the onboarding suites pass.
5.3 `docs/android-app.md` says what the line says and when, in `Using it`; the check
on a phone has the owner's step; `What is verified` and `What is open` say what the
programs proved and what the owner's phone must show.
5.4 The branch is pushed as one pull request from `master`. The APK is built from the
pushed head on Windows with the persistent Odrig signing key, its signer, alignment
and packaging verified, placed on the Drive beside the earlier deliveries without
overwriting them, and published where a phone can download it by a link, the link
recorded with the build's provenance and told to the owner. No secret is printed or
committed. The owner's phone check remains open until the owner reports it.
