"""Where things are: the repository, the web code, the Android project, the work folder and
the shared toolchains."""

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "app"
WWW = APP / "www"
# The converter's library, which the web code imports from `converter/` beside its own
# files: served from here, and copied into the package by the build.
CONVERTER_LIB = ROOT / "converter" / "lib"
LIBRARY_FOLDER = "converter"
# The default preview catalog, which the web code imports from `thumbnails/` beside its own
# files: served from here, and copied into the package by the build.
THUMBNAILS = ROOT / "thumbnails"
THUMBNAILS_FOLDER = "thumbnails"
TOOLCHAIN = APP / "toolchain.json"
PACKAGE = APP / "package.json"
LOCK = APP / "package-lock.json"
NODE_MODULES = APP / "node_modules"
CAPACITOR = NODE_MODULES / ".bin" / "cap"
ANDROID = APP / "android"
GRADLEW = ANDROID / "gradlew"
BUILT_APK = ANDROID / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

# What a build of this checkout makes is in its work folder, which git ignores.
WORK = ROOT / "build" / "app"


def tools_folder(environ=None, root=ROOT):
    """The folder of the toolchains that checkouts share: `ODRIG_TOOLS` when it is set, else
    the checkout's own `build/`."""
    named = (os.environ if environ is None else environ).get("ODRIG_TOOLS")
    return pathlib.Path(named).expanduser().resolve() if named else root / "build"


TOOLS = tools_folder()
# The toolchains a setup makes, which checkouts share: the JDK, the Android SDK, Gradle's
# user home with its caches, the Android user folder and npm's cache. Without
# `ODRIG_TOOLS` it is the work folder itself.
SHARED = TOOLS / "app"
SETUP_LOCK = TOOLS / "setup.lock"
DOWNLOADS = SHARED / "downloads"
JDK = SHARED / "jdk"
SDK = SHARED / "android-sdk"
SDK_MANAGER = SDK / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
ADB = SDK / "platform-tools" / "adb"
GRADLE = SHARED / "gradle"
ANDROID_USER = SHARED / "android-user"
NPM_CACHE = SHARED / "npm-cache"
HOME = SHARED / "home"
# What the shared toolchains were set up from, and what this checkout's packages were.
SHARED_RECORD = SHARED / "setup.json"
STAGED = WORK / "www"
APK = WORK / "odrig-debug.apk"
SETUP_RECORD = WORK / "setup.json"
