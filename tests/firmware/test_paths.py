import os
import pathlib
import subprocess
import tempfile
import unittest

from fwtool import paths

from . import ROOT, support

PROTECTED_NAME = "esp32-backup"
SOURCE_FOLDERS = ("firmware", "tests/firmware", "tests/board", "tests/air")
SOURCE_ENDINGS = (".py", ".cpp", ".h", ".json", ".in", ".txt", ".md", ".sha256")
STOCK_FILES = ROOT / "firmware" / "wled-16.0.1"
ALLOWED_TO_NAME_IT = {ROOT / "firmware" / "fwtool" / "paths.py", pathlib.Path(__file__).resolve()}


def sources():
    for folder in SOURCE_FOLDERS:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in SOURCE_ENDINGS and STOCK_FILES not in path.parents:
                yield path


class WorkFolder(unittest.TestCase):
    def test_the_work_folder_is_build_firmware_inside_the_repository(self):
        self.assertEqual(paths.ROOT, ROOT)
        self.assertEqual(paths.WORK, ROOT / "build" / "firmware")
        self.assertTrue(paths.inside(paths.WORK, paths.ROOT))

    def test_every_folder_of_the_tool_is_inside_the_work_folder_or_the_shared_toolchains(self):
        for folder in (paths.WLED, paths.STANDALONE, paths.OUT, paths.STORAGE):
            self.assertTrue(paths.inside(folder.parent, paths.WORK) and folder.is_absolute(), folder)
        for folder in (paths.VENV, paths.PYTHON, paths.PIO_CORE, paths.PIO_CACHE, paths.NPM_CACHE, paths.PIP_CACHE, paths.WLED_SOURCE, paths.NEWER):
            self.assertTrue(paths.inside(folder.parent, paths.SHARED) and folder.is_absolute(), folder)

    def test_the_shared_toolchains_are_odrig_tools_or_else_the_checkout_s_build(self):
        self.assertEqual(paths.tools_folder({}, ROOT), ROOT / "build")
        self.assertEqual(paths.tools_folder({"ODRIG_TOOLS": "/srv/odrig-tools"}, ROOT), pathlib.Path("/srv/odrig-tools").resolve())
        self.assertEqual(paths.SHARED, paths.TOOLS / "firmware")
        self.assertEqual(paths.SETUP_LOCK, paths.TOOLS / "setup.lock")
        if "ODRIG_TOOLS" not in os.environ:
            self.assertEqual((paths.SHARED, paths.WLED_SOURCE), (paths.WORK, paths.WLED))

    def test_git_ignores_the_work_folder(self):
        done = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "build/firmware/out/odrig-firmware.bin"])
        self.assertEqual(done.returncode, 0)


class BackupGuard(unittest.TestCase):
    def test_the_protected_folder_is_the_factory_backup_at_the_repository_root(self):
        self.assertEqual(paths.PROTECTED, ROOT / PROTECTED_NAME)

    def test_every_output_path_under_the_backup_is_refused(self):
        inside = [
            paths.PROTECTED,
            paths.PROTECTED / "storage.bin",
            paths.PROTECTED / "new" / "deep" / "file.bin",
            ROOT / "build" / ".." / PROTECTED_NAME / "x.bin",
            pathlib.Path(os.path.relpath(paths.PROTECTED / "x.bin")),
            str(paths.PROTECTED / "x.bin"),
        ]
        for path in inside:
            self.assertEqual(support.reason_of(self, lambda: paths.output(path)), "backup-protected", path)

    def test_a_link_that_leads_into_the_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            link = pathlib.Path(folder, "link")
            link.symlink_to(paths.PROTECTED)
            self.assertEqual(support.reason_of(self, lambda: paths.output(link / "x.bin")), "backup-protected")

    def test_any_other_output_path_is_passed_on(self):
        for path in (paths.OUT / "odrig-firmware.bin", ROOT / "esp32-backup-other" / "x.bin", pathlib.Path("/tmp/x.bin")):
            self.assertEqual(paths.output(path), path)
        self.assertEqual(paths.output("build/x"), pathlib.Path("build/x"))

    def test_no_source_names_the_backup_but_the_guard_and_this_test(self):
        checked = list(sources())
        self.assertIn(ROOT / "firmware" / "fw.py", checked)
        naming = {path for path in checked if PROTECTED_NAME in path.read_text(encoding="utf-8", errors="replace")}
        self.assertEqual(naming, ALLOWED_TO_NAME_IT)
