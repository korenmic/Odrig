import re
import subprocess
import unittest

from fwtool import paths, wled

from . import ROOT

README = paths.PATCHES / "README.md"
SIXTEEN = "010-sixteen-parallel-outputs.patch"


def tracked_patches():
    """The patch files git tracks in the folder of patches, in the order of their names."""
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", str(paths.PATCHES.relative_to(ROOT))], capture_output=True, text=True, check=True)
    return sorted(ROOT / name for name in listed.stdout.split("\n") if name.endswith(".patch"))


def changed_files(patch):
    return re.findall(r"(?m)^diff --git a/(\S+) b/\S+$", patch.read_text(encoding="utf-8"))


class Patches(unittest.TestCase):
    def test_the_tracked_patch_files_are_the_ones_the_build_applies(self):
        self.assertEqual([path.name for path in tracked_patches()], [path.name for path in wled.patch_files()])
        self.assertIn(SIXTEEN, [path.name for path in tracked_patches()])

    def test_every_patch_file_applies_to_wleds_files_at_the_pinned_commit(self):
        wled.check()
        for patch in tracked_patches():
            done = subprocess.run(["git", "-C", str(paths.WLED), "apply", "--check", "--cached", "--whitespace=nowarn", str(patch)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, f"{patch.name}: {done.stderr}")

    def test_a_patch_that_does_not_fit_the_commit_is_seen_by_that_check(self):
        broken = "diff --git a/wled00/const.h b/wled00/const.h\n--- a/wled00/const.h\n+++ b/wled00/const.h\n@@ -1 +1 @@\n-no such line\n+another\n"
        done = subprocess.run(["git", "-C", str(paths.WLED), "apply", "--check", "--cached", "-"], input=broken, capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)

    def test_the_names_begin_with_a_number_that_orders_them(self):
        for patch in tracked_patches():
            self.assertRegex(patch.name, r"^\d{3}-[a-z0-9-]+\.patch$")

    def test_every_patch_file_says_first_what_it_changes_and_why_the_usermod_cannot(self):
        for patch in tracked_patches():
            text = patch.read_text(encoding="utf-8")
            before = text[:text.index("diff --git ")]
            self.assertGreater(len(before.split()), 30, patch.name)
            self.assertIn("usermod cannot", before, patch.name)
            for name in changed_files(patch):
                self.assertIn(name, before, f"{patch.name}: {name}")

    def test_the_readme_names_every_patch_file(self):
        text = README.read_text(encoding="utf-8")
        for patch in tracked_patches():
            self.assertIn(f"`{patch.name}`", text)
        self.assertNotIn("holds no patch", text)
        named = re.findall(r"`(\d{3}-[a-z0-9-]+\.patch)`", text)
        self.assertEqual(sorted(set(named) - {"010-what-it-changes.patch"}), [path.name for path in tracked_patches()])


class SixteenParallelOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        whole = (paths.PATCHES / SIXTEEN).read_text(encoding="utf-8")
        cls.text = whole[whole.index("diff --git "):]
        cls.added = [line[1:] for line in cls.text.splitlines() if line.startswith("+") and not line.startswith("+++")]
        cls.removed = [line[1:] for line in cls.text.splitlines() if line.startswith("-") and not line.startswith("---")]

    def test_it_changes_three_files_of_wled(self):
        self.assertEqual(changed_files(paths.PATCHES / SIXTEEN), ["wled00/FX_fcn.cpp", "wled00/bus_wrapper.h", "wled00/const.h"])

    def test_the_esp32_s3_gets_sixteen_parallel_channels(self):
        self.assertEqual([line.split("//")[0].split() for line in self.added if "WLED_MAX_I2S_CHANNELS" in line], [["#define", "WLED_MAX_I2S_CHANNELS", "16"]])
        self.assertEqual([line.split("//")[0].split() for line in self.removed if "WLED_MAX_I2S_CHANNELS" in line], [["#define", "WLED_MAX_I2S_CHANNELS", "8"]])

    def test_the_parallel_types_are_the_sixteen_lane_ones(self):
        self.assertEqual(len([line for line in self.added if re.match(r"\s*typedef X16\w+Method X1\w+Method;", line)]), 9)
        self.assertEqual(len([line for line in self.added if re.match(r"#define B_32_IP_\w+ NeoPixelBus<\w+, NeoParallelMethod\(\w+\)>", line)]), 12)
        self.assertIn("#define NeoParallelMethod(x) X16 ## x ## Method", self.added)
        self.assertIn("#define NeoParallelMethod(x) X8 ## x ## Method", self.added)

    def test_every_change_is_for_the_esp32_s3_only(self):
        self.assertEqual(len([line for line in self.added if "CONFIG_IDF_TARGET_ESP32S3" in line]), 2)
        estimate = self.text[self.text.index("diff --git a/wled00/FX_fcn.cpp"):self.text.index("diff --git a/wled00/bus_wrapper.h")]
        self.assertRegex(estimate, r"\+\s+#if defined\(CONFIG_IDF_TARGET_ESP32S3\)\n\+\s+if \(useParallelI2S\) i2sCommonMem \*= 16;.*\n\+\s+#else\n\s+if \(useParallelI2S\) i2sCommonMem \*= 8;")
