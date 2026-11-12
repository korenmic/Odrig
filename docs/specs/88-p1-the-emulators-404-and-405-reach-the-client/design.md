# Design: the emulator's 404 and 405 reach the client

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/88-p1-the-emulators-404-and-405-reach-the-client/seed.md`.

## The race

`Handler.answer` in `emulator/httpd.py` gives the 405 of another method on `/odrig` and on
`/seek`, and the 404 of another path, through `Handler.empty`. `empty` writes an answer
without a body and closes the connection; it does not read the body the request carries.

`http.client` writes a request's head and its body in two sends. When the body reaches the
server after the server has read the head, it is still unread when the server closes the
connection, or it arrives after the close. Either way TCP answers with a reset (RFC 1122,
4.2.2.13: data pending at a close, or received after it). On Windows a reset discards what
the client has received and not read yet, the answer among it, and `getresponse()` fails
with `ConnectionAbortedError: [WinError 10053]`. RFC 9112, 9.6, describes this loss of a
server's last answer. Under the load of a whole run of the emulator's suite the body comes
late often enough to fail the suite about one run in five; sent 0.2 s after the head, it
loses the answer every time.

When the server reads the declared body before it answers, nothing is unread at the close
and nothing more arrives after it: the connection ends with an orderly close and the client
reads the whole answer.

## The change

All of it is in `Handler` of `emulator/httpd.py`. The check of `Content-Length` and the
reading loop of `body` become two methods of their own, which `body` and `empty` share:

```python
def declared_length(self):
    """The length of the body that the request declares with a `Content-Length` that is a
    whole number, or `None`."""
    length = self.headers.get("Content-Length")
    if length is None or not WHOLE_NUMBER.fullmatch(length.strip()):
        return None
    return int(length.strip())

def read_body(self, left):
    """Reads `left` bytes of the request's body and gives the first of them, or `None`
    when the connection ends inside the body."""
    kept = b""
    while left > 0:
        piece = self.rfile.read(min(left, CHUNK))
        if not piece:
            self.close_connection = True
            return None
        left -= len(piece)
        if len(kept) < BODY_KEPT:
            kept += piece[:BODY_KEPT - len(kept)]
    return kept

def body(self):
    """The first bytes of the request's body, or `None` after a 411 or a connection that
    ended inside the body."""
    length = self.declared_length()
    if length is None:
        self.empty(411)
        return None
    return self.read_body(length)

def empty(self, status, headers=None):
    """An answer without a body, after which the connection is closed. The body that the
    request declares is read to its end and dropped first: closing a connection with
    bytes unread resets it, and the client can lose the answer. When the connection ends
    inside that body, nothing is written."""
    length = None if "Transfer-Encoding" in self.headers else self.declared_length()
    if length is not None and self.read_body(length) is None:
        return
    self.close_connection = True
    ...  # the status, the headers and the end of the head, as today
```

- `declared_length` and `read_body` are the lines of today's `body`, moved: the same
  `WHOLE_NUMBER`, pieces of `CHUNK` bytes, the first `BODY_KEPT` kept. `body` does with
  them what it does today, the 411 included.
- `empty` takes no length from a request that has a `Transfer-Encoding` header, whatever
  its value: with a transfer coding, the `Content-Length` does not give the length of the
  body (RFC 9112, 6.3), and the server reads no transfer coding. Such a request, and one
  without a `Content-Length` that is a whole number, is answered at once, as today.
- `empty` is called before any body is read: by `answer` for the 404 and the 405, by `body`
  for the 411, which has no length to read, and by `page` and `mapping`, which answer
  `GET`s. So the body is never read twice.
- `"Transfer-Encoding" in self.headers` does not depend on the case of the name, as every
  lookup in the headers.
- No limit and no timeout: a client that declares more than it sends holds its own
  connection until it closes, as on `POST /odrig` today. The threads stay daemon threads,
  so stopping the server does not wait for them. A connection that breaks while its body
  is read ends with a `ConnectionError`, which `Server.handle_error` already ignores.
- A request with `Expect: 100-continue` is told to go on by `BaseHTTPRequestHandler` before
  `answer` runs, so its body comes and is read.

## The tests

`tests/emulator/support.py`: `raw_request` takes three more arguments, each with a default
that keeps what it does today, so that every test that calls it is unchanged:

```python
def raw_request(port, data, seconds=5, later=None, pause=0.0, end=False):
    """Sends bytes to the page address, then `later` after `pause` seconds when it is given,
    and with `end` ends its own side of the connection; gives everything that comes back
    until the server closes the connection or stays silent."""
```

`tests/emulator/test_http.py`, in `WhatTheServerPassesOn`, whose server is
`httpd.Server` with a stand-in engine that keeps every line handed to it:

- **A body that comes after its head.** For `POST /odrig/x` and 404, and `PUT /odrig` and
  405: the head with `Content-Length: 2`, then `on` 0.2 s later, read to the end of the
  connection. The answer begins `HTTP/1.1 404 ` or `HTTP/1.1 405 `; its fields hold
  `Content-Length: 0` and `Connection: close`, and `Allow: POST` for the 405; nothing
  follows the head. The engine is handed no line.
- **A long body.** `POST /odrig/x` with 300,000 bytes, through `http.client`: 404 and an
  empty body; no line handed to the engine.
- **A connection that ends inside the body.** The head of `POST /odrig/x` with
  `Content-Length: 10`, 2 bytes of body, then the end of the client's side: nothing comes
  back.
- **No length to read.** The head of `POST /odrig/x` alone, with no `Content-Length`, with
  `Content-Length: many`, and with `Transfer-Encoding: chunked` and `Content-Length: 10`:
  each gets its 404 at once, with no body sent.

Every test already in the suite stays as it is.

## The proofs that it failed

On the branch, with the tests written and `emulator/httpd.py` not yet changed, on Windows:

- the body that comes after its head fails with `ConnectionAbortedError: [WinError
  10053]`, as `master` was measured to do in 20 of 20 tries;
- the connection that ends inside the body gets the 404, written before the body was read;
- the long body is run and what it gave is noted: on `master` 16 of 20 tries lost their
  404 the same way;
- the test of no length to read passes before the change as after.

The commit of the change quotes what each gave.

## Broken on `master`, mended on the branch

The owner asked to see the tests the seed mends broken on `master` and passing on the
branch. `master` is the branch's base, 51e1e3e4, checked out in a worktree of its own with
the core built. On Windows:

- **The new tests on `master`'s server.** `tests/emulator/test_http.py` and
  `tests/emulator/support.py` of the branch are copied over `master`'s in that worktree
  and the four tests run; then the worktree is put back with `git checkout`. The body
  that comes after its head and the connection that ends inside the body fail, as in the
  proof above. The long body is run ten times there and ten times on the branch.
- **The six tests already in the suite**, those that send a body to a 404 or a 405:
  - `tests.emulator.test_http.Commands.test_another_method_gets_405_with_allow_post_no_body_and_changes_nothing`
  - `tests.emulator.test_http.Commands.test_the_path_is_odrig_exactly_whatever_follows_a_question_mark`
  - `tests.emulator.test_http.WhatTheServerPassesOn.test_the_front_end_is_not_called_for_another_method_a_missing_length_or_another_path`
  - `tests.emulator.test_page_files.Served.test_no_other_file_is_served`
  - `tests.emulator.test_page_files.TheApp.test_nothing_else_of_the_repository_is_served`
  - `tests.emulator.test_events.Stream.test_the_mapping_file_is_served_byte_for_byte`

  They are run by a script under `scratch/`, outside the repository, that wraps
  `http.client.HTTPConnection._send_output` so that a body of bytes is sent 0.2 s after
  its head, the delay the load of a whole run gives at random, and then hands the six to
  `unittest`. On `master` they fail with `ConnectionAbortedError: [WinError 10053]`; on
  the branch they pass. The script is not part of the change.
- **The emulator's suite as it is**, five whole runs on `master` and five on the branch,
  one at a time: the failures of a 404 or a 405 are counted on each.

`verification.md` records each run: the commands, the counts and the errors seen.

## The pages

- `docs/emulator.md`, "Commands over HTTP", one more point after "An answer without a body
  closes its connection.":

  ```text
  - Before a 404 or a 405, the body that the request declares with a `Content-Length` is
    read to its end and dropped, so that the closed connection is not reset and the client
    gets the answer. A request whose body has no such length is answered at once.
  ```

- `tests/emulator/test_docs.py`: a test of its own that finds in the section, its
  whitespace joined, "An answer without a body closes its connection." and "Before a 404
  or a 405, the body that the request declares with a `Content-Length` is read to its end
  and dropped".
- `docs/drifts.md`, at its end:
  - `## Seed 88: the body of a 404 or a 405 is read before the answer`: the race, its
    cause, the body read rather than the connection closed slowly, and no limit.
  - `## Seed 88: which answers read the body, and which are given at once`: every answer
    of `empty`, the `Transfer-Encoding` of any value, and the 411.

## The delivery

The branch `seed-88-404-and-405-reach-the-client`, made from `master` 51e1e3e4, is pushed
after the tasks before the last, and a pull request is opened against `master`. Every suite
that works on the computer is run on Windows, one at a time, and the proofs above are
made. `verification.md` records them, with the pull request and its CI: the firmware
workflow runs for a pull request into `master`, and it holds no suite of the emulator. The
last task sets the seed `completed`, with `completedAt`, and takes its line out of "What is
coming" in `AGENTS.md`, so that `master` is right once the pull request is merged. No
firmware image and no APK is built.
