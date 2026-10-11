import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import support

THIRD_PARTY = ("numpy", "PIL", "av")

# Runs everything that must work with the standard library alone, in the interpreter that
# executes it, and prints the exit statuses and which third-party libraries were loaded.
SCRIPT = """
import json, sys
from odrig import cli
from odrig.generators import dense, dvd_bounce, hello_world

folder, mapping, show = sys.argv[1:4]
statuses = {
    "hello_world": hello_world.main([folder + "/hello.json", "--mapping", mapping]),
    "dvd_bounce": dvd_bounce.main([folder + "/dvd.json", "--mapping", mapping]),
    "dense": dense.main([folder + "/dense.json", "--mapping", mapping, "--seconds", "1"]),
    "encode": cli.main(["encode", folder + "/hello.json", folder + "/hello.odrg"]),
    "decode": cli.main(["decode", folder + "/hello.odrg", folder + "/back.json"]),
    "check": cli.main(["check", folder + "/hello.odrg"]),
    "pack": cli.main(["pack", "--show", show, "--mapping", mapping, "--sources", folder, "--out", folder + "/out"]),
}
loaded = sorted(name for name in %r if name in sys.modules)
print(json.dumps({"statuses": statuses, "loaded": loaded, "site": "site" in sys.modules}))
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
            names = sorted(entry.name for entry in Path(folder, "out").iterdir())
            self.assertEqual(names, ["dvd.odrg", "hello.odrg", "mapping.json", "show.json"])
            return json.loads(done.stdout.splitlines()[-1])

    def test_everything_but_import_runs_without_loading_a_third_party_library(self):
        report = self.run_script()
        self.assertEqual(set(report["statuses"].values()), {0}, report)
        self.assertEqual(len(report["statuses"]), 7)
        self.assertEqual(report["loaded"], [])

    def test_everything_but_import_runs_where_no_third_party_library_is_installed(self):
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
