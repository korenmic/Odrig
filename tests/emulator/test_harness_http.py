import http.client
import threading
import unittest
from unittest import mock

from . import support


class ConnectionRecovery(unittest.TestCase):
    def fixture(self):
        emulator = support.Emulator.__new__(support.Emulator)
        emulator.port = 1
        emulator._kept = []
        emulator._keeping = threading.Lock()
        connection = mock.Mock(sock=None)
        response = connection.getresponse.return_value
        response.status = 200
        response.will_close = False
        response.read.return_value = b'{"ok":true}\n'
        connection.request.side_effect = lambda *a, **k: connection.connect() if connection.sock is None else None
        return emulator, connection

    def test_local_buffer_exhaustion_is_retried_before_any_command_is_sent(self):
        emulator, connection = self.fixture()
        unavailable = OSError('local socket buffer exhausted')
        unavailable.winerror = 10055

        def connect():
            if connection.connect.call_count == 1:
                raise unavailable
            connection.sock = object()

        connection.connect.side_effect = connect
        with mock.patch.object(http.client, 'HTTPConnection', return_value=connection), \
                mock.patch.object(support.time, 'sleep'):
            self.assertEqual(emulator.command('off'), b'{"ok":true}\n')
        self.assertEqual(connection.connect.call_count, 2)
        connection.request.assert_called_once_with('POST', '/odrig', body=b'off')

    def test_a_reply_failure_never_replays_a_possibly_applied_command(self):
        emulator, connection = self.fixture()
        connection.connect.side_effect = lambda: setattr(connection, 'sock', object())
        connection.getresponse.side_effect = OSError('reply lost')
        with mock.patch.object(http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaisesRegex(OSError, 'reply lost'):
                emulator.command('off')
        self.assertEqual(connection.request.call_count, 1)
        connection.close.assert_called_once()

    def test_other_connect_errors_are_immediate(self):
        emulator, connection = self.fixture()
        connection.connect.side_effect = ConnectionRefusedError('refused')
        with mock.patch.object(http.client, 'HTTPConnection', return_value=connection):
            with self.assertRaises(ConnectionRefusedError):
                emulator.command('off')
        self.assertEqual(connection.connect.call_count, 1)

    def test_local_buffer_recovery_has_a_fixed_deadline(self):
        emulator, connection = self.fixture()
        unavailable = OSError('buffer exhausted')
        unavailable.winerror = 10055
        connection.connect.side_effect = unavailable
        with mock.patch.object(http.client, 'HTTPConnection', return_value=connection), \
                mock.patch.object(support.time, 'sleep'), \
                mock.patch.object(support.time, 'monotonic', side_effect=[0, 1, 3]):
            with self.assertRaisesRegex(OSError, 'buffer exhausted'):
                emulator.command('off')
        self.assertEqual(connection.connect.call_count, 2)
        connection.request.assert_not_called()
