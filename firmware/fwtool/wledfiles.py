"""WLED's stored settings in a storage image: its JSON files read as objects, and written
back with every other file left as it was."""

import json

from littlefs.errors import LittleFSError

from . import Failure, storage

# The configuration, which WLED serves to every device on its network, and the secrets,
# which it serves to none.
CONFIG = "/cfg.json"
SECRETS = "/wsec.json"


def files_of(image):
    """Every file of a storage image: the content of each by its path."""
    return storage.files_in(storage.mount(image))


def _not_json(name):
    raise ValueError(name)


def object_of(files, path):
    """The object one of WLED's settings files holds. An absent file counts as empty."""
    if path not in files:
        return {}
    try:
        value = json.loads(files[path].decode("utf-8"), parse_constant=_not_json)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Failure("wled-settings-malformed", f"{path} in the board's storage is not JSON") from None
    if not isinstance(value, dict):
        raise Failure("wled-settings-malformed", f"{path} in the board's storage is not a JSON object")
    return value


def inner(value, path, *names):
    """The object at a path of member names inside a settings object, or None when a
    member of the path is absent. A member that is there and is no object is refused."""
    for depth, name in enumerate(names):
        if name not in value:
            return None
        value = value[name]
        if not isinstance(value, dict):
            raise Failure("wled-settings-malformed", f"{'.'.join(names[:depth + 1])} in {path} in the board's storage is not an object")
    return value


def text_of(value):
    """A value as WLED writes its settings files: JSON without spaces."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def written(image, objects):
    """A new image in which each of the settings files given holds the object given for
    it. Returns the image and its files. The file system keeps its version and its size,
    and every other file its bytes, or the image is refused."""
    system = storage.mount(image)
    before = storage.files_in(system)
    try:
        for path, value in objects.items():
            with system.open(path, "wb") as file:
                file.write(text_of(value).encode("utf-8"))
        system.unmount()
    except LittleFSError as error:
        if error.code == storage.NO_SPACE:
            raise Failure("no-space", "WLED's stored settings do not fit into storage") from None
        raise Failure("verify-failed", f"the file system refused WLED's stored settings: {error}") from None
    made = bytes(system.context.buffer)
    if storage.geometry(made) != storage.geometry(image):
        raise Failure("verify-failed", "the file system changed its version or its size")
    after = files_of(made)
    difference = storage.differing(_others(after, objects), _others(before, objects))
    if difference:
        raise Failure("verify-failed", f"a file other than {' and '.join(objects)} changed in the new image: {difference}")
    return made, after


def _others(files, apart_from):
    return {path: content for path, content in files.items() if path not in apart_from}
