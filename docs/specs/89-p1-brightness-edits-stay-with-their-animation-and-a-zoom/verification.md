# Verification: brightness edits stay with their animation, and a brightness zoom (seed 89)

Done on Windows 11 on 2026-11-24, in the worktree of the branch
`seed-89-brightness-edits-and-zoom`, made from `seed-87-live-mirror` at 3ab15e17 with
`master`'s seed merged in. Pull request: #70, against `seed-87-live-mirror`.

## Commits

| Commit | Task |
|---|---|
| 124fc998 | `master`'s commit of the seed merged in |
| 2f6e940b | The spec |
| 93dddd90 | 1. A gesture stays with its animation |
| 8d94f864 | 2. The hold and the default's line |
| 8c563fd4 | 3. The brightness zoom |
| 2077b3d9 | 4. Against the real emulator |
| df3fde44 | 5. The pages |
| a9a8d6dd | B-1. The list under the taller panel, a bridge of the run |
| this commit | 6. Deliver seed 89 |

The bridge B-1 came from task 6's run of every suite: the zoom's row of task 3 made the
panel that stays at the top 56 pixels taller, so a row held near the tabs no longer
scrolled a long list at 360 by 740, and a 412 x 915 phone kept 3.5 rows of the list under
the panel, not four. Its commit carries both and the failures seen.

## Faults seen failing first

- Task 1, with the app unchanged, 9 tests and 10 failures, each in the commit message:
  - the held drag and the typed digits were dropped at a change of animation;
  - a save queued behind a change was not sent;
  - a press while the panel lagged was refused;
  - a target chosen during a drag was not said.
- Task 2: no hold after a move, and no line after a confirmed default.
- Task 3: no zoom and no zoom row in the layout.
- Task 4: on the branch's base 124fc998, in a temporary worktree with the new class copied
  in, the drag and the typed digits on `a.odrg` across the end of its turn were dropped,
  the panel showing `Animation 2: b.odrg` under `Default brightness`; the drag into a clock
  break saved nothing for `a.odrg`.
- B-1: `test_order`'s held row did not reach the list's end, and `test_frozen` found 3
  rows where it asked for 4.

## Suites

Every suite, one after another, by `tests/run.py --serial`, at df3fde44:

| Suite | Result |
|---|---|
| converter (npm) | 1,606 tests, OK |
| converter (Python) | 552 tests, OK |
| onboarding | 88 tests, OK |
| runner | 26 tests, OK |
| mapping | 49 tests, OK |
| firmware-host | 37 tests, OK |
| firmware | 696 tests; 3 failures that only this computer's arrangement gives |
| core | 1,341 tests, OK, 1 skipped |
| emulator | 769 tests, OK, 20 skipped |
| app | 730 tests; the 2 faults that B-1 mends, and the 2 known below |

The app's suite again at a9a8d6dd, after B-1: 730 tests; only the two known below.

Known on this computer, not faults of the code:

- `tests.firmware.test_env` and `tests.firmware.test_paths`: three tests fail under the
  junction that shares this computer's toolchains (`ODRIG_TOOLS`), as before this seed;
  both modules pass with `ODRIG_TOOLS` unset, as the CI runs them.
- `tests.app.test_message_source` imports Pillow, which the documented `.venv` does not
  hold; it passes with the base Python 3.14 that has Pillow 12.3.0.
- Under the load of a whole run, `test_shared_tools`' lock (a temporary `setup.lock`
  still held at cleanup) once, and `test_catalog`'s rebuild once; each passes alone.

## The check in a browser against the emulator

The app in Chrome against the emulator on a show of three animations of the board's own
storage and a card of two, with turns of five seconds:

- The zoom kept from an earlier session read `Zoom 0 to 12` at a fresh load. Real arrow
  keys on `Start` made it `Zoom 2 to 12`, kept as `2 12`.
- With the zoom of 2 to 12, one click on the slider gave exactly 5 for `red.odrg`:
  `Saved 5 for red.odrg.`
- A drag held across the end of red's turn showed `Animation 1: red.odrg, no longer
  playing` with 7 and 8. At its release the panel moved to `green.odrg` and said
  `Saved 8 for red.odrg.`; green kept the default. Red came back with 8, ticked.
- After the emulator restarted on the same folder and the app reloaded, red showed 8,
  ticked, the other animations the show's default 32, and the zoom 2 to 12.
- A click the tools sent late landed on `green.odrg`'s panel, which showed `Default
  brightness`, and set the default, as the panel said.

## The APK

Built from a9a8d6dd by the repository's tools with the JDK of Android Studio and the
Android SDK, signed with the persistent key:

| | |
|---|---|
| Source | a9a8d6dd, no tracked change |
| Size | 19,273,876 bytes |
| SHA-256 | 8e16dd7bd842e0910f17d8871093993d60155de9f24962dfa5f9df1d6ce146a3 |
| Certificate SHA-256 | 5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1 |
| Alignment | `zipalign -c 4` passed |

## Pull request and CI

#70, `seed-89-brightness-edits-and-zoom` into `seed-87-live-mirror`, mergeable. Its base is
not `master`, so the Firmware hosts workflow does not run on it; the seed changes no file
that workflow builds or tests.

## Open

The owner's phone check, with turns of about 30 seconds:

- An animation's override dragged across the end of its turn is saved for that animation,
  and comes back with that value, again after the board and the app restart.
- A zoom of 2 to 12 lets the slider move between 4 and 5, and is kept after the app
  restarts.
- The board's brightness stays at 40 or less during the check.
