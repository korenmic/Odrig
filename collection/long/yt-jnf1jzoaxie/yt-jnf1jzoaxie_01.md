# Psychedelic Oil Projections - Party Like It's 1969

- File: `yt-jnf1jzoaxie_01.odrg`
- Key: `87ccc06a-66399967`
- Animation: 60 x 60, frames, 900 s, 27000 frames
- Source: https://www.youtube.com/watch?v=jnf1JZOaxIE
- Platform: YouTube
- Uploader: LIQUID dot LIGHTING
- Title: Psychedelic Oil Projections - Party Like It's 1969
- Media id: jnf1JZOaxIE
- Part: group 1 of 2, from 0 s for 900 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then for each piece of 150 s from S s, `node --max-old-space-size=8000 converter/odrig.js import CUT.mp4 PIECE.json --mapping mapping/legs-20.json --fit fit --start S --duration 150` (the last piece without `--duration`), `node --max-old-space-size=8000 converter/odrig.js encode PIECE.json PIECE.odrg` and `node converter/odrig.js check PIECE.odrg`, then the join of the pieces into X.odrg by join_odrg.py, checked against them by verify_join.mjs, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-jnf1jzoaxie/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was not proven a loop, so the whole of it, 1174.730 s, was converted in 2 groups of 15 minutes.
