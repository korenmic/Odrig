"""Record mode: the core on a virtual clock, every tick written to a file."""

import collections
import re
import sys

from . import binding, failure, host, recfile

Command = collections.namedtuple("Command", "time line")

SCRIPT_LINE = re.compile(r"([0-9]+) (.*)", re.S)


def tick_count(length_ms):
    """The number of ticks below a length: 0 ms, 20 ms, 40 ms and so on."""
    if length_ms <= 0:
        raise failure.Failure(failure.BAD_LENGTH, "the length of a recording is above 0 seconds")
    return (length_ms + recfile.TICK_MS - 1) // recfile.TICK_MS


def read_script(path, length_ms):
    """The timed commands of a script file, in file order, or `bad-script`."""
    try:
        with open(path, "rb") as file:
            text = file.read().decode("utf-8")
    except OSError as error:
        raise failure.Failure(failure.BAD_SCRIPT, f"{path}: {error.strerror or type(error).__name__}") from None
    except UnicodeDecodeError:
        raise failure.Failure(failure.BAD_SCRIPT, f"{path}: the script is not UTF-8") from None
    commands = []
    for number, line in enumerate(text.split("\n"), start=1):
        if line in ("", "\r") or line.startswith("#"):
            continue
        match = SCRIPT_LINE.fullmatch(line)
        if not match:
            raise failure.Failure(failure.BAD_SCRIPT, f"{path}, line {number}: a line is a time in milliseconds, a space and a command")
        time = int(match.group(1))
        if commands and time < commands[-1].time:
            raise failure.Failure(failure.BAD_SCRIPT, f"{path}, line {number}: the time {time} is earlier than the one before it")
        if time >= length_ms:
            raise failure.Failure(failure.BAD_SCRIPT, f"{path}, line {number}: the time {time} is not inside the {length_ms} ms of the recording")
        commands.append(Command(time, match.group(2).encode("utf-8")))
    return commands


def ticks(core, count, commands, out):
    """Runs the core over the ticks and yields each one for the record file.

    A command is given to the core with its own time, before the first tick that is not
    earlier than it, and its reply is printed to `out`. A command later than the last tick
    is given after it.
    """
    waiting = collections.deque(commands)

    def send(until):
        while waiting and (until is None or waiting[0].time <= until):
            command = waiting.popleft()
            reply = core.command(command.time, command.line)
            print("reply", command.time, reply.decode("ascii", "replace").rstrip("\n"), file=out)

    for index in range(count):
        now = recfile.TICK_MS * index
        send(now)
        produced = core.poll(now)
        yield now, produced, core.frame() if produced else b""
    send(None)


def run(show_dir, out_path, length_ms, script_path, library_path, out=None):
    """Records `length_ms` of the show in a folder into a record file."""
    out = sys.stdout if out is None else out
    count = tick_count(length_ms)
    commands = read_script(script_path, length_ms) if script_path is not None else []
    files = host.FolderHost(show_dir)
    try:
        core = binding.Core(library_path, files)
        try:
            recfile.write(out_path, core.legs, ticks(core, count, commands, out))
        except OSError as error:
            raise failure.Failure(failure.CANNOT_WRITE, f"{out_path}: {error.strerror or type(error).__name__}") from None
    finally:
        files.close()
        out.flush()
