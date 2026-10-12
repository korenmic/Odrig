"""The show file of docs/show.md: the items that can be played and what plays at power-on."""

import dataclasses
import re

from . import errors, files as input_files, strictjson

VERSION = 1
LARGEST_ID = 65535
LONGEST_TURN = 65535
FILE_NAME = re.compile(r"[a-z0-9._-]{1,32}")
ENDING = ".odrg"

_MEMBERS = ("version", "brightness", "items")
_OPTIONAL = ("start",)
_ANIMATION_MEMBERS = ("id", "file")
_CYCLE_MEMBERS = ("id", "cycle", "seconds")


@dataclasses.dataclass(frozen=True)
class Item:
    id: int
    file: str | None
    cycle: tuple[int, ...] | None
    seconds: int | None


@dataclasses.dataclass(frozen=True)
class Show:
    brightness: int
    items: tuple[Item, ...]
    start: int | None


def read(path):
    """Reads a show file. A file that is absent is `show-missing`."""
    data = input_files.read(path, missing=errors.SHOW_MISSING)
    with errors.naming(path):
        return loads(data)


def loads(data):
    """Reads a show file given as bytes: its format first, then its ids."""
    try:
        show = _show(data)
    except errors.Rejection as rejection:
        raise errors.Rejection(
            errors.SHOW_MALFORMED, f"{rejection.reason}: {rejection.detail}"
        ) from None
    _check_ids(show)
    return show


def files(show):
    """The different file names the show uses, in the order of their first use."""
    names = []
    for item in show.items:
        if item.file is not None and item.file not in names:
            names.append(item.file)
    return names


def _malformed(detail):
    return errors.Rejection(errors.SHOW_MALFORMED, detail)


def _show(data):
    top = strictjson.loads(data)
    if type(top) is not dict:
        raise errors.Rejection(errors.BAD_JSON, "the top level is not an object")
    if "version" not in top:
        raise errors.Rejection(errors.MISSING_MEMBER, 'the file has no member "version"')
    version = strictjson.integer(top["version"], what="version")
    if version != VERSION:
        raise errors.Rejection(errors.BAD_VERSION, f"version is {version}, not {VERSION}")
    strictjson.members(top, _MEMBERS, _OPTIONAL)
    brightness = strictjson.integer(top["brightness"], 0, 255, what="brightness")
    listed = strictjson.array(top["items"], what="items")
    items = tuple(_item(entry, f"entry {position} of items") for position, entry in enumerate(listed, 1))
    start = strictjson.integer(top["start"], what="start") if "start" in top else None
    return Show(brightness, items, start)


def _item(entry, what):
    if type(entry) is not dict:
        raise errors.Rejection(errors.BAD_TYPE, f"{what} is not an object")
    if "file" in entry:
        strictjson.members(entry, _ANIMATION_MEMBERS, what=what)
    else:
        strictjson.members(entry, _CYCLE_MEMBERS, what=what)
    number = strictjson.integer(entry["id"], 1, LARGEST_ID, what=f"id of {what}")
    if "file" in entry:
        name = entry["file"]
        if type(name) is not str:
            raise errors.Rejection(errors.BAD_TYPE, f"file of item {number} is not a string")
        if not FILE_NAME.fullmatch(name) or not name.endswith(ENDING):
            raise _malformed(
                f"file of item {number} is not 1 to 32 characters from a-z, 0-9, -, _ and . ending in {ENDING}"
            )
        return Item(number, name, None, None)
    cycle = strictjson.array(entry["cycle"], what=f"cycle of item {number}")
    if not cycle:
        raise _malformed(f"cycle of item {number} is empty")
    for named in cycle:
        strictjson.integer(named, what=f"an entry of the cycle of item {number}")
    seconds = strictjson.integer(entry["seconds"], 1, LONGEST_TURN, what=f"seconds of item {number}")
    return Item(number, None, tuple(cycle), seconds)


def _check_ids(show):
    """Repeated ids first, then ids that no item has, then cycles that name a cycle."""
    kinds = {}
    for item in show.items:
        if item.id in kinds:
            raise errors.Rejection(errors.DUPLICATE_ID, f"two items have the id {item.id}")
        kinds[item.id] = "cycle" if item.cycle is not None else "animation"
    for item in show.items:
        for named in item.cycle or ():
            if named not in kinds:
                raise errors.Rejection(
                    errors.UNDEFINED_ID, f"the cycle of item {item.id} names the id {named}, which no item has"
                )
    if show.start is not None and show.start not in kinds:
        raise errors.Rejection(errors.UNDEFINED_ID, f"start names the id {show.start}, which no item has")
    for item in show.items:
        for named in item.cycle or ():
            if kinds[named] == "cycle":
                raise errors.Rejection(
                    errors.NESTED_CYCLE, f"the cycle of item {item.id} names item {named}, which is a cycle"
                )
