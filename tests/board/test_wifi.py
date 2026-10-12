import time
import unittest

from . import support

# The longest that WLED takes to open its access point after a restart, with room to spare.
OPENS_WITHIN = 30.0
WPA2_WITH_A_PASSWORD = 3


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


if __name__ == "__main__":
    unittest.main()
