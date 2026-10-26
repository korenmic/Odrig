"""The environment of every process the tool starts.

It keeps PlatformIO, npm and pip inside the work folder: their packages and every cache.
The newer USB software has PlatformIO's folders of its own and shares the caches of pip
and npm. `HOME` is left as the caller has it.
"""

import os

from . import paths

FOLDERS = {
    "PLATFORMIO_CORE_DIR": paths.PIO_CORE,
    "PLATFORMIO_BUILD_CACHE_DIR": paths.PIO_CACHE,
    "npm_config_cache": paths.NPM_CACHE,
    "PIP_CACHE_DIR": paths.PIP_CACHE,
}
NEWER_FOLDERS = dict(FOLDERS, PLATFORMIO_CORE_DIR=paths.NEWER_PIO_CORE, PLATFORMIO_BUILD_CACHE_DIR=paths.NEWER_PIO_CACHE)
SWITCHES = {
    "PLATFORMIO_SETTING_ENABLE_TELEMETRY": "No",
    "npm_config_update_notifier": "false",
}


def child(caller=None, newer=False):
    """The caller's environment with the tool's variables set and its programs first; with
    `newer`, those of the newer USB software."""
    made = dict(os.environ if caller is None else caller)
    for name, folder in (NEWER_FOLDERS if newer else FOLDERS).items():
        made[name] = str(folder)
    made.update(SWITCHES)
    programs = str((paths.NEWER_VENV if newer else paths.VENV) / "bin")
    tools = {str(paths.VENV / "bin"), str(paths.NEWER_VENV / "bin")}
    earlier = [folder for folder in made.get("PATH", "").split(os.pathsep) if folder and folder not in tools]
    made["PATH"] = os.pathsep.join([programs] + earlier)
    return made
