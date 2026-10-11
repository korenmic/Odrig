"""JSON frames, the tracked source format of an animation: strict reading, canonical writing.

A picture is a `bytes` object of 3 * W * H bytes: red, green and blue for each pixel, in the
pixel order of docs/format.md (bottom row first, each row left to right). A frame is a pair
`(ms, picture)`.
"""

import dataclasses
import struct

from . import errors, files, strictjson

VERSION = 1
WHITE = 0xFFFFFF

_MEMBERS = ("version", "width", "height", "frames")
_FRAME_MEMBERS = ("ms", "pixels")


@dataclasses.dataclass(frozen=True)
class Animation:
    width: int
    height: int
    frames: tuple[tuple[int, bytes], ...]


def loads(data):
    """Reads a JSON frames file given as bytes. Frames are kept as the file lists them."""
    top = strictjson.loads(data)
    if type(top) is not dict:
        raise errors.Rejection(errors.BAD_JSON, "the top level is not an object")
    if "version" not in top:
        raise errors.Rejection(errors.MISSING_MEMBER, 'the file has no member "version"')
    version = strictjson.integer(top["version"], what="version")
    if version != VERSION:
        raise errors.Rejection(errors.BAD_VERSION, f"version is {version}, not {VERSION}")
    strictjson.members(top, _MEMBERS)
    width = strictjson.integer(top["width"], 1, what="width")
    height = strictjson.integer(top["height"], 1, what="height")
    listed = strictjson.array(top["frames"], what="frames")
    if not listed:
        raise errors.Rejection(errors.NO_FRAMES, "frames is empty")
    count = width * height
    frames = []
    for number, frame in enumerate(listed, 1):
        what = f"frame {number}"
        strictjson.members(frame, _FRAME_MEMBERS, what=what)
        ms = strictjson.integer(frame["ms"], 1, what=f"ms of {what}")
        pixels = strictjson.array(frame["pixels"], what=f"pixels of {what}")
        if len(pixels) != count:
            raise errors.Rejection(
                errors.BAD_PIXEL_COUNT,
                f"{what} has {len(pixels)} pixels, not {width} * {height} = {count}",
            )
        frames.append((ms, _picture(pixels, what)))
    return Animation(width, height, tuple(frames))


def read(path):
    """Reads a JSON frames file."""
    data = files.read(path)
    with errors.naming(path):
        return loads(data)


def merged(frames):
    """The frames with consecutive identical pictures joined into one, durations added."""
    result = []
    for ms, picture in frames:
        if result and result[-1][1] == picture:
            result[-1] = (result[-1][0] + ms, picture)
        else:
            result.append((ms, picture))
    return result


def dumps(animation, merge=True):
    """The canonical bytes of a JSON frames file, with identical neighbours merged.

    `merge=False` keeps every frame as given. Only the expected frames of the test vectors
    are written that way: one frame for every frame record.
    """
    size = 3 * animation.width * animation.height
    if animation.width < 1 or animation.height < 1 or not animation.frames:
        raise ValueError("an animation has a canvas and at least one frame")
    lines = []
    for ms, picture in merged(animation.frames) if merge else animation.frames:
        if ms < 1 or len(picture) != size:
            raise ValueError("a frame lasts at least 1 ms and has 3 * W * H bytes")
        lines.append(f'    {{"ms": {ms}, "pixels": {list(colours(picture))}}}')
    text = (
        "{\n"
        f'  "version": {VERSION},\n'
        f'  "width": {animation.width},\n'
        f'  "height": {animation.height},\n'
        '  "frames": [\n' + ",\n".join(lines) + "\n"
        "  ]\n"
        "}\n"
    )
    return text.encode("utf-8")


def write(path, animation):
    """Writes the animation as a canonical JSON frames file."""
    files.write(path, dumps(animation))


def colours(picture):
    """The colour of every pixel of a picture as the integer red * 65536 + green * 256 + blue."""
    count = len(picture) // 3
    padded = bytearray(4 * count)
    padded[1::4] = picture[0::3]
    padded[2::4] = picture[1::3]
    padded[3::4] = picture[2::3]
    return struct.unpack(f">{count}I", padded)


def colour_count(frames):
    """The number of different colours that appear in the pictures of the frames."""
    seen = set()
    for picture in {picture for _, picture in frames}:
        seen.update(colours(picture))
    return len(seen)


def _picture(pixels, what):
    """The picture of a `pixels` array, checking every entry in order."""
    if set(map(type, pixels)) != {int} or min(pixels) < 0 or max(pixels) > WHITE:
        for position, pixel in enumerate(pixels):
            strictjson.integer(pixel, 0, WHITE, what=f"pixel {position} of {what}")
    packed = bytearray(struct.pack(f">{len(pixels)}I", *pixels))
    del packed[0::4]
    return bytes(packed)
