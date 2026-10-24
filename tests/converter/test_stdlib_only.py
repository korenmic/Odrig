import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support

THIRD_PARTY = ("numpy", "PIL", "av")

# Runs the generators and the library's readers and writers in the interpreter that executes
# it, and prints the exit statuses, what the library made, and which third-party libraries
# were loaded.
SCRIPT = """
import json, sys
from odrig import jsonframes, mapping, odrg, show
from odrig.generators import dense, dvd_bounce, hello_world, line_groups, lines_test

folder, legs, listed = sys.argv[1:4]
statuses = {
    "hello_world": hello_world.main([folder + "/hello.json", "--mapping", legs]),
    "dvd_bounce": dvd_bounce.main([folder + "/dvd.json", "--mapping", legs]),
    "dense": dense.main([folder + "/dense.json", "--mapping", legs, "--seconds", "1"]),
    "lines_test": lines_test.main([folder + "/lines-test.json", "--mapping", legs]),
    "line_groups": line_groups.main([folder + "/line-group.json", "--mapping", legs, "--group", "1"]),
}
canvas = mapping.read(legs)
animation = jsonframes.read(folder + "/hello.json")
decoded = odrg.decode(odrg.encode(animation))
made = {
    "canvas": [canvas.width, canvas.height],
    "decoded": [decoded.width, decoded.height, len(decoded.records) > 0],
    "items": len(show.read(listed).items),
}
loaded = sorted(name for name in %r if name in sys.modules)
print(json.dumps({"statuses": statuses, "made": made, "loaded": loaded, "site": "site" in sys.modules}))
""" % (THIRD_PARTY,)


class StandardLibraryOnly(unittest.TestCase):
    def run_script(self, *options):
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run(
                [
                    sys.executable,
                    *options,
                    "-c",
                    SCRIPT,
                    folder,
                    str(support.ROOT / "mapping" / "legs-2.json"),
                    str(support.ROOT / "shows" / "example" / "show.json"),
                ],
                cwd=support.ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stderr, "")
            names = sorted(entry.name for entry in Path(folder).iterdir())
            self.assertEqual(names, ["dense.json", "dvd.json", "hello.json", "line-group.json", "lines-test.json"])
            return json.loads(done.stdout.splitlines()[-1])

    def test_the_generators_and_the_library_run_without_loading_a_third_party_library(self):
        report = self.run_script()
        self.assertEqual(report["statuses"], {"hello_world": 0, "dvd_bounce": 0, "dense": 0, "lines_test": 0, "line_groups": 0}, report)
        self.assertEqual(report["made"], {"canvas": [60, 6], "decoded": [60, 6, True], "items": 3})
        self.assertEqual(report["loaded"], [])

    def test_they_run_where_no_third_party_library_is_installed(self):
        # -S leaves out the folder that installed libraries live in.
        report = self.run_script("-S")
        self.assertEqual(set(report["statuses"].values()), {0}, report)
        self.assertEqual(report["loaded"], [])
        self.assertIs(report["site"], False)

    def test_the_libraries_cannot_be_imported_under_that_option(self):
        done = subprocess.run(
            [sys.executable, "-S", "-c", "import numpy"], cwd=support.ROOT, capture_output=True, text=True
        )
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("ModuleNotFoundError", done.stderr)


if __name__ == "__main__":
    unittest.main()
