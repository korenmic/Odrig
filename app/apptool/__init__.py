"""The tool of the operators' app: everything `python3 app/app.py` does."""


class Failure(Exception):
    """A command cannot do its work. The tool prints `error: <reason>: <detail>`."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
