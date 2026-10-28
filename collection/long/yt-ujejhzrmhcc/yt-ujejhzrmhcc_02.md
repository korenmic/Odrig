# A Vibrant Trippy Visual Loop | Colorful Screensaver for 10 Hours (4K, Silent)

- File: `yt-ujejhzrmhcc_02.odrg`
- Key: `9e47c7e4-48435621`
- Animation: 60 x 60, frames, 900 s, 27000 frames
- Source: https://www.youtube.com/watch?v=UJEJHzRmhcc
- Platform: YouTube
- Uploader: Urban Sightline
- Title: A Vibrant Trippy Visual Loop | Colorful Screensaver for 10 Hours (4K, Silent)
- Media id: UJEJHzRmhcc
- Part: group 2 of 8, from 900 s for 900 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then for each piece of 150 s from S s, `node --max-old-space-size=8000 converter/odrig.js import CUT.mp4 PIECE.json --mapping mapping/legs-20.json --fit fit --start S --duration 150` (the last piece without `--duration`), `node --max-old-space-size=8000 converter/odrig.js encode PIECE.json PIECE.odrg` and `node converter/odrig.js check PIECE.odrg`, then the join of the pieces into X.odrg by join_odrg.py, checked against them by verify_join.mjs, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-ujejhzrmhcc/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was proven a loop of 6400 s from 0 s, so one period of it was converted, in 8 groups of 15 minutes.
