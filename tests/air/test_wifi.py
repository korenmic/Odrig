"""The board's network as WLED itself shows it to a device that has joined: its name and
the length of its password, and that the password is served to nobody."""

import json
import unittest

from fwtool import wifi

from . import support


class TheNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = wifi.read()

    def test_wleds_settings_name_the_network_as_the_settings_file_does(self):
        status, _, body = support.request("GET", "/json/cfg")
        self.assertEqual(status, 200)
        access = json.loads(body)["ap"]
        self.assertEqual(access["ssid"], self.settings.name)
        self.assertEqual(access["pskl"], len(self.settings.password))
        self.assertNotIn("psk", access)
        self.assertFalse(self.settings.password.encode("ascii") in body)

    def test_the_stored_configuration_is_served_and_holds_no_password(self):
        status, _, body = support.request("GET", "/cfg.json")
        self.assertEqual(status, 200)
        access = json.loads(body)["ap"]
        self.assertEqual(access["ssid"], self.settings.name)
        self.assertNotIn("psk", access)
        self.assertFalse(self.settings.password.encode("ascii") in body)

    def test_the_file_of_secrets_is_not_served(self):
        for path in ("/wsec.json", "/edit?edit=/wsec.json", "/edit?download=/wsec.json"):
            status, _, body = support.request("GET", path)
            self.assertNotEqual(status, 200, path)
            self.assertFalse(self.settings.password.encode("ascii") in body, path)


if __name__ == "__main__":
    unittest.main()
