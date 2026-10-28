# loop distort GIF by Psyklon

- File: `psyklon-paint-distort_fit.odrg`
- Key: `8531b020-295125`
- Animation: 60 x 60, frames, 3.2 s, 32 frames
- Source: https://giphy.com/gifs/trippy-psychedelic-paint-3oz8xYBsFsGm3BXkgU
- Platform: Giphy
- Uploader: Psyklon
- Title: loop distort GIF by Psyklon
- Media id: 3oz8xYBsFsGm3BXkgU
- Part: whole
- Crop: none
- Fit: fit, with the mapping mapping/legs-20.json
- Made with: the download of the GIF with curl, then `node --max-old-space-size=16000 converter/odrig.js import MEDIA FRAMES.json --mapping mapping/legs-20.json --fit fit`, then `node --max-old-space-size=16000 converter/odrig.js encode FRAMES.json X.odrg`, then `node converter/odrig.js check X.odrg`
- Converted: 2026-10-26
- Found: the card's folder odrig, at gifs/
- Added: 2026-10-27
- Notes: Made with is read from the job's script, convert_links.py, since the commands were not logged; Crop, Part and Converted come from its lines in quick-gifs-2026-10-26.log. The file downloaded was https://media.giphy.com/media/3oz8xYBsFsGm3BXkgU/giphy.gif.
