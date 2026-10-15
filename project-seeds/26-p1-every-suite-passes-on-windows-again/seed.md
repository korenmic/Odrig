# Every suite passes on Windows again

## Summary

Make every suite that runs on Windows pass there again, after the work that came to
`master` since seed 11: seven tests of the emulator's suite that fail on Windows, the stop
of the command tool's `--log` that is not tested there, the operators' app's suite that
has never been run there, and two of its tests that fail there. The entry file then says
what is true.

## Priority

- `P1`

## Depends On

- Seed 11, which made the emulator, the tools and their suites run on Windows.
- The work whose tests fail on Windows: seed 14 (the show's files stay open while it
  plays), seed 19 (the preview), seed 20 (a USB drive), seed 23 (the command tool's
  `--log`), and seeds 09 and 17 (the operators' app and its suite).

## Product Context

The owner works on Windows as well as on macOS. Seed 11 left every suite that runs on
Windows passing there, and the entry file says so. Newer work was written and tested on
macOS, and on Windows 11 with Python 3.14 these fail now:

| Suite | What fails on Windows | Why |
|---|---|---|
| Emulator, `test_binding` | `test_frame_has_1080_bytes_and_they_are_the_reference`, `test_poll_gives_a_refresh_at_every_grid_time_and_none_between` | the test's temporary folder is removed while the core still has a file of it open: `PermissionError: [WinError 32]` |
| Emulator, `test_drive` | `test_the_folder_appearing_and_going_plugs_the_drive_in_and_pulls_it_out` | the same, for a file of the drive |
| Emulator, `test_preview` | `test_a_file_plays_alone_until_the_preview_is_interrupted` | the test stops the preview with `os.killpg`, which Windows does not have, and the preview and its emulator go on running |
| Emulator, `test_preview` | `test_a_relative_path_and_the_installations_canvas_by_default` | a preview left running by the test before holds port 8600, so the preview says `port 8600 is taken` |
| Emulator, `test_preview` | `test_a_page_port_that_is_taken_gives_a_free_one` | `OSError: [WinError 10022]` where the test holds the port |
| Emulator, `test_demo` | `test_the_packed_folder_holds_the_files_the_other_tests_of_the_suites_play` | the packed demo folder is not the one the core's suite expects |
| App, `test_docs` | `test_every_message_of_the_app_is_on_the_page`, `test_every_message_of_making_an_animation_is_on_the_page` | `no Chrome was found`: the suite looks for Chrome only where macOS and Linux keep it |

Besides these, the tests of the stop of `odrigctl --log` are skipped on Windows, because
the tests cannot send Ctrl+C to another program there, so that stop is not tested on
Windows at all. The app's suite, `tests/app`, has never been run on Windows as a whole.
And the entry file says that the emulator's suite passes on Windows, which is not true
today.

## Technical Constraints

- Nothing changes on macOS or Linux: what each program does there, and what each test
  checks there, stay as they are. A change that is needed for Windows is made so that it
  is a no-op elsewhere.
- What a program writes does not change on any system: the converter's output, the
  packed folders, the recordings and the lines on the serial port and the line port.
- A test is mended where the fault is. A fault of a test's own Windows handling is mended
  in the test or its support. A fault of a program on Windows is mended in the program.
- The core does not keep a file of a show or of a drive open once its host has stopped it
  or let it go; a temporary folder of a test can then be removed on Windows. The core's
  seven functions keep their names and their meaning.
- A test that starts a program stops it, and everything that program started, on Windows
  as on macOS. On Windows a program is stopped as the other tests of the suites stop one:
  started in a new process group, and given Ctrl+Break. Nothing a test starts is left
  running, and no port stays taken after it.
- No test takes it as given that port 8600 is free. A test that checks the default port
  checks the message `port 8600 is taken; the page is on <port>` when another program
  holds 8600, and the default itself when it is free.
- On Windows the command tool's `--log` stops on Ctrl+Break as it stops on Ctrl+C, and
  the tests of its stop run on Windows by sending Ctrl+Break.
- A browser that a test starts is Chrome, headless, with a profile folder of its own that
  is made for the run and removed after it. It never opens a window, and it is never
  asked for its version with `--version`. On Windows the suites find Chrome in its usual
  places: `Program Files`, `Program Files (x86)` and the user's `AppData\Local`, after
  `ODRIG_CHROME`.
- A test of the app's suite that needs what this computer does not have, such as an
  Android phone, is skipped on Windows with its reason, exactly as it is skipped on a Mac
  that does not have it. Nothing is installed in the system: what a suite fetches goes
  under the repository's `tools/` or `build/`, as the suites already do.
- Suites run one at a time on Windows: two at once can use up the system's ports
  (`WinError 10055`).

## Required Behavior

1. The seven tests of the emulator's suite in the table pass on Windows.
2. The tests of the stop of `odrigctl --log` run on Windows and pass.
3. The app's suite runs on Windows. Every test of it passes there or is skipped for a
   reason that a Mac without the same thing would give too, and the two tests in the
   table pass.
4. After any suite on Windows, no program it started runs, and no port it took is taken.
5. The entry file and the getting-started page say exactly which suites pass on Windows,
   and the onboarding tests check those sentences.

## Definition Of Done

1. On Windows 11, run one at a time, each of these ends with no failure: the converter's
   suite, the Python library's, the core's, the emulator's, the app's and the onboarding
   suite.
2. None of them skips a test on Windows that it runs on macOS, except the app's tests
   that need a phone or another thing the computer does not have, each with its reason.
3. No window opens while they run, and nothing they started is running afterwards.
4. The changes are written so that macOS runs the same tests with the same results; the
   check on a Mac is made at the review.

## Open Questions

None.
