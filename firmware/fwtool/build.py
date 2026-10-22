"""Builds an image with PlatformIO, in WLED's folder or in the folder of the standalone
firmware, on the software known good or on the newer USB software, and keeps it in the
work folder with its SHA-256 beside it."""

import collections
import hashlib
import shutil
import subprocess
import sys

from . import Failure, env, paths, standalone, toolchain, wled

Kind = collections.namedtuple("Kind", "environment image")

KINDS = {
    "firmware": Kind("odrig", "odrig-firmware.bin"),
    "probe": Kind("odrig_probe", "odrig-probe.bin"),
    "stock": Kind("esp32s3dev_16MB_opi", "stock-built.bin"),
    "standalone": Kind("odrig_standalone", "odrig-standalone.bin"),
    "standalone-probe": Kind("odrig_standalone_probe", "odrig-standalone-probe.bin"),
    "trial": Kind("odrig_trial", "odrig-trial.bin"),
    "trial-probe": Kind("odrig_trial_probe", "odrig-trial-probe.bin"),
    "microsd": Kind("odrig_microsd", "odrig-microsd.bin"),
}

# The kinds that are built without WLED, as a project of their own.
WITHOUT_WLED = ("standalone", "standalone-probe")

# The kinds that are built on the newer USB software, with its own PlatformIO.
ON_NEWER = ("trial", "trial-probe", "microsd")

# The trial's kind that takes the place of the firmware and of the probe build.
TRIAL_OF = {"firmware": "trial", "probe": "trial-probe"}

# The size of the first application partition of WLED's 16 MB layout.
APPLICATION_SIZE = 0x300000


def image_path(kind):
    return paths.OUT / KINDS[kind].image


def checksum_path(image):
    return image.with_name(image.name + ".sha256")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for piece in iter(lambda: file.read(1 << 20), b""):
            digest.update(piece)
    return digest.hexdigest()


def write_checksum(image):
    checksum_path(image).write_text(f"{sha256(image)}  {image.name}\n")


def check_size(image, limit=APPLICATION_SIZE):
    size = image.stat().st_size
    if size > limit:
        raise Failure("image-too-large", f"{image.name} has {size} bytes and the application partition {limit}")
    return size


def checked_image(image):
    """An image that is there and matches the SHA-256 written beside it."""
    if not image.is_file():
        raise Failure("image-missing", f"{image} is not there; build it first")
    beside = checksum_path(image)
    if not beside.is_file():
        raise Failure("image-missing", f"{beside} is not there; build the image again")
    written = beside.read_text().split()
    if not written or written[0] != sha256(image):
        raise Failure("checksum-mismatch", f"{image.name} does not have the SHA-256 written in {beside.name}")
    return image


def keep(built, image):
    """Copies a built image into the work folder's output, with its checksum."""
    image = paths.output(image)
    if not built.is_file():
        raise Failure("build-failed", f"the build left no {built}")
    size = check_size(built)
    image.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(built, image)
    write_checksum(image)
    return size


def pio_command(environment, verbose=False, folder=None, python=None):
    command = [str(paths.PYTHON if python is None else python), "-m", "platformio", "run", "-d", str(paths.WLED if folder is None else folder), "-e", environment]
    return command + ["-v"] if verbose else command


def build(kind, verbose=False):
    """Builds one kind of image. Returns its path and its size."""
    made = KINDS[kind]
    newer = kind in ON_NEWER
    toolchain.python_environment()
    if newer:
        toolchain.newer_environment()
    if kind in WITHOUT_WLED:
        wled.check()
        folder = standalone.write_project()
    else:
        wled.restore_and_patch(patches=None if kind == "stock" else paths.PATCHES)
        wled.write_override()
        folder = paths.WLED
    python = paths.NEWER_PYTHON if newer else paths.PYTHON
    done = subprocess.run(pio_command(made.environment, verbose, folder, python), env=env.child(newer=newer), stdout=sys.stderr)
    if done.returncode != 0:
        raise Failure("build-failed", f"PlatformIO ended with status {done.returncode} for the environment {made.environment}")
    image = image_path(kind)
    size = keep(folder / ".pio" / "build" / made.environment / "firmware.bin", image)
    return image, size
