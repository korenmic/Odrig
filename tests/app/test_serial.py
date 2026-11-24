"""The app on the link USB serial, through a stand-in of the APK's sender."""

import json
import unittest

from tests.emulator import support as emulator_support
from . import support
from .test_target import entered


class OverUsbSerial(unittest.TestCase):
    def emulator(self):
        folder = entered(self, emulator_support.example_show())
        return entered(self, emulator_support.Emulator(folder))

    def test_the_app_answers_plays_and_goes_back_to_wifi_with_the_switch(self):
        emulator = self.emulator()
        found = support.run('serial', address=f'127.0.0.1:{emulator.port}', settings={'rows': 2}).seen
        self.assertEqual(found['route'], 'Sent over USB serial.')
        self.assertEqual((found['wifiShown'], found['usbShown'], found['usbState']), (False, True, 'A board answers on USB serial.'))
        self.assertEqual(found['sends'], 0)
        self.assertEqual(json.loads(emulator.command('status'))['animation'], found['played'])
        self.assertEqual(found['after'], 'wifi')

    def test_a_withheld_reply_is_a_lost_reply_and_the_link_comes_back(self):
        emulator = self.emulator()
        found = support.run('serial', address=f'127.0.0.1:{emulator.port}', settings={'rows': 2, 'withhold': 'status'}).seen
        self.assertEqual(found['lost'], "No answer over USB serial. Check the cable to the board's USB port and that the installation has power. (no-answer)")
        self.assertEqual(found['route'], 'Sent over USB serial.')

    def test_without_a_board_on_usb_the_app_says_what_to_do(self):
        found = support.run('serial', settings={'noDevice': True}).seen
        self.assertEqual(found['failure'], "No board is connected by USB. Connect the phone to the board's USB port with a cable, then press Connect over USB. (no-usb)")
        self.assertNotIn('write', found['log'])


if __name__ == '__main__':
    unittest.main()
