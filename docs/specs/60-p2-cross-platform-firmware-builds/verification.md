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

## Integrity bridge 6 — actual cross-host proof and canonical fixture paths

PR35's first host run41142210975 actually builds and inspects the default firmware
on all three hosts from clean committed5c823c0. All have input fingerprint
`d055794f3cdbbf80a932589cb26606944fc5247b69431b939fc023cea13cbf43`.

| Actual host | Image bytes | Image SHA256 |
|---|---:|---|
| win32/x86_64 | 1879216 | `a8b4f482b325c0ca016e3b041d2deabfaaced38f36465d943de741c7641cc509` |
| darwin/arm64 | 1879216 | `8dec6b2b3d628ab88ebf38b676daf4d551a3b748959cd77fa996b5ba19d82fa5` |
| linux/x86_64 | 1879232 | `fa5179b80f640e25db7be0e1dca75f7039c882cc241ca979130dc06aea35c18c` |

Each host passes offline image/current-player inspection and its647-test firmware
suite. Linux's complete job passes. Windows and Mac fail the same three new fixture
expectations: Windows TEMP uses RUNNER~1, which resolves to runneradmin; Mac /var
resolves to /private/var. The product correctly emits canonical paths, while tests
compared their alternate spelling. The failed matrix is a PR-caused test regression,
not successful final CI. The Mac walkthrough did not run after this failed step.

The repair changes only expected configuration/cache paths to their canonical
identity, retaining the same tests/assertions and production behavior. The affected
host28 + runner26 suites pass by discovery normally and again with a real local
Windows8.3 temporary root (54 tests in each run). Original failed records and host
artifacts are retained under `build/seed60-ci-initial/`; repair proof is in
`seed60-task5-ci-fixtures-verified.log` and `seed60-task5-shortpaths.log`.

TACTIC's integrity bridge separates this necessary committed CI repair from the
existing final delivery task. The planned requirements/scope remain unchanged:
task6 is this minimal bridge; task5 stays unchecked until the committed repair's
remote checks, final artifacts and handoff are complete. This permits a truthful
one-task/one-proof-commit boundary without rewriting pushed history. Actual Mac
arm64, Windows x86_64 and Linux x86_64 default compilation is observed; Mac Intel,
Linux arm64 and optional variants are not claimed. Final artifacts are rebuilt from
the bridge revision before delivery; the already created dedicated key is reused.

## Integrity bridge 7 — checked Clang scheduling frame

Run41144153561 passes the complete Windows/Linux jobs and the Mac default build,
offline inspection and firmware647/host28/runner26 suites. Its Mac newcomer run
then observes a real checked-core failure: Clang/ASan reports playlist_turn's frame
as528 bytes against the unchanged512-byte warning/error bound. The seven-test
walkthrough has one failure; its converter1595, Python552 and onboarding88 checks
pass, while core/emulator cannot proceed past this compilation error. Original
failure: `build/seed60-task5-mac-walkthrough-failed.log`. This is owned by the PR;
the failed overall run is not treated as final successful CI or artifact delivery.

The existing bounded clocks-only scheduling block is extracted into a separate
ODRIG_NOINLINE clock_only_turn helper, called under the same mode condition.
A structural comparison verifies that its body is token-identical and that the
remainder of player.cpp is unchanged after accounting for that extraction/call.
No algorithm, state field, arena budget,512-byte bound or sanitizer is changed.
An early checked Mac core host build now precedes cold firmware setup in CI, so
this compiler protection is tested before a long default build.

Local strict checked host and shared library builds pass, retaining Werror and
frame512 with the Windows compiler's supported runtime checks. All2392 discovered
regressions pass: core1035, emulator656, firmware647, host28 and runner26, with
the established explicit host skips. This includes existing Off/Between/Only,
complete message-loop, playlist restoration and emulator transport cases. Proof:
`build/seed60-task7-suites.log` and `seed60-task7-structural-review.log`.

The actual updated Mac Clang/ASan bound and complete newcomer walkthrough remain
the post-commit remote gate owned by task5. The final firmware and APK are rebuilt
again after this committed safety repair, with its new current-input identity and
the same persistent signer; no stale52b artifact is delivered. No board is used.

## Task 5 — final host gate and artifact delivery

The corrected software revision is `7e51b988de85603da1e396ca3a0ad53dd3c2f785`. Its
[host run](https://github.com/korenmic/Odrig/actions/runs/41147438908) has successful Windows x86_64 and Linux x86_64 jobs,
including each default build, offline image/source/symbol inspection and all discovered
firmware/host/runner checks. The owner explicitly requested skipping Mac verification
and using Windows alternatives. The Mac default build, offline inspection, host tests
and checked core build had already passed; cancellation of its full newcomer walkthrough
was requested, and its result is excluded from the delivery gate. The retained run
status is `completed`/`cancelled`, not an all-host green claim. Windows native firmware setup,
spaced-path builds, checked core/emulator suites and APK packaging supply the local
alternative. The PR matrix now requires Windows/Linux; Mac remains opt-in via the
manual workflow's include_macos input, including its full newcomer walkthrough.
After the workflow/documentation policy update, all88 discovered onboarding checks
pass locally (run20261031-022600-134704). No Windows verification depends on Mac access.
All downloaded compiled input
maps equal `224a133c05622531faf2d60c35a6d30d4b660bea7f2ff9520924d0107d113774`. Exact downloaded image and ELF hashes are checked
against the retained provenance/inspection records.

| Actual host | Image bytes | Image SHA256 |
|---|---:|---|
| win32/x86_64 | 1879264 | `b9071e7bb2be5db80130f20ac64d9ddba40955627dd34459d681d99f6b839297` |
| linux/x86_64 | 1879280 | `5288575a95e48bf812c3857294dc16d81e23f836d55d6911a3d887ffa9e7894c` |

Only the default was actually compiled. Mac Intel, Linux arm64 and optional variants
remain unperformed; eight variant selections are covered by their existing tests.
No physical board, SD installation, wiring, power or phone check is claimed.

Final Windows firmware and shared-code APK were rebuilt from the clean software
revision above after the CI fixture repair. The final CI host-selection change does
not change compiled firmware or shared app inputs. Firmware uses the existing fw.py default
pipeline and passes offline image validation/current-player inspection. APK uses
authoritative shared staging, Capacitor8.5.3, existing JDK21/SDK36/build-tools35 and
the pinned Gradle8.14.3 wrapper with isolated caches/home. The same eight APK tests
pass with native Windows SDK tool resolution only: application/permissions/HTTP,
native activity/plugin and every web/converter/thumbnail asset byte-for-byte. Test
proof is bound to the final APK hash; its bundled source note is clean/current.
The generic automatic APK archive manifest remains Mac-arm64-only; no general APK
host pipeline was added. The validated native Windows packaging recipe is recorded
in the delivered signing notes.

The dedicated persistent PKCS12/RSA2048 key is reused across final rebuilds. Its
certificate SHA256 is `5a489ec294e53cdec085d71092cf4e7285ae08d4d43c19929d84130f3649f0f1`. The owner's global Android debug
keystore remains byte-identical. Key, credential JSON, public certificate and reuse
instructions were uploaded beside the APK in Google Drive `Artifacts/odrig/`; no
private credential or key was committed. The old Mac signer was explicitly waived.
The reuse notes explain that an old-key installation can require uninstalling before
installing the new signer, and that future builds must reuse this backed-up key.

| Delivered file | Bytes | SHA256 |
|---|---:|---|
| `odrig-debug.p12` | 2674 | `b49e3f8b499571af7ae7281cfeb09eaa7fdb15cebc9a59397eced9e978318324` |
| `odrig-firmware.bin` | 1879296 | `94d1bd97605f10adb795da6ea31e3f0d5336ccc49eb823323b82d11669bfe2b3` |
| `odrig-debug.apk` | 19046838 | `51db8ac28ba1654375c95c6f47af4df3eed6fc37ab0a48fddf71874b14bb0a3c` |

The existing `odrig-debug.apk` and `odrig-firmware.bin` were opened in place with
r+b, overwritten/truncated, flushed, and read back. Their mounted Drive file
identities were preserved: APK inode11084,
firmware inode11087, on the same
device before/after. Prior bytes are backed up under build/. Every delivered byte
hash is verified, including private-key/credential backups and firmware checksum,
provenance and inspection companions. `odrig-delivery.json` is the Drive receipt;
local proof is `build/seed60-task5-drive-proof.json`. The unrelated recording is
untouched. This verifies the mounted Drive filesystem update/readback, without
claiming an independent remote API response.

[PR35](https://github.com/korenmic/Odrig/pull/35) is the only final PR, targeting
master from the stacked tip branch. The delivery/CI-policy commit does not change
compiled/app inputs; its post-push Windows/Linux checks are owned before the ready handoff and
reported in the PR/checkpoint. Four physical acceptance tasks from56–59 stay open.
The final commit audit extends the22 earlier proof commits with this task5 boundary.
Every task has a separate checkbox/proof commit. Six earlier subjects omit the
required Seed/task prefix: `541e702`, `907d812`, `f24aa9f`, `c59aa8d`, `b677d19`, `8ae2e35`. These naming deviations are disclosed;
pushed history is preserved. They do not bundle implementation tasks.
