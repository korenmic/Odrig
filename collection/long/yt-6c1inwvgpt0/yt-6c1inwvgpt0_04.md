# Relaxing Digital Lava Lamp | Psychedelic Background/Screensaver Video Loop [1 Hour, 4K]

- File: `yt-6c1inwvgpt0_04.odrg`
- Key: `4093bc5e-20104458`
- Animation: 60 x 60, frames, 900 s, 27000 frames
- Source: https://www.youtube.com/watch?v=6C1INWVGPT0
- Platform: YouTube
- Uploader: waveform
- Title: Relaxing Digital Lava Lamp | Psychedelic Background/Screensaver Video Loop [1 Hour, 4K]
- Media id: 6C1INWVGPT0
- Part: group 4 of 4, from 2700 s for 900 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then for each piece of 150 s from S s, `node --max-old-space-size=8000 converter/odrig.js import CUT.mp4 PIECE.json --mapping mapping/legs-20.json --fit fit --start S --duration 150` (the last piece without `--duration`), `node --max-old-space-size=8000 converter/odrig.js encode PIECE.json PIECE.odrg` and `node converter/odrig.js check PIECE.odrg`, then the join of the pieces into X.odrg by join_odrg.py, checked against them by verify_join.mjs, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-6c1inwvgpt0/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was not proven a loop, so the whole of it, 3600.000 s, was converted in 4 groups of 15 minutes. This last group runs to the end of the video.
