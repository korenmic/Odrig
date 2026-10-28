# Acid Warp (PC MS-DOS, 1992)

- File: `yt-smrp9nezqso_03.odrg`
- Key: `e27f8571-1943194`
- Animation: 60 x 60, frames, 46.06 s, 1230 frames
- Source: https://www.youtube.com/watch?v=smRP9neZqso
- Platform: YouTube
- Uploader: MS-DOS Friends
- Title: Acid Warp (PC MS-DOS, 1992)
- Media id: smRP9neZqso
- Part: group 3 of 3, from 1800 s for 46.070 s
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the cut of the group with ffmpeg into CUT.mp4 without loss, then `node --max-old-space-size=24000 converter/odrig.js import CUT.mp4 FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=24000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at long/yt-smrp9nezqso/
- Added: 2026-10-27
- Notes: Made with is read from the script run_long.sh, since the commands were not logged. The video was not proven a loop, so the whole of it, 1846.070 s, was converted in 3 groups of 15 minutes. This last group runs to the end of the video.
