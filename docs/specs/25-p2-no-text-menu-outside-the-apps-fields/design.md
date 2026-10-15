# Design: no text menu outside the app's fields

## Overview

One rule in the style sheet and one listener at the start of the app. The style sheet
makes the text of every element unmarkable, and gives the marking back to an element
that is `:read-write`, the name that CSS and the DOM give an element one can type into
now. The listener stops the menu of every `contextmenu` event whose element is not
`:read-write`. Both go by the kind of an element and name none, so an element added
later is a field, or is not, by what it is.

## What this design relies on

- In Chrome and in Android's web view, which are both Chromium, an element whose
  `user-select` is `none` has text that a long press, a double click, a drag and
  "select all" do not mark. The menu of marking and copying opens on marked text or in
  a field, so where nothing is marked it does not open.
- A long press in Android's web view, and a right click in a browser, send a
  `contextmenu` event to the element under the finger or the pointer, and its default is
  the menu. In a field the element of the event is the field.
- `:read-write` matches an `input` of a kind that takes typing (text, number, search,
  url, e-mail, telephone, password, and the dates and times) while it is neither read
  only nor switched off, a `textarea` likewise, and an element made editable. It does
  not match a slider, a file chooser, a button or a check box. Chrome and Android's web
  view have it long before version 80, the oldest web view the APK takes.
- The app's three fields are `input` of type `text` (seed 09, seed 17); none is read
  only or switched off.
- Neither Capacitor's activity nor the app's own Java code registers a menu or a long
  click for the web view (seed 09: `MainActivity` registers the sender and keeps the
  screen on). The web view does what the page says, so the Android project does not
  change.
- `-webkit-touch-callout` is Safari's: on an iPhone it is the menu a long press opens
  over a link or a picture. Chrome and Android's web view do not know it.
- The emulator shows the app in a frame of its page, from the same files, so what the
  app's page says holds there too.

## The style sheet

`app/www/style.css`, after the rule `*` that is there:

```css
* {
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
}

:read-write {
  -webkit-user-select: text;
  user-select: text;
  -webkit-touch-callout: default;
}
```

Chrome marks text in a field even when the field has `none`, but Safari does not; the
second rule makes a field the same in both.

`app/www/old.html` takes the first of the two rules into its own style. It has no field
and keeps no script, so a right click on it in a browser still opens the browser's menu:
only an old web view shows that page, and it has no right click.

## The listener

`app/www/main.js`, the start of the app:

```js
document.addEventListener("contextmenu", (event) => {
  if (!(event.target instanceof Element && event.target.matches(":read-write"))) {
    event.preventDefault();
  }
});
```

It does nothing else. No action of the app is bound to a long press.

## Tests

`tests/app/`, in Chrome without a window, against a stand-in target that answers
`status`, `list` and `space`. One scenario:

- With the show screen shown, with the storage screen, with the question before a
  removal, with the target screen and with a message, it asks the browser to select all
  with no field in focus, and reads what is marked: nothing.
- In each of those five, it reads for every element of the page from `html` down its
  tag, its kind and whether it is read only, the computed `user-select`, and whether a
  `contextmenu` event sent to it was stopped. The test takes the fields by their kind,
  an `input` of a kind that takes typing and is not read only, or a `textarea`, and
  finds three: `address`, `start` and `length`. Each has `text` and a menu that goes on;
  every other element has `none` and a stopped menu.
- It stops the menu on the button `Storage` and then presses it: the storage screen is
  shown.
- It adds to the target screen an `input` of type text, one of type number, one without
  a type, a `textarea`, a read-only text field, a slider, a paragraph and a button. The
  first four are fields and the last four are not.
- It loads `old.html` into the frame: no text is marked by "select all", and every
  element has `none`.

The style sheet's text has `-webkit-touch-callout: none` in the rule `*` and `default`
for `:read-write`, which a test reads, since Chrome does not report it.

The check that nothing depends on a long press, in `test_look.py`, takes `contextmenu`
among the events the web code listens to, and checks that its one listener only stops
the menu.

## Documents

[android-app.md](../../android-app.md): in "Using it", where a long press marks text and
opens the menu and where it does nothing; in "The check on a phone", a step for it; in
"What is verified" and "What is open", the long press. [decisions.md](../../decisions.md),
a line in its change log; `AGENTS.md`: the seed leaves "What is coming";
[firmware-prerequisites.md](../../firmware-prerequisites.md), "Seeds not finished": the
owner's check.

## What needs the owner

- The check on a phone with the new APK: a long press on a label and on a button marks
  nothing and opens nothing, and one in the address field marks text and opens the menu.
