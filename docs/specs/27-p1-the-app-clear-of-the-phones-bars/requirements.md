# Requirements: the app clear of the phone's bars

Seed: [`project-seeds/27-p1-the-app-clear-of-the-phones-bars/seed.md`](../../../project-seeds/27-p1-the-app-clear-of-the-phones-bars/seed.md).

On 2026-10-16 the owner showed the operators' app on a phone with Android's three buttons
at the bottom: the app's tabs lay under Android's buttons, and its heading under the
clock of the status bar. The app targets Android 16, where every app is drawn under the
bars, edge to edge, and its page keeps no room for them. This spec has the page keep that
room, as the phone reports it.

The seed has no open questions: the owner asked for the app to end where the bars begin,
and the seed's constraints decide the rest.

In this document "the bars" are Android's bar at the top, with the clock and the icons,
and its bar at the bottom, with the buttons Back, Home and the list of apps or the line
of gesture navigation; "the cut-out" is the place of the phone's camera in the screen;
"the room" at a side is what the phone reports for the bars and the cut-out there, in
CSS pixels; "the tabs" are the buttons `Show`, `Storage` and `Target`; and "the heading"
is the top of the screen that is shown.

## Requirement 1: the room of the bars

1. The page SHALL take the room at each of the four sides from what the phone reports
   for its bars and its cut-out: the values the app's Android shell gives the page, or
   the web view's own, and no fixed size.
2. With the room reported, every control and every text of the app SHALL lie inside the
   area that the room leaves: the heading below the room at the top, the tabs above the
   room at the bottom, and everything clear of the room at the left and at the right.
3. The room SHALL show the app's black background, and the bars' icons SHALL be light,
   so that they stay readable on it.
4. This SHALL hold for a bar of three buttons and for the thinner bar of gesture
   navigation, held upright and sideways, where a bar or the cut-out may stand at a side.
5. With no room reported, as in a browser where the emulator serves the same web code
   under `/app/`, the page SHALL look as it does today.

## Requirement 2: scrolling

1. The screens SHALL scroll within the app's area: what scrolls up does not show in the
   room at the top.
2. The last line of the show screen's list and of the storage screen's list SHALL be
   scrollable into view above the tabs.

## Requirement 3: the keyboard

1. While the phone's keyboard is open for a field, the tabs SHALL not stand over the
   field: they are hidden until the keyboard closes or the field loses the focus.
2. The field SHALL stay in view above the keyboard.

## Requirement 4: what does not change

1. The commands, the board, the converter and the emulator SHALL not change, and the app
   SHALL send the lines it sends today.
2. Only the app's web code changes, and its Android project only where the web code
   cannot do it: the bars' style and the colour behind them. No package is added.

## Requirement 5: tests and documents

1. The app's suite SHALL check in Chrome, with the room set at each side as the Android
   shell sets it, that the page keeps it: upright with a bar of three buttons and with
   gesture navigation, and sideways with a bar and the cut-out at the sides; the lists
   scrolled to their ends; and a field with the keyboard open. It SHALL check that the
   page without the room is as before.
2. The suite of the APK SHALL check that the APK has the setting of the bars.
3. `docs/android-app.md` SHALL say how the app keeps clear of the bars, and the check on
   a phone SHALL have the step for it.
4. Every suite that needs no board and no phone SHALL pass, and a new APK SHALL be built.
5. On a phone, the owner checks that the tabs and the heading are clear of both bars,
   held upright and sideways, and that a field stays in view with the keyboard open.
