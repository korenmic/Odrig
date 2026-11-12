"""At every refresh of a mirror, the turn the board's plan says the board shows, written into
the record the core shows in place of the show."""

import threading

DEGREES_PER_TURN = 90
# The record's tests: the diagonal, and a snake's.
DIAGONAL = 1
SNAKE = 2


def item_at(plan, board_ms):
    """The item of a plan whose part holds a moment of the board's clock, or `None`."""
    for item in plan.get("items") or ():
        start, end = item.get("start"), item.get("end")
        if isinstance(start, int) and start <= board_ms and (end is None or board_ms < end):
            return item
    return None


class Driver:
    """Writes the turn into the core's record at every tick, from what the keeper and the
    files know at once: a tick looks nothing up and waits for nothing.

    `names` is the host's table of the mirror's names, `<key>.odrg` to a local path. A key
    not found yet is asked of the fetcher. `dark` says why the LEDs are dark, or `None`:
    `no-plan`, `canvas`, `nothing`, `no-key` or `fetching`; `item` is the item of the
    board's plan on the LEDs.
    """

    def __init__(self, keeper, files, fetcher, names):
        self.keeper = keeper
        self.files = files
        self.fetcher = fetcher
        self.names = names
        self.canvas = None
        self.dark = "no-plan"
        self.item = None
        self._turn = None
        self._lock = threading.Lock()

    def drive(self, record, local_ms):
        """Fills in the record for a refresh at `local_ms` of the emulator's clock. Returns the
        board's miniature output, `True` or `False`, or `None` while no plan says it."""
        plan, offset = self.keeper.snapshot()
        if plan is None or offset is None:
            return self._dark(record, "no-plan", None)
        board = self.keeper.board_canvas()
        if board is not None and self.canvas is not None and board != self.canvas:
            return self._dark(record, "canvas", plan)
        record.on = 1 if plan.get("on") else 0
        record.rotation = (plan.get("rotation") or 0) // DEGREES_PER_TURN % 4
        record.test = (SNAKE if plan.get("snake") else DIAGONAL) if plan.get("test") else 0
        record.snake = plan.get("snake") or 0
        item = item_at(plan, local_ms + offset)
        if item is None:
            return self._dark(record, "nothing", plan)
        key = item.get("key")
        if key is None:
            return self._dark(record, "no-key", plan, item)
        found = self.files.known(key)
        if found is None:
            self.fetcher.want(item.get("id"), key)
            return self._dark(record, "fetching", plan, item)
        path, kind = found
        name = f"{key}.odrg"
        self.names[name] = path
        start = item["start"] - (item.get("from") or 0)
        turn = (item.get("id"), start, name)
        if turn != self._turn:
            self._turn = turn
            record.serial = (record.serial + 1) & 0xFFFFFFFF
        record.name = name.encode("ascii")
        record.type = kind
        record.brightness = item.get("brightness", plan.get("brightness", 255))
        record.loop_ms = item.get("loop") or 0
        record.seed = item.get("seed") or 0
        record.zero_ms = max(0, start - offset)
        self._set(None, item)
        return bool(plan.get("mini"))

    def _dark(self, record, why, plan, item=None):
        if record.name:
            record.name = b""
            record.serial = (record.serial + 1) & 0xFFFFFFFF
            self._turn = None
        self._set(why, item)
        return None if plan is None else bool(plan.get("mini"))

    def _set(self, why, item):
        with self._lock:
            self.dark, self.item = why, item

    def shown(self):
        """`(dark, item)`, as the latest tick left them."""
        with self._lock:
            return self.dark, self.item
