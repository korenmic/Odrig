"""The APK: Capacitor copies the web code into the Android project, and Gradle builds it."""

import hashlib
import shutil
import subprocess
import sys

from . import Failure, env, paths, stage, toolchain


def _run(what, command, **settings):
    done = subprocess.run(command, capture_output=True, text=True, **settings)
    if done.returncode != 0:
        raise Failure("build-failed", f"{what} ended with status {done.returncode}: {(done.stdout + done.stderr).strip()[-900:]}")
    return done


def gradle_command():
    """The command that builds the debug APK. Nothing of it stays running afterwards.
    Java takes the user's folder from the system and not from the environment, and the
    Android build keeps a settings file there: it is told the work folder's own."""
    return [str(paths.GRADLEW), "--no-daemon", f"-Duser.home={paths.HOME}", "-p", str(paths.ANDROID), "assembleDebug"]


def build(out=sys.stdout):
    """Builds the debug APK into the work folder and prints its path, size and SHA-256."""
    home = toolchain.setup(out)
    stage.staged()
    _run("cap sync android", [str(paths.CAPACITOR), "sync", "android"], cwd=paths.APP, env=env.child(home, home=True))
    paths.BUILT_APK.unlink(missing_ok=True)
    paths.HOME.mkdir(parents=True, exist_ok=True)
    _run("gradlew assembleDebug", gradle_command(), cwd=paths.ANDROID, env=env.child(home))
    if not paths.BUILT_APK.is_file():
        raise Failure("build-failed", f"Gradle left no {paths.BUILT_APK.relative_to(paths.ROOT)}")
    shutil.copyfile(paths.BUILT_APK, paths.APK)
    data = paths.APK.read_bytes()
    print(f"apk: {paths.APK}", file=out)
    print(f"bytes: {len(data)}", file=out)
    print(f"sha256: {hashlib.sha256(data).hexdigest()}", file=out)
    return paths.APK
