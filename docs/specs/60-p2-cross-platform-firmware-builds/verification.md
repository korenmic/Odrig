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

## Task 4 — actual local builds and the host matrix

Windows11 x86_64, Python3.14.2: the actual `firmware/fw.py build` completed the
default `odrig_microsd` in750.63s including cold vendor downloads. Selected platform
55.03.312-1, Arduino3.3.12/IDF5.5.5 and compiler14.2.0+20260121 stayed at their pins.
Image1,879,248 bytes, SHA256
`3e238d39c5eea921e37c44837646132ff831eac9fa8956befba286bc1f5b5044`;
reported application flash1,818,869/3,145,728 and static RAM70,836/327,680 bytes.
Offline esptool validates ESP32-S3 segments, checksum and image validation hash.
Its embedded ELF hash matches the inspected ELF; linked `odrig_core_begin`,
`odrig_core_feed` and `odrig_core_poll` are present. No board was opened/flashed.

The compiled runtime/configuration fingerprint is
`d055794f3cdbbf80a932589cb26606944fc5247b69431b939fc023cea13cbf43`.
Local build revision is cfa61e1 with tracked task4 documentation edits recorded as
dirty; no runtime source changed. The final software/artifact revision follows in
task5. Six corrupt/stale copies of the actual image were refused (checksum, chip,
body/provenance, input identity, source revision and vendor identity), preserving
the original. Logs: `build/seed60-task4-default-build.log`, default-inspection.log
and inspection-refusals.json; outputs include `.bin.build.json`, image-info.txt and
verification.json. The source provenance, ELF SHA and image hash are distinct.

An owned detached test checkout at `scratch/firmware path check` used shared native
tools. An actual build interruption at4.07s left no successful output. A subsequent
intentional current-header `#error` was observed at the spaced checkout's path,
proving its current source was compiled; that probe was restored exactly. The clean
build then passed in253.40s, warm reuse in30.91s, and offline inspection in1.12s.
Both dependency stamp bytes and mtimes stayed unchanged. All current input hashes
matched the normal checkout. Final spaced image1,879,248 bytes, SHA256
`9f8680a14ea874e0ea934aab93b7e1a735acc221e5cac74c40ffa1bf6aa43f2f`.
Different absolute paths/ELF metadata explain why byte identity is not promised;
source/configuration identity and image properties match. Proof and selected outputs
are retained under `build/seed60-task4-spaced-*`. The temporary checkout is removed
after copying its proof. Shared tools themselves had no spaces in this local case;
the configured CI checkout also puts its default toolchain under a spaced root.

Host matrix: read-only GitHub token, same PR head, Python3.12, Windows/macOS/Linux,
bounded compilation and retained firmware/ELF/provenance/inspection/test artifacts.
The Mac job also runs the newcomer walkthrough, required by the changed guide.
Workflow YAML is parsed locally and official actions are pinned to resolved commit
SHAs. Actual remote host/architecture results are still pending task5, not inferred
from these local runs. Only the default variant was compiled here; all eight variant
selections remain tested. Other variants and unobserved architectures are not claimed.

Affected verification: firmware647 PASS/one explicit Win1314 skip in the final native
discovery log; host28, runner26 and onboarding88 PASS. Initial onboarding failures
exposed stale Mac-only/suite expectations and page length overflow; updated wording
and registry retain the original150/200-line caps. The final firmware doc check also
passes after keeping its developer-tools phrase intact. Earlier task3 and seed59
full-suite evidence remains above; no unnecessary app/runtime rerun was added.
Physical, electrical, board and phone acceptance remains open.
