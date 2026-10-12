"""Where things are: the repository, the web code, the Android project and the work folder."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "app"
WWW = APP / "www"
TOOLCHAIN = APP / "toolchain.json"
PACKAGE = APP / "package.json"
LOCK = APP / "package-lock.json"
NODE_MODULES = APP / "node_modules"
CAPACITOR = NODE_MODULES / ".bin" / "cap"
ANDROID = APP / "android"
GRADLEW = ANDROID / "gradlew"
BUILT_APK = ANDROID / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

# Everything a setup and a build make is in the work folder, which git ignores.
WORK = ROOT / "build" / "app"
DOWNLOADS = WORK / "downloads"
JDK = WORK / "jdk"
SDK = WORK / "android-sdk"
SDK_MANAGER = SDK / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
ADB = SDK / "platform-tools" / "adb"
GRADLE = WORK / "gradle"
ANDROID_USER = WORK / "android-user"
NPM_CACHE = WORK / "npm-cache"
HOME = WORK / "home"
STAGED = WORK / "www"
APK = WORK / "odrig-debug.apk"
SETUP_RECORD = WORK / "setup.json"
