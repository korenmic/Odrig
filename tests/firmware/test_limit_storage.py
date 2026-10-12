import json
import unittest

from littlefs.errors import LittleFSError

from fwtool import Failure, limit, storage, wifi

from . import support

DISK_VERSION_2_1 = 0x00020001


def files(image):
    return storage.files_in(storage.mount(image))


def config(image):
    return json.loads(files(image)["/cfg.json"].decode("utf-8"))


def order(value):
    """The names of all members of a JSON value, in the order they have, at every depth."""
    if isinstance(value, dict):
        return [(name, order(inner)) for name, inner in value.items()]
    if isinstance(value, list):
        return [order(inner) for inner in value]
    return None


def without_the_limit(value):
    left = json.loads(json.dumps(value))
    left["hw"]["led"].pop("maxpwr", None)
    return left


class OnBothSetsOfFiles(unittest.TestCase):
    """The bench board's files, and the files WLED writes when it saves its settings. Both
    hold a limit of 850."""

    def each(self, check):
        for label, given in (("the bench board", support.BENCH_FILES), ("what WLED saved", support.SAVED_FILES)):
            with self.subTest(files=label):
                check(support.storage_image(given))

    def test_only_the_limit_differs(self):
        def check(before):
            after = limit.apply(before, 0)
            self.assertEqual(config(after)["hw"]["led"]["maxpwr"], 0)
            self.assertEqual(without_the_limit(config(after)), without_the_limit(config(before)))
            self.assertEqual(order(config(after)), order(config(before)))
        self.each(check)

    def test_every_other_file_has_its_bytes_and_the_file_system_its_version_and_size(self):
        def check(before):
            after = limit.apply(before, 40000)
            old, new = files(before), files(after)
            self.assertEqual(sorted(new), sorted(old))
            for path in old:
                if path != "/cfg.json":
                    self.assertEqual(new[path], old[path], path)
            self.assertEqual(storage.geometry(after), storage.geometry(before))
        self.each(check)

    def test_the_outputs_of_the_configuration_keep_their_own_numbers(self):
        before = support.storage_image(support.SAVED_FILES)
        after = limit.apply(before, 0)
        self.assertEqual(config(after)["hw"]["led"]["ins"], config(before)["hw"]["led"]["ins"])
        self.assertEqual(config(after)["hw"]["led"]["ins"][0]["maxpwr"], 425)

    def test_the_value_it_holds_already_gives_the_same_image_and_no_run(self):
        def check(before):
            self.assertEqual(limit.stored(before), 850)
            self.assertIs(limit.apply(before, 850), before)
            changed = limit.apply(before, 0)
            self.assertIs(limit.apply(changed, 0), changed)
            self.assertEqual(storage.runs(changed, limit.apply(changed, 0), support.BLOCK_SIZE), [])
        self.each(check)

    def test_another_value_and_then_the_first_give_the_first(self):
        def check(before):
            first = limit.apply(before, 0)
            back = limit.apply(limit.apply(first, 36000), 0)
            self.assertEqual(limit.stored(back), 0)
            self.assertTrue(files(back) == files(first))
            self.assertEqual(config(limit.apply(first, 850)), config(before))
        self.each(check)

    def test_stored_gives_what_was_set(self):
        def check(before):
            for milliamps in (0, 1, 850, 36000, 65535):
                self.assertEqual(limit.stored(limit.apply(before, milliamps)), milliamps)
        self.each(check)

    def test_the_runs_of_changed_blocks_applied_to_the_old_image_give_the_new_one(self):
        def check(before):
            after = limit.apply(before, 0)
            runs = storage.runs(before, after, support.BLOCK_SIZE)
            self.assertTrue(1 <= len(runs) <= 3, len(runs))
            patched = bytearray(before)
            for offset, content in runs:
                patched[offset:offset + len(content)] = content
            self.assertTrue(bytes(patched) == after)
        self.each(check)

    def test_the_limit_and_the_networks_settings_do_not_disturb_each_other(self):
        settings = wifi.Settings("odrig-in-a-test", "a-made-up-password")

        def check(before):
            both = limit.apply(wifi.apply(before, settings), 0)
            self.assertTrue(wifi.holds(both, settings))
            self.assertEqual(limit.stored(both), 0)
            other_way = wifi.apply(limit.apply(before, 0), settings)
            self.assertTrue(files(other_way) == files(both))
        self.each(check)


class WhereTheMemberIsMissing(unittest.TestCase):
    def applied(self, content, milliamps=850):
        given = {path: data for path, data in support.BENCH_FILES.items() if path != "/cfg.json"}
        if content is not None:
            given["/cfg.json"] = content
        before = support.storage_image(given)
        return before, limit.apply(before, milliamps)

    def test_without_a_configuration_the_file_is_created_with_the_limit_only(self):
        before, after = self.applied(None)
        self.assertIsNone(limit.stored(before))
        self.assertEqual(files(after)["/cfg.json"], b'{"hw":{"led":{"maxpwr":850}}}')

    def test_a_missing_hw_is_added_last(self):
        before, after = self.applied(b'{"ap":{"ssid":"odrig","pskl":10},"def":{"on":true}}', 0)
        self.assertIsNone(limit.stored(before))
        self.assertEqual(files(after)["/cfg.json"], b'{"ap":{"ssid":"odrig","pskl":10},"def":{"on":true},"hw":{"led":{"maxpwr":0}}}')

    def test_a_missing_led_is_added_last_in_hw(self):
        before, after = self.applied(b'{"hw":{"btn":{"max":4}},"def":{}}')
        self.assertEqual(files(after)["/cfg.json"], b'{"hw":{"btn":{"max":4},"led":{"maxpwr":850}},"def":{}}')

    def test_a_missing_member_is_added_last_in_led(self):
        before, after = self.applied(b'{"hw":{"led":{"total":360,"fps":50}}}')
        self.assertIsNone(limit.stored(before))
        self.assertEqual(files(after)["/cfg.json"], b'{"hw":{"led":{"total":360,"fps":50,"maxpwr":850}}}')

    def test_a_limit_that_is_no_whole_number_counts_as_none_and_is_replaced(self):
        for odd in (b"850.0", b'"850"', b"true", b"null", b"[850]"):
            with self.subTest(value=odd):
                before, after = self.applied(b'{"hw":{"led":{"maxpwr":' + odd + b',"fps":50}}}')
                self.assertIsNone(limit.stored(before))
                self.assertEqual(files(after)["/cfg.json"], b'{"hw":{"led":{"maxpwr":850,"fps":50}}}')


class Refusals(unittest.TestCase):
    def test_a_configuration_that_is_not_what_wled_writes_is_refused(self):
        forms = {
            "an array": b"[]",
            "not JSON": b'{"hw":{"led":',
            "not UTF-8": b'{"id":{"name":"\xff\xfe"}}',
            "hw that is a number": b'{"hw":5}',
            "hw that is null": b'{"hw":null}',
            "led that is an array": b'{"hw":{"led":[850]}}',
            "led that is a text": b'{"hw":{"led":"850"}}',
        }
        for label, content in forms.items():
            with self.subTest(form=label):
                before = support.storage_image({**support.BENCH_FILES, "/cfg.json": content})
                with self.assertRaises(Failure) as caught:
                    limit.apply(before, 850)
                self.assertEqual(caught.exception.reason, "wled-settings-malformed")
                self.assertIn("/cfg.json", caught.exception.detail)
                self.assertIsNone(limit.stored(before))

    def test_a_refusal_names_the_member_that_is_no_object(self):
        before = support.storage_image({**support.BENCH_FILES, "/cfg.json": b'{"hw":{"led":7}}'})
        with self.assertRaises(Failure) as caught:
            limit.apply(before, 850)
        self.assertIn("hw.led in /cfg.json", caught.exception.detail)

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
        with self.assertRaises(Failure) as caught:
            limit.apply(full, 0)
        self.assertEqual(caught.exception.reason, "no-space")

    def test_a_newer_disk_version_stays(self):
        before = support.storage_image(support.SAVED_FILES, version=DISK_VERSION_2_1)
        self.assertEqual(storage.geometry(limit.apply(before, 0))[0], DISK_VERSION_2_1)


if __name__ == "__main__":
    unittest.main()
