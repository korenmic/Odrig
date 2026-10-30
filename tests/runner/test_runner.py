import hashlib
import io
import json
import os
import subprocess
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from tests import run
from firmware.fwtool import host as firmware_host

ROOT = pathlib.Path(__file__).resolve().parents[2]


class HostSelection(unittest.TestCase):
    def test_direct_entry_point_loads_its_host_helpers(self):
        done = subprocess.run([sys.executable, str(ROOT / 'tests' / 'run.py'), '--help'],
                              cwd=ROOT, capture_output=True, encoding='utf-8')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('--builds', done.stdout)

    def runner(self,root):
        with mock.patch.object(run,'Job',return_value=None):
            return run.Runner(run.parser().parse_args([]),root=root,suites=[],out=io.StringIO())

    def test_firmware_python_comes_from_the_current_hosts_isolated_cache(self):
        with tempfile.TemporaryDirectory(prefix='odrig-runner-host-') as directory,mock.patch.dict(os.environ,{'ODRIG_TOOLS':''}):
            root=pathlib.Path(directory)
            python=firmware_host.program(firmware_host.tool_root(root/'build'/'firmware')/'venv','python')
            python.parent.mkdir(parents=True);python.touch()
            self.assertEqual(self.runner(root).firmware_python(),python)

    def test_shared_firmware_tools_keep_host_selection_and_spaced_paths(self):
        with tempfile.TemporaryDirectory(prefix='odrig-runner-shared-host-') as directory:
            root=pathlib.Path(directory)
            tools=root/'shared tools'
            python=firmware_host.program(firmware_host.tool_root(tools/'firmware')/'venv','python')
            python.parent.mkdir(parents=True);python.touch()
            with mock.patch.dict(os.environ,{'ODRIG_TOOLS':str(tools)}):
                self.assertEqual(self.runner(root).firmware_python(),python)

    def test_unsupported_apk_build_is_reported_without_blocking_the_firmware_build(self):
        with tempfile.TemporaryDirectory(prefix='odrig-runner-build-host-') as directory:
            root=pathlib.Path(directory)
            (root/'app').mkdir()
            (root/'app'/'toolchain.json').write_text(json.dumps({'jdk':{},'command-line-tools':{}}),encoding='utf-8',newline='\n')
            runner=self.runner(root)
            runner.builds=[run.Build('apk',['app/app.py','build'],'out/app.apk'),
                           run.Build('firmware',['firmware/fw.py','build'],'out/firmware.bin')]
            try:
                with mock.patch.object(run.subprocess,'Popen') as spawned:
                    runner.start_builds()
                self.assertEqual(spawned.call_count,1)
                self.assertIn('firmware/fw.py',spawned.call_args.args[0])
                self.assertIn('SKIPPED',runner.built['apk']['outcome'])
                self.assertIn('not run',runner.out.getvalue())
            finally:
                for state in runner.built.values():
                    if state.get('handle'):state['handle'].close()

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

    def test_a_run_of_some_suites_keeps_the_previous_times_of_the_others(self):
        root = standin_root(self, ALL)
        ran(root, "--workers", "2")
        ran(root, "--suites", "beta")
        report = json.loads((root / "build" / "tests" / "report.json").read_text())
        self.assertEqual(set(report["suites"]), {"alpha", "beta", "gamma"})
        self.assertIn("tests.alpha.test_c.Failing.test_wrong", {test["id"] for test in report["tests"]})

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


LEAVES = """
import os
import pathlib
import subprocess
import sys
import unittest


class Leaves(unittest.TestCase):
    def test_it_leaves_a_process_running(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        pathlib.Path("left.pid").write_text(str(child.pid))
"""


NAMED = r"""
import unittest


class Named(unittest.TestCase):
    def test_named(self):
        self.fail("\u00e9t\u00e9 \u05e9")
"""


class Writing(unittest.TestCase):
    def test_the_output_is_utf_8_whatever_the_encoding_of_the_console(self):
        root = standin_root(self, {"tests/beta/test_named.py": NAMED})
        written = io.BytesIO()
        console = io.TextIOWrapper(written, encoding="cp1252")
        with mock.patch.object(sys, "stdout", console):
            status = run.main(["--suites", "beta"], root=root, suites=STANDIN)
            console.flush()
        self.assertEqual(status, 1)
        self.assertIn("\u00e9t\u00e9 \u05e9".encode("utf-8"), written.getvalue())


class Sweeping(unittest.TestCase):
    def test_a_run_ends_the_processes_its_tests_left_running(self):
        root = standin_root(self, {"tests/beta/test_leaves.py": LEAVES})
        status, out = ran(root, "--suites", "beta")
        self.assertEqual(status, 0, out)
        pid = int((root / "left.pid").read_text())
        self.addCleanup(run.end, [pid])
        self.assertIn("swept 1 processes this run's tests left running", out)
        self.assertFalse(run.alive(pid))

    def test_strays_are_those_of_a_run_s_id_or_emulators_of_temporary_and_preview_folders(self):
        listed = [
            (11, "1-00:00:00", "python -m emulator /var/folders/a/b/T/tmpx/show --port 0 HOME=/x"),
            (12, "00:10", "python -m unittest discover ODRIG_RUN=run-1 HOME=/x"),
            (13, "00:10", "python -m emulator build/demo-20/show HOME=/x"),
            (14, "00:10", "python -m emulator /Users/x/odrig/build/preview/77/show --parent 77"),
            (15, "00:10", "python -m emulator x ODRIG_RUN=run-2"),
        ]
        self.assertEqual([pid for pid, _, _ in run.strays(listed=listed)], [11, 12, 14, 15])
        self.assertEqual([pid for pid, _, _ in run.strays("run-1", listed=listed)], [12])

    def test_end_ends_a_process(self):
        import subprocess
        import sys
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        run.end([child.pid])
        self.assertIsNotNone(child.wait(timeout=5))


MAKES = """
import pathlib, sys, time
time.sleep(0.3)
if sys.argv[1] == "fail":
    print("the stand-in toolchain is missing")
    sys.exit(4)
pathlib.Path("out").mkdir(exist_ok=True)
pathlib.Path("out", sys.argv[1]).write_bytes(b"built")
"""

CHECKS = """
import pathlib
import unittest


class Built(unittest.TestCase):
    def test_the_build_is_there(self):
        self.assertEqual(pathlib.Path("out/thing.bin").read_bytes(), b"built")
"""

WITH_BUILDS = (
    run.Suite("beta", "tests/beta"),
    run.Suite("checks", "tests/checks", only="builds"),
)


def stand_in_builds(made):
    return (
        run.Build("thing", ["makes.py", made], f"out/{made}", then="checks"),
        run.Build("other", ["makes.py", "other.bin"], "out/other.bin"),
    )


class Builds(unittest.TestCase):
    def root(self):
        root = standin_root(self, {"tests/beta/test_whole.py": ONE, "tests/checks/test_built.py": CHECKS})
        (root / "makes.py").write_text(MAKES)
        return root

    def test_with_builds_both_are_built_beside_the_suites_and_the_waiting_suite_runs_after(self):
        root = self.root()
        out = io.StringIO()
        status = run.main(["--builds", "--workers", "4"], root=root, suites=WITH_BUILDS, out=out, builds=stand_in_builds("thing.bin"))
        printed = out.getvalue()
        self.assertEqual(status, 0, printed)
        self.assertRegex(printed, r"(?m)^thing: 5 bytes, \d+ s, SHA-256 [0-9a-f]{8}\.\.\.$")
        self.assertRegex(printed, r"(?m)^other: 5 bytes, \d+ s, SHA-256 [0-9a-f]{8}\.\.\.$")
        self.assertLess(printed.index("thing: 5 bytes"), printed.index("checks: 1 tests"))
        self.assertIn("beta: 1 tests", printed)
        report = json.loads((root / "build" / "tests" / "report.json").read_text())
        self.assertEqual(report["builds"]["thing"]["bytes"], 5)
        self.assertEqual(report["builds"]["thing"]["sha256"], hashlib.sha256(b"built").hexdigest())

    def test_a_build_that_fails_says_why_fails_the_run_and_its_suite_is_not_run(self):
        root = self.root()
        out = io.StringIO()
        status = run.main(["--builds"], root=root, suites=WITH_BUILDS, out=out, builds=stand_in_builds("fail"))
        printed = out.getvalue()
        self.assertEqual(status, 1, printed)
        self.assertIn("thing: FAILED with status 4", printed)
        self.assertIn("the stand-in toolchain is missing", printed)
        self.assertIn("checks: not run: thing was not built", printed)
        self.assertRegex(printed, r"(?m)^other: 5 bytes")

    def test_without_builds_nothing_is_built(self):
        root = self.root()
        out = io.StringIO()
        status = run.main([], root=root, suites=WITH_BUILDS, out=out, builds=stand_in_builds("thing.bin"))
        self.assertEqual(status, 0, out.getvalue())
        self.assertFalse((root / "out").exists())
        self.assertNotIn("checks:", out.getvalue())

    def test_the_real_builds_are_the_tools_own_commands(self):
        self.assertEqual([(build.name, build.command, build.output, build.then) for build in run.BUILDS], [
            ("apk", ["app/app.py", "build"], "build/app/odrig-debug.apk", "apk"),
            ("firmware", ["firmware/fw.py", "build"], "build/firmware/out/odrig-firmware.bin", None),
        ])


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


    def test_a_module_heavier_than_a_worker_s_share_is_given_by_its_classes(self):
        tests = [{"suite": "alpha", "id": test_id, "seconds": seconds} for test_id, seconds in (
            ("big.A.test_one", 7), ("big.A.test_two", 5), ("big.B.test", 8), ("small.C.test", 2))]
        runner, suite = self.runner({"tests": tests})
        # The share is 11 s: big, 20 s, goes by its classes A (12 s) and B (8 s).
        parts = runner.split(suite, ["big", "small"], {"big": ["A", "B"], "small": ["C"]})
        self.assertEqual(parts, [(["big.A"], 12.0), (["big.B", "small"], 10.0)])

    def test_a_heavy_module_of_one_class_stays_whole(self):
        tests = [{"suite": "alpha", "id": "big.A.test", "seconds": 20}, {"suite": "alpha", "id": "small.C.test", "seconds": 2}]
        runner, suite = self.runner({"tests": tests})
        self.assertEqual(runner.split(suite, ["big", "small"], {"big": ["A"], "small": ["C"]}), [(["big"], 20.0), (["small"], 2.0)])


class TheTable(unittest.TestCase):
    def test_every_suite_of_the_table_is_a_folder_of_the_repository(self):
        for suite in run.SUITES:
            with self.subTest(suite=suite.name):
                self.assertTrue((ROOT / suite.folder).is_dir(), suite.folder)

    def test_the_board_s_suites_are_never_run_and_every_other_folder_of_tests_is_known(self):
        known = {suite.folder for suite in run.SUITES}
        holding = {f"tests/{path.name}" for path in (ROOT / "tests").iterdir() if path.is_dir() and any(path.glob("test*.py"))}
        self.assertEqual(holding - known, {f"tests/{name}" for name in run.NEVER})
