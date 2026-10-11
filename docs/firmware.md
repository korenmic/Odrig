# The firmware

The firmware is WLED 16.0.1 for the ESP32-S3, built from WLED's own source with one usermod
added that hosts the core of [core.md](core.md). One tool, `firmware/fw.py`, sets up the
tools the build needs, fetches WLED, builds, flashes, restores stock WLED and installs a
show into the board's storage.

This page covers [what the tool needs](#what-the-tool-needs), [the work folder](#the-work-folder),
the [commands](#commands) of the tool and what was [verified on the board](#verified-on-the-board).

## What the tool needs

On the Mac before the tool runs:

- macOS with Apple's command-line developer tools,
- git,
- Python 3.10 or later, as `python3`.

Everything else the tool installs itself, into the work folder, the first time a command is
run. That first time needs a network connection; later runs do not fetch again.

| What | Version | From |
|---|---|---|
| WLED's source | tag `v16.0.1`, commit `29b389df1c1aaec6ff53aea742d17063b985906c` | `https://github.com/wled/WLED.git` |
| PlatformIO and its Python packages | 6.1.17, as WLED's own `requirements.txt` at the tag pins them | PyPI |
| esptool | 5.4.0 | PyPI |
| littlefs-python | 0.19.0 | PyPI |
| Node.js and npm | 20.18.0 and 10.8.2, the package `nodejs-wheel` 20.18.0 | PyPI |

The last three are pinned in `firmware/requirements.txt`. WLED's build needs Node.js to pack
its web interface; `.nvmrc` of WLED 16.0.1 asks for 20.18.

The tool refuses to work with a WLED folder that is not at the pinned commit
(`wled-mismatch`), and with a Python below 3.10 (`setup-failed`).

## The work folder

The work folder is `build/firmware/` under the repository root. Git ignores it, and removing
it removes everything the tool installed, fetched or built.

```
build/firmware/
  venv/            Python environment: PlatformIO, esptool, littlefs-python, Node.js and npm
  pio/             PlatformIO's platforms, toolchains and packages
  pio-cache/       PlatformIO's build cache
  npm-cache/       npm's cache
  pip-cache/       pip's cache
  WLED/            WLED's source at the pinned commit
  out/             the built images
  storage/         storage images read from the board
```

Every program the tool starts gets these variables, so that nothing lands in the home
folder. `HOME` is left as it is.

| Variable | Value |
|---|---|
| `PLATFORMIO_CORE_DIR` | `build/firmware/pio` |
| `PLATFORMIO_BUILD_CACHE_DIR` | `build/firmware/pio-cache` |
| `PLATFORMIO_SETTING_ENABLE_TELEMETRY` | `No` |
| `npm_config_cache` | `build/firmware/npm-cache` |
| `npm_config_update_notifier` | `false` |
| `PIP_CACHE_DIR` | `build/firmware/pip-cache` |
| `PATH` | `build/firmware/venv/bin`, then the caller's |

The paths are absolute.

## Commands

Run from the repository root.

```
python3 firmware/fw.py setup
python3 firmware/fw.py test
```

`fw.py` itself uses only the Python standard library. It checks the command line, makes sure
the work folder holds WLED's source and the Python environment, and then runs the command
with that environment's Python.

| Status | Meaning |
|---:|---|
| 0 | The command did its work. |
| 1 | It could not. One line `error: <reason>: <detail>` is written to standard error. |
| 2 | The command line was not understood. Nothing is set up for such a command line. |

| Reason | Condition |
|---|---|
| `setup-failed` | A tool could not be installed or fetched, or Python is older than 3.10. |
| `wled-mismatch` | `build/firmware/WLED` is not a checkout of its own at the pinned commit. |
| `patch-failed` | A patch file of `firmware/patches/` does not apply. |
| `backup-protected` | An output path lies in the factory backup of the board, which no tool writes. |

### setup

```
python3 firmware/fw.py setup
```

Puts WLED's source and the tools into the work folder and prints the work folder and the
version each tool reports. Every step is skipped when its result is there: the clone of WLED
when `build/firmware/WLED` exists, the Python environment when `build/firmware/venv` has its
Python, and the packages when the two requirement files are the ones that were installed.
Every other command does the same before its own work, so `setup` never has to be run by
hand.

```
work folder: /Users/you/odrig/build/firmware
python: Python 3.14.6
platformio: PlatformIO Core, version 6.1.17
node: v20.18.0
npm: 10.8.2
esptool: esptool v5.4.0
```

### test

```
python3 firmware/fw.py test
```

Runs the suite in `tests/firmware/`: every `test_*.py` file there, found by discovery. It
needs no board, no network connection and nothing outside the work folder.

## Verified on the board

What the design assumed and an early task then tried, on this Mac and on the board. The
letters are those of the design's table "Assumed, to be verified by an early task".

| # | Assumption | What was found |
|---|---|---|
| A1 | PlatformIO 6.1.17 installs and runs under this Mac's Python, 3.14. | It installs under Python 3.14.6 with every package at the version WLED pins, `pip check` finds nothing broken, and `pio --version` prints `PlatformIO Core, version 6.1.17`. |
| A2 | `nodeenv` puts Node 20.18 into the work folder. | Not tried: `nodeenv` fetches Node.js from nodejs.org, and the tool fetches from PyPI only. The package `nodejs-wheel` 20.18.0 from PyPI is used in its place: `node --version` from the work folder prints `v20.18.0`, and `npm --version` prints `10.8.2`. See "Seed 04: Where Node.js comes from" in [drifts.md](drifts.md). |

The home folder was listed before and after the first `setup`, with the modification time of
every entry, and so were the folders in it where caches usually land: `~/.cache`, `~/.npm`,
`~/.config`, `~/.local`, `~/Library/Caches`, `~/Library/Application Support` and
`~/Library/Preferences`. One entry differed: `~/Library/Application Support/Claude`, the
folder of the application that ran the commands. No `~/.platformio` and no `~/.buildcache`
appeared, and `~/.npm` and `~/Library/Caches/pip` kept their times.
