# Clock 36: a golden wrist watch, rotated 90 degrees clockwise

- File: `clock-036.odrg`
- Key: `59237a75-7004`
- Animation: 60 x 60, frames, 30 s, 586 frames, 600 of 50 ms before the same ones are merged
- Source: the collection's widget `clocks/clock-036.odrgx` on the card, drawn into frames for one loop of 30 s with the fixed seed 1, then rotated 90 degrees clockwise
- Platform: unknown
- Uploader: the owner
- Title: a golden wrist watch
- Media id: tile 36
- Part: whole: one loop of the widget, 30 s
- Crop: 123:124:643:387, the tile's cut, its printed number painted out
- Fit: scaled to 60 x 60 with a box filter and reduced to 8 colours
- Made with: `rotate-clocks.mjs` beside seed 54: the converter's drawing code draws `clock-036.odrgx` at 0, 50, ... ms of its loop with seed 1 into `FRAMES.json`, each frame turned; `node converter/odrig.js encode FRAMES.json clock-036.odrg`
- Converted: 2026-11-02
- Found: made from the collection's `clocks/clock-036.odrgx` in the repository
- Added: 2026-11-02
- Notes: A frames copy of the picture dial, its hands drawn as the player draws them at seed 1, so the same on every turn; turned 90 degrees clockwise, its top edge on the right.
