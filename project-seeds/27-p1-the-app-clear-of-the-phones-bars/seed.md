# The app clear of the phone's bars

## Summary

On the phone, the operators' app draws its screen only between Android's bars: below the
bar at the top, with the clock and the icons, and above the bar at the bottom, with the
buttons Back, Home and the list of apps, or the line of gesture navigation. Nothing of
the app lies under a bar, and a press on a bar's button never lands on the app.

## Priority

- `P1`

## Depends On

- Seed 09, for the operators' app and its APK.
- Seed 25, which changes the same files of the app's page; this seed is done after its
  pull request is merged.

## Product Context

On 2026-10-16 the owner showed the app on a phone with Android's three buttons at the
bottom. The app fills the whole screen, under both bars:

- At the bottom, the tabs `Show`, `Storage` and `Target` lie under Android's buttons: the
  three lines of the list of apps over `Show`, the circle of Home over `Storage`, the
  arrow of Back and the button of accessibility over `Target`. A press there is a press
  on Android's button, and a tab is hard to read.
- At the top, the app's heading, `ON`, lies under the clock of the status bar.

The app is a web page in Android's web view, inside a Capacitor 8.5.3 project that targets
Android 16 (API 36). From Android 15 an app that targets it is drawn under the bars, edge
to edge, and from Android 16 an app can no longer opt out of that. The app's page asks for
the whole screen, `viewport-fit=cover`, and its style keeps no room for the bars.

## Technical Constraints

- Only the app's own web code and, where the web code cannot do it, its Android project
  change. The commands, the board, the converter and the emulator do not.
- The room is taken from what the phone reports for its bars and its camera cut-out, not
  from a fixed size: phones differ, and the bottom bar of gesture navigation is thinner
  than the bar of three buttons.
- The area under the bars shows the app's black background, and the bars' icons stay
  readable on it.
- In a browser, where the emulator serves the same web code under `/app/` and no bars
  are reported, the page looks as it does today.
- The app's suites run its web code in Chrome; the check on a phone is the owner's.

## Required Behavior

1. On a phone with three buttons and on one with gesture navigation, the app's tabs lie
   wholly above the bottom bar, and its heading wholly below the top bar.
2. The same holds when the phone is turned sideways, where a bar or the camera cut-out
   may stand at a side.
3. The lists of the show and storage screens scroll within the app's area, and their
   last line can be scrolled into view above the tabs.
4. When the keyboard opens for a field, the field stays in view and the tabs do not ride
   up over it.
5. The page of the app says how the app keeps clear of the bars.

## Definition Of Done

1. All test suites that need no board and no phone pass, and the app's suite checks in
   Chrome that the page keeps the room the phone reports at each side.
2. A new APK is built, and the owner checks it on a phone: the tabs and the heading are
   clear of both bars, held upright and sideways.

## Open Questions

None. The owner asked for the app to end where the bars begin; the constraints above
decide the rest.
