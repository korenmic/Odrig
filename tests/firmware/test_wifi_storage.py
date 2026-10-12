import json
import unittest

from littlefs.errors import LittleFSError

from fwtool import storage, wifi

from . import support

DISK_VERSION_2_1 = 0x00020001

# Settings made for these tests. Neither password is a secret.
FIRST = wifi.Settings("odrig-in-a-test", "a-first-made-up-password")
SECOND = wifi.Settings("another name, 32 characters long", "x" * 63)


def files(image):
    return storage.files_in(storage.mount(image))


def config(image):
    return json.loads(files(image)["/cfg.json"].decode("utf-8"))


def secrets(image):
    return json.loads(files(image)["/wsec.json"].decode("utf-8"))


def without(value, *members):
    """A settings object without some members of its access point."""
    left = json.loads(json.dumps(value))
    for member in members:
        left.get("ap", {}).pop(member, None)
    return left


def order(value):
    """The names of all members of a JSON value, in the order they have, at every depth."""
    if isinstance(value, dict):
        return [(name, order(inner)) for name, inner in value.items()]
    if isinstance(value, list):
        return [order(inner) for inner in value]
    return None


class TheBenchBoard(unittest.TestCase):
    """The files the bench board holds: a configuration without an access point, no secrets."""

    @classmethod
    def setUpClass(cls):
        cls.before = support.storage_image(support.BENCH_FILES)
        cls.after = wifi.apply(cls.before, FIRST)

    def test_the_configuration_is_the_old_object_with_the_access_point_added_last(self):
        old, new = config(self.before), config(self.after)
        self.assertEqual(list(new), list(old) + ["ap"])
        self.assertEqual(new["ap"], {"ssid": FIRST.name, "pskl": len(FIRST.password)})
        self.assertEqual(list(new["ap"]), ["ssid", "pskl"])
        del new["ap"]
        self.assertEqual(json.dumps(new), json.dumps(old))

    def test_the_configuration_is_json_without_spaces(self):
        text = files(self.after)["/cfg.json"]
        self.assertTrue(text.startswith(support.BENCH_FILES["/cfg.json"][:-1] + b',"ap":{"ssid":"'))
        self.assertTrue(text.endswith(b'","pskl":%d}}' % len(FIRST.password)))

    def test_the_file_of_secrets_is_created_with_the_password_only(self):
        self.assertNotIn("/wsec.json", files(self.before))
        self.assertTrue(secrets(self.after) == {"ap": {"psk": FIRST.password}})

    def test_every_other_file_has_its_bytes(self):
        old, new = files(self.before), files(self.after)
        self.assertEqual(sorted(new), sorted([*old, "/wsec.json"]))
        for path in old:
            if path != "/cfg.json":
                self.assertEqual(new[path], old[path], path)

    def test_the_disk_version_and_the_size_stay(self):
        self.assertEqual(storage.geometry(self.after), storage.geometry(self.before))
        self.assertEqual(len(self.after), len(self.before))

    def test_holds_and_name_in_answer_for_both_images(self):
        self.assertFalse(wifi.holds(self.before, FIRST))
        self.assertIsNone(wifi.name_in(self.before))
        self.assertTrue(wifi.holds(self.after, FIRST))
        self.assertFalse(wifi.holds(self.after, SECOND))
        self.assertFalse(wifi.holds(self.after, wifi.Settings(FIRST.name, SECOND.password)))
        self.assertFalse(wifi.holds(self.after, wifi.Settings(SECOND.name, FIRST.password)))
        self.assertEqual(wifi.name_in(self.after), FIRST.name)


class WhatWledSaved(unittest.TestCase):
    """The files WLED writes when it saves its settings."""

    @classmethod
    def setUpClass(cls):
        cls.before = support.storage_image(support.SAVED_FILES)
        cls.after = wifi.apply(cls.before, FIRST)

    def test_only_the_name_the_length_and_the_password_differ(self):
        old, new = config(self.before), config(self.after)
        self.assertEqual((new["ap"]["ssid"], new["ap"]["pskl"]), (FIRST.name, len(FIRST.password)))
        self.assertEqual(without(new, "ssid", "pskl"), without(old, "ssid", "pskl"))
        old, new = secrets(self.before), secrets(self.after)
        self.assertTrue(new["ap"]["psk"] == FIRST.password)
        self.assertTrue(without(new, "psk") == without(old, "psk"))

    def test_wleds_other_wifi_settings_and_its_other_secrets_are_as_before(self):
        old, new = config(self.before), config(self.after)
        for member in ("chan", "hide", "behav", "ip"):
            self.assertEqual(new["ap"][member], old["ap"][member], member)
        for member in ("nw", "wifi", "ota", "hw", "if"):
            self.assertEqual(new[member], old[member], member)
        old, new = secrets(self.before), secrets(self.after)
        for member in ("nw", "if", "pin", "ota"):
            self.assertTrue(new[member] == old[member], member)

    def test_the_order_of_all_members_is_as_before(self):
        self.assertEqual(order(config(self.after)), order(config(self.before)))
        self.assertEqual(order(secrets(self.after)), order(secrets(self.before)))

    def test_a_number_with_a_fraction_and_text_outside_ascii_read_back_equal(self):
        new = config(self.after)
        self.assertEqual(new["id"]["name"], "Wänd ß")
        self.assertIn("Wänd ß".encode("utf-8"), files(self.after)["/cfg.json"])
        self.assertEqual(new["light"]["gc"], {"bri": 1.0, "col": 2.2, "val": 2.8})
        self.assertEqual((new["if"]["ntp"]["lt"], new["if"]["ntp"]["ln"]), (-0.5, 1e-7))
        self.assertIs(type(new["light"]["gc"]["bri"]), float)
        self.assertIn(b'"port1":65506', files(self.after)["/cfg.json"])

    def test_every_other_file_has_its_bytes_and_wleds_copy_is_not_edited(self):
        old, new = files(self.before), files(self.after)
        self.assertEqual(sorted(new), sorted(old))
        for path in old:
            if path not in ("/cfg.json", "/wsec.json"):
                self.assertEqual(new[path], old[path], path)
        self.assertIn(b"an-older-name", new["/bkp.cfg.json"])

    def test_holds_and_name_in_answer_for_both_images(self):
        self.assertFalse(wifi.holds(self.before, FIRST))
        self.assertEqual(wifi.name_in(self.before), "WLED-AP")
        self.assertTrue(wifi.holds(self.before, wifi.Settings("WLED-AP", "wled1234")))
        self.assertTrue(wifi.holds(self.after, FIRST))
        self.assertEqual(wifi.name_in(self.after), FIRST.name)


class Applying(unittest.TestCase):
    def test_a_password_in_the_configuration_is_gone_afterwards(self):
        given = dict(support.SAVED_FILES)
        given["/cfg.json"] = given["/cfg.json"].replace(b'"pskl":8,"chan"', b'"pskl":8,"psk":"left-in-the-open","chan"')
        before = support.storage_image(given)
        self.assertFalse(wifi.holds(before, wifi.Settings("WLED-AP", "wled1234")))
        after = wifi.apply(before, FIRST)
        self.assertNotIn("psk", config(after)["ap"])
        self.assertFalse(b"left-in-the-open" in files(after)["/cfg.json"])
        self.assertEqual(list(config(after)["ap"]), ["ssid", "pskl", "chan", "hide", "behav", "ip"])
        self.assertTrue(wifi.holds(after, FIRST))

    def test_a_password_in_the_configuration_alone_is_reason_enough_to_write(self):
        first = wifi.apply(support.storage_image(support.SAVED_FILES), FIRST)
        system = storage.mount(first)
        with system.open("/cfg.json", "wb") as file:
            file.write(files(first)["/cfg.json"].replace(b'"pskl":', b'"psk":"left-in-the-open","pskl":'))
        system.unmount()
        with_it = bytes(system.context.buffer)
        self.assertFalse(wifi.holds(with_it, FIRST))
        after = wifi.apply(with_it, FIRST)
        self.assertIsNot(after, with_it)
        self.assertTrue(wifi.holds(after, FIRST))

    def test_without_a_configuration_the_file_is_created_with_the_access_point_only(self):
        given = {path: content for path, content in support.BENCH_FILES.items() if path != "/cfg.json"}
        after = wifi.apply(support.storage_image(given), FIRST)
        self.assertEqual(files(after)["/cfg.json"], b'{"ap":{"ssid":"%s","pskl":%d}}' % (FIRST.name.encode(), len(FIRST.password)))
        self.assertTrue(wifi.holds(after, FIRST))

    def test_an_access_point_that_is_an_empty_object_is_filled(self):
        given = dict(support.BENCH_FILES)
        given["/cfg.json"] = b'{"ap":{},"def":{"on":true}}'
        after = wifi.apply(support.storage_image(given), FIRST)
        self.assertEqual(list(config(after)), ["ap", "def"])
        self.assertTrue(wifi.holds(after, FIRST))

    def test_a_newer_disk_version_stays(self):
        before = support.storage_image(support.SAVED_FILES, version=DISK_VERSION_2_1)
        after = wifi.apply(before, FIRST)
        self.assertEqual(storage.geometry(after)[0], DISK_VERSION_2_1)
        self.assertEqual(storage.geometry(after), storage.geometry(before))

    def test_the_same_settings_again_give_the_same_image_and_no_run(self):
        for given in (support.BENCH_FILES, support.SAVED_FILES):
            once = wifi.apply(support.storage_image(given), FIRST)
            twice = wifi.apply(once, FIRST)
            self.assertIs(twice, once)
            self.assertEqual(storage.runs(once, twice, support.BLOCK_SIZE), [])

    def test_other_settings_and_then_the_first_give_the_first(self):
        for given in (support.BENCH_FILES, support.SAVED_FILES):
            first = wifi.apply(support.storage_image(given), FIRST)
            other = wifi.apply(first, SECOND)
            self.assertTrue(wifi.holds(other, SECOND) and not wifi.holds(other, FIRST))
            self.assertEqual(wifi.name_in(other), SECOND.name)
            back = wifi.apply(other, FIRST)
            self.assertTrue(wifi.holds(back, FIRST))
            self.assertTrue(files(back) == files(first))

    def test_the_runs_of_changed_blocks_applied_to_the_old_image_give_the_new_one(self):
        for given in (support.BENCH_FILES, support.SAVED_FILES):
            before = support.storage_image(given)
            after = wifi.apply(before, FIRST)
            runs = storage.runs(before, after, support.BLOCK_SIZE)
            self.assertTrue(1 <= len(runs) <= 4, len(runs))
            patched = bytearray(before)
            for offset, content in runs:
                self.assertEqual(offset % support.BLOCK_SIZE, 0)
                patched[offset:offset + len(content)] = content
            self.assertTrue(bytes(patched) == after)

    def test_settings_files_that_are_not_what_wled_writes_are_refused(self):
        forms = {
            "a configuration that is an array": {"/cfg.json": b'[{"ap":{}}]'},
            "a configuration that is not JSON": {"/cfg.json": b'{"ap":{"ssid":"cut'},
            "a configuration that is not UTF-8": {"/cfg.json": b'{"id":{"name":"\xff\xfe"}}'},
            "an access point that is a number": {"/cfg.json": b'{"ap":5}'},
            "an access point that is null": {"/cfg.json": b'{"ap":null}'},
            "secrets that are not JSON": {"/wsec.json": b"not JSON"},
            "secrets that are a text": {"/wsec.json": b'"psk"'},
            "secrets whose access point is an array": {"/wsec.json": b'{"ap":["psk"]}'},
        }
        for label, changed in forms.items():
            with self.subTest(form=label):
                before = support.storage_image({**support.SAVED_FILES, **changed})
                with self.assertRaises(wifi.Failure) as caught:
                    wifi.apply(before, FIRST)
                self.assertEqual(caught.exception.reason, "wled-settings-malformed")
                self.assertIn(next(iter(changed)), caught.exception.detail)
                self.assertFalse(wifi.holds(before, FIRST))

    def test_a_refusal_names_the_file_and_no_value_of_it(self):
        before = support.storage_image({**support.SAVED_FILES, "/wsec.json": b'{"ap":"a-made-up-secret"}'})
        with self.assertRaises(wifi.Failure) as caught:
            wifi.apply(before, FIRST)
        self.assertIn("/wsec.json", caught.exception.detail)
        self.assertNotIn("a-made-up-secret", caught.exception.detail)
        self.assertNotIn(FIRST.password, caught.exception.detail)

    def test_a_file_system_with_no_room_is_no_space(self):
        given = dict(support.BENCH_FILES)
        given["/cfg.json"] = b'{"um":{"note":"' + b"n" * 9000 + b'"}}'
        system = storage.mount(support.storage_image(given, blocks=16))
        full, number = bytes(system.context.buffer), 0
        with self.assertRaises(LittleFSError):
            while True:
                with system.open(f"/fill-{number}.bin", "wb") as file:
                    file.write(bytes(range(256)) * 16)
                full, number = bytes(system.context.buffer), number + 1
        self.assertGreater(number, 0)
        with self.assertRaises(wifi.Failure) as caught:
            wifi.apply(full, FIRST)
        self.assertEqual(caught.exception.reason, "no-space")
        self.assertFalse(wifi.holds(full, FIRST))

    def test_name_in_gives_none_for_what_has_no_name(self):
        for content in (b'{"ap":{}}', b'{"ap":{"ssid":5}}', b'{"ap":5}', b"not JSON", b"[]"):
            self.assertIsNone(wifi.name_in(support.storage_image({"/cfg.json": content})), content)
        self.assertIsNone(wifi.name_in(support.storage_image({"/odrig/show.json": b"a show"})))


if __name__ == "__main__":
    unittest.main()
