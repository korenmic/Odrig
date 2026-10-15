"""Writes the media the app's suite converts into a folder: a GIF and an mp4 in H.264.

It is run by the Python of `.venv`, which has the packages that write them:
`.venv/bin/python -m tests.app.media FOLDER`.
"""

import pathlib
import sys

from PIL import Image

from tests.converter import media_fixtures

# A GIF of four pictures of 32 x 16: a flat colour with a bar of another colour that
# moves, so that each way of fitting it gives another picture. The last delay is 0, which
# counts as 100 ms.
GIF_SIZE = (32, 16)
GIF_DELAYS = (30, 50, 70, 0)
BAR = 8


def gif_pictures():
    pictures = []
    for number in range(len(GIF_DELAYS)):
        picture = Image.new("RGB", GIF_SIZE, media_fixtures.COLOURS[number])
        for x in range(BAR * number, BAR * number + BAR):
            for y in range(GIF_SIZE[1]):
                picture.putpixel((x, y), media_fixtures.COLOURS[number + 4])
        pictures.append(picture)
    return pictures


def main(folder):
    folder = pathlib.Path(folder)
    media_fixtures.save_gif(folder / "clip.gif", gif_pictures(), GIF_DELAYS)
    media_fixtures.write_video(folder / "clip.mp4", media_fixtures.COLOURS, codec="libx264")
    # Ten seconds, long enough to be stopped while it is made.
    media_fixtures.write_video(folder / "long.mp4", media_fixtures.COLOURS * 25, codec="libx264")
    # A file named as a video that is none.
    (folder / "broken.mp4").write_bytes(b"this is not a video\n" * 50)


if __name__ == "__main__":
    main(sys.argv[1])
