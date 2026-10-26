"""The lengths of animations, for the page's seek bar.

A length comes from the catalog of the storage the file is in, when the storage has one;
else from the converter's `check` of the file, when Node.js is on the path; else the
engine takes it from a loop it has seen twice. The catalogs and the checks are read in a
thread of their own, so that a refresh of the core is never delayed, and their results
wait here until the engine takes them.
"""

import os
import queue
import re
import shutil
import subprocess
import threading

CONVERTER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "converter", "odrig.js")
DURATION = re.compile(rb"duration_ms: ([0-9]+)")
CHECK_SECONDS = 600
FIND = object()
# A storage's catalog, as catalog.md describes it: the marker, the pages, and the record of
# a change under way. A page line holds the entry's check value, its bytes, its width and
# height, its length in milliseconds, its type and its name.
CATALOG_MARKER = "catalog.txt"
CATALOG_PAGES = 16
CATALOG_CHANGING = "catalog.do"
CATALOG_LINE = re.compile(r"[0-9a-f]{8} [0-9]+ [0-9]+ [0-9]+ ([0-9]+) [a-z]+ (.+)")


def catalog_lengths(folder):
    """`{name: length in ms}` of the catalog of a folder: empty without a marker, with a
    change under way, or with a page that cannot be read."""
    if not os.path.isfile(os.path.join(folder, CATALOG_MARKER)) or os.path.exists(os.path.join(folder, CATALOG_CHANGING)):
        return {}
    found = {}
    for number in range(CATALOG_PAGES):
        page = os.path.join(folder, f"catalog-{number:02d}.txt")
        if not os.path.isfile(page):
            continue
        try:
            with open(page, "rb") as file:
                lines = file.read().decode("ascii", "replace").split("\n")
        except OSError:
            return {}
        for line in lines:
            if not line:
                continue
            entry = CATALOG_LINE.fullmatch(line)
            if entry is None:
                return {}
            found[entry.group(2)] = int(entry.group(1))
    return found


class Lengths:
    """What is known of the lengths, and the thread that finds them out.

    `node` is the path of Node.js, `None` for none; by default it is looked for on the
    path. `known(path)` answers from what was read already; `request(path)` has the file's
    storage catalog read and, failing it, the file checked, and `take()` gives the results
    that came since, each `(path, ms or None, source or None)`.
    """

    def __init__(self, node=FIND, converter=CONVERTER):
        self.node = shutil.which("node") if node is FIND else node
        self.converter = converter
        self._lock = threading.Lock()
        self._tables = {}
        self._checked = {}
        self._pending = set()
        self._asked = queue.Queue()
        self._results = queue.Queue()
        self._thread = None

    def known(self, path):
        """`(ms, source)` from the catalogs and checks read so far, or `(None, None)`."""
        folder, name = os.path.split(path)
        with self._lock:
            table = self._tables.get(folder)
            if table is not None and name in table:
                return table[name], "catalog"
            checked = self._checked.get(path)
            if checked is not None:
                return checked, "check"
        return None, None

    def request(self, path):
        """Has the length of a file found out, unless it was asked for already."""
        with self._lock:
            if path in self._pending or path in self._checked:
                return
            folder = os.path.dirname(path)
            if folder in self._tables and self.node is None:
                return
            self._pending.add(path)
            if self._thread is None:
                self._thread = threading.Thread(target=self._work, name="lengths", daemon=True)
                self._thread.start()
        self._asked.put(path)

    def take(self):
        """The results that came since the last call."""
        taken = []
        while True:
            try:
                taken.append(self._results.get_nowait())
            except queue.Empty:
                return taken

    def settle(self):
        """Waits until every request has been answered."""
        self._asked.join()

    def _work(self):
        while True:
            path = self._asked.get()
            try:
                self._results.put(self._find(path))
            finally:
                with self._lock:
                    self._pending.discard(path)
                self._asked.task_done()

    def _find(self, path):
        folder, name = os.path.split(path)
        with self._lock:
            table = self._tables.get(folder)
        if table is None:
            table = catalog_lengths(folder)
            with self._lock:
                self._tables[folder] = table
        if name in table:
            return path, table[name], "catalog"
        found = self._check(path) if self.node is not None else None
        with self._lock:
            self._checked[path] = found
        return path, found, "check" if found is not None else None

    def _check(self, path):
        try:
            done = subprocess.run([self.node, self.converter, "check", path], capture_output=True, timeout=CHECK_SECONDS)
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        found = DURATION.search(done.stdout)
        return int(found.group(1)) if found else None
