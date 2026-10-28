# Atari STe demo - Blitter Plasma

- File: `cryptkeeper-vzpmbe1orri_fit.odrg`
- Key: `b0106d19-12110095`
- Animation: 60 x 60, frames, 284.1 s, 8195 frames
- Source: https://www.youtube.com/watch?v=vzPMBE1ORRI
- Platform: YouTube
- Uploader: Cryptkeeper
- Title: Atari STe demo - Blitter Plasma
- Media id: vzPMBE1ORRI
- Part: whole
- Crop: 572:356:82:48
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the crop of its dark bars with ffmpeg to 572:356:82:48, then `node --max-old-space-size=16000 converter/odrig.js import MEDIA FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=16000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at youtube/
- Added: 2026-10-27
- Notes: Made with is read from the job's script, convert_links.py, since the commands were not logged; Crop, Part and Converted come from its lines in quick-youtube-2026-10-26.log.
