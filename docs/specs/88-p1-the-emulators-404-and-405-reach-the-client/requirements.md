# Requirements: the emulator's 404 and 405 reach the client

The seed is `project-seeds/88-p1-the-emulators-404-and-405-reach-the-client/`. It has no
open question. Where these requirements decide a point the seed leaves to the design, the
decision is recorded in `docs/drifts.md`.

## 1. The body is read before the answer

1.1 When the emulator's web server answers a request 404 or 405, and the request has a
`Content-Length` that is a whole number and no `Transfer-Encoding`, the server reads that
many bytes of the request's body and drops them, then writes the answer.

1.2 A body of any length is read to its end, as the body of `POST /odrig` is. No limit and
no timeout is added.

1.3 This holds for every 404 and 405 of the server: the 405 of another method on `/odrig`
and on `/seek`, the 404 of another path, and the 404 of a file of the page or of the
mapping file that cannot be read.

1.4 When the connection ends before the declared body has all arrived, no answer is
written and the connection is closed, as `POST /odrig` does then.

## 2. The answers are unchanged

2.1 Each 404 and 405 has the status, the headers and the empty body it has today: `Allow:
POST` on a 405, `Content-Length: 0` and `Connection: close`.

2.2 The connection is closed after the answer.

2.3 The core is not called for a 404 or a 405.

## 3. What stays as it is

3.1 A request answered 404 or 405 that has no `Content-Length`, one that is not a whole
number, or a `Transfer-Encoding` header such as `chunked`, is answered at once, as today:
its body has no length that the server reads.

3.2 The 411 of `POST /odrig` and `POST /seek` is unchanged: its status, its headers, its
closing, and no body read.

3.3 `POST /odrig`, `POST /seek`, the files of the page and of the app, the event stream and
`GET /show/mapping.json` read and answer as before.

3.4 The server's threads stay daemon threads: stopping the emulator does not wait for a
connection whose body is still coming.

3.5 No command changes, and neither do the core, the app, the firmware, `odrigctl` or the
web server of the app's tool. No firmware image and no APK is built: neither holds a byte
of the change.

3.6 Nothing that the LEDs or a phone show changes, so no check by the owner is needed.

## 4. Tests

4.1 `tests/emulator/test_http.py` sends `POST /odrig/x` and `PUT /odrig` to a server of
its own, each with a body of 2 bytes sent 0.2 s after its head, and reads each to the end
of the connection: the 404 and the 405 arrive whole, with the headers of 2.1, and the
core's stand-in is handed no line.

4.2 The same file sends `POST /odrig/x` with a body of 300,000 bytes through
`http.client`: the answer is 404 with an empty body.

4.3 The same file checks 1.4, with a connection that ends inside the body it declares, and
3.1, with a 404 to a request whose body has no length to read, answered at once.

4.4 The test of 4.1, and the test of 4.3 that checks 1.4, are seen failing on Windows before
the change: the first with `ConnectionAbortedError: [WinError 10053]`, the second with the
404 written. What each gave, and what the test of 4.2 gave, goes into the commit message.

4.5 Every test already in the emulator's suite passes unedited.

4.6 On Windows, the emulator's suite is run five whole times on the branch, one run at a
time, and no test of a 404 or a 405 fails.

4.7 The owner asked to see the tests that the seed mends broken on `master` and passing on
the branch. On Windows, each of these is run against `master` at the branch's base and
against the branch:

- the test of 4.1, and the test of 4.3 that checks 1.4: they fail on `master`'s server;
- the test of 4.2, ten times: the times it loses its 404 on `master` are counted;
- the six tests already in the suite that send a body to a 404 or a 405, with
  `http.client` sending each body 0.2 s after its head: they fail on `master`;
- the emulator's suite, five whole times: its failures of a 404 or a 405 on `master` are
  counted.

On the branch, all of them pass.

4.8 Every suite that works on the computer passes on Windows, one at a time, as rule 11
asks. A failure that is known on this computer and is not a fault of the code is named in
`verification.md`.

## 5. Pages, the seed and the delivery

5.1 `docs/emulator.md`, "Commands over HTTP", says that the body that a request answered
404 or 405 declares is read to its end and dropped before the answer.

5.2 `tests/emulator/test_docs.py` checks that sentence, in a test of its own.

5.3 `docs/drifts.md` gains two entries at its end: the race, its cause, and why the body is
read rather than the connection closed slowly; and which answers read the body and which
requests are answered at once.

5.4 `docs/decisions.md` is unchanged.

5.5 The branch is pushed and a pull request opened against `master`.

5.6 `verification.md`, beside this spec, records the commits, the proofs of 4.4, 4.6 and
4.7, the suites, the pull request and its CI.

5.7 The seed is `in_progress` from the first task, and `completed`, with `completedAt`, at
the last, which also takes it out of "What is coming" in `AGENTS.md`: `master` is right
the moment the pull request is merged.
