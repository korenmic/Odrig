# Message clock 3 · טמפרטורה

- File: `v7-temperature.odrgx`
- Key: `41660ebf-9574`
- Animation: 60 x 60, widget, 36.6 s, 0 frames: the player draws it
- Source: the owner's retained `led_grid_simulator_v7_tabs_v4_no_blink.html`, tab 3, beside the generator's source folder
- Platform: unknown
- Uploader: the owner
- Title: 3 · טמפרטורה
- Media id: source tab 3
- Part: whole: this tab alone, repeated without continuing into another tab
- Crop: none
- Fit: drawn at 60 x 60 in the source default split layout, text above rolling digits and the bottom moving square
- Made with: `node project-seeds/59-p2-message-clock-widgets-and-clocks-only-mode/source/generate.mjs SOURCES`; `node converter/odrig.js encode SOURCE.json ANIMATION.odrgx`; `node converter/odrig.js thumbnail ANIMATION.odrgx --catalog thumbnails --card collection/card --beside`
- Converted: 2026-10-30
- Found: the retained source page in the repository
- Added: 2026-10-30
- Notes: All 6 source captions preserve their exact Hebrew wording, punctuation, order and timing. The existing authored small Hebrew font and scaled large-digit font replace Arial/monospace; text scales 0.8 horizontally and 8/9 vertically with 9-pixel line spacing, digits scale 0.6 horizontally and 2/3 vertically and sit centered in their 16-row wheel windows. Area sampling and alpha4 quantization keep masks portable. The source's unlit-dot decoration is omitted from physical pixels. Time and rolling wheels are deterministic from the turn seed, not a real-time clock. The standard GIF is a short accelerated preview sampled across the loop; the runtime retains the complete 36.6-second sequence. Source/font hashes and role flags are in the generator manifest.
