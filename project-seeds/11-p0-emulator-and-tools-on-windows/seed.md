# Emulator and tools on Windows

## Summary

Make the converter, the emulator and the command tool work on Windows from a fresh clone, with
the same commands as on macOS, so that a contributor on a Windows computer can make
animations and try them in the emulator. The work is done and verified on the Windows
computer.

## Priority

- `P0`

## Depends On

- Seeds 01 to 05, which built the tools.
- Seed 10, whose getting-started page and animation guide this seed extends for Windows.

## Product Context

A second contributor is starting on a Windows computer, to prepare animations and test them
before they go to the board.

The converter was written to run anywhere but has only ever been run on macOS. The emulator
and the command tool run on macOS only, for three reasons:

- The shared core is built as a library by a makefile that expects the Mac's compiler.
- The emulator's virtual serial port is a pseudo-terminal, which Windows does not have.
- The command tool opens serial ports the way macOS and Linux do.

None of this needs a new design. The emulator is a Python program around the shared core
with a web page, and all three are portable. What is missing is a way to build the core on
Windows, a stand-in for the virtual serial port, and serial access on Windows.

The board stays with the first computer. Building and flashing firmware on Windows is not
part of this seed.

## Technical Constraints

- One code base. Nothing changes in how the tools behave on macOS, and the existing suites
  keep passing there.
- Windows 10 and 11, with Python 3.10 or later. The emulator and the command tool still use
  only the Python standard library.
- The core's source files are used unchanged. On Windows the core is built by a tracked
  script that works with the compilers a Windows developer normally has: Microsoft's C++
  build tools, or a GCC or Clang toolchain. The page that explains setup says which one to
  install when none is present.
- GNU Make is not required on Windows.
- The line protocol is the same on every route: one command line in, one reply line out, as
  `docs/commands.md` defines.
- No driver or other system component is installed to imitate a serial port.
- Paths, line endings and file names behave the same on every platform. Tracked files do not
  change when checked out on Windows.
- The work is implemented and tested on the Windows computer. What cannot be tested there is
  listed for the first computer.

## Required Behavior

1. One documented command builds the core's shared library on Windows.
2. The emulator starts on Windows with the same command line as on macOS, serves the same
   page, and accepts commands over HTTP.
3. On Windows the emulator offers the line protocol of its virtual serial port on a local TCP
   port instead, and prints that address at start. The same option exists on macOS, where the
   virtual serial port stays the default.
4. The command tool reaches a target by a serial port name, by an HTTP address, or by the
   address of the emulator's local TCP port, on every platform.
5. The command tool opens a real serial port on Windows, by its `COM` name, in the way that
   does not restart the board.
6. The record mode and the test suites of the converter, the core and the emulator run on
   Windows with one documented command each.
7. The getting-started page and the animation guide gain what a Windows contributor needs:
   what to install, the commands, and what is not available on Windows.
8. When the JavaScript converter is present in the repository, its suite is run on Windows
   too and the result is recorded.

## Definition Of Done

1. On Windows, from a fresh clone: setup, then the converter suite, the core suite and the
   emulator suite pass.
2. On Windows, the demo show for the target canvas plays in the emulator at 20 or more
   refreshes per second, the page shows the LEDs and the mapping view in Edge and in Chrome,
   and the command tool's `play`, `brightness` and `status` give the expected replies over
   HTTP and over the local TCP port.
3. On Windows, importing a GIF and a video for the target canvas, packing a show and playing
   it in the emulator works as the animation guide describes.
4. On macOS, the existing suites pass and the virtual serial port works as before.
5. The check of a real board on a `COM` port is listed as open for whoever has a board on a
   Windows computer.

## Open Questions

None. Use the resolved behavior in this seed.
