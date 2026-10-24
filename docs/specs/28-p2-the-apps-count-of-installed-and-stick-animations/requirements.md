# Requirements: the app's count of installed and external animations

Seed: [`project-seeds/28-p2-the-apps-count-of-installed-and-stick-animations/seed.md`](../../../project-seeds/28-p2-the-apps-count-of-installed-and-stick-animations/seed.md).

On 2026-10-16 the owner had to empty the board to tell from the app whether a stick was
read. This spec puts two numbers on the app's dashboard: how many animations the board has
in its own storage, and how many come from the external storage, a microSD card since
seed 38 (a USB stick before it). The numbers come from replies the app already gets.

The owner answered the seed's one question on 2026-10-24: a plugged-in medium with no
animations shows 0. Further choices were made under the owner's mandate of 2026-10-24 and
are recorded in `docs/drifts.md`, "Seed 28".

In this document "the dashboard" is the app's show screen; "the internal line" and "the
external line" are its two lines about storage, which seed 29 added and which say the
capacity of the board's own storage and of the external storage; "the external storage" is
the player's drive, a microSD card or a USB stick; "an animation item" is an item of the
reply to `list` that is not a cycle; and "the newest list" is the list the app put
together from the last complete run of `list` requests.

## Requirement 1: the number of the board's own animations

1. The internal line SHALL say the number of the show's own animations, from `animations`
   of the newest reply to `space`, before the capacity: `Internal storage: 84 animations,
   free 6.7 MB of 13.5 MB`, and `1 animation` for one.
2. While the newest `status` reports that the show is invalid, the internal line SHALL say
   `animations not known` in place of the number, because `space` reports 0 then.
3. While the app has no reply to `space`, the internal line SHALL say what it says today.

## Requirement 2: the number of the external storage's animations

1. While the newest reply to `space` reports the external storage present, the external
   line SHALL say the number of its animations before its capacity:
   `External storage: 12 animations, free 3.1 GB of 31.9 GB (read-only).`, with
   `1 animation` for one and `0 animations` for a medium without any.
2. While the external storage is absent, the external line SHALL say what it says today,
   `External storage: absent (read-only).`, with no number and no label of a number.
3. With the medium present and its capacity unknown, the line SHALL say the number and
   that the capacity is unavailable.

## Requirement 3: how the external number is found

1. The number SHALL be found from the newest list and the newest reply to `space`: when
   the animation items carry a member that tells the storage of each, the items that it
   names external are counted; otherwise the number is the animation items of the newest
   list less `animations` of `space`.
2. The number SHALL never be found from the ids of the items.
3. When the difference is below 0, or no list has been put together since the app began
   with this address, the line SHALL say `animations not known yet` in place of the
   number.

## Requirement 4: while the board reads its animations

1. While the newest `list` request of the app was answered `busy`, the external line SHALL
   say `animations not known yet` in place of the number, and the internal line SHALL
   still say its number.
2. When a list is complete again, both numbers SHALL be shown.

## Requirement 5: what does not change

1. The app SHALL send the same lines, no more often than today. No command is added, no
   reply gains a member, and nothing changes in the board's firmware, the core or the
   emulator's host.
2. The storage screen's two lines SHALL use the same words as the dashboard's, being made
   by the same code.
3. What the app shows SHALL be the same in the APK and in the emulator's Controller view.

## Requirement 6: tests and documents

1. The app's suite SHALL check in Chrome: against the emulator with no drive, with a drive
   of animations, with a drive whose folder `odrig` is empty, and with a drive plugged in
   and pulled out while the app runs; and against a stand-in target that answers `list`
   with `busy`, and one whose show is invalid.
2. `docs/android-app.md` SHALL say what the two numbers are, and the check on a phone
   SHALL have a step for them.
3. Every suite that needs no board and no phone SHALL pass, and a new APK SHALL be built.
4. On a phone, the owner checks the two numbers against the board with the card in and
   with it out.
