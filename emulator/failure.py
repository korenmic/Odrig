"""Why the emulator cannot start: one reason name and a detail for people."""

NOT_A_FOLDER = "not-a-folder"
CORE_NOT_BUILT = "core-not-built"
SERIAL_UNAVAILABLE = "serial-unavailable"
ADDRESS_IN_USE = "address-in-use"
BAD_LENGTH = "bad-length"
BAD_SCRIPT = "bad-script"

REASONS = (NOT_A_FOLDER, CORE_NOT_BUILT, SERIAL_UNAVAILABLE, ADDRESS_IN_USE, BAD_LENGTH, BAD_SCRIPT)


class Failure(Exception):
    """The emulator cannot start. It is printed as `error: <reason>: <detail>`."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail

    def line(self):
        return f"error: {self.reason}: {self.detail}"
