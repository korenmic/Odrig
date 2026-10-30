# Cross-platform firmware builds — verification

## Task 1 — host-aware setup and owned processes

Observed failures before fixes:

- Windows Python resolved to `venv/bin/python`, instead of `Scripts/python.exe`.
- Successful setup left a real descendant running after its parent exited.
- A failed clone left a partial source at the reusable cache's final path.
- Copying removed a preexisting unrelated `.partial` folder.
- An interrupted command left its captured pipe handles open.
- A consoleless Windows process with CRT streams but no Win32 standard handles
  lost all forwarded setup output (`'' != 'owned-output'`).
- A descendant retaining an explicitly inherited output pipe made successful
  parent exit time out instead of completing cleanup.

The discovered `tests/firmware_host` suite passes all17 tests, including real
process trees on successful/failed exit, timeout and interruption, with resource
warnings treated as errors. It verifies native paths/aliases, unsupported-host
rejection before fetching, distinct host caches, unchanged macOS layout, pinned
WLED rejection, completed-only base/newer stamps, idempotence, UTF-8/spaced arguments
and safe uniquely owned staging. It needs no installed firmware packages or board.

Actual Windows x64 setup through `firmware/fw.py setup` succeeded with Python3.14.2,
PlatformIO6.1.17, Node20.18.0, npm10.8.2 and esptool5.4.0. Tools are under
`build/firmware/hosts/win32-x86_64/`; the existing macOS paths are unchanged. Two
concurrent repeated setups both succeeded (5.119s and5.943s) with the dependency
stamp's bytes and modification time unchanged. The newer environment was separately
installed through its existing lazy setup API, and a repeat returned no work:
PlatformIO6.2.0, Node20.18.0 and npm10.8.2. Requirement pins were not changed.

Setup uses explicit UTF-8 streams and hidden owned processes. Windows children start
suspended, enter their job and are resumed; a watcher closes remaining descendants
at parent exit, including ones retaining output pipes. Unix uses a separate process
group. Pipes and process handles close on every tested outcome. No global key, PATH,
compiler or package installation was changed, and no board was reached.

Full legacy firmware fixture/runner portability belongs to task3. No firmware image,
optional variant, macOS/Linux build, APK or signing-key delivery is claimed here.

## Task 2 — portable build configuration and provenance

Observed before fixes: both generated projects rejected real spaced paths;
Windows checksum output used CRLF; PlatformIO compilation had no explicit job bound.
The discovered host suite now passes all28 tests with resource warnings as errors.
Generated include/forced-include arguments retain complete normalized paths, while
dependency specifications and ordinary INI path values remain complete strings.
Every existing kind keeps its environment, base/newer family, patch choice, output
name, image/checksum validation and provenance handoff in isolated build tests.
Concurrent builds of one checkout serialize before source mutation/compilation.

The actual pinned PlatformIO6.1.17 local dependency manager was inspected and
exercised on Windows: `symlink://` writes a `.pio-link` JSON reference, not a
privileged filesystem link. A real integration test installs a library at a spaced
path with `os.symlink` forbidden and observes a subsequent source edit immediately.
Therefore the existing linking mechanism is retained on all hosts; copied-library
refresh/deletion is unnecessary. No fallback copy or administrator requirement is
introduced.

The image's `.sha256` uses explicit UTF-8/LF. A new `.bin.build.json` companion
records committed/dirty tracked source identity, host, selected environment/tools,
vendor manifest identities, source/configuration hashes and exact image size/hash.
It excludes generated core builds and operator Wi-Fi settings. Tests verify changed
current-source fingerprints, exact bytes, dirty-state reporting and atomic UTF-8/LF
publication. Compiler paths/timestamps/ELF metadata can differ between hosts; source
and image properties are the stated comparison, not a binary-identity promise.

These are configuration, lifecycle and provenance checks, with simulated compilation
for variant mapping. Actual default/image/symbol and cross-host build proof follows
tasks4–5; no real firmware image or physical acceptance is claimed by task2.

## Task 3 — native firmware verification and runner integration

The ordinary runner discovers firmware647, firmware-host28 and runner26 tests;
all three suites pass (701 tests, one Windows privilege skip). The firmware suite
uses the selected native host cache interpreter, including shared tools at spaced
paths. Proof: `build/seed60-task3-suites-verified.log` and its run report. The direct
`tests/run.py` entry point is exercised too. No board suite or board is selected.

Observed before corrections: unavailable Windows ASan/UBSan libraries, binary
stdin translated by the Windows C runtime, Unix-only compiler/executable and path
expectations, literal backslashes interpreted as regex escapes, and missing HOME.
Native C/C++ fixtures now use the core's compiler/runtime-check selection, native
executable names, binary input/output and complete normalized configuration paths.
This Windows compiler supports undefined-behaviour traps, stack protection and
standard-library assertions; unavailable ASan is not claimed. Other hosts retain
the runtime checks their compiler actually supports. The 200 randomized limiter
cases and storage/format/flash-region protections are retained.

A discovered runner execution also exposed a lock-holder launcher leaving its
child alive after kill/wait (WinError32 during temporary-directory cleanup). The
lock fixture now starts the direct base interpreter, so kill/wait owns the process
holding the lock. Refresh/live-mode source assertions follow the current locked
publication and helper boundaries, without changing runtime firmware behavior.

The filesystem-symlink guard alone skips with explicit WinError1314 when Windows
denies symlink privileges. Other backup/output guards run, and the unprivileged
PlatformIO JSON-link integration remains tested. This is not a skipped build.

The runner registers host-only firmware tests, bounds the firmware suite to one
worker and locates the correct base/native cache. With `--builds`, a canonical APK
toolchain that has no archive for this host is explicitly reported as not run;
the firmware build still runs and no existing APK is removed or called rebuilt.
Actual local firmware builds, cross-host CI and final artifact delivery follow.
