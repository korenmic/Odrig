# The core builds on Windows again

## Summary

On Windows the core no longer builds, with either compiler the build script takes there.
`python core/build.py shared` stops with an error, and the emulator then loads whatever
older `core/build/odrig_core.dll` is left on the disk, without a word. With GCC, the
WinLibs build of MinGW-w64 that the script finds first on the owner's computer, one
comparison of `core/src/catalog.cpp` is refused as a comparison of a signed and an
unsigned number. With Microsoft's compiler, nine functions of `catalog.cpp` and
`player.cpp` are marked `__attribute__((noinline))`, which it does not know, and one
`Marker` of `catalog.cpp` is said to be perhaps read before it is set. Every warning is an
error in the core's build, so each of these stops it. This seed mends the three places,
without changing what the core does, and adds a test that compiles the core with
Microsoft's compiler wherever the suite finds it. Nothing else changes: not the board, the
firmware, macOS, the emulator, the app or any command.

## Priority

- `P1`

## Depends On

- Seed 11, for the build script `core/build.py`, which builds the core on Windows with
  GCC, Clang or Microsoft's compiler, with every warning as an error.
- Seed 26, for every suite passing on Windows, which this fault undid for the core's
  suite and for everything that loads the library.
- Seeds 35 and 41, whose code holds the three places: the catalogs of the storages, and
  the exhausting order of the playlist.

## Product Context

The owner wants to run the emulator on Windows with the animations of the installation's
collection browsable in the app's explorer. On 2026-10-27 the build of the core failed on
the owner's computer, and the emulator ran an old library without saying so. A core that
does not build on Windows also stops the core's suite there, `python core/build.py test`,
since the suite builds the core first, and every suite that loads the library tests an old
one or none.

## Technical Constraints

- **What happens today.** Read and built at `master` 3a9ba57 on 2026-10-27, on Windows 11.
  - The script finds, in this order, the compiler named with `--cxx`, the one `CXX`
    names, one unpacked under `tools/`, one on the path, and then Microsoft's
    (`core/build.py`, `find`). On the owner's computer the one on the path is
    `g++` 16.1.0 of WinLibs (MinGW-w64, UCRT), and Microsoft's is the Build Tools 18,
    `cl` 14.50.
  - The flags are `GNU_FLAGS` and `MICROSOFT_FLAGS` of the script: `-Wall -Wextra
    -Wpedantic -Wshadow -Werror` with GCC, `/W4 /WX` with Microsoft's compiler.
  - With GCC, every source of `core/src/` and of `tests/core/host/` compiles but one:

    ```
    src/catalog.cpp:860:33: error: comparison of integer expressions of different signedness: 'int' and 'const uint32_t' {aka 'const unsigned int'} [-Werror=sign-compare]
      860 |             if (line.length + 1 < kOrderLineRoom) {
    error: build-failed: g++ ended with status 1
    ```

    `line.length` is a `uint16_t` of `OrderReader` (`core/src/core_state.h`). It becomes
    an `int` in the sum, which is never negative there; GCC 16 still warns. The Clang of
    macOS does not.
  - With Microsoft's compiler, `catalog.cpp` and `player.cpp` do not compile: `error
    C2065: 'noinline': undeclared identifier`, at `catalog.cpp` lines 304, 335, 402, 560,
    758 and 807 and `player.cpp` lines 316, 370 and 387, and every call of those
    functions after them. `__attribute__` belongs to GCC and Clang. The functions are kept
    out of line so that the frame of the refresh stays small (`-Wframe-larger-than=512`).
  - With those lines mended, `catalog.cpp` still stops it: `warning C4701: potentially
    uninitialized local variable 'marker' used`, at line 1136, in
    `catalog_read_internal`. The `Marker` there is read only when `read_marker` has set
    it, so the warning is wrong, but it is an error with `/WX`.
  - With the three places mended in a copy, both compilers build the shared library, and
    every source of the core and of the test host compiles with each, with the flags of
    the library and with those of the test host.
  - No suite compiles the core with Microsoft's compiler today: the core's suite uses the
    toolchain the script found first, which is GCC on the owner's computer.
- **The mend.**
  - The comparison takes the length as an unsigned number:
    `static_cast<uint32_t>(line.length) + 1 < kOrderLineRoom`. The same lines are read
    and the same lines are refused.
  - One macro of the core's own headers marks a function as not inlined: `__declspec(noinline)`
    for Microsoft's compiler and `__attribute__((noinline))` for every other. The nine
    functions use it. GCC and Clang, and so the firmware's build and macOS, compile
    exactly what they compile today.
  - The `Marker` of `catalog_read_internal` starts as zeros. It is set before it is read,
    as today.
  - No flag of the build script changes, and no warning is turned off.
- **The test.** In the emulator's suite, beside the tests of the build script
  (`tests/emulator/test_build_script.py`): every source of the core compiles with
  Microsoft's compiler, with the flags the script gives it, into a folder of the test's
  own, wherever the script finds that compiler; the test is skipped where it does not, as
  on macOS. It is seen failing first, with the errors above. The GCC fault is seen in the
  core's suite, whose build fails today, and whose test
  `test_they_are_valid_in_every_standard_from_cpp11_on` compiles every source with
  `-Werror`.
- **What stays.** The core's behaviour, its frames, the board, the firmware and its build,
  the build script, the Makefile and macOS, the emulator, the command tool, the app and
  every command and reply.
- **Not in this seed.** The emulator does not check that the library it loads is as new
  as the core's sources. That it ran an old library without a word is a gap of its own,
  for a seed of its own if the owner wants one.
- **The pages.** `docs/core.md` says that the emulator's suite compiles the core with
  Microsoft's compiler where it finds it. `docs/drifts.md` gains an entry at its end.

## Required Behavior

1. On Windows, `python core/build.py shared` and `python core/build.py test` build the
   core with GCC, the WinLibs build of MinGW-w64, with every warning an error, as the
   script does it.
2. On Windows, the same commands with `--cxx cl` build it with Microsoft's compiler.
3. What the core does is unchanged, and so is what GCC and Clang compile for the board and
   for macOS.
4. A test compiles every source of the core with Microsoft's compiler wherever the suite
   finds it.

## Definition Of Done

1. On Windows, `python core/build.py shared` builds `core/build/odrig_core.dll` with GCC,
   and with `--cxx cl` in a folder of its own the library builds with Microsoft's
   compiler.
2. On Windows every suite passes, one at a time: the converter's own, the converter's,
   the core's, the emulator's with the new test run and not skipped, the app's and the
   onboarding suite.
3. The emulator, started on Windows with no `--core`, plays a show and lists a drive with
   the library built from the branch.

## Open Questions

None. The comparison, the macro and the zeros change no behaviour, and the warning flags
stay as they are; the emulator's check of an old library stays outside this seed.
