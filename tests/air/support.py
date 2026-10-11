"""Helpers shared by the tests that reach the board over its network."""

import contextlib
import http.client
import io
import json

from odrigctl import cli as command_tool

from . import ADDRESS, PORT

SECONDS = 5.0

# What brings the player to one known state before a session, whatever was sent before.
PREPARE = ("on", "brightness 32", "play 3")


def host():
    """The address as `host` or `host:port`."""
    address = ADDRESS[len("http://"):] if ADDRESS.startswith("http://") else ADDRESS
    return address.rstrip("/")


def request(method, path, body=None, content_type=None):
    """One HTTP request to the board. Returns the status, the headers and the body."""
    connection = http.client.HTTPConnection(host(), timeout=SECONDS)
    try:
        headers = {} if content_type is None else {"Content-Type": content_type}
        connection.request(method, path, body=body, headers=headers)
        answer = connection.getresponse()
        return answer.status, dict(answer.getheaders()), answer.read()
    finally:
        connection.close()


def command(target, *words):
    """Sends one command with the command tool, to `--port NAME` or `--http ADDRESS`.
    Returns the tool's exit status and the reply, read as JSON."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = command_tool.main([*target, "--timeout", str(SECONDS), *words])
        except SystemExit as stopped:
            status = stopped.code
    if status not in (0, 1):
        raise AssertionError(f"`{' '.join(words)}` to {' '.join(target)}: status {status}: {err.getvalue()}")
    return status, json.loads(out.getvalue())


def over_the_port(*words):
    return command(["--port", PORT], *words)


def over_http(*words):
    return command(["--http", ADDRESS], *words)


def session(send, lines):
    """Sends the lines of a session with one of the two senders. Returns, for each, the
    tool's exit status and the reply without its `fps`."""
    answers = []
    for line in lines:
        status, reply = send(*line.split(" "))
        answers.append((status, {name: value for name, value in reply.items() if name != "fps"}))
    return answers
