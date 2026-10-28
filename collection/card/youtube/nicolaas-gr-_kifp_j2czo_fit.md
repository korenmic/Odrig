# Splösh by Proxima - a pico-8 demo (2019)

- File: `nicolaas-gr-_kifp_j2czo_fit.odrg`
- Key: `b02543ee-14868500`
- Animation: 60 x 60, frames, 193.08 s, 4456 frames
- Source: https://www.youtube.com/watch?v=_KIFP_j2cZo
- Platform: YouTube
- Uploader: Nicolaas Groeneboom (Leuat)
- Title: Splösh by Proxima - a pico-8 demo (2019)
- Media id: _KIFP_j2cZo
- Part: whole
- Crop: 384:384:128:48
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the video with yt-dlp, then the crop of its dark bars with ffmpeg to 384:384:128:48, then `node --max-old-space-size=16000 converter/odrig.js import MEDIA FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=16000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at youtube/
- Added: 2026-10-27
- Notes: Made with is read from the job's script, convert_links.py, since the commands were not logged; Crop, Part and Converted come from its lines in quick-youtube-2026-10-26.log.
