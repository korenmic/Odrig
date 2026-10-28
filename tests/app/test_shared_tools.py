import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from . import support

from apptool import Failure, paths, setuplock, toolchain  # noqa: E402

# A process that holds the lock for a while, or until it is killed.
HOLDER = textwrap.dedent("""
    import sys, time
    sys.path[:0] = [{app!r}]
    from apptool import setuplock
    with setuplock.held(sys.argv[1]):
        print("held", flush=True)
        time.sleep(float(sys.argv[2]))
""")


class Folders(unittest.TestCase):
    def test_the_shared_toolchains_are_odrig_tools_or_else_the_checkout_s_build(self):
        self.assertEqual(paths.tools_folder({}, support.ROOT), support.ROOT / "build")
        self.assertEqual(paths.tools_folder({"ODRIG_TOOLS": "/srv/odrig-tools"}, support.ROOT), pathlib.Path("/srv/odrig-tools").resolve())
        self.assertEqual((paths.SHARED, paths.SETUP_LOCK), (paths.TOOLS / "app", paths.TOOLS / "setup.lock"))
        if "ODRIG_TOOLS" not in os.environ:
            self.assertEqual(paths.SHARED, paths.WORK)

    def test_the_toolchains_are_shared_and_what_a_build_makes_is_the_checkout_s(self):
        for folder in (paths.DOWNLOADS, paths.JDK, paths.SDK, paths.GRADLE, paths.ANDROID_USER, paths.NPM_CACHE, paths.HOME, paths.SHARED_RECORD):
            self.assertEqual(folder.parent, paths.SHARED, folder)
        for folder in (paths.STAGED, paths.APK, paths.SETUP_RECORD):
            self.assertEqual(folder.parent, paths.WORK, folder)
        for folder in (paths.NODE_MODULES, paths.BUILT_APK):
            self.assertIn(support.ROOT, folder.parents, folder)


class TheLock(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.lock = pathlib.Path(folder.name) / "tools" / "setup.lock"

    def holder(self, seconds):
        process = subprocess.Popen([sys.executable, "-c", HOLDER.format(app=str(support.APP)), str(self.lock), str(seconds)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        self.assertEqual(process.stdout.readline().strip(), "held")
        return process

    def test_a_second_setup_waits_for_the_first_and_then_goes_on(self):
        self.holder(1.5)
        told = []
        started = time.monotonic()
        with setuplock.held(self.lock, waiting=lambda: told.append(True), step=0.05):
            waited = time.monotonic() - started
        self.assertEqual(told, [True])
        self.assertGreater(waited, 0.5)

    def test_the_lock_of_a_setup_that_died_is_free(self):
        self.holder(60).kill()
        time.sleep(0.2)
        with setuplock.held(self.lock, wait=2, step=0.05):
            pass

    def test_a_lock_held_longer_than_the_wait_is_a_failure(self):
        self.holder(60)
        with self.assertRaises(Failure) as refused, setuplock.held(self.lock, wait=0.3, step=0.05):
            pass
        self.assertEqual(refused.exception.reason, "setup-failed")


class TheRecords(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def test_a_record_keeps_the_members_it_is_not_given(self):
        record = self.folder / "app" / "setup.json"
        toolchain._write_record(record, {"package-lock": "a"})
        toolchain._write_record(record, {"toolchain": "b"})
        toolchain._write_record(record, {"package-lock": "c"})
        self.assertEqual(json.loads(record.read_text()), {"package-lock": "c", "toolchain": "b"})

    def test_the_setup_takes_the_lock_of_the_shared_toolchains(self):
        taken = []

        class Held:
            def __init__(self, path, **settings):
                taken.append(path)

            def __enter__(self):
                return self

            def __exit__(self, *raised):
                return False

        with mock.patch.object(setuplock, "held", Held), mock.patch.object(toolchain, "node_version"), mock.patch.object(toolchain, "_setup", return_value="home"):
            self.assertEqual(toolchain.setup(), "home")
        self.assertEqual(taken, [paths.SETUP_LOCK])


if __name__ == "__main__":
    unittest.main()
