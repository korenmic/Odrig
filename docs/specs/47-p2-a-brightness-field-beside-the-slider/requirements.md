# Requirements: a brightness field beside the slider

The seed is `project-seeds/47-p2-a-brightness-field-beside-the-slider/`. It has no open
question, and the owner ordered it specified and built without a question pass; where
these requirements decide a point the seed leaves open, the decision is recorded at the
end of `docs/drifts.md`.

Words used here: the **field** is the text field `#level-number`; the **slider** is the
range `#level`; the **value in force** is the value this phone last wrote into the field,
by the slider, by a value sent from the field, or by following `status`, and there is none
before the first `status`; the field holds **text not sent** while its text differs from
the value in force written in decimal (the empty text while there is none); a **commit** is
Enter or the keyboard's Done key in the field, or the field's `change` when it is left.

## 1. The field and the slider

1.1 The top panel of the Animations screen has, in the place of `Set the brightness to
<span id="level-number">`, one line: the label `Set the brightness to` in the lettering of
`.slider-label`, and the field `<input id="level-number" type="text" inputmode="numeric"
enterkeyhint="done" autocomplete="off">` that it labels, with the placeholder `-`.

1.2 The slider stays under that line, full width, with the accessible name `Brightness`.
The fact `Brightness N`, `#brightness`, is unchanged and follows every `status`.

1.3 Until the first `status` the field is empty and shows `-`, and the slider stands at 0.

1.4 The field is never disabled; it dims with the panel while the installation does not
answer, as the slider does.

## 2. The sync

2.1 Every `input` of the slider, and its `change` when it is let go, writes the slider's
value into the field, and that value becomes the value in force. 0 is written `0`.

2.2 Anything typed or pasted into the field that is not a digit is removed as it is typed.
While the field holds a whole value from 0 to 255, the slider stands at it, at each
keystroke, and nothing is sent; while the text is empty or above 255 the slider stays where
it stands.

2.3 When the slider is moved while the field holds text not sent, the slider's move wins:
the text not sent is dropped, the field loses the focus, which closes the phone's keyboard,
the slider's value is written into the field, and the slider sends as it does today.

## 3. A commit

3.1 Enter or Done commits only when the field holds text not sent, and the focus stays in
the field; the app does not close the keyboard. The field's `change` commits when it holds
text not sent. An Enter followed by the field's `change` sends once.

3.2 A commit reads the digits as a whole number, leading zeros read away: `080` is 80 and
the field is rewritten `80`.

3.3 A committed value from 0 to 255 that differs from the value in force, or any such value
while there is none, is sent as letting go of the slider is: the slider is set to it, it
becomes the value in force, and `sendLevel` sends `brightness <n>` with its 200 ms spacing,
a waiting brightness replaced by the newer one, and the value sent again when a second or
more has passed since this phone's last send.

3.4 Nothing is sent at a keystroke; for a value equal to the value in force; for an
empty field, which is not 0; for a value above 255; or for a commit while the app is
hidden. In each, the field and the slider show the value in force (empty and 0 while there
is none).

3.5 A value above 255 committed while the app is shown makes a line under the slider say
`The brightness is 0 to 255.`; the line is a `p` with `role="status"` and
`aria-live="polite"`, stands under the slider so that the slider never moves while it
shows, and goes at the next keystroke in the field or the next value sent.

3.6 No `Saving` and no `Saved` line: the fact confirms within about two seconds, a refusal
is said in the app's place for messages as for the slider, and a send without a reply is
not repeated.

## 4. Status

4.1 While the field holds text not sent, or has the focus while the phone's keyboard is
open (the app's typing state), a `status` reply changes neither the field nor the slider.

4.2 Otherwise both follow `status` by today's rule of the slider: not while the slider is
held, and only when a second has passed since this phone's last send. A value set on
another phone shows in the fact within two seconds, and in the field and the slider once
the field is left or the keyboard closed.

## 5. On a phone, and one app

5.1 The label and the field stand on one line; the field is about 5.5 em wide, at least 44
px wide and 48 px high, its digits tabular; the slider is 8 px under it. Every look test of
the app passes at 320 and 360 px upright and 740 px sideways.

5.2 While the keyboard is open the tabs hide and the field is scrolled into view, as for
every field. A long press marks text in the field, which is the first field of the page.

5.3 The field listens to `input`, `change` and `keydown` only: the set of events the app
listens to, which a test pins, is unchanged.

5.4 The emulator's Controller view and the APK show the same field from the same
`app/www`. Nothing in `core/`, `firmware/`, `emulator/`, `docs/commands.md` or
`docs/core.md` changes; the app sends the same line, `brightness <n>`, and the table of the
lines the app sends, with its count, is unchanged.

## 6. Documents and tests

6.1 `docs/android-app.md`: the Animations bullet of "What it is", the first column of the
slider's row in the table of lines, the sentence on the slider in "Using it" step 3, the
paragraph that names the fields where a long press marks text, step 4 of "The check on a
phone" and the brightness in "What is verified".

6.2 The app's suite checks in Chrome against a stand-in and the emulator: the field sent by
Enter and by leaving it; Enter and `change` sending once; the slider following typed values
and the field following the slider; a slider move dropping text not sent; `080` written
`80`; a value equal to the value in force sending nothing; an empty field and 256 sending
nothing, with the range said for 256 under the slider; a commit while the page is hidden
sending nothing; a `status` leaving the field alone while it holds text not sent; the
spacing of the sends kept; the field's size and look at 320, 360 and 740 px. The slider's
tests pass unchanged but for reading the number from the field's value.

6.3 Every suite that works on this computer passes. A new APK is built and put with the
artifacts on the share and on Drive.

6.4 The owner checks on a phone: typing 8 and pressing Done sets the installation to 8 and
the slider stands at 8; moving the slider shows its number in the field. That check is left
open to the owner, and the seed stays `in_progress` until it is made.
