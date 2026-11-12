"""The files a mirror plays: the local copy of each key, `crc-size` as a catalog writes it,
looked for in the collections and among what the mirror fetched before, and the fetch from the
board of a key found nowhere."""

import base64
import binascii
import os
import pathlib
import threading
import time

# Where a mirror keeps what it fetched, under the repository's root.
KEPT = pathlib.Path("build", "mirror")
SUFFIXES = (".odrg", ".odrgx")
SETTINGS = ("env", "env.template")
SHARE = "ODRIG_ANIMATIONS"
# How long a key that could not be had is not asked for again.
AGAIN_SECONDS = 10.0
# The bytes of a file one `read` asks for.
PIECE = 720
# What the first bytes of a file say it holds, as the core's mirror takes it: an ODRG file
# is frames, and a container names its content at its sixth byte.
FRAMES = 1
CONTAINER = b"ODRX"


def parsed_key(key):
    """`(crc, size)` of a key, or `None` for one that is not a key."""
    if not isinstance(key, str):
        return None
    crc, dash, size = key.partition("-")
    if not dash or len(crc) != 8 or not size.isascii() or not size.isdigit():
        return None
    try:
        return int(crc, 16), int(size)
    except ValueError:
        return None


def crc_of(path):
    crc = 0
    with open(path, "rb") as file:
        while True:
            piece = file.read(1 << 20)
            if not piece:
                return crc
            crc = binascii.crc32(piece, crc)


def type_of(path):
    """The content type of a file, 1 frames, 2 a text or 3 a widget, or `None`."""
    try:
        with open(path, "rb") as file:
            head = file.read(6)
    except OSError:
        return None
    if len(head) < 6:
        return None
    return head[5] if head.startswith(CONTAINER) else FRAMES


def share_of(root):
    """The folder of the share's collection, as `env` names it, or `None`."""
    for name in SETTINGS:
        try:
            lines = (root / name).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            setting, equals, value = line.partition("=")
            if equals and setting.strip() == SHARE and value.strip():
                return pathlib.Path(value.strip())
        return None
    return None


class Files:
    """The local files of keys: `known` answers from what was found, at once, and `find`
    looks: among what the mirror fetched before, then the files of the collections whose
    size and CRC-32 are the key's. A file's CRC-32 is taken once, and kept by its path, its
    size and the time it was changed."""

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.kept = self.root / KEPT
        share = share_of(self.root)
        self.places = [self.root / "collection"] + ([share] if share is not None else [])
        self._found = {}
        self._crcs = {}
        self._lock = threading.Lock()

    def known(self, key):
        """`(path, type)` of a key found before, or `None`."""
        with self._lock:
            return self._found.get(key)

    def find(self, key):
        """Looks for the local file of a key: `(path, type)`, or `None`."""
        parsed = parsed_key(key)
        if parsed is None:
            return None
        crc, size = parsed
        for path in self._candidates(key, size):
            kind = type_of(path)
            if kind is not None and self._crc(path) == crc:
                with self._lock:
                    self._found[key] = (path, kind)
                return path, kind
        return None

    def keep(self, key, data):
        """Keeps fetched bytes under their key, written whole before they take the name."""
        self.kept.mkdir(parents=True, exist_ok=True)
        path = self.kept / f"{key}.odrg"
        part = self.kept / f"{key}.part"
        part.write_bytes(data)
        os.replace(part, path)
        kind = type_of(path)
        with self._lock:
            self._found[key] = (path, kind)
        return path

    def _candidates(self, key, size):
        kept = self.kept / f"{key}.odrg"
        if kept.is_file():
            yield kept
        for place in self.places:
            if not place.is_dir():
                continue
            for folder, _, names in os.walk(place):
                for name in names:
                    if name.endswith(SUFFIXES):
                        path = pathlib.Path(folder, name)
                        try:
                            if path.stat().st_size == size:
                                yield path
                        except OSError:
                            continue

    def _crc(self, path):
        try:
            stat = path.stat()
        except OSError:
            return None
        known = self._crcs.get(path)
        if known is not None and known[0] == (stat.st_size, stat.st_mtime_ns):
            return known[1]
        try:
            crc = crc_of(path)
        except OSError:
            return None
        self._crcs[path] = ((stat.st_size, stat.st_mtime_ns), crc)
        return crc


class Fetcher:
    """Finds the files of the keys asked for, one at a time: locally first, else from the
    board with `read <id> <offset> 720` through the man in the middle, between the clients'
    lines, kept once its size and its CRC-32 are the key's. `fetching` is `(id, key, bytes)`
    of a fetch from the board under way, or `None`."""

    def __init__(self, middle_, files, clock=time.monotonic):
        self.middle = middle_
        self.files = files
        self.clock = clock
        self.fetching = None
        self._wanted = []
        self._tried = {}
        self._lock = threading.Condition()
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name="mirror-files", daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        with self._lock:
            self._stopping = True
            self._lock.notify_all()
        self._thread.join(5.0)

    def want(self, item_id, key):
        """Asks for the file of a key, that of the board's animation with this id."""
        with self._lock:
            if key in (wanted for _, wanted in self._wanted) or (self.fetching is not None and self.fetching[1] == key):
                return
            tried = self._tried.get(key)
            if tried is not None and self.clock() - tried < AGAIN_SECONDS:
                return
            self._tried[key] = self.clock()
            self._wanted.append((item_id, key))
            self._lock.notify_all()

    def _run(self):
        while True:
            with self._lock:
                while not self._stopping and not self._wanted:
                    self._lock.wait()
                if self._stopping:
                    return
                item_id, key = self._wanted.pop(0)
            if self.files.find(key) is not None:
                continue
            data = self._fetch(item_id, key)
            with self._lock:
                self.fetching = None
            if data is not None:
                self.files.keep(key, data)

    def _fetch(self, item_id, key):
        parsed = parsed_key(key)
        if parsed is None or not isinstance(item_id, int):
            return None
        crc, size = parsed
        data = b""
        with self._lock:
            self.fetching = (item_id, key, 0)
        while len(data) < size:
            piece = self._piece(self.middle.ask(b"read %d %d %d" % (item_id, len(data), PIECE)))
            if not piece:
                return None
            data += piece
            with self._lock:
                if self._stopping:
                    return None
                self.fetching = (item_id, key, len(data))
        if len(data) != size or binascii.crc32(data) != crc:
            return None
        return data

    @staticmethod
    def _piece(reply):
        """The bytes of a reply to `read`, or `None` for a refusal or no reply. Its data is
        base64 of the URL's alphabet without padding, as `upload data` takes it."""
        if reply is None or not reply.startswith(b'{"ok":true'):
            return None
        start = reply.find(b'"data":"')
        if start < 0:
            return None
        text = reply[start + 8:reply.find(b'"', start + 8)]
        try:
            return base64.b64decode(text + b"=" * (-len(text) % 4), altchars=b"-_", validate=True)
        except ValueError:
            return None
