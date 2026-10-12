"""A phone that is connected by USB: the APK is installed on it."""

import subprocess
import sys

from . import Failure, env, paths


def devices(listed):
    """The devices of what `adb devices` printed that are ready for a command."""
    found = []
    for line in listed.splitlines()[1:]:
        words = line.split()
        if len(words) >= 2 and words[1] == "device":
            found.append(words[0])
    return found


def install(out=sys.stdout, adb=paths.ADB, apk=paths.APK):
    """Installs the built APK on the one phone that is connected."""
    if not apk.is_file():
        raise Failure("build-failed", f"there is no {apk.relative_to(paths.ROOT)}; python3 app/app.py build makes it")
    if not adb.is_file():
        raise Failure("setup-failed", f"there is no {adb.relative_to(paths.ROOT)}; python3 app/app.py setup installs it")
    listed = subprocess.run([str(adb), "devices"], capture_output=True, text=True, env=env.child())
    found = devices(listed.stdout)
    if len(found) != 1:
        raise Failure("no-device", f"{len(found)} phones are connected by USB and ready; exactly one has to be")
    done = subprocess.run([str(adb), "-s", found[0], "install", "-r", str(apk)], capture_output=True, text=True, env=env.child())
    if done.returncode != 0:
        raise Failure("setup-failed", f"adb install ended with status {done.returncode}: {(done.stdout + done.stderr).strip()[-400:]}")
    print(f"installed: {apk.name} on {found[0]}", file=out)
    return 0
