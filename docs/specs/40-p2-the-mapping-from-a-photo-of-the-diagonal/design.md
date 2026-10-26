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
                                                // scaled to at most 900 pixels on its long side
export function analyse(picture);               // the reading below, from a picture
export function assignment(current, reading);   // the new pins from the current ones
```

`app/www/screens/photomap.js` is the screen: the button, the words, the file input
`#photo`, the preview canvas `#photo-preview`, the choices, Apply, Discard and Other
reading. It uses the editor's latest mapping and its save, which `screens/mapping.js`
exports as `latest()` and `saveFromPhoto(pins)`.

## The analysis

1. **Grey and peaks.** The grey of a pixel is `(2R + 5G + B) / 8`, smoothed over its 3 x 3
   neighbourhood. The peaks are the pixels no neighbour beats, at or above the median
   plus 24.
2. **The level.** The count of peaks at or above each level of brightness is taken from
   the brightest level down to that floor. The level is the middle of the longest stretch
   of levels over which the count stays the same, at 1 to 100 peaks; when no stretch is
   12 levels long the count never settles, `many`, refused. The peaks at or above the
   level are the lit LEDs, each with its glow width, the mean of its three shortest bright
   runs along the eight directions; peaks nearer than 1.5 widths are one LED, and an LED
   wider than 2.5 times the median width is noise, counted for the words.
3. **The slant.** Each axis is unslanted by the fraction of the other coordinate, from
   -0.3 to 0.3 in steps of 0.005, that makes the gaps between the sorted coordinates most
   even.
4. **The grids.** On each axis the LEDs are sorted; each step from the last place's value
   is compared with the median of the four nearest other gaps, and the next LED is
   `round(step / that median)` places on, at least one, or at the same place under 0.6 of
   a pitch. Places are 0 to 59; when the span passes 59, the sixty places that hold the
   most LEDs are kept and the others are noise. The y places count from the bottom.
5. **The stubs and the sides.** LEDs one place apart on both axes chain into stubs. The
   stubs rise to the right when the wall is seen upright and fall when it is seen from
   the side, a quarter turn either way; the picture is then read with the wires' edge at
   the bottom or the top, or at the left or the right, the positions along the picture's
   columns or down its rows. On each axis of the wall the residue, 0 to 2, at which the
   most stubs part into threes of consecutive places starts the threes.
6. **The readings.** On an axis with the LEDs spanning `n` places, the offset of the
   first place is the residue, or the residue plus the largest multiple of three up to
   `59 - n`; each side's pairs of offsets are readings: position `p = (col + x offset)
   div 3 + 1` shows the snake its LEDs vote for, `s = (row + y offset) div 3 + 1`, and
   the positions no LED is at get the numbers no position shows, in order. The readings
   come with the advised side first, the wires at the bottom or the left.
7. **The result.** `{points, readings: [{side, positions: snake or null by position,
   filled: [{position, snake}], xEnd, yEnd}], ignored, found, turned, frame}`, or
   `{refused: true, found, why}`. The preview draws the stubs and the filled positions of
   the chosen reading on the photo, scaled, through `frame.point`.

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
