"""A worker of `tests/run.py`: runs some modules of one suite, or a whole suite by
discovery, and writes one line of JSON for every test it ran.

    python -m tests.runner_worker --results FILE (--modules A,B,... | --discover FOLDER)

Each line holds the test's id, its outcome (`ok`, `fail`, `error`, `skip`, `expected`,
`unexpected`), its seconds and, for a failure or an error, the text unittest prints for it.
The worker ends with status 0 when every test passed and 1 otherwise.
"""

import argparse
import json
import sys
import time
import unittest


class Recorded(unittest.TextTestResult):
    """unittest's text result, which also writes every test's line to the results file."""

    sink = None

    def startTest(self, test):
        self._began = time.monotonic()
        self._outcome = "ok"
        self._detail = ""
        super().startTest(test)

    def _write(self, test, outcome, detail):
        began = getattr(self, "_began", None)
        seconds = 0.0 if began is None else time.monotonic() - began
        line = {"id": test.id(), "outcome": outcome, "seconds": round(seconds, 3), "detail": detail}
        self.sink.write(json.dumps(line) + "\n")
        self.sink.flush()

    def stopTest(self, test):
        super().stopTest(test)
        self._write(test, self._outcome, self._detail)
        self._began = None

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._outcome, self._detail = "fail", self.failures[-1][1]

    def addError(self, test, err):
        super().addError(test, err)
        detail = self.errors[-1][1]
        if getattr(self, "_began", None) is None:
            # An error outside a test, in a class's or a module's set-up or tear-down.
            self._write(test, "error", detail)
        else:
            self._outcome, self._detail = "error", detail

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            failed = self.failures if issubclass(err[0], test.failureException) else self.errors
            self._outcome = "fail" if failed is self.failures else "error"
            self._detail = (self._detail + "\n" if self._detail else "") + failed[-1][1]

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._outcome, self._detail = "skip", reason

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._outcome = "expected"

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._outcome = "unexpected"


def tests_of(arguments):
    loader = unittest.defaultTestLoader
    if arguments.discover:
        return loader.discover(arguments.discover, top_level_dir=".")
    return unittest.TestSuite(loader.loadTestsFromName(name) for name in arguments.modules.split(",") if name)


def main(argv=None):
    made = argparse.ArgumentParser(prog="python -m tests.runner_worker")
    made.add_argument("--results", required=True)
    group = made.add_mutually_exclusive_group(required=True)
    group.add_argument("--modules")
    group.add_argument("--discover")
    arguments = made.parse_args(argv)
    with open(arguments.results, "w", encoding="utf-8") as sink:
        Recorded.sink = sink
        runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=Recorded)
        result = runner.run(tests_of(arguments))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
