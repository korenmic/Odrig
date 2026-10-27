# Requirements: the core builds on Windows again

The seed is `project-seeds/51-p1-the-core-builds-on-windows-again/`. It has no open
question. Where these requirements decide a point the seed leaves to the design, the
decision is recorded in `docs/drifts.md`.

## 1. GCC

1.1 On Windows, `python core/build.py shared` builds `core/build/odrig_core.dll` with the
GNU-style compiler the script finds, the WinLibs build of MinGW-w64 GCC 16 on the owner's
computer, with the flags of the script, `-Werror` among them.

1.2 On Windows, `python core/build.py test` builds the library and the test host with that
compiler and runs the core's suite, which passes.

1.3 The comparison of `core/src/catalog.cpp` that GCC 16 refuses, in the reading of a
drive's catalog page, compares an unsigned length. The lines that are taken and the lines
that are marked too long are the same as before.

## 2. Microsoft's compiler

2.1 On Windows, `python core/build.py shared --cxx cl` builds the library with
Microsoft's compiler, with `/W4 /WX`, in a checkout whose `core/build/` is its own; and
every source of the core and of the test host compiles with it, with the flags the script
gives each, those of the library, of the checked library and of the test host.

2.2 The functions of `catalog.cpp` and `player.cpp` that are kept out of line stay out of
line with every compiler: Microsoft's marks them as not inlined in its own words, GCC and
Clang in theirs, through one macro of the core's own headers.

2.3 The `Marker` of `catalog_read_internal` has a value before any path can read it. It is
read only after `read_marker` has set it, as before.

## 3. Nothing else changes

3.1 What the core does is unchanged: every reply, every file it writes, every frame it
draws.

3.2 GCC and Clang compile the same code as before, for the board, for macOS and for
Windows: the macro is `__attribute__((noinline))` for them.

3.3 No flag of `core/build.py` or of `core/Makefile` changes, and no warning is turned
off, in the build or in a source.

3.4 The firmware and its build, the emulator, the command tool, the app, the converter and
every command are unchanged.

3.5 The emulator's check of the library it loads stays as it is; the seed leaves it out.

## 4. Tests

4.1 The emulator's suite, beside the tests of the build script, compiles every source of
`core/src/` with Microsoft's compiler and the flags the script gives it, into a temporary
folder, wherever the script finds that compiler, and is skipped with a reason where it
does not.

4.2 That test is seen failing on Windows before the mend, with `error C2065: 'noinline':
undeclared identifier`, and after the macro with `warning C4701: potentially
uninitialized local variable 'marker' used`.

4.3 The GCC fault is seen in the core's suite before the mend: `python core/build.py test`
stops with `-Werror=sign-compare` at `src/catalog.cpp:860`.

4.4 On Windows every suite passes, one at a time: `npm test --prefix converter`, the
converter's, the core's, the emulator's with the test of 4.1 run and not skipped, the
app's and the onboarding suite.

## 5. Pages and the seed

5.1 `docs/core.md` says that the emulator's suite compiles the core with Microsoft's
compiler where the build script finds it.

5.2 `docs/drifts.md` gains one entry at its end, with the answers of the design.

5.3 The seed is `in_progress` from the first task and `completed`, with `completedAt`,
after the last; `AGENTS.md` no longer names it in "What is coming" then.

5.4 The emulator, started on Windows with no `--core` from the main checkout, loads the
library built from the branch, plays a show and lists a drive.
