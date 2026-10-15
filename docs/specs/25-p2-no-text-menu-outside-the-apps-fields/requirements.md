# Requirements: no text menu outside the app's fields

Seed: [`project-seeds/25-p2-no-text-menu-outside-the-apps-fields/seed.md`](../../../project-seeds/25-p2-no-text-menu-outside-the-apps-fields/seed.md).

In the operators' app a long press, or a right click in a browser, does what it does on
any web page: it marks a word and opens the menu of copying, sharing and searching,
wherever it lands. On a phone held by an operator this gets in the way. This spec keeps
that menu in the fields one types into, and takes it away everywhere else.

The owner answered the seed's question on 2026-10-15:

1. The rule holds wherever the app's page runs: in the APK and in a browser, where the
   emulator serves the same web code under `/app/`.

In this document "the app" is the web code of `app/www/`, in the APK, in a browser and
in the emulator's page; "a field" is an element one can type into now: a text field, a
number field, or any other field that takes typing; and "the menu" is what a long press
or a right click opens: the menu of marking, copying, pasting, sharing and searching
text, or a browser's menu of the page.

## Requirement 1: outside the fields

1. A long press or a right click on anything of the app that is not a field SHALL mark
   no text and open no menu: the headings, the labels, the lines of the state, the lists
   of the show screen and of the storage screen, a message, the question before a
   removal, the buttons, the slider, the button that chooses a file, the drawn animation
   and the empty parts of the screen.
2. No text outside the fields SHALL be marked in another way either: a double click, a
   drag over it and a browser's "select all" mark nothing.
3. Every control SHALL keep working by a tap or a click as before: the buttons, the
   slider, the button that chooses a file, the three buttons at the bottom, the buttons
   of the question and `OK` of a message.
4. The page that a web view that is too old shows, `old.html`, SHALL mark no text either.
   It stays a page without scripts.

## Requirement 2: in the fields

1. In a field a long press SHALL mark text and open the menu of copying and pasting as
   before, a right click in a browser SHALL open the browser's menu, and typing SHALL
   work as before.
2. The fields of today SHALL be the three the app has: the address on the target screen,
   and `Start at` and `Length` of the part of a video on the storage screen.
3. A field that is read only, or switched off, takes no typing and SHALL count as no
   field. The app has none today.

## Requirement 3: a field added later

1. An element added to the page later, by a change of `index.html` or by the code while
   the app runs, SHALL get the behaviour of its kind with no change elsewhere: a text
   field, a number field and a text area that of the fields of today, and anything else
   that of the rest.
2. The rule SHALL be stated once in the style sheet and once in the scripts, both by the
   same description of a field, and neither SHALL name an element of the page.

## Requirement 4: what does not change

1. The commands, the board's firmware, the converter and the emulator SHALL NOT change.
   The app's Android project SHALL NOT change unless the web code cannot do what this
   spec asks.
2. The app SHALL send the same lines as before, and no action of the app SHALL depend on
   a long press.

## Requirement 5: tests and documents

1. The app's suite SHALL check in Chrome without a window, for every element of the
   page, with each screen shown, with a message and with the question: that text can be
   marked only in the fields, and that the menu of a right click is stopped outside the
   fields and not in them. It SHALL check the same for fields and other elements made
   after the app started, that a browser's "select all" marks nothing on any screen, and
   that `old.html` marks nothing.
2. Every suite that needs no board and no phone SHALL pass.
3. [android-app.md](../../android-app.md) SHALL say where a long press marks text and
   where it does not, and its check on a phone SHALL have a step for it.
4. A new APK SHALL be built, and the owner SHALL check it on a phone: a long press on a
   label and on a button marks nothing and opens nothing, and one in the address field
   marks text and opens the menu. Only a person can make that check.

## Left out on purpose

- The emulator's own page around the app: its texts can be marked as before.
- What the phone draws outside the web view: the keyboard and the phone's file picker.
- A long press as a gesture of the app: it does nothing in the app, as before.
