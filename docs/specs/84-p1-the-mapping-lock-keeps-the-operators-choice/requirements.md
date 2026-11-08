# Requirements

Seed 84, `project-seeds/84-p1-the-mapping-lock-keeps-the-operators-choice/seed.md`. The
app's web code, its tests and documents. No firmware, core, command, reply, wiring or power
change.

## 1. One value, kept on the phone

1.1 The app keeps one lock value, `locked` or `unlocked`, in the web view's `localStorage`
under `odrig.mappingLock`.
1.2 The same value holds for Wi-Fi and USB serial, for every target address and every
board. Nothing of it is sent to the board.

## 2. Only the operator changes it

2.1 The value changes only when the operator presses `Lock mapping edits` and confirms in
the "Are you sure?" dialog. Cancel, Escape or a dismissed dialog change nothing.
2.2 Nothing else changes it: leaving Settings; the page hidden (another app, the screen
off); a lost reply, `No answer` or a reconnection; `client.begin()`, which a change of
target or of link goes through; a reload of the app, a restart of the phone, or an update
signed with the same key.

## 3. The first value

3.1 With no stored value the lock is `locked`.
3.2 A stored value other than `unlocked` or `locked` is read as `locked`, and is replaced
only by the operator's next confirmed choice.

## 4. The control answers at any time

4.1 The control can be pressed with or without a board that answers, and with or without a
fresh mapping read; it is disabled only while a pin move is held or a mapping save is in
flight.
4.2 The dialog stays open, and its answer applies, across polls, lost replies,
reconnections and a change of target.

## 5. What the lock allows

5.1 Unlocked, edits still need a board that answers, a fresh mapping read and a mapping
the editor can edit. Until then the lock's status line keeps the value and says why edits
wait; edits come back by themselves.
5.2 Locked, every mapping write is blocked, in its handlers too, as today.

## 6. Unsent edits

6.1 Leaving Settings, hiding the page, a lost link or a change of target drop a held move,
an unsent queued edit and an open photo apply, as today. An already-sent save is
reconciled against its own target.
6.2 Leaving Settings closes a pending confirmation, which changes nothing.

## 7. When the phone cannot keep it

7.1 When the web view refuses to store the value, the choice holds while the app runs, and
the status line says that it could not be kept on this phone.

## 8. Everywhere

8.1 The Controller in a browser and the APK run the same code; a browser keeps the value
per profile.

## 9. The documents

9.1 `docs/android-app.md`: "Mapping edit lock", a step of "The check on a phone" and a
bullet of "What is open".
9.2 The change log of `docs/decisions.md` with the owner's ruling of 2026-11-07, which
replaces seed 69's session-only rule; an entry at the end of `docs/drifts.md`.
