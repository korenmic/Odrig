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
    piece of `answers` from then on. A name in `refuses` makes that function fail, and
    `found` is the flags of the settings the port is found with: DTR and RTS both driven
    by the port unless told otherwise."""

    HANDLE = 0x1234
    DTR_ON, DTR_HANDSHAKE, RTS_ON, RTS_HANDSHAKE, RTS_TOGGLE, CTS_FLOW = 0x0010, 0x0020, 0x1000, 0x2000, 0x3000, 0x0004

    def __init__(self, before=(), answers=(), refuses=(), takes=None, found=0x0001 | 0x0010 | 0x1000, second_refused=False):
        self.calls = []
        self.found = found
        self.second_refused = second_refused
        self.written_settings = []
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

    def GetCommState(self, handle, settings):
        self.calls.append(("GetCommState",))
        if "GetCommState" in self.refuses:
            return 0
        found = settings._obj
        found.BaudRate, found.flags, found.ByteSize, found.Parity, found.StopBits = 1200, self.found, 7, 2, 2
        return 1

    def SetCommState(self, handle, settings):
        given = settings._obj
        self.calls.append(("SetCommState",))
        self.settings = (given.DCBlength, given.BaudRate, given.flags, given.ByteSize, given.Parity, given.StopBits)
        self.written_settings.append(self.settings)
        if self.second_refused and len(self.written_settings) == 2:
            return 0
        return 0 if "SetCommState" in self.refuses else 1

    def lines(self):
        """What each writing of the settings does to the two modem lines, in order: a line
        the settings no longer leave to the port goes low."""
        states = [self.found, *(written[2] for written in self.written_settings)]
        lowered = []
        for before, after in zip(states, states[1:]):
            step = []
            if before & 0x3000 and not after & 0x3000:
                step.append("RTS")
            if before & 0x0030 and not after & 0x0030:
                step.append("DTR")
            lowered.append(step)
        return lowered

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

    def test_rts_is_lowered_before_dtr_by_two_writings_of_the_settings(self):
        self.opened()
        self.assertEqual([call[0] for call in self.kernel.calls], ["CreateFileW", "GetCommState", "SetCommState", "SetCommState", "SetCommTimeouts"])
        self.assertEqual(self.kernel.lines(), [["RTS"], ["DTR"]], "the modem lines are not lowered RTS first, DTR second")

    def test_the_first_writing_takes_rts_from_the_port_and_leaves_dtr_as_it_was(self):
        for found in (Kernel.DTR_ON | Kernel.RTS_ON, Kernel.DTR_ON | Kernel.RTS_HANDSHAKE | Kernel.CTS_FLOW, Kernel.DTR_HANDSHAKE | Kernel.RTS_TOGGLE, Kernel.DTR_ON):
            with self.subTest(found=hex(found)):
                self.opened(found=1 | found)
                first, second = (written[2] for written in self.kernel.written_settings)
                self.assertEqual(first & 0x3000, 0, "RTS is still the port's to drive")
                self.assertEqual(first & 0x0030, found & 0x0030, "DTR changed with RTS")
                self.assertEqual(first & 0x030C, 0, "flow control is still asked for")
                self.assertEqual(second, winserial.BINARY)
                for step in self.kernel.lines():
                    self.assertNotEqual(step, ["RTS", "DTR"], "both lines change in one writing, in an order the system chooses")
                self.assertNotIn(["DTR"], self.kernel.lines()[:1], "DTR goes low while RTS may still be high")

    def test_a_port_whose_rts_was_left_to_a_handshake_gets_no_request_it_would_refuse(self):
        port = self.opened(found=1 | Kernel.DTR_ON | Kernel.RTS_HANDSHAKE, before=[REPLY])
        self.assertFalse(hasattr(self.kernel, "EscapeCommFunction"))
        self.assertEqual(self.kernel.lines(), [["RTS"], ["DTR"]])
        self.assertEqual(b"".join(port.received(0.05)), REPLY)

    def test_a_port_that_has_both_lines_low_already_changes_neither(self):
        self.opened(found=winserial.BINARY)
        self.assertEqual(self.kernel.lines(), [[], []])

    def test_the_settings_are_115200_baud_8_bits_no_parity_one_stop_bit(self):
        self.opened()
        for length, baud, flags, bits, parity, stop in self.kernel.written_settings:
            self.assertEqual((length, baud, bits, parity, stop), (ctypes.sizeof(winserial.DCB), 115200, 8, 0, 0))

    def test_the_two_structures_have_the_sizes_of_windows_on_every_system(self):
        self.assertEqual((ctypes.sizeof(winserial.DCB), ctypes.sizeof(winserial.Timeouts)), (28, 20))
        self.assertEqual((winserial.DCB.flags.offset, winserial.DCB.ByteSize.offset, winserial.DCB.wReserved1.offset), (8, 18, 26))
        self.assertEqual((ctypes.sizeof(winserial.DWORD), ctypes.sizeof(winserial.WORD)), (4, 2))

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
        for refusing in ({"refuses": ("GetCommState",)}, {"refuses": ("SetCommState",)}, {"second_refused": True}):
            with self.assertRaises(OSError) as caught:
                winserial.Port("NUL", kernel := Kernel(**refusing))
            self.assertTrue(caught.exception.strerror)
            self.assertEqual(kernel.named("CloseHandle"), [("CloseHandle", Kernel.HANDLE)], refusing)

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
        for name in ("GetCommState", "SetCommState", "SetCommTimeouts", "ReadFile", "WriteFile", "CloseHandle"):
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
