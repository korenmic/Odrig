# Psychedelic Colorful Ambient Waves - Trippy Blurred Video Background Animation (2 Hours/No Sound)

- File: `yt-xicnl77dchu_04.odrg`
- Key: `eee2ac1b-51542153`
- Animation: 60 x 60, frames, 900 s, 27000 frames
- Source: https://www.youtube.com/watch?v=XICnl77dchU
- Platform: YouTube
- Uploader: Ambiefix
- Title: Psychedelic Colorful Ambient Waves - Trippy Blurred Video Background Animation (2 Hours/No Sound)
- Media id: XICnl77dchU
- Part: group 4 of 9, from 2700 s for 900 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then for each piece of 150 s from S s, `node --max-old-space-size=8000 converter/odrig.js import CUT.mp4 PIECE.json --mapping mapping/legs-20.json --fit fit --start S --duration 150` (the last piece without `--duration`), `node --max-old-space-size=8000 converter/odrig.js encode PIECE.json PIECE.odrg` and `node converter/odrig.js check PIECE.odrg`, then the join of the pieces into X.odrg by join_odrg.py, checked against them by verify_join.mjs, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-xicnl77dchu/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was not proven a loop, so the whole of it, 7409.870 s, was converted in 9 groups of 15 minutes.
