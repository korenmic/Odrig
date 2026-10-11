# The converter

`odrig` is the command-line tool that works with the animation formats of
[format.md](format.md). It is a Python package at the repository root, started as
`python -m odrig <subcommand>`.

## Setup

The tool needs Python 3.10 or later. Create a virtual environment inside the repository
once:

```
python3 -m venv .venv
```

Every command on this page is run from the repository root with the Python of that
environment, written `python` below: `.venv/bin/python` on macOS and Linux,
`.venv\Scripts\python` on Windows. Nothing is installed outside the `.venv` folder, and git
ignores it.

## Exit statuses

| Status | Meaning |
|---:|---|
| 0 | The subcommand did its work. |
| 1 | An input was rejected. One line `error: <reason>: <detail>` is written to standard error and no output is left behind. The reasons are listed in [reasons.md](reasons.md). |
| 2 | The command line was not understood. A usage message is written to standard error and nothing else is written. |

## decode

```
python -m odrig decode IN.odrg OUT.json
```

Reads an ODRG file with the reference decoder and writes its frames as a JSON frames file
in the canonical layout. Frame records that follow each other with the same picture are
written as one frame, so the JSON file shows the same picture at every millisecond as the
ODRG file. An existing output file is replaced.

```
python -m odrig decode hello.odrg hello.json
```

A file that breaks the format is rejected with one of the reasons under "ODRG files" in
[reasons.md](reasons.md), and no output is written.

## Tests

```
python -m unittest discover -s tests/converter -t .
```

This one command runs the whole suite of the tool. It finds the tests by itself: every file
named `test_*.py` in `tests/converter/` is run, so a new test file needs no change anywhere
else. The suite needs no hardware and no network connection.
