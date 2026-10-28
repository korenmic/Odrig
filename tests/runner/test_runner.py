import io
import json
import pathlib
import shutil
import tempfile
import textwrap
import unittest

from tests import run

ROOT = pathlib.Path(__file__).resolve().parents[2]

PASSING = """
import time
import unittest


class Passing(unittest.TestCase):
    def test_quick(self):
        self.assertTrue(True)

    def test_slower(self):
        time.sleep(0.2)
"""

FAILING = """
import unittest


class Failing(unittest.TestCase):
    def test_wrong(self):
        self.assertEqual(1, 2, "the stand-in fails")
"""

ONE = """
import unittest


class One(unittest.TestCase):
    def test_one(self):
        pass
"""

SKIPPING = """
import unittest


class Skipping(unittest.TestCase):
    def test_runs(self):
        pass

    @unittest.skip("not on this computer")
    def test_skipped(self):
        pass
"""

STANDIN = (
    run.Suite("alpha", "tests/alpha", split=True),
    run.Suite("beta", "tests/beta"),
    run.Suite("later", "tests/later", only="walkthrough"),
)


def standin_root(test, files):
    """A folder like the repository's root, with the worker and the given test files."""
    folder = tempfile.TemporaryDirectory()
    test.addCleanup(folder.cleanup)
    root = pathlib.Path(folder.name)
    (root / "tests").mkdir()
    (root / "tests" / "__init__.py").write_text("")
    shutil.copy(ROOT / "tests" / "runner_worker.py", root / "tests" / "runner_worker.py")
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not (path.parent / "__init__.py").exists():
            (path.parent / "__init__.py").write_text("")
        path.write_text(textwrap.dedent(text))
    return root


def ran(root, *argv, suites=STANDIN):
    out = io.StringIO()
    status = run.main(list(argv), root=root, suites=suites, out=out)
    return status, out.getvalue()


ALL = {
    "tests/alpha/test_a.py": PASSING,
    "tests/alpha/test_b.py": ONE,
    "tests/alpha/test_c.py": FAILING,
    "tests/beta/test_whole.py": SKIPPING,
    "tests/later/test_later.py": ONE,
    "tests/gamma/test_new.py": ONE,
}


class Running(unittest.TestCase):
    def test_every_suite_runs_at_once_split_by_module_with_a_line_each_and_the_failure_in_full(self):
        root = standin_root(self, ALL)
        status, out = ran(root, "--workers", "2")
        self.assertEqual(status, 1, out)
        self.assertIn("alpha: 4 tests", out)
        self.assertIn("FAILED (failures=1)", out)
        self.assertIn("beta: 2 tests", out)
        self.assertIn("OK (skipped=1)", out)
        self.assertIn("FAIL: tests.alpha.test_c.Failing.test_wrong", out)
        self.assertIn("the stand-in fails", out)
        # A folder of tests the table does not know runs whole; one asked for by an option
        # does not run without it.
        self.assertIn("gamma: 1 tests", out)
        self.assertNotIn("later:", out)
        self.assertIn("slowest", out)
        self.assertRegex(out, r"FAILED: wall time \d+ s")
        logs = [path.name for path in (root / "build" / "tests").iterdir() if path.is_dir()]
        self.assertEqual(len(logs), 1)
        self.assertEqual(sorted(path.name for path in (root / "build" / "tests" / logs[0]).glob("alpha-*.jsonl")), ["alpha-1.jsonl", "alpha-2.jsonl"])

    def test_the_report_holds_every_test_and_every_suite(self):
        root = standin_root(self, ALL)
        ran(root, "--workers", "2")
        report = json.loads((root / "build" / "tests" / "report.json").read_text())
        self.assertEqual(set(report["suites"]), {"alpha", "beta", "gamma"})
        self.assertEqual(report["suites"]["beta"]["outcome"], "OK (skipped=1)")
        tests = {test["id"]: test for test in report["tests"]}
        self.assertEqual(tests["tests.alpha.test_c.Failing.test_wrong"]["outcome"], "fail")
        self.assertEqual(tests["tests.beta.test_whole.Skipping.test_skipped"]["outcome"], "skip")
        self.assertGreaterEqual(tests["tests.alpha.test_a.Passing.test_slower"]["seconds"], 0.2)
        self.assertGreater(report["wall"], 0)

    def test_passing_suites_end_with_status_0_and_an_option_adds_its_suite(self):
        root = standin_root(self, {name: text for name, text in ALL.items() if "test_c" not in name})
        status, out = ran(root, "--walkthrough")
        self.assertEqual(status, 0, out)
        self.assertIn("later: 1 tests", out)
        self.assertRegex(out, r"OK: wall time \d+ s")

    def test_suites_picks_by_name_and_refuses_an_unknown_one(self):
        root = standin_root(self, ALL)
        status, out = ran(root, "--suites", "beta")
        self.assertEqual(status, 0, out)
        self.assertIn("beta: 2 tests", out)
        self.assertNotIn("alpha:", out)
        with self.assertRaises(SystemExit) as refused:
            ran(root, "--suites", "nothing")
        self.assertIn("no suite named nothing", str(refused.exception))

    def test_serial_runs_one_suite_after_another_each_in_one_process(self):
        root = standin_root(self, ALL)
        status, out = ran(root, "--serial")
        self.assertEqual(status, 1, out)
        self.assertIn("one after another", out)
        self.assertIn("alpha: 4 tests", out)
        logs = next(path for path in (root / "build" / "tests").iterdir() if path.is_dir())
        self.assertEqual(sorted(path.name for path in logs.glob("alpha*.jsonl")), ["alpha.jsonl"])

    def test_a_worker_that_dies_without_its_results_is_a_failure_with_its_output(self):
        root = standin_root(self, {"tests/beta/test_whole.py": "import os\nos._exit(3)\n"})
        status, out = ran(root, "--suites", "beta")
        self.assertEqual(status, 1, out)
        self.assertIn("beta: 0 tests", out)
        self.assertIn("a worker ended without its results", out)
        self.assertIn("ended with status 3", out)


class Splitting(unittest.TestCase):
    def runner(self, previous, workers=2, cap=None):
        arguments = run.parser().parse_args(["--workers", str(workers)])
        made = run.Runner(arguments, root=ROOT, suites=STANDIN, out=io.StringIO())
        made.previous = previous
        return made, run.Suite("alpha", "tests/alpha", split=True, cap=cap)

    def test_without_a_report_the_modules_go_round_the_order_of_discovery(self):
        runner, suite = self.runner({})
        self.assertEqual(runner.split(suite, ["a", "b", "c", "d", "e"]), [(["a", "c", "e"], None), (["b", "d"], None)])

    def test_with_a_report_the_slowest_go_first_each_to_the_least_loaded_worker(self):
        tests = [{"suite": "alpha", "id": f"{module}.Case.test", "seconds": seconds} for module, seconds in (("a", 10), ("b", 1), ("c", 1), ("d", 8))]
        runner, suite = self.runner({"tests": tests})
        # a (10) to the first; d (8) to the second; b (1) and c (1) to the second, then 10 each.
        self.assertEqual(runner.split(suite, ["a", "b", "c", "d"]), [(["a"], 10.0), (["b", "c", "d"], 10.0)])

    def test_a_module_the_report_lacks_counts_as_the_mean_and_a_cap_bounds_the_workers(self):
        tests = [{"suite": "alpha", "id": "a.Case.test", "seconds": 4}, {"suite": "alpha", "id": "b.Case.test", "seconds": 2}]
        runner, suite = self.runner({"tests": tests}, workers=8, cap=2)
        parts = runner.split(suite, ["a", "b", "new"])
        self.assertEqual(len(parts), 2)
        self.assertEqual(sorted(sum((names for names, _ in parts), [])), ["a", "b", "new"])
        self.assertEqual(sorted(seconds for _, seconds in parts), [4.0, 5.0])


class TheTable(unittest.TestCase):
    def test_every_suite_of_the_table_is_a_folder_of_the_repository(self):
        for suite in run.SUITES:
            with self.subTest(suite=suite.name):
                self.assertTrue((ROOT / suite.folder).is_dir(), suite.folder)

    def test_the_board_s_suites_are_never_run_and_every_other_folder_of_tests_is_known(self):
        known = {suite.folder for suite in run.SUITES}
        holding = {f"tests/{path.name}" for path in (ROOT / "tests").iterdir() if path.is_dir() and any(path.glob("test*.py"))}
        self.assertEqual(holding - known, {f"tests/{name}" for name in run.NEVER})
