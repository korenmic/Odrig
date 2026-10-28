# C64 Demo: ECM Plasma by Desire 13 October 2020!

- File: `c64-fvbx_kaqtii_fit.odrg`
- Key: `eb9a9a70-6231006`
- Animation: 60 x 60, frames, 61.88 s, 1547 frames
- Source: https://www.youtube.com/watch?v=fvBx_KaqtII
- Platform: YouTube
- Uploader: C64!
- Title: C64 Demo: ECM Plasma by Desire 13 October 2020!
- Media id: fvBx_KaqtII
- Part: whole
- Crop: 608:380:52:50
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the crop of its dark bars with ffmpeg to 608:380:52:50, then `node --max-old-space-size=16000 converter/odrig.js import MEDIA FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=16000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at youtube/
- Added: 2026-10-27
- Notes: Made with is read from the job's script, convert_links.py, since the commands were not logged; Crop, Part and Converted come from its lines in quick-youtube-2026-10-26.log.
