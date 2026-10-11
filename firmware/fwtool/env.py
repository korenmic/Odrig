"""The environment of every process the tool starts.

It keeps PlatformIO, npm and pip inside the work folder: their packages and every cache.
`HOME` is left as the caller has it.
"""

import os

from . import paths

FOLDERS = {
    "PLATFORMIO_CORE_DIR": paths.PIO_CORE,
    "PLATFORMIO_BUILD_CACHE_DIR": paths.PIO_CACHE,
    "npm_config_cache": paths.NPM_CACHE,
    "PIP_CACHE_DIR": paths.PIP_CACHE,
}
SWITCHES = {
    "PLATFORMIO_SETTING_ENABLE_TELEMETRY": "No",
    "npm_config_update_notifier": "false",
}


def child(caller=None):
    """The caller's environment with the tool's variables set and its programs first."""
    made = dict(os.environ if caller is None else caller)
    for name, folder in FOLDERS.items():
        made[name] = str(folder)
    made.update(SWITCHES)
    programs = str(paths.VENV / "bin")
    earlier = [folder for folder in made.get("PATH", "").split(os.pathsep) if folder and folder != programs]
    made["PATH"] = os.pathsep.join([programs] + earlier)
    return made
