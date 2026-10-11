"""The Python side of the tests of the JavaScript converter: what only the Python tool has.

Started as `python converter/tests/reference.py REQUEST [ARGUMENT ...]`. A request reads
its input from standard input as JSON and writes its result to standard output as JSON.
Bytes travel as hexadecimal text, and whole numbers of any size as decimal text.
"""

import contextlib
import fractions
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from odrig import cli, jsonframes  # noqa: E402


def _run(argv):
    """One command line of the Python tool, run in this interpreter: status and both streams."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = cli.main(argv)
    return [status, out.getvalue(), err.getvalue()]


def check(arguments, files):
    """What `python -m odrig check --format FORMAT case.FORMAT` gives for each file.

    The files are given as hexadecimal text. Each is written under the name `case.json` or
    `case.odrg` into an empty folder, in which the tool is run.
    """
    (kind,) = arguments
    name = f"case.{kind}"
    results = []
    before = os.getcwd()
    with tempfile.TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            for data in files:
                with open(name, "wb") as file:
                    file.write(bytes.fromhex(data))
                results.append(_run(["check", "--format", kind, name]))
        finally:
            os.chdir(before)
    return results


def sixdigits(arguments, values):
    """`format(float(n / d), ".6g")` for each pair of whole numbers `[n, d]`."""
    return [format(float(fractions.Fraction(int(n), int(d))), ".6g") for n, d in values]


def _animation(given):
    frames = tuple((int(ms), bytes.fromhex(picture)) for ms, picture in given["frames"])
    return jsonframes.Animation(int(given["width"]), int(given["height"]), frames)


def dumps(arguments, animations):
    """The bytes of `odrig.jsonframes.dumps` for each animation, merged unless `merge` is false."""
    return [jsonframes.dumps(_animation(given), merge=given.get("merge", True)).hex() for given in animations]


def milliseconds(arguments, texts):
    """The whole milliseconds the command line reads from each text of seconds, as decimal text."""
    return [str(cli._milliseconds(text)) for text in texts]


REQUESTS = {"check": check, "sixdigits": sixdigits, "dumps": dumps, "milliseconds": milliseconds}


def main(argv):
    request, arguments = argv[0], argv[1:]
    given = json.load(sys.stdin)
    json.dump(REQUESTS[request](arguments, given), sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
