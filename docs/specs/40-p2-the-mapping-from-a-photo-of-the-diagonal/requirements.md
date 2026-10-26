# Requirements: the mapping from a photo of the diagonal

The seed is `project-seeds/40-p2-the-mapping-from-a-photo-of-the-diagonal/`. The owner
asked for it to be decided without a question pass; where these requirements decide a
point the seed leaves open, the decision is recorded in `docs/drifts.md`.

## 1. The photo

1.1 Settings' Mapping section has a button `From a photo`, shown while the installation's
mapping is editable, which takes an image file of the phone through the browser's file
chooser (`image/*`). No camera is part of the app.

1.2 Beside the button the app says what the photo must hold: the whole wall, the diagonal
showing, in a room as dark as can be had, the edge where the wires come in at the bottom
of the picture or at its left.
While the diagonal is not showing, a button `Show the diagonal` starts it through the
existing test; the app does not stop it by itself.

1.3 The picture is read with its orientation metadata applied, scaled to at most 900
pixels on its long side, and analysed in the app's own code. Nothing of it leaves the
phone, and it is dropped when the result is discarded, applied, or the screen is left.

## 2. The reading

2.1 The lit LEDs of the diagonal are found as the bright peaks of the picture at a level
of brightness taken from the picture itself: the count of peaks at or above each level is
watched from the brightest level down, and the level is where the count holds steady over
the longest stretch of levels, at one to a hundred peaks, the lit LEDs having come in
together before the lenses of the unlit LEDs and the room's reflections. A room's light on
the lenses is the normal case, not a fault. Peaks much wider than the others are dropped as
noise.

2.2 The LEDs stand on two grids of sixty places, the columns across the wall and the rows
up it, in threes. The pitch of each grid comes from the gaps between neighbouring LEDs,
and the picture's slant is taken out before the places are found. The slope of the stubs
tells whether the wall is seen upright, the positions across the picture, or from the
side, the positions down it; which edge of the picture the wires come in at, the picture
cannot tell, and the reading takes the advised edge first, the bottom or the left, and
offers the other. A stub at position p and height s means that the physical position p
shows snake s.

2.3 The new assignment gives position p the pin that drives snake s today: `pins[p-1]`
becomes the current `pins[s-1]`. When every position shows its own snake, the assignment
is the current one.

2.4 A best effort, never all or nothing: a gap of about two pitches inside a grid is a
place with no stub. The snake whose number no stub has goes to the position no stub is at;
with more than one, the remaining numbers go to the remaining positions in order, lowest
to leftmost.

2.5 A gap at an end of a grid, which the pitch cannot place, gives more than one reading:
the stubs fit the grid shifted by the gap either way. Every reading that fits is kept, at
most four, and the operator chooses, 2.9 and 3.3.

2.6 A picture whose count of bright peaks never holds steady, fewer than two lit LEDs, or
LEDs that fit no grid of sixty places, is a refusal that says how many bright spots were
found and repeats the advice of 1.2, with `Try another photo`.

## 3. The preview and the save

3.1 The result shows the photo scaled down with each stub circled and the number of the
snake its height gives, and a position with no stub marked with the number it gets.

3.2 Under it, in words: `Position p shows snake s.` for each position whose snake differs
from its own number; `Every position shows its own snake.` when none does; `Position p
shows no snake; snake s goes there.` for a dead line; and `n bright spots were ignored.`
when noise was dropped.

3.3 The readings are shown as a row of choices, each redrawing the preview: `Wires at
the bottom` and `Wires at the top` for a wall seen upright, `Wires at the left` and
`Wires at the right` for one seen from the side, the advised edge first, with `Position 1
dark` and `Position 20 dark` for a gap at an end of the positions, and `Lowest snake
missing` and `Highest snake missing` for a gap at an end of the heights; the app says that
only the wall can tell them apart: which edge the wires come in at, which end strip is
dark, and after Apply whether the diagonal begins at the bottom left.

3.4 `Apply` saves the assignment with `mapping set` at the revision of the mapping last
read, as the editor saves, and the editor's column shows the saved pins; a refusal or a
missing reply is said as there. `Discard` drops the result. After an Apply, `Other
reading` stays available while another reading exists, and applies it.

## 4. What does not change

4.1 Only `app/www/` changes: no command, no reply member, no library, no download, and
nothing of the core, the firmware or the emulator's host. The addition is in the order of
30 KB.

4.2 The analysis is the same in the APK, the browser and the emulator's Controller view.

## 5. Tests and documents

5.1 The app's suite checks the analysis in Chrome on photos the test makes: the diagonal
drawn as a wall of LEDs at a permutation, seen tilted, foreshortened, blurred, with noise
and uneven light, for the default mapping and several permutations, each read back
exactly; a dead line in the middle read with its snake put in the place that remains; a
dead line at an end offering both readings; two dead lines; a bright spot of noise
ignored; a wall seen from the side read with the wires at the left, and one seen from the
far edge read under the wires at the top; the owner's four photos of the unlit wall beside
the seed, each refused with the count found, and the owner's two screenshots of the
diagonal in a lit room, read to the mapping their stubs show; a photo whose orientation
metadata turns it, read upright.

5.2 The app's suite checks the screen against the emulator: the button and its words, the
diagonal offered and started, the preview with its numbers, the words of 3.2, the choices
of 3.3, Apply saving the permutation on the target, Discard, Other reading, and a conflict
on Apply said.

5.3 docs/android-app.md describes the feature; docs/decisions.md gets a dated line.

5.4 A new APK is built. The owner takes a photo of the installation with the diagonal
showing and checks the result on a phone; with the owner's leave that photo joins the
tests beside the seed.
