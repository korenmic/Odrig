"""Runs every suite that works on this computer, at the same time.

    .venv/bin/python tests/run.py [--suites A,B] [--serial] [--workers N] [--slowest N]
                                  [--walkthrough]

The suites of `tests/core`, `tests/emulator`, `tests/app`, `tests/converter` and
`tests/firmware` are split by test module across worker processes; the others run whole,
each in one process. The modules are found at run time by unittest's discovery, as
`-m unittest discover -s FOLDER -t .` finds them, and given to the workers by their seconds
in the previous run's report, the slowest first. The core is built once, before any suite
that needs it. The runner prints a line for each suite as it ends, the output of every
failing test, the slowest tests and the wall time, writes `build/tests/report.json`, and
ends with status 0 only when every suite passed.

It needs only Python's own library and runs on macOS, Linux and Windows.
"""

import argparse
import ctypes
import json
import os
import pathlib
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"
REPORT = pathlib.Path("build") / "tests" / "report.json"
LOGS = pathlib.Path("build") / "tests"
# The suites that need the board, which the firmware tool runs.
NEVER = ("board", "air")


class Suite:
    """A suite the runner knows: its name, its folder, whether it is split by module, the
    most workers it takes, what it needs, and the option that asks for it when it is not run
    by default."""

    def __init__(self, name, folder, split=False, cap=None, needs=(), only=None, kind="unittest"):
        self.name, self.folder, self.split, self.cap = name, folder, split, cap
        self.needs, self.only, self.kind = needs, only, kind


SUITES = (
    Suite("converter-npm", "converter/tests", kind="npm", needs=("node",)),
    Suite("converter", "tests/converter", split=True),
    Suite("onboarding", "tests/onboarding"),
    Suite("runner", "tests/runner"),
    Suite("mapping", "tests/mapping", needs=("core",)),
    Suite("firmware", "tests/firmware", split=True, needs=("firmware-python",)),
    Suite("core", "tests/core", split=True, needs=("core",)),
    Suite("emulator", "tests/emulator", split=True, needs=("core",)),
    Suite("app", "tests/app", split=True, cap=4, needs=("core",)),
    Suite("walkthrough", "tests/walkthrough", only="walkthrough"),
    Suite("apk", "tests/apk", only="builds"),
)


def default_workers():
    return max(2, (os.cpu_count() or 4) - 2)


def parser():
    made = argparse.ArgumentParser(prog="python tests/run.py", description="Runs every suite that works on this computer, at the same time.")
    made.add_argument("--suites", help="only these suites, by name, separated by commas")
    made.add_argument("--serial", action="store_true", help="one suite after another, each in one process")
    made.add_argument("--workers", type=int, default=default_workers(), help="worker processes of a split suite (default: the processors less two)")
    made.add_argument("--slowest", type=int, default=30, help="how many of the slowest tests to print (default 30)")
    made.add_argument("--walkthrough", action="store_true", help="also run the walkthrough of the pages, in a fresh copy")
    made.add_argument("--sweep", action="store_true", help="list and end the processes earlier runs and tests left behind, and run nothing")
    return made


# What marks a process as left by a run or a test: the runner's id in its environment, or
# an emulator whose show is in a temporary folder or in a preview's work folder.
MARKER = re.compile(r"(?:^|\s)ODRIG_RUN=(\S+)")
LEFT_EMULATOR = re.compile(r"-m emulator \S*(?:/T/|/tmp/|\\Temp\\|build/preview/\d+/show)")


def processes():
    """(id, age, command with its environment where the system shows it) of the processes
    this user can see."""
    found = []
    if WINDOWS:
        done = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"],
                              capture_output=True, text=True)
        for line in done.stdout.splitlines():
            pid, _, command = line.partition("\t")
            if pid.strip().isdigit():
                found.append((int(pid), "", command))
        return found
    options = "-axwwE" if sys.platform == "darwin" else "-axww"
    done = subprocess.run(["ps", options, "-o", "pid=", "-o", "etime=", "-o", "command="], capture_output=True, text=True)
    for line in done.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit():
            pid, age, command = int(parts[0]), parts[1], parts[2]
            if sys.platform.startswith("linux"):
                try:
                    command += " " + pathlib.Path(f"/proc/{pid}/environ").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
                except OSError:
                    pass
            found.append((pid, age, command))
    return found


def strays(run_id=None, listed=None):
    """The processes a run left: with `run_id`, those that carry it; without, every one that
    carries a run's id and every emulator of a temporary or a preview's folder."""
    mine = {os.getpid(), os.getppid()}
    left = []
    for pid, age, command in (processes() if listed is None else listed):
        if pid in mine:
            continue
        marked = MARKER.search(command)
        if run_id is not None:
            if marked and marked.group(1) == run_id:
                left.append((pid, age, command))
        elif marked or LEFT_EMULATOR.search(command):
            left.append((pid, age, command))
    return left


def end(pids, seconds=2.0):
    """Ends processes: a termination signal, then a kill of those still there."""
    for pid in pids:
        try:
            if WINDOWS:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    deadline = time.monotonic() + seconds
    while not WINDOWS and time.monotonic() < deadline and any(alive(pid) for pid in pids):
        time.sleep(0.1)
    for pid in pids:
        if not WINDOWS and alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def alive(pid):
    if WINDOWS:
        listed = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True)
        return f'"{pid}"' in listed.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Job:
    """A job object of Windows, whose system shows no process's environment: each worker is
    put in it, every process a worker starts joins it, and what is still in it once the
    workers have ended is what the run's tests left running."""

    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.restype = ctypes.c_void_p
        self.kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.kernel.QueryInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        self.handle = self.kernel.CreateJobObjectW(None, None)

    def add(self, process):
        self.kernel.AssignProcessToJobObject(self.handle, int(process._handle))

    def members(self):
        class Listed(ctypes.Structure):
            _fields_ = [("assigned", ctypes.c_uint32), ("listed", ctypes.c_uint32), ("ids", ctypes.c_size_t * 4096)]

        found = Listed()
        if not self.kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(found), ctypes.sizeof(found), None):
            return []
        return [found.ids[index] for index in range(found.listed)]

    def left(self):
        """The members whose parent is not one, such as a Python that a launcher started:
        ending one with its tree ends what it started."""
        members = self.members()
        if not members:
            return []
        query = " OR ".join(f"ProcessId={pid}" for pid in members)
        done = subprocess.run(["powershell", "-NoProfile", "-Command", f"Get-CimInstance Win32_Process -Filter '{query}' | ForEach-Object {{ \"$($_.ProcessId) $($_.ParentProcessId)\" }}"],
                              capture_output=True, text=True)
        parents = dict(tuple(map(int, line.split())) for line in done.stdout.splitlines() if len(line.split()) == 2)
        return [pid for pid in members if parents.get(pid) not in members]


def sweep(out):
    left = strays()
    for pid, age, command in left:
        print(f"{pid}  {age}  {MARKER.sub('', command)[:160]}", file=out)
    end([pid for pid, _, _ in left])
    print(f"swept {len(left)} processes", file=out, flush=True)
    return 0


class Runner:
    def __init__(self, arguments, root=ROOT, suites=SUITES, out=sys.stdout):
        self.arguments, self.root, self.out = arguments, pathlib.Path(root), out
        self.suites = list(suites)
        self.run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
        self.logs = self.root / LOGS / self.run_id
        self.previous = self.read_report()
        self.records = []
        self.summary = {}
        self.failed = False
        self.env = dict(os.environ, ODRIG_RUN=self.run_id, PYTHONUNBUFFERED="1")
        self.job = Job() if WINDOWS else None

    def say(self, line=""):
        print(line, file=self.out, flush=True)

    def read_report(self):
        try:
            return json.loads((self.root / REPORT).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    # What runs.

    def chosen(self):
        names = None if not self.arguments.suites else [name.strip() for name in self.arguments.suites.split(",") if name.strip()]
        known = {suite.name for suite in self.suites}
        if names:
            unknown = [name for name in names if name not in known]
            if unknown:
                raise SystemExit(f"error: no suite named {', '.join(unknown)}; the suites are {', '.join(sorted(known))}")
        chosen = []
        for suite in self.suites:
            if names is not None:
                if suite.name in names:
                    chosen.append(suite)
            elif suite.only is None or getattr(self.arguments, suite.only, False):
                chosen.append(suite)
        if names is None:
            chosen += self.unknown_folders()
        return chosen

    def unknown_folders(self):
        """Every folder of tests/ holding tests that the table does not know: run whole, so
        that a new suite is never left out."""
        known = {suite.folder for suite in self.suites}
        found = []
        tests = self.root / "tests"
        for folder in sorted(path for path in tests.iterdir() if path.is_dir()) if tests.is_dir() else ():
            relative = f"tests/{folder.name}"
            if folder.name in NEVER or relative in known or not any(folder.glob("test*.py")):
                continue
            found.append(Suite(folder.name, relative))
        return found

    def missing(self, suite):
        """Why a suite cannot run on this computer, or None."""
        for need in suite.needs:
            if need == "node" and (shutil.which("node") is None or not (self.root / "converter" / "node_modules").exists()):
                return "Node.js or the converter's packages are missing: npm ci --prefix converter"
            if need == "firmware-python" and self.firmware_python() is None:
                return "the firmware tool's Python is not set up: python3 firmware/fw.py setup"
        return None

    def firmware_python(self):
        name = "python.exe" if WINDOWS else "python"
        folder = "Scripts" if WINDOWS else "bin"
        path = self.root / "build" / "firmware" / "venv" / folder / name
        return path if path.exists() else None

    def python_of(self, suite):
        if suite.name == "firmware":
            return str(self.firmware_python())
        return sys.executable

    def env_of(self, suite):
        env = dict(self.env)
        if suite.name == "firmware":
            earlier = [env["PYTHONPATH"]] if env.get("PYTHONPATH") else []
            env["PYTHONPATH"] = os.pathsep.join([str(self.root), str(self.root / "firmware")] + earlier)
            sys.path.insert(0, str(self.root / "firmware"))
            try:
                from fwtool import env as tool_env
                env = tool_env.child(env)
            finally:
                sys.path.remove(str(self.root / "firmware"))
        return env

    # The core, built once.

    def build_core(self):
        if WINDOWS:
            commands = [[sys.executable, "core/build.py", "host"], [sys.executable, "core/build.py", "shared"]]
        else:
            commands = [["make", "-C", "core", "all", "shared", "build/odrig_host", f"PYTHON={sys.executable}"]]
        began = time.monotonic()
        for command in commands:
            done = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True, text=True)
            if done.returncode != 0:
                self.say(f"core build: FAILED with status {done.returncode}")
                self.say(done.stdout + done.stderr)
                return False
        self.env["ODRIG_CORE_BUILT"] = "1"
        self.say(f"core build: {time.monotonic() - began:.0f} s")
        return True

    # Splitting.

    def modules_of(self, suite):
        """The test modules of a suite, in the order of discovery, found by a child process
        that runs the same discovery as `-m unittest discover -s FOLDER -t .`."""
        code = (
            "import json, sys, unittest\n"
            "found = {}\n"
            "def walk(tests):\n"
            "    for test in tests:\n"
            "        if isinstance(test, unittest.TestSuite):\n"
            "            walk(test)\n"
            "            continue\n"
            "        name, kind = type(test).__module__, type(test).__name__\n"
            "        if name == 'unittest.loader':\n"
            "            name, kind = (test.id().split('.', 3)[-1] if test.id().startswith('unittest.loader._FailedTest.') else name), None\n"
            "        classes = found.setdefault(name, [])\n"
            "        if kind is not None and kind not in classes:\n"
            "            classes.append(kind)\n"
            f"walk(unittest.defaultTestLoader.discover({suite.folder!r}, top_level_dir='.'))\n"
            "print(json.dumps(list(found.items())))\n"
        )
        done = subprocess.run([self.python_of(suite), "-c", code], cwd=self.root, env=self.env_of(suite), capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError(f"the discovery of {suite.folder} failed:\n{done.stdout}{done.stderr}")
        found = json.loads(done.stdout.strip().splitlines()[-1])
        return [module for module, _ in found], {module: classes for module, classes in found}

    def seconds_by(self, suite, depth):
        """The seconds of the previous run's tests of a suite, summed by module (depth 2) or
        by class (depth 1)."""
        seconds = {}
        for test in self.previous.get("tests", ()):
            if test.get("suite") == suite.name:
                unit = test["id"].rsplit(".", depth)[0]
                seconds[unit] = seconds.get(unit, 0.0) + float(test.get("seconds", 0.0))
        return seconds

    def split(self, suite, modules, classes=None):
        """The modules of a suite given to its workers: the slowest first, each to the worker
        with the least seconds so far; round the order of discovery without a report. A
        module that took more than a worker's share in the previous run is given by its test
        classes instead. Each worker keeps its parts in the order of discovery."""
        count = max(1, min(self.arguments.workers, suite.cap or self.arguments.workers, len(modules)))
        known = self.seconds_by(suite, 2)
        if not known:
            parts = [modules[index::count] for index in range(count)]
            return [(part, None) for part in parts if part]
        typical = statistics.mean(known.values())
        expected = {module: known.get(module, typical) for module in modules}
        share = sum(expected.values()) / count
        by_class = self.seconds_by(suite, 1)
        units, order = [], {}
        for module in modules:
            kinds = (classes or {}).get(module) or []
            if expected[module] > share and len(kinds) > 1:
                for kind in kinds:
                    unit = f"{module}.{kind}"
                    order[unit] = len(order)
                    units.append(unit)
                    expected[unit] = by_class.get(unit, expected[module] / len(kinds))
            else:
                order[module] = len(order)
                units.append(module)
        loads = [[0.0, []] for _ in range(min(count, len(units)))]
        for unit in sorted(units, key=lambda name: -expected[name]):
            least = min(loads, key=lambda load: load[0])
            least[0] += expected[unit]
            least[1].append(unit)
        return [(sorted(names, key=order.get), seconds) for seconds, names in loads if names]

    def expected_of(self, suite):
        return float(self.previous.get("suites", {}).get(suite.name, {}).get("seconds", 0.0))

    # Jobs.

    def jobs_of(self, suite, serial):
        """The processes a suite runs as: (command, results file, expected seconds)."""
        self.logs.mkdir(parents=True, exist_ok=True)
        if suite.kind == "npm":
            npm = shutil.which("npm") or "npm"
            return [([npm, "test", "--prefix", "converter"], None, self.expected_of(suite))]
        worker = [self.python_of(suite), "-m", "tests.runner_worker"]
        if serial or not suite.split:
            results = self.logs / f"{suite.name}.jsonl"
            return [([*worker, "--results", str(results), "--discover", suite.folder], results, self.expected_of(suite))]
        jobs = []
        modules, classes = self.modules_of(suite)
        for index, (modules, seconds) in enumerate(self.split(suite, modules, classes)):
            results = self.logs / f"{suite.name}-{index + 1}.jsonl"
            jobs.append(([*worker, "--results", str(results), "--modules", ",".join(modules)], results, seconds or 0.0))
        return jobs

    def run(self):
        began = time.monotonic()
        chosen = self.chosen()
        serial = self.arguments.serial
        self.say(f"run {self.run_id}: {len(chosen)} suites, {'one after another' if serial else f'{self.arguments.workers} workers'}")
        runnable = []
        for suite in chosen:
            why = self.missing(suite)
            if why:
                self.say(f"{suite.name}: not run: {why}")
            else:
                runnable.append(suite)
        if any("core" in suite.needs for suite in runnable) and not self.build_core():
            self.failed = True
            runnable = [suite for suite in runnable if "core" not in suite.needs]
        queue = []
        for suite in runnable:
            for command, results, expected in self.jobs_of(suite, serial):
                queue.append({"suite": suite, "command": command, "results": results, "expected": expected})
        if not serial:
            queue.sort(key=lambda job: -job["expected"])
        self.execute(queue, 1 if serial else self.arguments.workers)
        left = [(pid, "", "") for pid in self.job.left()] if WINDOWS else strays(self.run_id)
        if left:
            end([pid for pid, _, _ in left])
            self.say(f"swept {len(left)} processes this run's tests left running")
        wall = time.monotonic() - began
        self.finish(wall)
        return 1 if self.failed else 0

    def execute(self, queue, slots):
        running = []
        left = {}
        for job in queue:
            left[job["suite"].name] = left.get(job["suite"].name, 0) + 1
        while queue or running:
            while queue and len(running) < slots:
                job = queue.pop(0)
                name = job["suite"].name
                log = self.logs / f"{name}-{len([1 for record in running if record['suite'].name == name]) + 1}-{id(job)}.log"
                job["log"] = log
                job["handle"] = open(log, "w", encoding="utf-8")
                job["began"] = time.monotonic()
                job["process"] = subprocess.Popen(job["command"], cwd=self.root, env=self.env_of(job["suite"]), stdout=job["handle"], stderr=subprocess.STDOUT)
                if self.job:
                    self.job.add(job["process"])
                self.summary.setdefault(name, {"began": job["began"], "jobs": []})
                running.append(job)
            time.sleep(0.1)
            for job in [job for job in running if job["process"].poll() is not None]:
                running.remove(job)
                job["handle"].close()
                job["ended"] = time.monotonic()
                name = job["suite"].name
                self.summary[name]["jobs"].append(job)
                left[name] -= 1
                if left[name] == 0:
                    self.suite_ended(job["suite"])

    def suite_ended(self, suite):
        state = self.summary[suite.name]
        jobs = state["jobs"]
        seconds = max(job["ended"] for job in jobs) - state["began"]
        status = max(job["process"].returncode != 0 for job in jobs)
        records = []
        for job in jobs:
            if job["results"] is not None and job["results"].exists():
                for line in job["results"].read_text(encoding="utf-8").splitlines():
                    record = json.loads(line)
                    record["suite"] = suite.name
                    records.append(record)
        self.records += records
        if suite.kind == "npm":
            text = jobs[0]["log"].read_text(encoding="utf-8", errors="replace")
            count = next((line.split()[-1] for line in text.splitlines() if line.startswith("ℹ tests ")), "?")
            failing = next((line.split()[-1] for line in text.splitlines() if line.startswith("ℹ fail ")), "?")
            tests = f"{count} tests"
            outcome = "OK" if not status else f"FAILED (fail {failing})"
        else:
            bad = [record for record in records if record["outcome"] in ("fail", "error", "unexpected")]
            skipped = sum(record["outcome"] == "skip" for record in records)
            tests = f"{len(records)} tests"
            if status and not bad:
                outcome = "FAILED (a worker ended without its results)"
            elif bad:
                failures = sum(record["outcome"] == "fail" for record in bad)
                errors = len(bad) - failures
                outcome = "FAILED (" + ", ".join(part for part in (f"failures={failures}" if failures else "", f"errors={errors}" if errors else "") if part) + ")"
            else:
                outcome = "OK" + (f" (skipped={skipped})" if skipped else "")
        self.summary[suite.name].update({"tests": tests, "seconds": seconds, "outcome": outcome})
        self.say(f"{suite.name}: {tests}, {seconds:.0f} s, {outcome}")
        if status:
            self.failed = True
            shown = False
            for record in records:
                if record["outcome"] in ("fail", "error", "unexpected"):
                    shown = True
                    self.say(f"  {record['outcome'].upper()}: {record['id']}")
                    for line in (record.get("detail") or "").rstrip().splitlines():
                        self.say(f"    {line}")
            if not shown:
                for job in jobs:
                    if job["process"].returncode != 0:
                        tail = job["log"].read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
                        self.say(f"  {' '.join(job['command'][:4])} ... ended with status {job['process'].returncode}:")
                        for line in tail:
                            self.say(f"    {line}")

    def finish(self, wall):
        if self.arguments.slowest and self.records:
            self.say(f"slowest {min(self.arguments.slowest, len(self.records))} tests:")
            for record in sorted(self.records, key=lambda record: -record["seconds"])[: self.arguments.slowest]:
                self.say(f"  {record['seconds']:7.1f} s  {record['suite']}: {record['id']}")
        # The suites this run did not run keep what the previous report holds of them, so
        # that the next split of every suite has its times.
        ran = set(self.summary)
        kept_suites = {name: state for name, state in self.previous.get("suites", {}).items() if name not in ran}
        kept_tests = [test for test in self.previous.get("tests", ()) if test.get("suite") not in ran]
        report = {
            "run": self.run_id,
            "wall": round(wall, 1),
            "suites": dict(kept_suites, **{name: {"tests": state.get("tests"), "seconds": round(state.get("seconds", 0.0), 1), "outcome": state.get("outcome")} for name, state in self.summary.items()}),
            "tests": kept_tests + [{"suite": record["suite"], "id": record["id"], "seconds": record["seconds"], "outcome": record["outcome"]} for record in self.records],
        }
        path = self.root / REPORT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        for folder in (self.root / LOGS).iterdir():
            if folder.is_dir() and folder.name != self.run_id:
                shutil.rmtree(folder, ignore_errors=True)
        self.say(f"{'FAILED' if self.failed else 'OK'}: wall time {wall:.0f} s ({wall / 60:.1f} min)")


def main(argv=None, root=ROOT, suites=SUITES, out=sys.stdout):
    arguments = parser().parse_args(argv)
    if arguments.workers < 1:
        raise SystemExit("error: --workers takes 1 or more")
    if arguments.sweep:
        return sweep(out)
    return Runner(arguments, root=root, suites=suites, out=out).run()


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
