import json
import pathlib
import secrets
import tempfile
import time
import unittest

from fwtool import storage, wifi

from . import PORT, support

# The longest that WLED takes to open its access point after a restart, with room to spare.
OPENS_WITHIN = 30.0
WPA2_WITH_A_PASSWORD = 3
SETTINGS_FILES = ("/cfg.json", "/wsec.json")


def reports_until_the_access_point_is_up(seconds=OPENS_WITHIN):
    """The probe build's reports from now until one has `ap` 1, that one included."""
    reports = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        reports.append(support.probe())
        if reports[-1]["ap"] == 1:
            break
        time.sleep(0.2)
    return reports


def hosted():
    """What the board hosts, as a program sees it over USB: the report once the access
    point is up, and storage read back afterwards."""
    report = reports_until_the_access_point_is_up()[-1]
    return report, support.storage_image()


def judged(test, settings, report, image):
    """Fails unless the network is up under the name of these settings, protected, and
    storage holds these settings."""
    test.assertEqual(report["ap"], 1)
    test.assertEqual(report["ap_name"], settings.name)
    test.assertEqual(report["ap_auth"], WPA2_WITH_A_PASSWORD)
    test.assertEqual(wifi.name_in(image), settings.name)
    test.assertTrue(wifi.holds(image, settings), "storage does not hold the settings")


def played(status):
    return {member: status[member] for member in ("ok", "on", "brightness", "playing", "error")}


class TheReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)

    def test_the_name_and_the_protection_are_the_radios_once_the_access_point_is_up(self):
        support.restart()
        reports = reports_until_the_access_point_is_up()
        for report in reports:
            self.assertIn("ap_name", report)
            self.assertIn("ap_auth", report)
            if report["ap"] == 0:
                self.assertIsNone(report["ap_name"])
                self.assertIsNone(report["ap_auth"])
        last = reports[-1]
        self.assertEqual(last["ap"], 1)
        self.assertIsInstance(last["ap_name"], str)
        self.assertTrue(1 <= len(last["ap_name"]) <= 32, len(last["ap_name"]))
        self.assertEqual(last["ap_auth"], WPA2_WITH_A_PASSWORD)


class TheSettings(unittest.TestCase):
    """`set-wifi` on the board: first with settings made here, then with the settings file.
    Both runs are made once, before the tests, which look at what they left."""

    @classmethod
    def setUpClass(cls):
        support.ensure("probe")
        with support.dim_show() as folder:
            support.ensure_installed(folder)
        cls.before = support.storage_image()
        cls.status_before = support.command(PORT, "status")[1]

        holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(holder.cleanup)
        cls.made = wifi.Settings("odrig-test-" + secrets.token_hex(3), secrets.token_urlsafe(24))
        given = pathlib.Path(holder.name, "settings.json")
        given.write_text(json.dumps({"name": cls.made.name, "password": cls.made.password}))
        cls.first = support.on_port("set-wifi", "--settings", given, "--wait", support.START_SECONDS)
        cls.first_report, cls.first_image = hosted()

        started = time.monotonic()
        cls.second = support.on_port("set-wifi", "--wait", support.START_SECONDS)
        cls.seconds = time.monotonic() - started
        cls.kept = storage.kept_images(len(cls.before))[0]
        cls.second_report, cls.second_image = hosted()
        cls.status_after = support.command(PORT, "status")[1]
        print(json.dumps({"set_wifi_seconds": round(cls.seconds, 1), "after_the_first": [cls.first_report["ap_name"], cls.first_report["ap_auth"]],
                          "after_the_second": [cls.second_report["ap_name"], cls.second_report["ap_auth"]]}))

    def lines(self, done, settings):
        self.assertEqual(done.status, 0, done.err)
        lines = done.out.splitlines()
        self.assertEqual(lines[:2], [f"name: {settings.name}", "password: set"])
        self.assertEqual(len(lines), 3)
        self.assertTrue(json.loads(lines[2])["ok"])
        self.assertFalse(settings.password in done.out + done.err)

    def test_settings_made_here_are_hosted_and_stored(self):
        self.lines(self.first, self.made)
        judged(self, self.made, self.first_report, self.first_image)

    def test_the_settings_file_is_hosted_and_stored(self):
        settings = wifi.read()
        self.assertEqual(settings.name, "odrig")
        self.lines(self.second, settings)
        judged(self, settings, self.second_report, self.second_image)
        self.assertFalse(wifi.holds(self.second_image, self.made))

    def test_the_board_holds_the_image_the_tool_wrote_also_after_wled_has_started_on_it(self):
        self.assertTrue(self.kept.name.endswith("-after.bin"), self.kept.name)
        self.assertTrue(self.second_image == self.kept.read_bytes())
        self.assertEqual(storage.kept_images(len(self.before))[0], self.kept)

    def test_nothing_but_the_access_point_in_wleds_two_files_changed(self):
        old, new = storage.files_in(storage.mount(self.before)), storage.files_in(storage.mount(self.second_image))
        self.assertEqual(sorted(set(new) - set(SETTINGS_FILES)), sorted(set(old) - set(SETTINGS_FILES)))
        for path in old:
            if path not in SETTINGS_FILES:
                self.assertTrue(new[path] == old[path], path)
        was, now = (json.loads(files["/cfg.json"]) if "/cfg.json" in files else {} for files in (old, new))
        was.pop("ap", None)
        now.pop("ap", None)
        self.assertEqual(json.dumps(now), json.dumps(was))

    def test_the_show_plays_as_before(self):
        self.assertEqual(played(self.status_after), played(self.status_before))
        self.assertEqual(self.status_after["playing"], 3)
        self.assertIsNone(self.status_after["error"])


if __name__ == "__main__":
    unittest.main()
