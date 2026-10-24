# Requirements: every suite passes on Windows again

Seed: [`project-seeds/26-p1-every-suite-passes-on-windows-again/seed.md`](../../../project-seeds/26-p1-every-suite-passes-on-windows-again/seed.md).

Seed 11 left every suite that runs on Windows passing there. Work that came to `master`
after it was written and tested on macOS, and some of its tests fail on Windows 11, or do
not run there. This spec makes them run and pass on Windows, and changes nothing on macOS.

The seed has no open question. In this document "the suites" are the suites that run on
Windows: the converter's (`npm test --prefix converter`), the Python library's
(`tests/converter`), the core's (`python core/build.py test`), the emulator's and the
command tool's (`tests/emulator`), the app's (`tests/app`) and the onboarding suite
(`tests/onboarding`). "A program a test starts" is any process a test starts: the
emulator, the preview, the command tool, Chrome, the converter and what they start.

## Requirement 1: the emulator's suite passes on Windows

**User story.** As a contributor on Windows, I want the emulator's suite to pass, so that
a failure there means my change broke something.

1. `test_binding`'s `test_frame_has_1080_bytes_and_they_are_the_reference` and
   `test_poll_gives_a_refresh_at_every_grid_time_and_none_between` SHALL pass on Windows.
2. `test_drive`'s
   `test_the_folder_appearing_and_going_plugs_the_drive_in_and_pulls_it_out` SHALL pass on
   Windows.
3. `test_preview`'s `test_a_file_plays_alone_until_the_preview_is_interrupted`,
   `test_a_relative_path_and_the_installations_canvas_by_default` and
   `test_a_page_port_that_is_taken_gives_a_free_one` SHALL pass on Windows.
4. `test_demo`'s
   `test_the_packed_folder_holds_the_files_the_other_tests_of_the_suites_play` SHALL pass
   on Windows.
5. On Windows the emulator SHALL let a folder whose files it reads, the show's or the
   drive's, be moved or removed while it holds them, as macOS does: the drive is pulled
   out by moving its folder `odrig` away, and a test's folder is removed after the test.

## Requirement 2: stopping a program on Windows

**User story.** As whoever runs a program in a terminal on Windows, I want Ctrl+C and
Ctrl+Break to end it as Ctrl+C ends it on macOS, so that nothing is left running.

1. On Windows the preview SHALL end on Ctrl+Break as it ends on Ctrl+C: it stops its
   emulator, removes its work folder, and ends with status 0.
2. On Windows `odrigctl --log` SHALL end on Ctrl+Break as it ends on Ctrl+C, with status
   0.
3. A test that starts one of these programs on Windows SHALL start it in a process group
   of its own and stop it with Ctrl+Break, as the other tests of the suites stop the
   emulator.
4. The tests of the stop of `odrigctl --log` SHALL run on Windows, not be skipped there,
   and pass.

## Requirement 3: no test takes a port for granted

1. No test SHALL take it as given that port 8600 is free.
2. A test that checks the preview's default port SHALL check, when another program holds
   port 8600, the message `preview: port 8600 is taken; the page is on <port>`, and when
   the port is free, that the page is on 8600 and nothing is said.
3. A test that holds a port to make it taken SHALL hold it in a way that Windows allows,
   and SHALL count the port as taken also when another program holds it already.

## Requirement 4: the app's suite on Windows

**User story.** As a contributor on Windows, I want the app's suite to run, so that the
operators' app is checked on the computer I have.

1. The app's suite SHALL find Chrome on Windows: the program `ODRIG_CHROME` names, and
   otherwise `Google\Chrome\Application\chrome.exe` under `Program Files`,
   `Program Files (x86)` and the user's `AppData\Local`, in that order.
2. `test_docs`'s `test_every_message_of_the_app_is_on_the_page` and
   `test_every_message_of_making_an_animation_is_on_the_page` SHALL pass on Windows.
3. Every test of the app's suite SHALL pass on Windows, or be skipped there for a reason
   that a Mac without the same thing gives too, such as a phone that is not connected.
4. On Windows the app tool's `serve` SHALL refuse a port another program holds with
   `address-in-use`, as it does on macOS, and SHALL end on Ctrl+Break with status 0.
5. A headless Chrome of the app's suite SHALL lay out the app's page on Windows as on
   macOS: no scrollbar takes room from the page.

## Requirement 5: what a test leaves, and what a browser does

1. After a suite has run on Windows, no program a test started SHALL be running, and no
   port a test took SHALL be taken.
2. A browser a test starts SHALL be Chrome, headless, with a profile folder of its own
   that is made for the run and removed after it. No window SHALL open, and Chrome SHALL
   never be asked for its version with `--version`.

## Requirement 6: the documents say what is true

1. `AGENTS.md`, "If you work on Windows", and `agent/getting-started.md`, "On Windows",
   SHALL say which suites pass on Windows: every one of the suites.
2. The onboarding suite SHALL check those sentences.
3. `docs/emulator.md` SHALL say how a test and a person stop the preview and
   `odrigctl --log` on Windows.

## Requirement 7: nothing changes on macOS

1. On macOS and Linux every program SHALL do what it does now, and every test SHALL check
   what it checks now. A change made for Windows SHALL do nothing elsewhere.
2. What a program writes SHALL NOT change on any system.

## Definition of done

1. On Windows 11, run one at a time, each of the suites ends with no failure.
2. None of them skips on Windows a test it runs on macOS, except the tests that need a
   virtual serial port or a file name that Windows does not allow, and tests of the app's
   suite that need a thing the computer does not have, each with its reason.
3. No window opens while they run, and no program they started runs afterwards.
4. macOS runs the same tests with the same results; that check is made at the review.
