# The app's count of installed and stick animations

## Summary

The show screen of the operators' app, its dashboard, shows how many animations the
installation has in its own storage and how many come from a USB stick. When no stick is
plugged in, the line of the stick is not shown.

## Priority

- `P2`

## Depends On

- Seed 09, for the operators' app.
- Seed 20, for the animations of a USB drive and their ids.
- Seed 22, for a stick through a hub, which this count makes visible at a glance.

## Product Context

On 2026-10-16 the owner tested the board's new firmware with a stick in a powered hub. To
tell from the app whether the stick is read, the board's own animations had to be removed,
so that any animation in the list could only be the stick's. The owner wants to see this
on the dashboard without emptying the board: one number for the animations in the board's
own storage, and one for those of the stick.

What the app already gets, without a new command:

- `space` answers with `animations`, the number of the show's own animations, also while
  the board is still reading its animations after a start.
- `list` lists the show's items and then the stick's animations, each stick animation as
  an animation item. While the board reads its animations after a start, `list` answers
  `busy`, for some minutes with a full storage.

The difference between the animation items of `list` and `animations` of `space` is the
number of the stick's animations.

## Technical Constraints

- Only the app's web code changes. No command is added and no reply gains a member unless
  the owner approves it.
- The count of the stick's animations does not lean on their ids being 60001 or more,
  which holds only while the show uses no such id.
- The app asks no more often than it does today for its status and its list.
- What the app shows is the same in the APK and in the emulator's controller view, which
  serves the same web code.

## Required Behavior

1. The dashboard shows the number of animations in the board's own storage, labelled as
   such.
2. When the stick has animations, the dashboard shows their number on a line of its own,
   labelled as the stick's.
3. When no stick is plugged in, that line is not shown: no label and no value.
4. When a stick is plugged in or pulled out, the line appears or goes at the app's next
   list, as the stick's animations in the list do today.
5. While `list` answers `busy` after a start, the dashboard shows the number of the board's
   own animations and says that the stick's are not known yet, instead of a wrong number.
6. The page of the app says what the two numbers are.

## Definition Of Done

1. All test suites that need no board and no phone pass, and the app's suite checks the
   numbers in Chrome against the emulator: with no drive, with a drive of animations, a
   drive plugged in and pulled out, and the board still reading after a start.
2. A new APK is built, and the owner checks it on a phone against the board: without a
   stick, the line of the stick is not there; with the stick in the hub, its number
   matches the stick's animations.

## Open Questions

1. A stick that is plugged in and has no animation in its folder `odrig` cannot be told
   from no stick at all by what the commands report today, so both hide the line. Is that
   enough, or should a reply tell the stick's state, which is a new member of a reply and
   needs the owner's yes?
