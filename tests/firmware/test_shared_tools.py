import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from fwtool import Failure, paths, setuplock, toolchain, wled

from . import FIRMWARE

# A process that holds the lock for a while, or until it is killed.
HOLDER = textwrap.dedent("""
    import sys, time
    sys.path[:0] = [{firmware!r}]
    from fwtool import setuplock
    with setuplock.held(sys.argv[1]):
        print("held", flush=True)
        time.sleep(float(sys.argv[2]))
""")


def holder(test, lock, seconds):
    """Starts a process that holds the lock, and returns it once it holds it."""
    python = getattr(sys, "_base_executable", sys.executable)
    process = subprocess.Popen([python, "-c", HOLDER.format(firmware=str(FIRMWARE)), str(lock), str(seconds)], stdout=subprocess.PIPE, encoding="utf-8")
    test.addCleanup(process.stdout.close)
    test.addCleanup(process.wait)
    test.addCleanup(process.kill)
    test.assertEqual(process.stdout.readline().strip(), "held")
    return process


class TheLock(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.lock = pathlib.Path(folder.name) / "tools" / "setup.lock"

    def test_a_second_setup_waits_for_the_first_and_then_goes_on(self):
        holder(self, self.lock, 1.5)
        told = []
        started = time.monotonic()
        with setuplock.held(self.lock, waiting=lambda: told.append(True), step=0.05):
            waited = time.monotonic() - started
        self.assertEqual(told, [True])
        self.assertGreater(waited, 0.5)

    def test_a_free_lock_is_taken_at_once_and_given_back(self):
        told = []
        with setuplock.held(self.lock, waiting=lambda: told.append(True)):
            self.assertTrue(self.lock.is_file())
        with setuplock.held(self.lock, wait=0):
            pass
        self.assertEqual(told, [])

    def test_the_lock_of_a_setup_that_died_is_free(self):
        holder(self, self.lock, 60).kill()
        time.sleep(0.2)
        with setuplock.held(self.lock, wait=2, step=0.05):
            pass

    def test_a_lock_held_longer_than_the_wait_is_a_failure(self):
        holder(self, self.lock, 60)
        with self.assertRaises(Failure) as refused, setuplock.held(self.lock, wait=0.3, step=0.05):
            pass
        self.assertEqual(refused.exception.reason, "setup-failed")


class TheWledCopy(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = pathlib.Path(folder.name) / "tools" / "WLED"
        (self.source / ".git").mkdir(parents=True)
        (self.source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        (self.source / ".pio" / "build").mkdir(parents=True)
        (self.source / ".pio" / "build" / "object.o").write_bytes(b"\x01\x02")
        (self.source / "platformio.ini").write_text("[platformio]\n")
        self.copy = pathlib.Path(folder.name) / "checkout" / "build" / "firmware" / "WLED"

    def test_a_checkout_gets_a_copy_of_the_source_with_its_git_and_build_folders(self):
        self.assertTrue(wled.copy(self.source, self.copy))
        self.assertEqual((self.copy / ".git" / "HEAD").read_text(), "ref: refs/heads/main\n")
        self.assertEqual((self.copy / ".pio" / "build" / "object.o").read_bytes(), b"\x01\x02")
        self.assertFalse(self.copy.with_name("WLED.partial").exists())
        # The copy is its own: a change in it leaves the source as it was.
        (self.copy / "platformio.ini").write_text("changed\n")
        self.assertEqual((self.source / "platformio.ini").read_text(), "[platformio]\n")

    def test_a_copy_that_is_there_or_is_the_source_itself_is_left_alone(self):
        self.copy.mkdir(parents=True)
        self.assertFalse(wled.copy(self.source, self.copy))
        self.assertEqual(list(self.copy.iterdir()), [])
        self.assertFalse(wled.copy(self.source, self.source))

    def test_the_copy_shares_the_blocks_where_the_system_can(self):
        self.assertEqual(wled.copy_command("a", "b", "darwin"), ["cp", "-c", "-R", "a", "b"])
        self.assertEqual(wled.copy_command("a", "b", "linux"), ["cp", "--reflink=auto", "-R", "a", "b"])
        self.assertIsNone(wled.copy_command("a", "b", "win32"))
        with mock.patch.object(wled, "copy_command", return_value=None):
            self.assertTrue(wled.copy(self.source, self.copy))
        self.assertTrue((self.copy / ".pio" / "build" / "object.o").is_file())


class TheSetup(unittest.TestCase):
    def test_it_takes_the_lock_of_the_shared_toolchains(self):
        taken = []

        class Held:
            def __init__(self, path, **settings):
                taken.append(path)

            def __enter__(self):
                return self

            def __exit__(self, *raised):
                return False

        with mock.patch.object(setuplock, "held", Held), mock.patch.object(toolchain, "_python_environment", return_value=["x"]), mock.patch.object(toolchain, "_newer_environment", return_value=["y"]):
            self.assertEqual(toolchain.python_environment(), ["x"])
            self.assertEqual(toolchain.newer_environment(), ["y"])
        self.assertEqual(taken, [paths.SETUP_LOCK, paths.SETUP_LOCK])


if __name__ == "__main__":
    unittest.main()
