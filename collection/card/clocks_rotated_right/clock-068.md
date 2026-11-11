# Clock 68: a kitchen timer with one hand, rotated 90 degrees clockwise

- File: `clock-068.odrg`
- Key: `85e54d56-17170`
- Animation: 60 x 60, frames, 30 s, 600 frames, 600 of 50 ms before the same ones are merged
- Source: the collection's widget `clocks/clock-068.odrgx` on the card, drawn into frames for one loop of 30 s with the fixed seed 1, then rotated 90 degrees clockwise
- Platform: unknown
- Uploader: the owner
- Title: a kitchen timer with one hand
- Media id: tile 68
- Part: whole: one loop of the widget, 30 s
- Crop: 121:113:901:771, the tile's cut, its printed number painted out
- Fit: scaled to 60 x 60 with a box filter and reduced to 8 colours
- Made with: `rotate-clocks.mjs` beside seed 54: the converter's drawing code draws `clock-068.odrgx` at 0, 50, ... ms of its loop with seed 1 into `FRAMES.json`, each frame turned; `node converter/odrig.js encode FRAMES.json clock-068.odrg`
- Converted: 2026-11-02
- Found: made from the collection's `clocks/clock-068.odrgx` in the repository
- Added: 2026-11-02
- Notes: A frames copy of the picture dial, its hands drawn as the player draws them at seed 1, so the same on every turn; turned 90 degrees clockwise, its top edge on the right.
