# No text menu outside the app's fields

## Summary

In the operators' app on the phone, a long press, or a right click, opens the menu of
marking and copying text only in a field one types into: a text field or a number field.
Everywhere else, on labels, headings, buttons, messages and lists, a long press marks no
text and opens no menu.

## Priority

- `P2`

## Depends On

- Seed 09, for the operators' app and its APK.
- Seed 17, for the storage screen and the screen that converts and uploads.

## Product Context

The app is a web page shown in Android's web view inside the APK. Today a long press
anywhere in it does what it does on a web page: it marks a word and opens the menu of
copying, sharing and searching. On a phone held by an operator at the installation this
gets in the way: a long press on a button or a label marks its text instead of doing
nothing, and the menu covers the screen. The owner wants that menu only where text is
typed: the address of the installation, the start and the length of a part of a video,
and any field of the same kind that comes later.

## Technical Constraints

- Only the app's own web code and, where the web code cannot do it, its Android project
  change. The commands, the board, the converter and the emulator do not.
- In a text field and a number field everything stays as it is: a long press marks text,
  the menu of copying and pasting opens, and typing works.
- Buttons, the slider, the file chooser and every other control keep working as before,
  by tap.
- The app's suites run its web code in Chrome; the check on a phone is the owner's.

## Required Behavior

1. A long press or a right click on anything but a text or number field marks no text and
   opens no menu: labels, headings, the lists of the storage screen, messages, buttons and
   the screen's empty parts.
2. In a text or a number field a long press marks text and opens the menu as before.
3. A field added later gets the same as the fields of today, without a change elsewhere.
4. The page of the app says so.

## Definition Of Done

1. All test suites that need no board and no phone pass, and the app's suite checks both
   behaviors in Chrome.
2. A new APK is built, and the owner checks it on a phone: a long press on a label and on
   a button opens nothing, and one in the address field marks text and opens the menu.

## The Owner's Answers

On 2026-10-15:

1. The rule holds wherever the app's page runs: in the APK and in a browser, where the
   emulator serves the same web code under `/app/`.
