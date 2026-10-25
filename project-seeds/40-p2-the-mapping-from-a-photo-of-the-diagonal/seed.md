# The mapping from a photo of the diagonal

## Summary

The operators' app learns the installation's mapping from one photo. With the diagonal
showing, each snake lights a short stub at a height that tells its number; a photo of the
whole wall taken from the front holds twenty such stubs. The app finds them, reads from
their left-to-right order which physical position each is at and from their heights which
snake each position drives, shows the twenty found stubs numbered on the photo, and saves
the mapping with the existing command on one tap. The work is in the app's web code
alone, with no third-party library: no command, no reply member, nothing in the firmware,
the core or the emulator's host.

## Priority

- `P2`

## Depends On

- Seed 30, for the saved mapping, `mapping get` and `mapping set`, and the diagonal under
  `mapping test on`.
- Seed 36, for Settings' mapping editor, which this seed adds a way into, and the Tests
  group that shows the diagonal.
- Seed 37, for the app's reading of image files on the phone, which the Upload tab does
  already.

## Product Context

On 2026-10-25 the owner wired the twenty snakes of the installation and set their pins
by hand in the mapping editor, looking at the LEDs. The owner asked whether the app
could do that sorting by itself from a picture taken by the phone's camera, with no
camera inside the app: an image file is enough.

The diagonal makes this a one-photo job. It runs from the bottom left to the top right of
the canvas, so in snake n it lights three pixels at rows 3n-2 to 3n of its three columns:
a stub whose height grows with the snake's number. A physical position that drives the
wrong snake shows its stub at the wrong height. Twenty stubs, ranked left to right and
ranked by height, give the whole permutation.

## Technical Constraints

- Only the app's web code in `app/www/` changes, once for the APK, the browser and the
  emulator's Controller view. No download, no new dependency, no library: the canvas of
  the web view does the picture work, as the Upload tab's reading of images does today.
  The addition stays small, in the order of 30 KB.
- The photo is any image file the phone gives, read as the Upload tab reads one, with the
  picture turned as its orientation metadata says. It is scaled down for the analysis, to
  at most 480 pixels on its long side.
- The photo is taken from the front of the installation, upright, with the whole wall in
  it and the diagonal showing. The app says so where it asks for the photo. It cannot tell
  a photo taken from behind, whose order is mirrored; the numbered preview lets the
  operator see it before anything is saved.
- The analysis: the picture in grey, a threshold set from the picture's own brightness so
  that the lit stubs stand out of the dark wall, the bright pixels grouped into connected
  patches, the twenty largest patches taken. Their centres ranked by horizontal position
  give the physical positions 1 to 20; ranked by height, from the bottom, the snake number
  each position drives. The new pins are the position's current pins, in snake order: the
  pin at position p becomes the pin of the snake that p shows.
- Exactly twenty patches with all horizontal ranks and all height ranks distinct, else the
  app refuses, says how many it found, and advises: a darker room, a lower exposure, the
  whole wall in the frame, the phone upright, from the front.
- The result is saved only on the operator's tap, with the revision the mapping was read
  with, through the same path as the mapping editor's save: a conflict or a refusal is
  said as there. A saved mapping is shown in the editor as usual.
- Nothing is sent to any computer but the installation; the photo stays on the phone and
  is dropped when the screen is left.

## Required Behavior

1. Settings' Mapping section gets a button, From a photo, which asks for an image file.
   While the diagonal is not showing, the app offers to show it first, through the
   existing test command, and says what the photo must hold.
2. The app analyses the file and shows it scaled down, with each found stub circled and
   numbered by the snake it reads from the height, and the words of the result: for
   example `Position 3 shows snake 7`, for every position whose snake differs from its
   own number, or `Every position shows its own snake` when the mapping is right.
3. One button, Apply, saves the mapping, and the editor's column shows the saved pins;
   Discard drops the result. Applying while another controller changed the mapping is
   refused and said, as in the editor.
4. When the app finds fewer or more than twenty stubs, or two at the same horizontal or
   height rank, it says the count it found and the advice of the constraints, and offers
   to try another photo.
5. The analysis works alike in the APK, the browser and the emulator's Controller view.
6. The page of the app describes the feature, its one-photo idea, what the photo must
   hold, and what it cannot tell.

## Definition Of Done

1. All test suites that need no board and no phone pass, and the app's suite checks the
   feature in Chrome against the emulator with synthetic photos made in the test: the
   diagonal's picture rendered as a wall of LEDs, warped as a phone from an angle would
   see it, blurred and with noise and uneven light, for the default mapping and for
   several permutations, each read back exactly and applied; a photo with a stub missing
   and one with two stubs merged refused with the right count; a photo turned by its
   orientation metadata read right; and a conflict on Apply said.
2. A new APK is built, and the owner takes a photo of the installation with the diagonal
   showing and checks the result on a phone; that photo, with the owner's leave, joins
   the test vectors.

## Reference Photos

`photos/` beside this seed holds four of the owner's photos of the installation on its
table, unpowered, from four sides, with a README that says where each was taken from and
which edge is the canvas's bottom. None shows the diagonal: with each of them the analysis
must refuse. A photo with the diagonal showing is the owner's to take, in the definition
of done.

## Open Questions

None. The owner asked for this seed to be answered without a question pass; the
decisions it needed are taken in the constraints: one photo of the diagonal rather than a
sequence of tests, the analysis in the app's own code rather than a library, a numbered
preview and a tap before the save rather than a save on its own, and a refusal with the
count found rather than a guess when the stubs are not twenty.

## The Owner's Answers

On 2026-10-25 the owner asked whether the app could reorder the snakes' pins by itself
from an image file, a picture taken by the phone's camera, with no camera integrated
into the app, and asked for the feasibility, the added size and the time before building
it: it is possible with about 30 KB more in the app and about a day's work plus the
owner's trials with real photos. The owner then asked for the seed.
