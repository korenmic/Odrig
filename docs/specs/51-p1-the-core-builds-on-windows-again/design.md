# Design: the core builds on Windows again

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/51-p1-the-core-builds-on-windows-again/seed.md`.

## The comparison GCC refuses

`page_step` in `core/src/catalog.cpp` gathers a line of a drive's catalog page into
`OrderReader::line`:

```cpp
if (line.length + 1 < kOrderLineRoom) {
```

`line.length` is a `uint16_t`; in the sum it becomes an `int`, and `kOrderLineRoom` is a
`const uint32_t`. GCC 16 warns of a signed and unsigned comparison, `-Wsign-compare` of
`-Wall`; the Clang of macOS sees that the value cannot be negative and does not. The mend:

```cpp
if (static_cast<uint32_t>(line.length) + 1 < kOrderLineRoom) {
```

The length is at most `kOrderLineRoom - 1`, 161, so the sum is the same number either way
and the same lines are taken.

## Not inlined, in each compiler's words

Nine functions are kept out of line so that the frame of the refresh stays within
`-Wframe-larger-than=512`: `act`, `read_record`, `finish`, `write_page`, `stage` and
`page_step` of `catalog.cpp`, and `lowest_in`, `next_animation` and `playlist_turn` of
`player.cpp`. They are written `__attribute__((noinline))`, which only GCC and Clang know.

`core/src/core_state.h`, which both files include through `catalog.h` and `player.h`,
defines one macro before its namespace:

```cpp
#if defined(_MSC_VER)
#define ODRIG_NOINLINE __declspec(noinline)
#else
#define ODRIG_NOINLINE __attribute__((noinline))
#endif
```

with a comment that says what it is for. The nine functions are written
`ODRIG_NOINLINE bool act(...)` and so on. For GCC and Clang the preprocessor gives the
same text as before, so the firmware's build and macOS compile what they compile now.
`clang-cl` defines `_MSC_VER` and knows `__declspec(noinline)`.

The macro goes into `core_state.h` and not into a header of its own: every source of the
core reaches that header already, and one macro does not need a file.

## The `Marker` Microsoft's compiler doubts

In `catalog_read_internal`:

```cpp
Marker marker;
if (catalog.state == kCatalogNone) {
    catalog.state = opened == kNone ? read_marker(source, marker) : kCatalogDamaged;
    ...
}
for (...; catalog.state == kCatalogOk; ...) { ... marker.counts[page] ... }
```

The state is `kCatalogNone` or `kCatalogDamaged` before the `if`, and becomes
`kCatalogOk` only through `read_marker`, so `marker` is set whenever it is read. Microsoft's
flow analysis does not follow the state and gives C4701, an error with `/WX`. The mend is
`Marker marker = {};`: zeros, then set as before. The structure is 100 bytes; the frame
of `catalog_read_internal` does not grow, and the zeros are written once a start. GCC's
`-Wmissing-field-initializers` does not warn for empty braces.

## The test

`tests/emulator/test_build_script.py` holds the tests of the build script and loads it as
a module, `build`. A new class there, `MicrosoftsCompiler`, has one test:

- It looks for the compiler as the script does when nothing is named:
  `build.microsoft(build.MICROSOFT[0], os.environ, shutil.which,
  build.microsoft_environment)`. When that gives `None`, as on macOS and on a Windows
  without Microsoft's build tools, the test is skipped and says why.
- In a temporary folder it compiles every source `build.sources()` gives, from `core/`,
  with `[toolchain.cxx, *build.MICROSOFT_FLAGS, "/c", "src/<source>",
  "/Fo<folder>\\<name>.obj"]` and the environment of the toolchain, several at a time.
- It asserts that every compilation ended with status 0, and on failure shows the name of
  the source and the lines of the compiler's output that hold `error` or `warning`.

It does not touch `core/build/`, so it does not disturb the library the rest of the suite
loads, and it takes about as long as one build with Microsoft's compiler. Only the
library's flags are used; the others are compiled by hand in the last check, in a
folder of its own.

## The proofs that it failed

- GCC: on the branch before the mend, `.venv\Scripts\python core/build.py shared` and
  `core/build.py test` stop with the error of `catalog.cpp:860`; the commit of the mend
  quotes it.
- Microsoft's compiler: the new test, run before the macro, fails with C2065 at the nine
  functions and C3861 at their calls; with the macro and before the zeros, with C4701 at
  `catalog.cpp`. The commit quotes both.

## The pages

- `docs/core.md`, after the sentence on the tests skipped with Microsoft's compiler: the
  emulator's suite compiles every source of the core with Microsoft's compiler wherever
  the build script finds it, also where the core is built with GCC.
- `docs/drifts.md`, at its end: `## Seed 51: the core builds on Windows again`, with the
  place of the macro, the zeros in place of a turned-off warning, and the emulator's check
  of an old library left out.

## The last check

Every suite on Windows, one at a time. Then, in a copy of `core/` and `tests/core/host/`
under `scratch/`, so that the checkout's `core/build/` keeps GCC's library:
`core/build.py shared --cxx cl`, and every source of the core and of the test host
compiled with Microsoft's compiler and the script's flags for the library, the checked
library and the test host. Running the core's suite on a library of Microsoft's compiler
is not part of this seed. Then the emulator, from the main checkout with no `--core`, with
an empty show and a drive, on ports of its own: `status` shows a playing animation and
`list` the drive's folders and files.
