# Acid Warp (PC MS-DOS, 1992)

- File: `yt-smrp9nezqso_02.odrg`
- Key: `49b9f0cb-47728067`
- Animation: 60 x 60, frames, 900 s, 24371 frames
- Source: https://www.youtube.com/watch?v=smRP9neZqso
- Platform: YouTube
- Uploader: MS-DOS Friends
- Title: Acid Warp (PC MS-DOS, 1992)
- Media id: smRP9neZqso
- Part: group 2 of 3, from 900 s for 900 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then for each piece of 150 s from S s, `node --max-old-space-size=8000 converter/odrig.js import CUT.mp4 PIECE.json --mapping mapping/legs-20.json --fit fit --start S --duration 150` (the last piece without `--duration`), `node --max-old-space-size=8000 converter/odrig.js encode PIECE.json PIECE.odrg` and `node converter/odrig.js check PIECE.odrg`, then the join of the pieces into X.odrg by join_odrg.py, checked against them by verify_join.mjs, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-smrp9nezqso/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was not proven a loop, so the whole of it, 1846.070 s, was converted in 3 groups of 15 minutes.
