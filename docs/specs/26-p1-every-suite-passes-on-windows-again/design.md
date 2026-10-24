# Design: every suite passes on Windows again

The causes below were found by running the failing tests on Windows 11 with Python 3.14
and Node.js 24, on `master` at `41f170d`. Each fix is made where the fault is, and each is
a no-op on macOS and Linux: it is taken only where the Windows behaviour it answers is
there.

## 1. The emulator's host lets go of a folder it reads (`emulator/host.py`)

**Cause.** `FolderHost` opens the files of the show and of the drive with `open(path,
"rb")`. On Windows a file opened that way cannot be removed, and neither can its folder:
`PermissionError: [WinError 32]`. macOS lets both go while the file is open. So:

- `test_binding`'s two tests fail in their cleanup: the binding read the show through
  `read_at`, whose file stays open after the test.
- `test_drive`'s pull-out test fails at `shutil.rmtree(self.top / "odrig")`: the drive's
  animation is playing. A person who pulls out the emulator's drive on Windows, as
  `docs/emulator.md` says (by moving the folder `odrig` away), meets the same refusal.

**Fix.** One function in `emulator/host.py` opens a file to read it. Elsewhere it is
`open(path, "rb")`. On Windows it opens the file with read, write and delete sharing:
`_winapi.CreateFile(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE |
FILE_SHARE_DELETE, 0, OPEN_EXISTING, 0, 0)`, turned into a file object with
`msvcrt.open_osfhandle` and `os.fdopen`. A missing file raises `FileNotFoundError` and any
other failure an `OSError`, as `open` does, so `open()` and `read_at()` keep their
answers. Both `open()` and `read_at()` use it, for the show's files and the drive's.

A trial on this computer: a file opened so stays readable while its folder is removed, and
the removal succeeds, as on macOS; opened with `open`, the removal fails with WinError 32.

The files the host writes (an upload's `.part`) are not changed.

## 2. The preview ends on Ctrl+Break (`preview/__init__.py`)

**Cause.** The preview turns SIGTERM into `KeyboardInterrupt` and catches Ctrl+C. On
Windows a test, or a terminal, ends a program in its own group with Ctrl+Break, which is
SIGBREAK. Python's default for SIGBREAK ends the program at once: the `finally` that stops
the emulator and removes the work folder does not run, and the emulator stays, holding
its port.

**Fix.** In `main`, SIGBREAK, where the system has it, gets the handler SIGTERM has:
`interrupted`, which raises `KeyboardInterrupt`. Nothing else changes.

## 3. The preview's tests stop it as Windows can (`tests/emulator/test_preview.py`)

**Cause.** `Preview.interrupt` calls `os.killpg`, which Windows does not have. The preview
it started stays, holds port 8600, and the next test that expects 8600 free finds it
taken. `test_a_page_port_that_is_taken_gives_a_free_one` binds port 8600 to make it
taken; when another program holds it already the bind fails, the test passes over that,
and then calls `listen()` on a socket that has no address: Windows refuses that with
WinError 10022, where macOS gives the socket a port of its own.

**Fix.**

- `Preview` starts the preview with `creationflags=support.OWN_GROUP` and
  `start_new_session=` only where the system is not Windows, and `interrupt` sends
  `support.STOP` (Ctrl+Break) on Windows and `os.killpg(..., SIGINT)` elsewhere, as
  before.
- The held port: when the bind fails because the port is taken, the test does not listen
  on that socket; the port is taken either way, which is what the test needs.
- `test_a_relative_path_and_the_installations_canvas_by_default` asks first whether port
  8600 is free (a bind on `127.0.0.1:8600` that is closed at once). When it is free, it
  checks what it checks now. When it is not, it checks the line
  `preview: port 8600 is taken; the page is on <port>` and a page on `<port>`.
- No other preview test assumes port 8600: each one that names no port is read the same
  way, through one helper of the test module.

## 4. `odrigctl --log` ends on Ctrl+Break (`odrigctl/cli.py`, `tests/emulator/test_tool_log.py`)

**Cause.** `--log` ends on `KeyboardInterrupt`. On Windows Ctrl+Break ends the tool at
once without the line it prints and the status 0 it gives. The tests of the stop are
skipped on Windows (`needs_interrupt`), because they send SIGINT.

**Fix.** In `main`, for `--log`, SIGBREAK where the system has it raises
`KeyboardInterrupt`, as Ctrl+C does. In the test, the program is started with
`creationflags=support.OWN_GROUP`, and stopped with `support.STOP` on Windows and SIGINT
elsewhere; `needs_interrupt` is removed. What the test checks does not change.

## 5. The demo test on Python's zlib-ng (`tests/emulator/test_demo.py`)

**Cause.** `test_the_packed_folder_holds_the_files_the_other_tests_of_the_suites_play`
compares the folder the converter packs with `tests/core/support.demo_show()`, which
encodes the two animations with the Python library. Python 3.14 on Windows is built with
zlib-ng (`zlib.ZLIB_RUNTIME_VERSION` is `1.3.1.zlib-ng`), whose DEFLATE bytes differ from
zlib's: `hello.odrg` is 1210 bytes from the converter and 1213 from the library. The
mapping, the show file and `dvd.odrg` are equal. macOS's Python uses zlib, and there the
bytes are equal.

**Fix.** The test compares `mapping.json` and `show.json` byte for byte everywhere. It
compares each `.odrg` byte for byte where `zlib.ZLIB_RUNTIME_VERSION` does not name
zlib-ng, as now; where it does, it compares what the file holds: the header, and the
records decoded with `odrig.odrg.decode`: canvas, durations and pixels. The condition is
on the zlib, not on the system.

## 6. The app's suite finds Chrome on Windows, and draws as on macOS (`tests/app/support.py`)

**Cause.** `CHROMES` lists the places of macOS and Linux only: on Windows, without
`ODRIG_CHROME`, `test_docs`'s two tests that read messages in Chrome fail with `no Chrome
was found`. With Chrome found, `test_look`'s
`test_the_three_screen_buttons_lie_along_the_bottom_edge_each_a_third_of_the_width`
measures 313 points for a third of 360 where it expects 328 (a sixth of 15 points short
for three buttons): Chrome on Windows gives the page a classic scrollbar 15 points wide,
which macOS's overlay scrollbar does not take.

**Fix.** `chrome()` looks, after `ODRIG_CHROME`, at the places of the system it runs on:
on Windows `Google\Chrome\Application\chrome.exe` under `%PROGRAMFILES%`,
`%PROGRAMFILES(X86)%` and `%LOCALAPPDATA%`, as `converter/tests/browser.test.js` does;
elsewhere the places it has now. Every headless Chrome the suite starts gets
`--hide-scrollbars`, which on macOS changes nothing, as its scrollbars take no room. If
the look test still differs on Windows with that flag, the cause found is fixed in the
test's support and recorded in `docs/drifts.md`.

## 7. The app's tool and its tests on Windows (`app/apptool/webserver.py`, `tests/app/test_tool.py`)

Causes and fixes, one for each failing test:

| Test | Cause | Fix |
|---|---|---|
| `test_a_port_that_is_taken_is_address_in_use` | `webserver.Server` sets `allow_reuse_address = True`; on Windows `SO_REUSEADDR` lets a second program bind a taken port, so `serve` does not fail and the test waits out its 20 seconds | `allow_reuse_address` is true only where the system is not Windows, as the emulator's `httpd.REUSE_ADDRESS` already is (product fix) |
| `test_serve_prints_its_address_serves_and_ends_with_status_0_at_a_signal` | the test sends SIGINT, which Windows cannot send (`Unsupported signal: 2`); `serve` itself already ends on SIGBREAK | start `serve` in its own group and send Ctrl+Break on Windows |
| `test_it_installs_on_the_one_phone_and_refuses_none_and_two` | the fake `adb` the test writes is a script with a `#!` line; Windows cannot run it (`WinError 193`) | on Windows the test's fake programs are written as `<name>.cmd` files that run the same Python with `"%*"`, and the test passes that path, as it passes the fake's path now |
| `test_the_sdk_tool_is_given_one_yes_and_the_packages_and_the_one_licence_must_be_there` | the same, for the fake `sdkmanager` | the same |
| `test_another_licence_or_a_missing_package_is_licence_refused` | the same: the fake does not run, so the tool says `setup-failed` | the same |
| `test_a_node_that_is_missing_or_too_old_is_node_missing` | the fake `node` on the test's `PATH` has no ending Windows runs, so `node` is not found | on Windows the fake is `node.cmd`, which the search of `PATH` finds by `PATHEXT` |
| `test_the_command_line_tools_are_unpacked_as_latest_with_their_executable_bits` | Windows keeps no executable bits: a file without them is still executable to `os.access` | the bits are checked where the system keeps them (`os.name == "posix"`); on Windows the test checks the files are there |
| `test_the_environment_of_a_child_keeps_everything_in_the_work_folder` | the test writes the expected `PATH` with `/` and `:` | the expected value is made with `os.path.join` and `os.pathsep`, as the tool makes it |

The tool's names of the Android programs (`sdkmanager`, `adb`) do not change: making the
APK on Windows is not in this seed. The fake programs of the tests are made by one helper
of the test module, so each test names a fake once.

## 8. Documents and checks

- `AGENTS.md`, "If you work on Windows": every suite that runs on Windows passes there,
  and the list names them: the converter's, the Python library's, the core's, the
  emulator's and the command tool's, the app's, and the onboarding suite.
- `agent/getting-started.md`, "On Windows": the same sentence; the app's suite gets its
  command in the Windows list. The page stays within its 200 lines.
- `docs/emulator.md`: a test, or a person, ends the preview and `odrigctl --log` on
  Windows with Ctrl+C in a terminal, or with Ctrl+Break sent to its own group; both end
  them as Ctrl+C does on macOS.
- The onboarding tests that hold those sentences are changed first and seen failing.
- One entry at the end of `docs/drifts.md`: what failed on Windows, its cause and its fix.

## 9. What a run leaves

Every fix above that stops a program stops it and what it started: the preview stops its
emulator in its `finally`; `--log` holds no child. After each suite the implementer checks
that no `python`, `node` or `chrome` process started by it is running and that ports 8600
and 8601 are free, before the next suite starts. Suites run one at a time.

## 10. What does not change

- No program's output: the converter's files, packed folders, recordings, lines.
- On macOS and Linux: `open` is used as now; SIGBREAK does not exist there; `os.killpg`
  and SIGINT stop the programs as now; the demo test compares bytes; `CHROMES` is as now
  and `--hide-scrollbars` takes no room; `allow_reuse_address` stays true; the fakes are
  `#!` scripts; the bits are checked.
