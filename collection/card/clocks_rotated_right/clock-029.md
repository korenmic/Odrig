# Clock 29: a fitness band with the hours above the minutes, rotated 90 degrees clockwise

- File: `clock-029.odrg`
- Key: `6de6ecc2-2401`
- Animation: 60 x 60, frames, 30 s, 277 frames, 600 of 50 ms before the same ones are merged
- Source: the collection's widget `clocks/clock-029.odrgx` on the card, drawn into frames for one loop of 30 s with the fixed seed 1, then rotated 90 degrees clockwise
- Platform: unknown
- Uploader: the owner
- Title: a fitness band with the hours above the minutes
- Media id: tile 29
- Part: whole: one loop of the widget, 30 s
- Crop: 121:122:1028:260, the tile's cut, its printed number painted out
- Fit: scaled to 60 x 60 with a box filter and reduced to 8 colours
- Made with: `rotate-clocks.mjs` beside seed 54: the converter's drawing code draws `clock-029.odrgx` at 0, 50, ... ms of its loop with seed 1 into `FRAMES.json`, each frame turned; `node converter/odrig.js encode FRAMES.json clock-029.odrg`
- Converted: 2026-11-02
- Found: made from the collection's `clocks/clock-029.odrgx` in the repository
- Added: 2026-11-02
- Notes: A frames copy of the picture display, its digits drawn as the player draws them at seed 1, so the same on every turn; turned 90 degrees clockwise, its top edge on the right.
