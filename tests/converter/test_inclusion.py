import unittest
from odrig import show, errors
from .test_show import source


class Inclusion(unittest.TestCase):
    def test_boolean_is_preserved_and_absence_remains_absent(self):
        self.assertIsNone(show.loads(source()).items[0].ignored)
        for value in (True, False):
            self.assertIs(show.loads(source(items=[{"id": 1, "file": "a.odrg", "ignored": value}])).items[0].ignored, value)

    def test_other_types_and_cycles_are_rejected(self):
        for value in (0, 1, "true", None, [], {}):
            with self.subTest(value=value), self.assertRaises(errors.Rejection):
                show.loads(source(items=[{"id": 1, "file": "a.odrg", "ignored": value}]))
        with self.assertRaises(errors.Rejection):
            show.loads(source(items=[{"id": 1, "cycle": [1], "seconds": 1, "ignored": False}]))
