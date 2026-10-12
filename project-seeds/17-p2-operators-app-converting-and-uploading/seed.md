# Operators' app for Android: converting and uploading

## Summary

The second part of the operators' app: on the phone, pick a video or a GIF, fit it to the
canvas, see a preview, convert it with the project's converter and upload it to the
installation with a progress bar. With it come the sizes of the installed animations, the
free storage, and removing an animation.

## Priority

- `P2`

## Depends On

- Seed 09, for the app this is added to: its build, its connection to the target and its
  screens.
- Seed 06, for the JavaScript converter the app runs on the phone.
- Seed 07, for the commands that report the storage, remove an animation and upload one.
- Seed 16, for the playlist an uploaded animation joins.

## Product Context

The first part of the app, seed 09, is command and control: it shows what plays, lists the
animations, plays one, and switches the LEDs. The owner split the app on 2026-10-12 and
put this part second: uploading a new animation from a phone is not the first priority.

Converting media is heavy work and belongs on the phone, not on the board. The app
converts with the same converter that runs on computers, so a file made on a phone is the
file a computer would make.

To convert for the installation, the phone has to know the canvas. The owner approved,
for this purpose, that the reply to `status` reports the width and the height of the
canvas.

## Technical Constraints

- The app stays plain JavaScript, HTML and CSS, as seed 09 builds it.
- The converter library from seed 06 is used as it is. Any copy placed in the app's
  package is made by the build, not kept in the repository.
- Video and GIF files are decoded with what the phone's web view provides. No decoder is
  bundled.
- The app talks to its target only with the commands of `docs/commands.md`. The one
  change to the command list is that `status` reports the canvas size.
- The core's working memory for the 60 x 60 canvas with 100 items stays under 128 KB.
- Tests that need a phone are kept apart from those that do not.

## Required Behavior

1. The reply to `status` has two more members, `width` and `height`: the size of the
   canvas of the installed mapping, and `null` for both when there is no mapping that
   can be used.
2. The list of installed animations shows the size of each, and the free storage.
3. The operator can remove an animation, after confirming.
4. The operator can pick a video or a GIF from the phone, choose how it fits the canvas
   and which part of it to use, and see a preview of the result on a drawn canvas.
5. The operator can upload the converted animation. The upload shows the percentage sent
   and the speed, and can be cancelled.
6. An uploaded animation takes its place in the playlist without anything else being
   sent.
7. Every failure is shown in plain words: a file that cannot be converted, not enough
   space, a refused command with its error code.

## Definition Of Done

1. Tests drive the app's web code in headless Chrome against the emulator and cover
   converting and uploading the test GIF and the test mp4, and playing them afterwards.
2. The debug APK is built with the one command of seed 09.
3. The owner, with the APK on a phone, converts and uploads a video to the emulator on
   the local network and to the board on its own network, and sees it play.
4. Converting and uploading with the app are documented.

## Open Questions

None. Use the resolved behavior in this seed.
