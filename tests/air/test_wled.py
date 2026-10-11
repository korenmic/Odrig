"""WLED's own interface beside the player. The last test saves WLED's LED settings, with the
pin of the last output changed, to see the usermod put the mapping's outputs back; WLED then
stores the mapping's outputs as its LED settings."""

import json
import time
import unittest

from . import support

RELEASE = "odrig_ESP32-S3_16MB_opi"
ENTRIES = ("odrig show", "odrig outputs", "odrig start")
SPARE_PIN = 12


def info():
    status, _, body = support.request("GET", "/json/info")
    assert status == 200, status
    return json.loads(body)


class Information(unittest.TestCase):
    def test_wled_reports_its_access_point_as_active(self):
        self.assertIs(info()["wifi"]["ap"], True)

    def test_the_release_is_the_firmwares(self):
        self.assertEqual(info()["release"], RELEASE)

    def test_the_usermod_reports_the_show_the_outputs_and_the_start(self):
        entries = info()["u"]
        for name in ENTRIES:
            self.assertIn(name, entries)
        self.assertEqual(entries["odrig show"][0], "ok")
        self.assertRegex(entries["odrig outputs"][0], r"^(\d+)/\1$")
        self.assertGreater(entries["odrig start"][0], 0)

    def test_wleds_start_page_is_served(self):
        status, headers, body = support.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertGreater(len(body), 1000)

    def test_wleds_json_interface_answers(self):
        status, _, body = support.request("GET", "/json/state")
        self.assertEqual(status, 200)
        self.assertIn("on", json.loads(body))


class WledsOwnControls(unittest.TestCase):
    def test_wleds_switch_brightness_and_live_override_do_not_reach_the_player(self):
        before = support.over_the_port("status")[1]
        for state in ({"on": False}, {"bri": 255}, {"lor": 2}, {"live": False}, {"on": True, "bri": 128, "lor": 0}):
            self.assertEqual(support.request("POST", "/json/state", json.dumps(state).encode(), "application/json")[0], 200)
            time.sleep(0.5)
            now = support.over_the_port("status")[1]
            self.assertEqual((now["on"], now["brightness"], now["playing"], now["error"]), (before["on"], before["brightness"], before["playing"], before["error"]), state)
        time.sleep(1.5)
        self.assertGreaterEqual(support.over_the_port("status")[1]["fps"], 49)


class LedSettings(unittest.TestCase):
    def test_the_mappings_outputs_come_back_after_wleds_led_settings_are_saved(self):
        before = info()["u"]["odrig outputs"][0]
        self.assertRegex(before, r"^(\d+)/\1$")
        status, _, body = support.request("GET", "/json/cfg")
        self.assertEqual(status, 200)
        outputs = json.loads(body)["hw"]["led"]["ins"]
        outputs[-1]["pin"] = [SPARE_PIN]
        saved = json.dumps({"hw": {"led": {"ins": outputs}}}).encode()
        self.assertEqual(support.request("POST", "/json/cfg", saved, "application/json")[0], 200)
        time.sleep(3.0)
        self.assertEqual(info()["u"]["odrig outputs"][0], before)
        self.assertEqual(support.over_the_port("status")[1]["error"], None)
        self.assertGreaterEqual(support.over_the_port("status")[1]["fps"], 49)
        status, _, body = support.request("GET", "/json/cfg")
        self.assertNotIn([SPARE_PIN], [output["pin"] for output in json.loads(body)["hw"]["led"]["ins"]])
