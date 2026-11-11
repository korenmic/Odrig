# The emulator's 404 and 405 reach the client

## Summary

The emulator's web server answers a request for an unknown path with 404, and another
method on `/odrig` or `/seek` with 405. It closes the connection after that answer without
reading the body the request carries. Closing a connection that still holds unread bytes
resets it, and on Windows the reset makes the client drop an answer it has received but not
read yet. `tests/emulator/test_http.py` then fails with
`ConnectionAbortedError: [WinError 10053]` where it expects its 404, about one run of the
emulator suite in five. With this seed the server reads the body a request declares before
it answers 404 or 405, so the connection closes without a reset and the answer arrives. The
answers themselves are unchanged. It is built on `master`.

## Priority

`P1`, as seeds 26, 51 and 53, which keep the suites passing on Windows.

## Product Context

- **Where it was seen.** While seed 87 was built, the emulator suite on Windows failed about
  one run in five in
  `test_the_front_end_is_not_called_for_another_method_a_missing_length_or_another_path`:
  `self.request("POST", "/odrig/x", b"on")` raised `ConnectionAbortedError: [WinError 10053]`
  inside `getresponse()`, where a 404 was expected. It failed the same way on the head of the
  fused branch of pull request #63, a19499fc, before any change of seed 87, and passed when
  it was run again.
- **The cause.** `Handler.empty` in `emulator/httpd.py` gives an answer without a body and
  closes the connection; its docstring says that a body the request may carry is not read.
  `http.client` writes a request's head and its body in two sends. When the body reaches
  the server after the server has read the head, it stays unread in the socket when the
  server closes it. TCP then resets the connection (RFC 1122, 4.2.2.13), and the reset can
  discard the answer the client has received but not read yet. RFC 9112, 9.6, describes
  this loss of an HTTP server's last answer.
- **Measured on `master` at a66c1cd2, on Windows 11, on 2026-11-11,** with the server
  started in a trial script:
  - 900 requests sent as the tests send them, `POST /odrig/x`, `PUT /odrig` and `POST /`,
    each with the body `on`, in a quiet process: all 900 got their answer. The race needs
    the load of a whole run.
  - 20 requests whose body was sent 0.2 s after their head: all 20 lost their 404 with
    `ConnectionAbortedError [WinError 10053]`.
  - 20 requests to `POST /odrig/x` with a body of 300,000 bytes, sent by `http.client`: 16
    lost their 404 the same way.
  - With the declared body read to its end before the 404 or 405, patched into the trial
    script: all 20 of each of the last two got their answer.
- **Who meets it.** Only the tests. The Controller view, the page, a phone through `--lan`
  and `odrigctl` send `POST /odrig` and `POST /seek` with the right method and path, and
  their `GET`s carry no body. The board is not involved: its firmware has its own web
  server.
- **Why it matters.** Rule 11 asks for every suite that works on the computer before a
  merge. On Windows the emulator suite fails about one run in five for no fault of the
  change, and someone has to run it again and judge the failure by hand.
- **The tests that send a body to a 404 or a 405:**
  - `tests/emulator/test_http.py`: another method on `/odrig`; the paths that are not
    `/odrig`; the front end not called for another method or another path.
  - `tests/emulator/test_page_files.py`: `POST`, `PUT` and `DELETE` on a page file and on a
    file of the app.
  - `tests/emulator/test_events.py`: `POST /show/mapping.json`.

## Required Behavior

1. **The body is read before a 404 or a 405.** When a request is answered 404 or 405 and
   has a `Content-Length` that is a whole number, the server reads that many bytes of body
   and drops them, then answers. A body of any length is read to its end, as the body of
   `POST /odrig` is.
2. **The answers are unchanged.** The status, the headers (`Allow: POST` on a 405,
   `Content-Length: 0`, `Connection: close`) and the empty body stay as they are, and the
   connection is still closed after the answer. The core is not called.
3. **A connection that ends inside the body.** When the client closes before the declared
   body is all there, no answer is written and the connection is closed, as `POST /odrig`
   does then.
4. **What stays as it is.**
   - A request answered 404 or 405 that has no `Content-Length`, or one that is not a whole
     number, or `Transfer-Encoding: chunked`, is answered at once, as today: its body has no
     length to read.
   - The 411 of `POST /odrig` and `POST /seek` is unchanged.
   - The page files, the event stream, `/show/mapping.json`, `POST /odrig` and `POST /seek`
     are unchanged.
5. **The documents.** `docs/emulator.md`, "Commands over HTTP", says that the body of a
   request answered 404 or 405 is read and dropped before the answer.

## Technical Constraints

- **One place.** The change is in `emulator/httpd.py`, where `Handler.empty` gives the 404
  and the 405. The reading loop of `Handler.body`, in pieces of `CHUNK` bytes with the
  length checked by `WHOLE_NUMBER`, is shared, not copied. The docstring of `empty` says
  what it does then.
- **Nothing else changes.** No command, core, app, firmware or `odrigctl` changes. No
  firmware image or APK is built for this seed: neither holds a byte of the change.
- **No new limit or timeout.** A client that declares more than it sends holds only its own
  connection, as on `POST /odrig` today. The server's threads stay daemon threads, so
  stopping the emulator does not wait for them.
- **Tests seen failing first, on Windows.**
  - `tests/emulator/test_http.py`: a `POST /odrig/x` and a `PUT /odrig` whose body of 2
    bytes is sent 0.2 s after their head, each read to the end of the connection: the 404
    and the 405 arrive whole, with their headers. Before the change this fails with
    `ConnectionAbortedError: [WinError 10053]`, as measured above, and that failure goes
    into the commit message.
  - The same file: a `POST /odrig/x` with a body of 300,000 bytes, sent by `http.client`,
    gets its 404.
  - Every other test of the emulator suite passes unedited.
- **The documents.**
  - `docs/emulator.md`, as item 5 says, with the sentence checked by
    `tests/emulator/test_docs.py`.
  - An entry at the end of `docs/drifts.md`: the race, its cause, and why the body is read
    rather than the connection closed slowly.
  - `docs/decisions.md` is unchanged: no decision changes.

## Open Questions

None. The owner asked for this seed on 2026-11-11, for `master`. The seed decides the rest:

- **The body is read, not the close slowed.** RFC 9112 also describes a slow close: the
  server closes its side, then reads until the client closes. Reading the declared body
  first covers every request that meets the race, keeps the change in one function and adds
  no wait to a connection.
- **The whole body, with no limit.** `POST /odrig` already reads a body of any length to its
  end. A limit for 404 and 405 would protect nothing that `/odrig` does not already allow,
  and a longer body would meet the race again: 16 of 20 bodies of 300,000 bytes lost their
  404.
- **A body without a usable length stays as it is.** A 411, a missing length and a chunked
  body have no length to read. No client and no test sends one to a 404 or a 405 with its
  body in a separate write.
- **The answers keep `Connection: close`.** Keeping the connection once the body is read
  would change the documented "An answer without a body closes its connection" for no gain.
- **Built on `master`.** `Handler.empty`, and the tests that send a body to a 404 or a 405,
  are the same on `master`, on the fused branch of pull request #63 and on seed 87's branch,
  pull request #68. Both branches get the change when they are brought up to date with
  `master`, as rule 11 asks; seed 87 changes another function of `emulator/httpd.py`,
  `command_line`.
- **No other server.** The web server of the app's tool, `app/apptool/webserver.py`, is
  tested with `GET`s without a body only, and the board's web server is the firmware's own.
  Neither is part of this seed.
- **Priority `P1`**, as the earlier seeds that keep the suites passing on Windows.

## The Owner's Answers

On 2026-11-11 the owner asked what the race was and whether its fix belongs on `master`, on
the fused branch or on seed 87's branch. The answer was `master`, and the owner asked for
this seed to be created.

## Definition Of Done

1. A requirements/design/tasks specification.
2. The emulator and onboarding suites pass on Windows with the new tests, seen failing
   first.
3. Every suite that works on the computer passes, as rule 11 asks, and in five whole runs of
   the emulator suite on Windows no test of a 404 or a 405 fails.
4. No check by the owner: nothing that the LEDs or a phone show changes.
