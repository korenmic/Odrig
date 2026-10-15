"""Writes the stored answers of the converter's suite, `converter/tests/expected/`.

It runs that suite in its recording mode, in which every request a test makes of the
Python package is answered by it and kept, and writes what was kept: one file for each
kind of request, with an answer on each line under its key and compressed when it is
large, and each file a request wrote that is too large to stay within its answer apart,
compressed, in `files/`. The suite then
checks the stored answers against the Python package in its own mode, `verify`.

Run from the repository root, with the Python that has the libraries of requirements.txt:

    .venv/bin/python -m tests.converter.make_expected
"""

import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "converter" / "tests" / "expected"
FILES = EXPECTED / "files"
# The most the stored answers may take, in bytes, and the largest file of answers that is
# not compressed.
LARGEST = 8 * 1024 * 1024
LARGEST_PLAIN = 65536


def record(records):
    """Runs the converter's suite, which keeps every answer in the folder `records`."""
    environment = dict(os.environ, ODRIG_EXPECTED="record", ODRIG_EXPECTED_RECORDS=str(records), ODRIG_PYTHON=sys.executable)
    done = subprocess.run(["npm", "test", "--prefix", "converter"], cwd=ROOT, env=environment)
    if done.returncode != 0:
        raise SystemExit(f"the converter's suite ended with status {done.returncode} while it recorded")


def merged(records):
    """The kept answers of every program of the suite, by kind and key. A request asked
    twice must have had the same answer both times."""
    kinds = {}
    for path in sorted(records.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            kept = kinds.setdefault(row["kind"], {})
            if row["key"] in kept and kept[row["key"]] != row["entry"]:
                raise SystemExit(f"two answers of the kind {row['kind']} for one request {row['key']}")
            kept[row["key"]] = row["entry"]
    return kinds


def write(kinds, records):
    """Writes the stored answers in place of those there were, and gives their size."""
    if EXPECTED.exists():
        shutil.rmtree(EXPECTED)
    FILES.mkdir(parents=True)
    large = set()
    for kind, entries in sorted(kinds.items()):
        lines = [f"{json.dumps(key)}: {json.dumps(entries[key], separators=(',', ':'))}" for key in sorted(entries)]
        text = ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")
        if len(text) <= LARGEST_PLAIN:
            (EXPECTED / f"{kind}.json").write_bytes(text)
        else:
            (EXPECTED / f"{kind}.json.gz").write_bytes(gzip.compress(text, compresslevel=9, mtime=0))
        for entry in entries.values():
            large.update(stored["file"] for stored in entry["written"].values() if "file" in stored)
    for digest in sorted(large):
        data = (records / "files" / digest).read_bytes()
        (FILES / f"{digest}.gz").write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    return sum(path.stat().st_size for path in EXPECTED.rglob("*") if path.is_file())


def main():
    with tempfile.TemporaryDirectory() as folder:
        records = pathlib.Path(folder)
        record(records)
        kinds = merged(records)
        size = write(kinds, records)
    count = sum(len(entries) for entries in kinds.values())
    print(f"{count} answers of {len(kinds)} kinds, {size} bytes")
    if size > LARGEST:
        raise SystemExit(f"the stored answers take {size} bytes, more than {LARGEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
