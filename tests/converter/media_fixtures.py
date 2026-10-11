"""Builds the short media files that the import tests read. No media file is tracked.

Every frame is one flat colour from a fixed list, so a frame that went through a lossy
encoder is still recognised by the list colour nearest to it.
"""

import os
from fractions import Fraction

import av
import numpy
from PIL import Image

COLOURS = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
    (128, 128, 128),
    (255, 128, 0),
    (0, 128, 255),
)
VIDEO_SIZE = (64, 36)
VIDEO_RATE = 25
FRAME_MS = 1000 // VIDEO_RATE


def nearest(colour):
    """The position in `COLOURS` of the list colour nearest to a colour."""
    return min(
        range(len(COLOURS)),
        key=lambda index: sum((a - int(b)) ** 2 for a, b in zip(COLOURS[index], colour)),
    )


def write_gif(path, colours, delays, size=(8, 4)):
    """A GIF whose frames are flat colours shown for the given delays in milliseconds."""
    images = [Image.new("RGB", size, colour) for colour in colours]
    save_gif(path, images, delays)


def save_gif(path, images, delays):
    images[0].save(path, save_all=True, append_images=images[1:], duration=list(delays), loop=0)


def write_video(path, colours, first_pts=0, codec="mpeg4", pixels="yuv420p", alpha=None):
    """An mp4 or mov, by the ending of `path`: 64 x 36, 25 frames per second, flat colours.

    `alpha`, for a codec that keeps transparency, makes the right half of every frame
    transparent with that colour under it.
    """
    width, height = VIDEO_SIZE
    with av.open(os.fspath(path), "w") as container:
        stream = container.add_stream(codec, rate=VIDEO_RATE)
        stream.width, stream.height, stream.pix_fmt = width, height, pixels
        stream.codec_context.time_base = Fraction(1, VIDEO_RATE)
        for number, colour in enumerate(colours):
            array = numpy.zeros((height, width, 4), dtype=numpy.uint8)
            array[:, :, :3] = colour
            array[:, :, 3] = 255
            if alpha is not None:
                array[:, width // 2:, :3] = alpha
                array[:, width // 2:, 3] = 0
            frame = av.VideoFrame.from_ndarray(array, format="rgba")
            frame.pts = first_pts + number
            frame.time_base = Fraction(1, VIDEO_RATE)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
