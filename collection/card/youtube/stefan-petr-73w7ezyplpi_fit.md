# FastFluid Preset for 128x128 LEDs

- File: `stefan-petr-73w7ezyplpi_fit.odrg`
- Key: `c323c408-10877304`
- Animation: 60 x 60, frames, 95.24 s, 2857 frames
- Source: https://www.youtube.com/watch?v=73w7eZyplpI
- Platform: YouTube
- Uploader: Stefan Petrick
- Title: FastFluid Preset for 128x128 LEDs
- Media id: 73w7eZyplpI
- Part: whole
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then `node --max-old-space-size=16000 converter/odrig.js import MEDIA FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=16000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at youtube/ and at its root
- Added: 2026-10-27
- Notes: Made with is read from the job's script, convert_links.py, since the commands were not logged; Crop, Part and Converted come from its lines in quick-youtube-2026-10-26.log.
