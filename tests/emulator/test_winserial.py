import ctypes
import sys
import time
import unittest
from unittest import mock

from odrigctl import client, winserial

REPLY = b'{"ok":true}\n'


class Kernel:
    """Stands in for `kernel32`: writes down every call, and is a port. A read gives the
    next piece of `before` until something has been written to the port, and the next
    piece of `answers` from then on. A name in `refuses` makes that function fail."""

    HANDLE = 0x1234

    def __init__(self, before=(), answers=(), refuses=(), takes=None):
        self.calls = []
        self.settings = None
        self.limits = []
        self.written = b""
        self.before = list(before)
        self.answers = list(answers)
        self.refuses = set(refuses)
        self.takes = takes

    def CreateFileW(self, name, access, share, security, disposition, flags, template):
        self.calls.append(("CreateFileW", name, access, share, disposition))
        return winserial.INVALID_HANDLE if "CreateFileW" in self.refuses else self.HANDLE

    def EscapeCommFunction(self, handle, function):
        self.calls.append(("EscapeCommFunction", {winserial.CLRRTS: "lower RTS", winserial.CLRDTR: "lower DTR"}.get(function, function)))
        return 0 if "EscapeCommFunction" in self.refuses else 1

    def GetCommState(self, handle, settings):
        self.calls.append(("GetCommState",))
        if "GetCommState" in self.refuses:
            return 0
        found = settings._obj
        found.BaudRate, found.flags, found.ByteSize, found.Parity, found.StopBits = 1200, 0x3011, 7, 2, 2
        return 1

    def SetCommState(self, handle, settings):
        given = settings._obj
        self.calls.append(("SetCommState",))
        self.settings = (given.DCBlength, given.BaudRate, given.flags, given.ByteSize, given.Parity, given.StopBits)
        return 0 if "SetCommState" in self.refuses else 1

    def SetCommTimeouts(self, handle, limits):
        given = limits._obj
        self.calls.append(("SetCommTimeouts",))
        self.limits.append((given.ReadIntervalTimeout, given.ReadTotalTimeoutMultiplier, given.ReadTotalTimeoutConstant, given.WriteTotalTimeoutMultiplier, given.WriteTotalTimeoutConstant))
        return 1

    def ReadFile(self, handle, buffer, size, count, overlapped):
        if "ReadFile" in self.refuses:
            return 0
        waiting = self.answers if self.written else self.before
        piece = waiting.pop(0)[:size] if waiting else b""
        if not piece:
            time.sleep(0.001)
        ctypes.memmove(buffer, piece, len(piece))
        count._obj.value = len(piece)
        return 1

    def WriteFile(self, handle, data, size, count, overlapped):
        if "WriteFile" in self.refuses:
            return 0
        taken = size if self.takes is None else min(size, self.takes)
        self.written += bytes(data[:taken])
        count._obj.value = taken
        return 1

    def CloseHandle(self, handle):
        self.calls.append(("CloseHandle", handle))
        return 1

    def named(self, name):
        return [call for call in self.calls if call[0] == name]


class Opening(unittest.TestCase):
    def opened(self, name="COM3", **kernel):
        self.kernel = Kernel(**kernel)
        port = winserial.Port(name, self.kernel)
        self.addCleanup(port.close)
        return port

    def test_the_port_is_opened_by_its_device_name_for_reading_and_writing_and_not_shared(self):
        self.opened("COM3")
        self.assertEqual(self.kernel.named("CreateFileW"), [("CreateFileW", "\\\\.\\COM3", winserial.GENERIC_READ | winserial.GENERIC_WRITE, 0, winserial.OPEN_EXISTING)])

    def test_a_port_above_com9_is_found_and_a_device_name_is_left_as_it_is(self):
        for name, device in (("COM1", "\\\\.\\COM1"), ("COM9", "\\\\.\\COM9"), ("COM10", "\\\\.\\COM10"), ("COM256", "\\\\.\\COM256"), ("\\\\.\\COM12", "\\\\.\\COM12")):
            self.assertEqual(winserial.device(name), device)
        self.opened("COM12")
        self.assertEqual(self.kernel.named("CreateFileW")[0][1], "\\\\.\\COM12")

    def test_rts_is_lowered_before_dtr_and_both_before_the_settings_are_written(self):
        self.opened()
        self.assertEqual([call[0] for call in self.kernel.calls], ["CreateFileW", "EscapeCommFunction", "EscapeCommFunction", "GetCommState", "SetCommState", "SetCommTimeouts"])
        self.assertEqual(self.kernel.named("EscapeCommFunction"), [("EscapeCommFunction", "lower RTS"), ("EscapeCommFunction", "lower DTR")], "the modem lines are not lowered RTS first, DTR second")

    def test_it_goes_on_when_both_requests_are_refused(self):
        port = self.opened(refuses=("EscapeCommFunction",), before=[REPLY])
        self.assertEqual(len(self.kernel.named("EscapeCommFunction")), 2)
        self.assertEqual(b"".join(port.received(0.05)), REPLY)

    def test_the_settings_are_115200_baud_8_bits_no_parity_one_stop_bit(self):
        self.opened()
        length, baud, flags, bits, parity, stop = self.kernel.settings
        self.assertEqual((length, baud, bits, parity, stop), (ctypes.sizeof(winserial.DCB), 115200, 8, 0, 0))
        self.assertEqual(ctypes.sizeof(winserial.DCB), 28)

    def test_the_settings_keep_dtr_and_rts_low_and_ask_for_no_flow_control(self):
        self.opened()
        flags = self.kernel.settings[2]
        self.assertEqual(flags & 0x0001, 1, "the port is not binary")
        self.assertEqual(flags & 0x0030, 0, "opening the port again would raise DTR")
        self.assertEqual(flags & 0x3000, 0, "opening the port again would raise RTS")
        self.assertEqual(flags & 0x030C, 0, "flow control is asked for")
        self.assertEqual(flags, winserial.BINARY)

    def test_a_read_returns_with_what_has_arrived(self):
        self.opened()
        self.assertEqual(self.kernel.limits, [(0xFFFFFFFF, 0xFFFFFFFF, winserial.POLL_MILLISECONDS, 0, 0)])
        self.assertGreater(winserial.POLL_MILLISECONDS, 0)

    def test_a_name_that_does_not_open_is_an_error_and_nothing_is_left_open(self):
        with self.assertRaises(OSError):
            winserial.Port("COM99", kernel := Kernel(refuses=("CreateFileW",)))
        self.assertEqual([call[0] for call in kernel.calls], ["CreateFileW"])

    def test_a_name_that_is_no_serial_port_is_an_error_and_is_closed(self):
        for refused in ("GetCommState", "SetCommState"):
            with self.assertRaises(OSError) as caught:
                winserial.Port("NUL", kernel := Kernel(refuses=(refused,)))
            self.assertTrue(caught.exception.strerror)
            self.assertEqual(kernel.named("CloseHandle"), [("CloseHandle", Kernel.HANDLE)], refused)

    def test_closing_twice_closes_once(self):
        port = self.opened()
        port.close()
        port.close()
        self.assertEqual(self.kernel.named("CloseHandle"), [("CloseHandle", Kernel.HANDLE)])


class ReadingAndWriting(unittest.TestCase):
    def opened(self, **kernel):
        self.kernel = Kernel(**kernel)
        port = winserial.Port("COM3", self.kernel)
        self.addCleanup(port.close)
        return port

    def test_what_arrives_is_given_in_pieces_as_it_comes_and_nothing_when_nothing_does(self):
        port = self.opened(before=[b"boot\n", b"", b'{"ok"', b":true}\n"])
        self.assertEqual(list(port.received(0.05)), [b"boot\n", b'{"ok"', b":true}\n"])
        self.assertEqual(list(port.received(0.01)), [])
        self.assertEqual(list(port.received(0)), [])

    def test_every_byte_is_written_also_when_the_port_takes_a_few_at_a_time(self):
        port = self.opened(takes=3)
        port.write(b"brightness 40\n", 2)
        self.assertEqual(self.kernel.written, b"brightness 40\n")
        self.assertEqual(self.kernel.limits[-1], (0xFFFFFFFF, 0xFFFFFFFF, winserial.POLL_MILLISECONDS, 0, 2000))

    def test_a_port_that_takes_no_byte_in_the_time_is_an_error(self):
        port = self.opened(takes=0)
        with self.assertRaises(OSError) as caught:
            port.write(b"status\n", 0.01)
        self.assertIn("takes no more bytes", caught.exception.strerror)

    def test_a_read_or_a_write_the_system_refuses_is_an_error(self):
        with self.assertRaises(OSError):
            list(self.opened(refuses=("ReadFile",)).received(0.05))
        with self.assertRaises(OSError):
            self.opened(refuses=("WriteFile",)).write(b"status\n", 1)


class TheExchange(unittest.TestCase):
    """The serial exchange of a system without `termios`, which the stand-in makes any
    system."""

    def exchange(self, *arguments, **kernel):
        self.kernel = Kernel(**kernel)
        with mock.patch.object(client, "termios", None), mock.patch.object(winserial, "kernel32", lambda: self.kernel), \
                mock.patch.object(client, "SETTLE_SECONDS", 0.01), mock.patch.object(client, "DISCARD_SECONDS", 0.02):
            return client.serial_exchange(*arguments)

    def test_the_line_is_sent_and_the_first_reply_comes_back_without_its_line_end(self):
        reply = self.exchange("COM7", b"status\n", 1, answers=[b"boot: ready\n", b'{"ok":true,', b'"on":true}\r\n'])
        self.assertEqual(reply, b'{"ok":true,"on":true}')
        self.assertEqual(self.kernel.written, b"status\n")
        self.assertEqual(self.kernel.named("CreateFileW")[0][1], "\\\\.\\COM7")
        self.assertEqual(len(self.kernel.named("CloseHandle")), 1)

    def test_what_was_waiting_in_the_port_is_discarded(self):
        reply = self.exchange("COM3", b"status\n", 1, before=[b'{"ok":true,"stale":1}\n'], answers=[b'{"ok":true,"fresh":1}\n'])
        self.assertEqual(reply, b'{"ok":true,"fresh":1}')
        self.assertEqual(self.kernel.before, [])

    def test_no_reply_within_the_time_is_unreachable(self):
        with self.assertRaises(client.Unreachable) as caught:
            self.exchange("COM3", b"status\n", 0.05, answers=[b"boot: ready\n"])
        self.assertEqual(str(caught.exception), "COM3: no reply within 0.05 seconds")
        self.assertEqual(len(self.kernel.named("CloseHandle")), 1)

    def test_a_name_that_does_not_open_is_unreachable(self):
        with self.assertRaises(client.Unreachable) as caught:
            self.exchange("COM99", b"status\n", 1, refuses=("CreateFileW",))
        self.assertTrue(str(caught.exception).startswith("COM99: "), caught.exception)

    def test_a_name_that_is_no_serial_port_is_unreachable(self):
        with self.assertRaises(client.Unreachable) as caught:
            self.exchange("NUL", b"status\n", 1, refuses=("GetCommState",))
        self.assertTrue(str(caught.exception).startswith("NUL: "), caught.exception)

    def test_another_judge_of_a_reply_may_be_given(self):
        reply = self.exchange("COM3", b"v\n", 1, lambda line: line.startswith(b"WLED"), answers=[b'{"ok":true}\nWLED 16.0.1\n'])
        self.assertEqual(reply, b"WLED 16.0.1")


@unittest.skipUnless(sys.platform == "win32", "kernel32 is a library of Windows")
class TheSystemsOwn(unittest.TestCase):
    def test_the_functions_are_those_of_kernel32_with_handles_as_wide_as_a_pointer(self):
        library = winserial.kernel32()
        self.assertEqual(ctypes.sizeof(library.CreateFileW.restype), ctypes.sizeof(ctypes.c_void_p))
        for name in ("EscapeCommFunction", "GetCommState", "SetCommState", "SetCommTimeouts", "ReadFile", "WriteFile", "CloseHandle"):
            self.assertEqual(ctypes.sizeof(getattr(library, name).argtypes[0]), ctypes.sizeof(ctypes.c_void_p), name)

    def test_a_port_that_is_not_there_is_unreachable_and_says_why(self):
        with self.assertRaises(client.Unreachable) as caught:
            client.serial_exchange("COM254", b"status\n", 1)
        self.assertRegex(str(caught.exception), r"\ACOM254: \S")

    def test_a_file_is_no_serial_port(self):
        with self.assertRaises(client.Unreachable) as caught:
            client.serial_exchange(__file__, b"status\n", 1)
        self.assertRegex(str(caught.exception), r": \S")


if __name__ == "__main__":
    unittest.main()
