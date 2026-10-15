# Design: the app clear of the phone's bars

## Overview

Capacitor 8.5.3, which the app is built with, already measures the bars and the cut-out
and gives them to the page: as four CSS variables on the page's root,
`--safe-area-inset-top`, `-right`, `-bottom` and `-left`, and, in a web view of version
140 or later, as the CSS values `env(safe-area-inset-*)`. The page uses none of them
today. The style sheet takes the room from them and keeps it at each side; a band of the
app's black covers the room at the top, under which the screens scroll; and the tabs go
away while the keyboard is open for a field. The Android project changes in two settings
only: the bars' icons light, and black behind the bars.

## What this design relies on

- Capacitor 8.5.3's core plugin `SystemBars` is registered in every app (its `Bridge`
  registers it) and, unless its setting `insetsHandling` says otherwise, handles the
  room as `css`:
  - In a web view of version 140 or later on a page whose viewport says
    `viewport-fit=cover`, as the app's does, the web view fills the screen, under the
    bars, and `env(safe-area-inset-*)` holds the room.
  - In an older web view it pads the window by the room itself and sets the room the
    page sees to 0: the page is then clear of the bars already.
  - In both cases it sets the four variables on `document.documentElement`, in CSS
    pixels, whole numbers, with the room at the bottom 0 while the keyboard is open.
  - While the keyboard is open it pads the window at the bottom by the keyboard's
    height, so the page's view ends where the keyboard begins.
- `SystemBars`'s setting `style` chooses the bars' icons: `DARK` gives light icons for a
  dark background. Without it the icons follow the phone's theme, and are dark in the
  phone's light theme. The plugin paints the window behind the page with the theme's
  `android:windowBackground`, which is light in the app's theme today.
- The setting `initialViewportFitValueHint` of `SystemBars`, `cover`, lets the plugin
  know the page's `viewport-fit` before the page has loaded, so that nothing jumps.
- A custom property may name another as its value with a fallback:
  `var(--safe-area-inset-top, env(safe-area-inset-top, 0px))`. Chrome and Android's web
  view have both since long before version 80, the oldest web view the APK takes.
- The app's suite runs the page in a frame of Chrome without a window, and a scenario can
  set the four variables on the frame's root as the plugin does, and change the frame's
  size as a keyboard does.

## The style sheet

`app/www/style.css`:

- In `:root`, the room at each side, from the plugin's variable, else the web view's
  value, else nothing:

  ```css
  --bar-top: var(--safe-area-inset-top, env(safe-area-inset-top, 0px));
  --bar-right: var(--safe-area-inset-right, env(safe-area-inset-right, 0px));
  --bar-bottom: var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0px));
  --bar-left: var(--safe-area-inset-left, env(safe-area-inset-left, 0px));
  ```

- `main`: its padding grows by the room at each side, `calc(8px + var(--bar-top))` and
  so on, and `calc(88px + var(--bar-bottom))` at the bottom, so that the last line of a
  list can be scrolled above the tabs.
- `nav`: its padding grows by the room at the left, the right and the bottom. Its black
  reaches the screen's edges, under the bottom bar, and its buttons stand above it.
- `#message` and `#confirm`: `left`, `right` and `bottom` grow by the room.
- `body::before`: a band fixed at the top, as high as the room there, in the app's black,
  above the page, so that what scrolls up goes under it and never shows under the clock.
- `body.typing nav { display: none; }`.

With no room every value is what it is today.

## The keyboard

`app/www/main.js` keeps, for each width of the view, the tallest height the view has had.
The keyboard is open when a field one types into, `:read-write`, has the focus and the
view is lower than three quarters of that height. On `focusin`, `focusout` and `resize`
the page sets the class `typing` on `body` while the keyboard is open, and takes it away
otherwise; when it sets it, the field is scrolled into view, `scrollIntoView` with
`block: "nearest"`. In a browser the view does not shrink when a field has the focus, so
the tabs stay.

## The Android project

- `app/capacitor.config.json`: `"plugins": {"SystemBars": {"insetsHandling": "css",
  "style": "DARK", "initialViewportFitValueHint": "cover"}}`.
- `app/android/app/src/main/res/values/styles.xml`: `AppTheme.NoActionBar`, the theme of
  the running app, has `android:windowBackground` black, so the room shows black also
  where the plugin pads the window.

No Java changes, and no package is added.

## Tests

- `tests/app/page/scenarios/bars.js`: measures the page without the room; sets the four
  variables the scenario is given on the frame's root, as the plugin does; and measures,
  on the show screen and on the storage screen, scrolled to the top and to the end:
  the box of every control and text, the tabs, the box of a message and of the question,
  what lies in the room at the top, and the colour there. Then, on the target screen, it
  gives the address field the focus, makes the frame a third lower, as the keyboard
  does, and measures the field and whether the tabs are shown; then takes the focus away
  and gives the frame its height back.
- `tests/app/test_bars.py`: the scenario upright at 360 x 740 with the room of a bar of
  three buttons, 24 at the top and 48 at the bottom, and with the room of gesture
  navigation, 24 and 16; sideways at 740 x 360 with 24 at the top, 48 at the right and a
  cut-out of 32 at the left. Each time: everything inside the area the room leaves, the
  heading below the top room and the tabs above the bottom room, the tabs' black reaching
  the bottom edge, the band of black over the top room when the screens are scrolled, the
  last row above the tabs, and with the keyboard the field in view and the tabs hidden,
  and shown again after. Without the room: `main`'s padding 8, 8, 88 and 8 pixels, and
  the tabs at the bottom edge, as before.
- `tests/app/test_look.py` and the other tests of the app pass as they are.
- `tests/apk/test_apk.py`: the APK's `assets/capacitor.config.json` has the setting of
  `SystemBars`.

## Documents

`docs/android-app.md`: under "Using it", how the app keeps clear of the bars, and the
tabs while the keyboard is open; a step of the check on a phone; "What is verified" and
"What is open". `docs/decisions.md`: a line in its change log. `AGENTS.md`: the seed leaves
"What is coming". `docs/firmware-prerequisites.md`: the seed among the seeds not
finished, with the owner's check.

## What needs the owner

The check on a phone, upright and sideways, with three buttons and with gesture
navigation where the owner has such a phone, and with the keyboard open.
