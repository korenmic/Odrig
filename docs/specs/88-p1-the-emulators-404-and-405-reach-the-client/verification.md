# Verification

## Software

Seed 88 is on the branch `seed-88-404-and-405-reach-the-client`, pull request #69, made
from `master` 51e1e3e4. These are its commits, in order:

| Commit | What it is |
|---|---|
| 48dacc2a | The spec |
| 0edc026d | Task 1: the body is read before a 404 or a 405 |
| c42efd9b | Task 2: the pages |

Everything below was run on Windows 11 with Python 3.14.2, on 2026-11-12.

## Seen failing first, on the branch

The four tests of task 1 in `tests/emulator/test_http.py`, with `emulator/httpd.py` not
yet changed, then changed; each repeated ten times in one process:

| Test | Before the change | After it |
|---|---|---|
| A body that comes 0.2 s after its head, to the 404 and to the 405 | 10 of 10 `ConnectionAbortedError: [WinError 10053]` | 10 of 10 pass |
| A connection that ends inside the body it declares | 10 of 10 get the 404, written before the body was read | 10 of 10 pass |
| A body of 300,000 bytes to a 404 | 6 of 10 `WinError 10053`, in `getresponse()` | 10 of 10 pass |
| A 404 to a body with no length to read | passes | passes |

## Broken on `master`, mended on the branch

The owner asked to see the tests that the seed mends broken on `master` and passing on the
branch. `master` at 51e1e3e4 was checked out in a worktree of its own with the core built;
the branch was at c42efd9b.

| What was run | On `master` | On the branch |
|---|---|---|
| The six tests already in the suite that send a body to a 404 or a 405, with each body sent 0.2 s after its head | all six fail: 10 errors with their sub-tests, each `ConnectionAbortedError: [WinError 10053]` | all six pass |
| The body that comes after its head, to the 404 and to the 405 | both fail, `WinError 10053` | pass |
| The connection that ends inside the body it declares | fails: the 404 is written | passes: no answer |
| The body of 300,000 bytes, ten runs | 10 of 10 lose the 404, `WinError 10053`; a single run before them passed | 10 of 10 pass |
| A 404 to a body with no length to read | passes | passes |

The new tests ran on `master`'s server with the branch's `tests/emulator/test_http.py` and
`tests/emulator/support.py` copied over `master`'s, which were put back after. The six
tests ran through a script outside the repository that wraps
`http.client.HTTPConnection._send_output`, so that a body of bytes is sent 0.2 s after its
head, the delay the load of a whole run gives at random:

- `tests.emulator.test_http.Commands.test_another_method_gets_405_with_allow_post_no_body_and_changes_nothing`:
  on `master` its sub-tests of `PUT`, `DELETE`, `OPTIONS`, `PATCH` and `BREW`
- `tests.emulator.test_http.Commands.test_the_path_is_odrig_exactly_whatever_follows_a_question_mark`
- `tests.emulator.test_http.WhatTheServerPassesOn.test_the_front_end_is_not_called_for_another_method_a_missing_length_or_another_path`,
  the test that failed the suite about one run in five
- `tests.emulator.test_page_files.Served.test_no_other_file_is_served`
- `tests.emulator.test_page_files.TheApp.test_nothing_else_of_the_repository_is_served`
- `tests.emulator.test_events.Stream.test_the_mapping_file_is_served_byte_for_byte`

## Suites

Run on Windows, one at a time:

| Suite | Tree | Tests | Result |
|---|---|---:|---|
| emulator | task 1 | 662 | OK (skipped=20), 746 s |
| onboarding | task 1 | 88 | OK |
| converter, `tests/converter` | task 2 | 552 | OK |
| onboarding | task 2 | 88 | OK |
| emulator | task 2 | 663 | OK (skipped=20), 687 s |
| `npm test --prefix converter` | c42efd9b | 1,602 | 1,601 pass, 1 skipped: a name with a quote, which Windows forbids in a file name |
| converter, `tests/converter` | c42efd9b | 552 | OK |
| onboarding | this commit | 88 | OK |
| converter, `tests/converter` | this commit | 552 | OK |

On 2026-11-12 the owner chose to merge once the tests that the seed mends were seen broken
on `master` and passing on the branch, and to run the rest after the merge: the core's
suite, five whole runs of the emulator's suite on the branch and five on `master`, and the
app's, the mapping, the firmware host, the runner and the firmware tool's suites. Their
results are told to the owner when they end.

## CI

The firmware workflow ran for the pull request at c42efd9b, run 43125675052. Both images
were built and inspected on Windows and on Ubuntu, and the firmware and firmware host suites
passed on both. On Windows the runner's suite failed one test,
`tests.runner.test_runner.Running.test_the_report_holds_every_test_and_every_suite`, with
`AssertionError: 0.188 not greater than or equal to 0.2`. That is the coarse clock of Python
3.12 on Windows: the same test failed pull request #50 the same way, and pull request #51,
not merged, times the runner's tests with the finest clock. The seed changes nothing of the
runner.

## Open

- [ ] The suites that the owner chose to run after the merge, listed above.
