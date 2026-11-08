# The mapping lock keeps the operator's choice

## Summary

Make `Lock mapping edits` a setting of the app on the phone that keeps the value the
operator chose, locked or unlocked, until the operator changes it. No other event changes
it: not leaving Settings, another app or the screen turning off, a lost reply, a
reconnection, a change between Wi-Fi and USB serial, a change of target, or a restart of
the app or the phone. The control can be changed with or without a board that answers.

## Priority

`P1`.

## Product Context

On 2026-11-07 the owner reported, on the APK of seed 82 over USB serial, that the lock "is
not persistent": after an unlock it "randomly becomes locked again before my clicks land",
and switching to another app and back "forgets the locking and defaults back to locked".
The owner's ruling: "Locking versus unlocking should be persistent forever and never fall
back into some defaults. It can only change when I manually change it." The lock "is an APK
individual setting and should be unaffected by the medium used forever". It is a fault of
`master`, not of the USB link, so this seed is built on `master` and not as a task of seed
82's pull request.

How it is today (`app/www/screens/mapping.js`, seed 69's rule in `docs/android-app.md`,
"Mapping edit lock": "Unlocking applies only to this Settings session on this app"):

- The lock lives in memory only, `editLocked = true` when the app starts.
- `relock()` puts it back to locked when Settings is left (`showing(false)`), when the page
  is hidden (`visibilitychange`, another app or the screen off), when the target changes
  (`reset()` after `client.begin()`: the Target screen's connect buttons, Wi-Fi or USB, and
  the app's start), and whenever `client.state.link` is not `answers`.
- One failed request sets the link to `no-answer` (`failed()` in `app/www/client.js`). So a
  single lost reply relocks. Over USB, while the board is busy after a start, replies are
  lost more often, which is why the relock looked random.
- The lock button itself is disabled while the mapping read is not fresh, the mapping is not
  editable or the board does not answer. A press can land on a disabled button.

Seed 72, planned and not started, asks for the same persistence (its items 2 and 3)
together with a Settings checkbox and typed pin edits. This seed delivers the persistence
now, on the current control. Seed 72, when it is built, makes its checkbox show and change
this seed's stored value and keeps its other items.

## Required Behavior

1. **One value, kept on the phone.** The app keeps one lock value, `locked` or `unlocked`,
   in its own storage on the phone (the web view's `localStorage`, as other settings of
   the app are kept). The same value holds for Wi-Fi and USB serial, for every target
   address and every board. It is not stored on the board and no command is added.
2. **Only the operator changes it.** The value changes only when the operator presses the
   control and confirms in the existing "Are you sure?" dialog. Cancel, Escape or a
   dismissed dialog change nothing. Nothing else changes it:
   - leaving Settings or the mapping editor;
   - switching to another app, the screen turning off, or the app sent to the background;
   - a lost reply, `No answer`, a reconnection, or a cable unplugged;
   - a change between Wi-Fi and USB serial, or of the target;
   - a restart of the app or the phone, or an update of the APK signed with the same key.
3. **The first value.** On a phone where the app never stored a value, after a new
   installation, the lock starts `locked`. That is the only default. A stored value the
   app does not know is read as `locked` and is replaced only by the operator's next
   confirmed choice.
4. **The control answers at any time.** The control can be pressed with or without a board
   that answers, and with or without a fresh mapping. It waits only while a pin move is
   held under a finger or a mapping save is in flight. The dialog stays open, and its
   answer applies, across polls, lost replies and reconnections.
5. **What the lock allows is unchanged.** Unlocked, edits still need a board that answers,
   a fresh mapping read and a mapping the editor can edit, as today. Until then the screen
   shows the kept value and why edits wait, and edits come back by themselves when the board
   answers again. Locked, every mapping write is blocked, in its handlers too, as today.
6. **Unsent edits are still dropped.** Leaving Settings, hiding the app or changing the
   target still drops a held move, an unsent queued edit and an open photo apply, as today.
   An already-sent save is still reconciled against its own target. Only the lock value is
   kept.
7. **When the phone cannot keep it.** If the phone refuses to store the value, the choice
   holds while the app runs, and Settings says that it could not be kept on this phone.
8. **Same code everywhere.** The Controller in a browser and the APK use the same code. In a
   browser the value is kept per browser profile.

## Technical Constraints

- App only: `app/www/screens/mapping.js`, with the value in `localStorage` under an
  `odrig.` key, as the target, the filters and the panel keep theirs, every access guarded
  as theirs are. No firmware, core, command, reply, wiring or power change. The mapping protocol, the board's
  revision checks and its saved mapping stay as they are.
- `relock()`'s cancelling of moves, drafts and the photo apply stays where it is today. It
  no longer writes the lock value.
- Tests seen failing first, by the app suite in the page: unlock, then hide the page and
  show it again; leave Settings and come back; a withheld reply (`no-answer`) and the next
  answer; `client.begin()` again, which a reconnection, a new target and a change of link
  all go through; a reload of the page. When seed 82's USB serial link is on `master`
  before this seed is built, also Wi-Fi to USB serial and back with the stand-in sender of
  its `tests/app/test_serial.py`. After each, the lock is still unlocked and an edit saves. The same sequence keeps a confirmed lock locked. Pressing
  the control with no board answering works, and Cancel changes nothing. The scenarios of
  `tests/app/page/scenarios/mapping-lock.js` that expect a relock are changed after the new
  tests were seen failing.
- Documents: `docs/android-app.md`, "Mapping edit lock", and its phone check; the change
  log of `docs/decisions.md` with the owner's ruling of 2026-11-07, which replaces seed
  69's session-only rule; an entry at the end of `docs/drifts.md`.

## Open Questions

None. The owner ruled that the lock is an app setting that keeps the operator's choice
forever, for every link. The seed decides the rest from that ruling: one value for every
target and board, `locked` only on a phone that never stored one, the control usable
without a board, unsent edits still dropped, and the existing confirmation kept.

## Definition Of Done

1. A requirements/design/tasks specification of the stored value, the removed relocks and
   the control's availability.
2. The app suite passes with the new tests, seen failing first.
3. An APK built from `master` with this change, signed with the persistent key.
4. The owner's check on the phone: unlock, switch to another app and back, turn the screen
   off and on, unplug and replug the USB cable, switch Wi-Fi and USB serial, close and
   reopen the app: still unlocked, and a pin move saves. Lock again, and the same steps keep
   it locked.
