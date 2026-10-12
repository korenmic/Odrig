# Tasks: Emulator and tools on Windows (seed 11)

Seeds 01 to 05 and 10 are implemented: these tasks use the converter `odrig/`, the core
`core/`, the emulator `emulator/`, the command tool `odrigctl/` and the suites in `tests/`
as they are. Where the real code differs from what this spec's design relies on, follow the
code and record the difference in `docs/drifts.md`.

Every task is done on the Windows computer. None needs the board. Nothing here can be run
on macOS: what a task changes for macOS goes into the list "open for the first computer"
that task 7 writes into `docs/emulator.md`.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. A suite is run by discovery, with the
  command the task names. Until task 4 the emulator suite has modules that do not load on
  Windows, and until task 6 the converter suite has tests that fail there: a task before
  those runs the suite and reads the results of the tests it added and of the modules it
  touched.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No file of `core/src/` or `core/include/` is changed, and `core/Makefile` is not changed.
- `emulator/serialport.py` is not edited, and the functions `_open`, `_received` and
  `_write` of `odrigctl/client.py` keep their text.
- Nothing is installed in the system. A compiler or another program that is fetched goes
  into `tools/` at the top of the repository, unpacked and not installed; a trial goes into
  `scratch/`. Git ignores both, and nothing in them is staged.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [ ] 1. The build script and the shared library of each system
  - Set the seed's state to `in_progress`.
  - `.gitignore` ignores `/tools/`. `.gitattributes` gets `* -text` as its first line.
  - Create `core/build.py` as the design gives it, with `shared`, `clean` and the static
    library; `test` comes with task 5. It writes `core/build/toolchain.json`.
  - `emulator/binding.py` gets `LIBRARY_NAME` and `BUILD_COMMAND` by system, and
    `emulator/app.py` takes its default `--core` from them.
  - `tests/emulator/__init__.py` builds with the build script where the system is not macOS.
  - `tests/emulator/test_build_script.py`: the order in which a compiler is found, with
    stand-ins for the path and for `tools/`; the flags of each kind; the names of the
    exports read from the header; `no-compiler`; and, on Windows, that the built library
    exports the seven functions and imports only libraries of Windows.
  - Requirements 1 and 6.1, and 2.2.

- [ ] 2. The line port, and the emulator starting on Windows
  - Create `emulator/lineport.py`. `emulator/app.py` gets `--tcp-port`, opens the ports of
    the system as the design's table says, prints `tcp:`, and waits for a signal in short
    waits, with `SIGBREAK` where it exists.
  - The event `hello` carries `tcp`. The page's header shows the line port.
  - `tests/emulator/test_lineport.py`: bytes in order and unchanged, a line in pieces,
    several lines at once, two connections, a reply to the connection that finished the
    line, no echo, the transport `tcp` in the log, `address-in-use`, the printed lines of
    each system, `--tcp-port` with `--record` refused, and `--serial-link` refused on
    Windows.
  - Requirements 2.1, 2.3 and 3.

- [ ] 3. The command tool: TCP, and a real serial port on Windows
  - `odrigctl/client.py` gets `tcp_exchange` and picks the serial port of the system.
    `odrigctl/cli.py` gets `--tcp`. Create `odrigctl/winserial.py`.
  - `tests/emulator/test_tool_tcp.py`: every command over TCP against the emulator, the
    exit statuses, a line that is no reply skipped, no answer in time, nothing listening,
    an address without a port.
  - `tests/emulator/test_winserial.py`, with a stand-in for `kernel32`: the name opened,
    also above `COM9`; RTS lowered before DTR; both refusals ignored; the settings written;
    a name that does not open. It runs on every system.
  - `tests/emulator/test_scope.py` knows the new modules and which of them may use `ctypes`
    and `socket`.
  - Requirement 4.

- [ ] 4. The emulator suite on Windows
  - Create `tests/emulator/js/shell.js`; the tests choose the JavaScript shell by system.
  - The helper `Emulator` reads the ports the emulator has and stops it with the signal of
    the system. Tests that need a pseudo-terminal are skipped where there is none, with the
    reason.
  - Run `python -m unittest discover -s tests/emulator -t .`; it passes on Windows.
  - Requirements 5.3, 5.5 and 5.6, and 2.4.

- [ ] 5. The core suite on Windows
  - `core/build.py` gets `test`: the test host with the checks the toolchain has.
  - `tests/core/host/` gets the calls of Windows for aligned memory and for unchanged
    input and output. `tests/core/support.py` reads `toolchain.json`; the tests that read
    an object listing read the form of the system.
  - Run `python core/build.py test`; it passes on Windows.
  - Requirement 5.2.

- [ ] 6. The converter suite on Windows
  - Settle each failure of `python -m unittest discover -s tests/converter -t .` on
    Windows as the design says, in the tests, and in the tool only where the tool writes
    other bytes on Windows.
  - Run the suite; it passes on Windows.
  - Requirements 5.1 and 6.2.

- [ ] 7. The pages
  - `agent/getting-started.md`, `agent/animation-guide.md`, `agent/README.md`,
    `agent/vocabulary.md`, `AGENTS.md`, `README.md`, `docs/emulator.md`, `docs/core.md`,
    `docs/commands.md`, and the change log of `docs/decisions.md`.
  - `docs/emulator.md` gets the two lists: open for the first computer, and open for
    whoever has a board on a Windows computer.
  - `tests/onboarding` and the tests of the documents in the other suites learn the
    commands of Windows.
  - Run the four quick suites; they pass on Windows.
  - Requirements 5.4 and 7.

- [ ] 8. The final check, and the seed's state
  - In a fresh clone on the Windows computer, set up as the getting-started page says: the
    four quick suites pass.
  - The demo show plays in the emulator; the page is looked at in Edge and in Chrome, LEDs
    view and mapping view; `play`, `brightness` and `status` over HTTP and over the line
    port give the expected replies; the refreshes a second are read.
  - A GIF and a video are imported for the target, packed and played, as the animation
    guide describes.
  - `docs/emulator.md`, "What has been checked", gets what was seen on Windows.
  - Set the seed's state to `completed`.
  - Requirements 2.5 and 8.
