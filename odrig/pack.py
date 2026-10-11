"""pack: builds the folder that is installed, from a show, a mapping and tracked sources."""

import contextlib
import os
import shutil

from . import errors, files, jsonframes, mapping, odrg, show

MAPPING_NAME = "mapping.json"
SHOW_NAME = "show.json"


def pack(show_path, mapping_path, sources_dir, out_dir, compressed=True):
    """Writes `mapping.json`, `show.json` and every `.odrg` file the show names into `out_dir`.

    Nothing is written before every source has been read, checked and encoded. The folder
    is built beside `out_dir` and moved into place when it is complete.
    """
    mapping_bytes = files.read(mapping_path, missing=errors.MAPPING_MISSING)
    with errors.naming(mapping_path):
        canvas = mapping.loads(mapping_bytes)
    show_bytes = files.read(show_path, missing=errors.SHOW_MISSING)
    with errors.naming(show_path):
        listed = show.loads(show_bytes)

    out_dir = os.fspath(out_dir)
    if os.path.lexists(out_dir) and (not os.path.isdir(out_dir) or os.listdir(out_dir)):
        raise errors.Rejection(errors.OUTPUT_NOT_EMPTY, f"{out_dir}: the output folder is not empty")

    content = {MAPPING_NAME: mapping_bytes, SHOW_NAME: show_bytes}
    for name in show.files(listed):
        source = os.path.join(os.fspath(sources_dir), name[: -len(show.ENDING)] + ".json")
        source_bytes = files.read(source, missing=errors.FILE_MISSING)
        try:
            animation = jsonframes.loads(source_bytes)
        except errors.Rejection as rejection:
            raise errors.Rejection(
                errors.FILE_MALFORMED, f"{source}: {rejection.reason}: {rejection.detail}"
            ) from None
        if (animation.width, animation.height) != (canvas.width, canvas.height):
            raise errors.Rejection(
                errors.SIZE_MISMATCH,
                f"{source}: the canvas is {animation.width} x {animation.height} "
                f"and the mapping's is {canvas.width} x {canvas.height}",
            )
        with errors.naming(source):
            content[name] = odrg.encode(animation, compressed=compressed)

    _write_folder(out_dir, content)


def _write_folder(out_dir, content):
    """Makes `out_dir` hold exactly `content`, or leaves everything as it was.

    The files are written into `<out_dir>.part`, which then takes the place of `out_dir`.
    """
    building = os.path.abspath(out_dir) + ".part"
    existed = os.path.isdir(out_dir)
    made = False
    try:
        os.mkdir(building)
        made = True
        for name, data in content.items():
            with open(os.path.join(building, name), "wb") as file:
                file.write(data)
        if existed:
            os.rmdir(out_dir)
        os.replace(building, out_dir)
    except OSError as error:
        if made:
            shutil.rmtree(building, ignore_errors=True)
        if existed:
            with contextlib.suppress(OSError):
                os.mkdir(out_dir)
        why = error.strerror or type(error).__name__
        raise errors.Rejection(errors.CANNOT_WRITE, f"{error.filename or out_dir}: {why}") from None
