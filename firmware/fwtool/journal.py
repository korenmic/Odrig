"""The journal of a change of the board's storage: a file in the work folder that names a
change from the moment before its first block is written until it is finished, so that a
change that was cut is finished or given up on purpose, by `recover-storage`."""

import json
import os

from . import Failure, paths

NAME = "change.json"
# The steps of a change: the free blocks are being written, the blocks in use are being
# written, the written blocks are being compared.
STEP_FREE, STEP_COMMIT, STEP_COMPARE = "free", "commit", "compare"


def path():
    return paths.STORAGE / NAME


def read():
    """The change the journal names, or None when there is no journal."""
    found = path()
    if not found.exists():
        return None
    try:
        change = json.loads(found.read_text(encoding="utf-8"))
        if not isinstance(change, dict) or change.get("step") not in (STEP_FREE, STEP_COMMIT, STEP_COMPARE):
            raise ValueError("it is not a journal of this tool")
        return change
    except (OSError, ValueError) as error:
        raise Failure("recovery-needed", f"the journal {found} cannot be read: {error}; a change of the board's storage may be unfinished. "
                      "Compare the board with its newest image, or install its show again with `install-show`, and remove the journal") from None


def refuse_open():
    """Refuses to go on while a change of the board's storage is not finished."""
    change = read()
    if change is not None:
        raise Failure("recovery-needed", f"a change of the board's storage was begun and not finished, at its step {change['step']}, as {path()} says; "
                      "run python3 firmware/fw.py recover-storage first")


def _write(change):
    target = paths.output(path())
    target.parent.mkdir(parents=True, exist_ok=True)
    spare = target.with_name(target.name + ".part")
    with open(spare, "w", encoding="utf-8") as file:
        file.write(json.dumps(change, sort_keys=True) + "\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(spare, target)


def begin(region, image_path, found):
    """Writes the journal of a change before its first block is written, at the step of
    the free blocks, and returns the change."""
    change = {
        "address": region.address, "size": region.size, "image": image_path.name, "step": STEP_FREE,
        "free": [[offset, len(content)] for offset, content in found.free],
        "in_use": [[offset, len(content)] for offset, content in found.in_use],
    }
    _write(change)
    return change


def step(change, name):
    """Records that a change has come to a step, before the step begins."""
    change["step"] = name
    _write(change)


def end():
    """Removes the journal of a change that is finished, or that was given up."""
    path().unlink(missing_ok=True)


def runs_of(change, image):
    """The runs of a change as its journal names them, with the bytes of the new image: the
    runs of free blocks and the runs of blocks in use."""
    return tuple([(offset, image[offset:offset + length]) for offset, length in change[part]] for part in ("free", "in_use"))


def outside(runs, size):
    """The stretches of a region of `size` bytes that none of the runs covers, as
    `(offset, length)`."""
    left, at = [], 0
    for offset, content in sorted(runs, key=lambda run: run[0]):
        if offset > at:
            left.append((at, offset - at))
        at = max(at, offset + len(content))
    if at < size:
        left.append((at, size - at))
    return left
