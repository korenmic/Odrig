"""The firmware tool: everything `python3 firmware/fw.py` does."""


class Failure(Exception):
    """A command cannot do its work. The tool prints `error: <reason>: <detail>`."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
