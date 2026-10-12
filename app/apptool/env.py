"""The environment of every process the tool starts.

It keeps the JDK, the Android SDK, Gradle and npm inside the work folder: their programs,
what they fetch and every cache and setting.
"""

import os

from . import paths

FOLDERS = {
    "ANDROID_HOME": paths.SDK,
    "ANDROID_USER_HOME": paths.ANDROID_USER,
    "GRADLE_USER_HOME": paths.GRADLE,
    "npm_config_cache": paths.NPM_CACHE,
}
SWITCHES = {"npm_config_update_notifier": "false"}


def child(java_home=None, home=False, caller=None):
    """The caller's environment with the tool's variables set. With the home of a JDK, it
    is the Java of the process and its programs come first. With `home`, the process
    takes the work folder's own folder for the user's: Capacitor's command line keeps a
    settings file there."""
    made = dict(os.environ if caller is None else caller)
    for name, folder in FOLDERS.items():
        made[name] = str(folder)
    made.update(SWITCHES)
    # A variable of an Android tool of another time would lead the build elsewhere.
    made.pop("ANDROID_SDK_ROOT", None)
    if java_home is not None:
        made["JAVA_HOME"] = str(java_home)
        programs = os.path.join(str(java_home), "bin")
        earlier = [folder for folder in made.get("PATH", "").split(os.pathsep) if folder and folder != programs]
        made["PATH"] = os.pathsep.join([programs] + earlier)
    if home:
        made["HOME"] = str(paths.HOME)
    return made
