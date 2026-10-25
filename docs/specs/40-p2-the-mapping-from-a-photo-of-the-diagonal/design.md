# Design: the mapping from a photo of the diagonal

## What this design relies on

- The diagonal, `mapping test on`, lights the pixels (x, x) of the 60 x 60 canvas. Snake
  s holds columns 3s-2 to 3s, so its lit pixels are the three at rows 3s-2 to 3s: a stub
  whose centre is the column 3s-1 and the row 3s-1. A physical position p drives the pin
  of some snake s, and shows that snake's stub at its own columns 3p-2 to 3p and at the
  rows 3s-1 ± 1.
- Settings' mapping editor, `app/www/screens/mapping.js`, reads the mapping, keeps its
  revision and pins, and saves a whole permutation with `client.mappingSet(revision,
  pins)`; its `draw` shows the saved column again. The Tests group starts the diagonal
  with `client.mappingTest(true)`.
- The Upload tab reads image files of the phone through a canvas, `app/www/convert.js`.
- The app's suite drives the web code in Chrome, `tests/app/support.py`, with page
  scenarios in `tests/app/page/scenarios/`; a scenario may fetch files of a folder the test
  names under `/m/`.

## The modules

`app/www/photo.js` is the analysis, with no DOM but a canvas it makes:

```js
export async function readPhoto(file);          // {width, height, grey: Uint8Array}, the picture
                                                // turned as its orientation metadata says and
                                                // scaled to at most 600 pixels on its long side
export function analyse(picture);               // the reading below, from a picture
export function assignment(current, reading);   // the new pins from the current ones
```

`app/www/screens/photomap.js` is the screen: the button, the words, the file input
`#photo`, the preview canvas `#photo-preview`, the choices, Apply, Discard and Other
reading. It uses the editor's latest mapping and its save, which `screens/mapping.js`
exports as `latest()` and `saveFromPhoto(pins)`.

## The analysis

1. **Grey and threshold.** The grey of a pixel is `(2R + 5G + B) / 8`. The threshold is
   the brightest of the grey's median plus 48, and the midpoint between the median and the
   99.8th percentile. Pixels at or above it are bright.
2. **Patches.** Bright pixels connected by their eight neighbours form patches; each has
   its mass and its centre, the mean of its pixels.
3. **Stubs.** The three LEDs of a stub may be three patches. Patches are joined by single
   linkage: the distances at which patches merge are sorted, and the cut is at the largest
   ratio between one merge distance and the next among cuts that leave 2 to 24 groups; the
   groups are the stubs. A group whose mass is under a quarter of the groups' median, or
   over four times it, is noise and is dropped, counted for the words.
4. **The tilt.** The centres are turned about the picture's middle by the angle, from -15
   to 15 degrees in steps of half a degree, that makes the gaps between the sorted x
   coordinates, and those between the sorted y coordinates, most even: the least sum of
   the two coefficients of variation.
5. **The grids.** On each axis the centres are sorted; the gap between each pair of
   neighbours is compared with the median of the four nearest other gaps, and the next
   centre is `round(gap / that median)` places on, at least one. The places of a stub are
   its x place and its y place, the y places counted from the bottom. Places are 0 to 19;
   a span over 19 places, or two stubs at one place of an axis, is `no grid`.
6. **The readings.** On an axis with the found stubs spanning `n` places, `20 - n`
   places are off the ends: the offset of the first found place may be any of 0 to
   `20 - n`. Each pair of an x offset and a y offset is a reading: position `p = x place
   + x offset + 1` shows snake `s = y place + y offset + 1`; the positions no stub is at
   get the numbers no stub has, in order. At most four readings are kept, the offsets 0
   and the largest on each axis; more than one dead line gives the same readings.
7. **The result.** `{stubs: [{x, y, position, snake}], readings: [{positions: snake or
   null by position, filled: [{position, snake}], xEnd, yEnd}], ignored, found}`, or
   `{refused: true, found}` for 2.6. The preview draws the stubs and the filled positions
   of the chosen reading on the photo, scaled.

The new pins: `assignment(current, reading)[p - 1] = current[s(p) - 1]`.

## The screen

Settings' Mapping section, after the column: the words of 1.2, `Show the diagonal` while
`latest().test` is false, `From a photo`, and the result's panel, hidden until a photo is
read: the preview, the words, the choices, `Apply`, `Discard`, `Other reading`. Apply
calls `saveFromPhoto(pins)`, which saves as a drag does and says the outcome in the
editor's summary; the panel stays until Discard or a target change, so that Other
reading can follow. Leaving Settings discards the photo. The file input is cleared after
each reading, so that the same file can be chosen again.

## Tests

`tests/app/page/scenarios/photo-analysis.js` makes photos on a canvas: a wall of 60 x 60
faint dots on a dark gradient, the stubs of a permutation as bright 3-pixel diagonals with
bloom, missing positions left dark, a spot of noise when asked; then rotated, scaled with a
mild perspective-like skew, blurred and sprinkled with noise; `analyse` on the pixels, for
the default mapping and permutations, a dead line in the middle, at an end, two dead
lines, noise; and the four photos of the seed fetched from `/m/`, refused.
`tests/app/media.py` writes a JPEG of a synthetic wall turned by an orientation tag;
`readPhoto` of it is read upright. `tests/app/page/scenarios/photomap.js` drives the
screen against the emulator and stand-in targets with a file given to the input through
a `DataTransfer`; `tests/app/test_photo.py` runs both. `tests/app/support.py` serves
`.jpg` under `/m/`.
