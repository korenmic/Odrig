"""The commands that take more than one exchange: listing a whole show, and uploading a file.

Both work through a `client.Session`, so the same code talks through a serial port and over
HTTP. Nothing here judges an id, a name or a file: every judgement is the target's, and its
replies are passed on as they come.
"""

import base64
import json
import time
import zlib

from . import client

BUSY_SECONDS = 600.0
BUSY_PAUSE_SECONDS = 0.2
STRAY_SECONDS = 0.5
# The codes after which the target holds no upload any more.
GONE = ("no-upload", "bad-checksum", "bad-file", "storage-error", "show-invalid")


def is_ok(reply):
    """Whether a reply reports success."""
    return json.loads(reply).get("ok") is True


def is_unchanged(reply):
    """Whether a reply to `upload begin` says that the target holds the file already."""
    return json.loads(reply).get("unchanged") is True


def error_of(reply):
    """The error code of a reply, or None for one that reports success."""
    return json.loads(reply).get("error")


def list_all(session, show, command=b"list"):
    """Asks for the items of the show, or with the command `order get` for the saved order,
    one reply after the other for as long as a reply names a next position, and hands each
    reply to `show`. Returns whether every reply reported success; it stops at one that
    does not."""
    line = command + b"\n"
    while True:
        reply = session.exchange(line)
        show(reply)
        if not is_ok(reply):
            return False
        following = json.loads(reply).get("next")
        if following is None:
            return True
        line = command + b" %d\n" % following


def upload(session, item, name, data, progress=None, checking=None, busy_seconds=BUSY_SECONDS, clock=time.monotonic, sleep=time.sleep):
    """Sends a file as an upload: `upload begin` with the CRC-32 of the file, the file in
    pieces of the size the reply names, each as one `upload data` line, and `upload end`
    with the CRC-32 of the file, again every 0.2 seconds while the reply is `busy`, for
    `busy_seconds` at most. A reply to `upload begin` that says `unchanged` ends the upload:
    the target holds the file already, and nothing more is sent. A reply `bad-argument` to
    it is followed by `upload begin` without the CRC-32, which every target takes.

    `item` and `name` go out as they are given, as text. `progress(sent, total, seconds)`
    is called after every piece that was acknowledged, with the time since `upload begin`
    was answered, and `checking()` once when all pieces are sent. Returns the reply that
    ended the upload: the one of `upload end` that reports success, the one of `upload
    begin` that says `unchanged`, or the first reply that does not report success. After a reply to a piece or to `upload end` that does not report
    success, the upload is cancelled unless the reply says that it is gone.
    """
    reply = session.exchange(f"upload begin {item} {name} {len(data)} {zlib.crc32(data):08x}\n".encode("utf-8"))
    if error_of(reply) == "bad-argument":
        # A target that does not take the CRC-32 with `upload begin` takes the line without it.
        reply = session.exchange(f"upload begin {item} {name} {len(data)}\n".encode("utf-8"))
    if not is_ok(reply) or is_unchanged(reply):
        return reply
    began = clock()
    piece = json.loads(reply)["chunk"]
    sent = 0
    while sent < len(data):
        part = data[sent:sent + piece]
        line = b"upload data %d %s\n" % (sent, base64.urlsafe_b64encode(part).rstrip(b"="))
        try:
            reply = session.exchange(line)
        except client.Unreachable:
            # No reply in time: the same line once more. `bad-offset` for it means that
            # the first one was taken and only its reply was lost.
            reply = session.exchange(line)
            if error_of(reply) == "bad-offset":
                reply = b'{"ok":true,"received":%d}' % (sent + len(part))
            else:
                session.discard(STRAY_SECONDS)
        if not is_ok(reply):
            return _given_up(session, reply)
        sent = json.loads(reply)["received"]
        if progress is not None:
            progress(sent, len(data), clock() - began)
    if checking is not None:
        checking()
    line = b"upload end %08x\n" % zlib.crc32(data)
    deadline = clock() + busy_seconds
    while True:
        reply = session.exchange(line)
        if error_of(reply) != "busy" or clock() >= deadline:
            break
        sleep(BUSY_PAUSE_SECONDS)
    return reply if is_ok(reply) else _given_up(session, reply)


def _given_up(session, reply):
    """Cancels the upload after a reply that does not report success, unless the reply
    says that the upload is gone. Returns the reply."""
    if error_of(reply) not in GONE:
        try:
            session.exchange(b"upload cancel\n")
        except client.Unreachable:
            pass
    return reply
