import random
import unittest

from odrig import errors, mapping, show

from . import support

MAPPING = '{"version": 1, "width": 60, "legs": [{"leg": 1, "pin": 1, "first_led": "right", "rows": [2, 1]}]}'


def with_width(text):
    return MAPPING.replace('"width": 60', f'"width": {text}')


def with_pin(text):
    return MAPPING.replace('"pin": 1', f'"pin": {text}')


def with_side(text):
    return MAPPING.replace('"right"', text)


# Texts used as mapping.json. Each is judged by the core and by the converter's reader.
MAPPING_TEXTS = {
    "the plain text": MAPPING,
    "white space of every kind": " \t\r\n" + MAPPING.replace(" ", " \n\t\r ") + "\r\n\t ",
    "no white space": MAPPING.replace(" ", ""),
    "members in another order": '{"legs": [{"rows": [2, 1], "first_led": "right", "pin": 1, "leg": 1}], "width": 60, "version": 1}',
    "a repeated member": '{"version": 1, ' + MAPPING[1:],
    "a repeated member in a leg": MAPPING.replace('"pin": 1', '"pin": 1, "pin": 1'),
    "a repeated member written with an escape": MAPPING.replace('"width": 60', '"width": 60, "\\u0077idth": 60'),
    "a byte-order mark": b"\xef\xbb\xbf" + MAPPING.encode(),
    "60.0": with_width("60.0"),
    "6e1": with_width("6e1"),
    "6E1": with_width("6E1"),
    "60e0": with_width("60e0"),
    "60.": with_width("60."),
    "-0 for a pin": with_pin("-0"),
    "-0.0 for a pin": with_pin("-0.0"),
    "-00 for a pin": with_pin("-00"),
    "-1 for a pin": with_pin("-1"),
    "a minus sign alone": with_pin("-"),
    "+1 for a pin": with_pin("+1"),
    "060": with_width("060"),
    "00": with_pin("00"),
    "0x3c": with_width("0x3c"),
    "6_0": with_width("6_0"),
    "true": with_width("true"),
    "false for a pin": with_pin("false"),
    "null": with_width("null"),
    "NaN": with_width("NaN"),
    "Infinity": with_width("Infinity"),
    "a number as text": with_width('"60"'),
    "a very long number": with_width("6" * 40),
    "a number of 5,000 digits": with_width("1" + "0" * 4999),
    "a very long zero": with_pin("0" * 40),
    "a pin of 31 digits that is 1": with_pin("0" * 30 + "1"),
    "4294967296 for a pin, which is 0 in 32 bits": with_pin("4294967296"),
    "4294967297 for a pin, which is 1 in 32 bits": with_pin("4294967297"),
    "an escaped member name": MAPPING.replace('"width"', '"\\u0077idth"'),
    "an escaped member name in capitals": MAPPING.replace('"width"', '"\\u0077\\u0069\\u0064\\u0074\\u0068"'),
    "an escaped capital in a member name": MAPPING.replace('"width"', '"\\u0057idth"'),
    "an escaped value": with_side('"r\\u0069ght"'),
    "an escaped value with capital digits": with_side('"\\u006Ceft"'),
    "an escaped slash in a value": with_side('"le\\/ft"'),
    "an escaped slash that is a whole name": MAPPING.replace('"width"', '"\\/"'),
    "an escaped line feed in a value": with_side('"left\\n"'),
    "an escaped zero in a value": with_side('"left\\u0000"'),
    "an escape that is no escape": with_side('"\\left"'),
    "an escape of three digits": with_side('"\\u006left"'),
    "an escape outside ASCII": with_side('"l\\u00e9ft"'),
    "an escaped pair of surrogates": with_side('"left\\ud83d\\ude00"'),
    "an escaped surrogate alone": with_side('"left\\ud83d"'),
    "a line feed in a string": with_side('"le\nft"'),
    "a tab in a string": with_side('"le\tft"'),
    "a letter outside ASCII in a value": with_side('"léft"'),
    "a letter outside ASCII in a name": MAPPING.replace('"width"', '"wîdth"'),
    "a no-break space between the members": MAPPING.replace(", ", ", ", 1),
    "a byte that is not UTF-8 in a string": MAPPING.encode().replace(b"right", b"r\xffght"),
    "a byte that is not UTF-8 after the text": MAPPING.encode() + b"\xff",
    "a zero byte after the text": MAPPING.encode() + b"\x00",
    "a zero byte before the text": b"\x00" + MAPPING.encode(),
    "text after the closing brace": MAPPING + "x",
    "a second value": MAPPING + "{}",
    "a second copy": MAPPING + MAPPING,
    "a comma after the closing brace": MAPPING + ",",
    "an empty file": "",
    "white space only": " \n",
    "the text cut before its last brace": MAPPING[:-1],
    "the text cut in a string": MAPPING[:30],
    "an array at the top": "[" + MAPPING + "]",
    "a number at the top": "1",
    "a string at the top": '"mapping"',
    "single quotes": MAPPING.replace('"', "'"),
    "a comma after the last member": MAPPING[:-1] + ",}",
    "a comma after the last row": MAPPING.replace("[2, 1]", "[2, 1,]"),
    "a comma before the first row": MAPPING.replace("[2, 1]", "[,2, 1]"),
    "two commas": MAPPING.replace("[2, 1]", "[2,, 1]"),
    "no comma between rows": MAPPING.replace("[2, 1]", "[2 1]"),
    "no colon": MAPPING.replace('"width": 60', '"width" 60'),
    "two colons": MAPPING.replace('"width": 60', '"width":: 60'),
    "a comment": MAPPING.replace(", ", ", /* width */ ", 1),
    "a name without quotes": MAPPING.replace('"width"', "width"),
    "an unknown member": MAPPING[:-1] + ', "name": "west"}',
    "an unknown member that holds an object": MAPPING[:-1] + ', "more": {"a": [1, {"b": null}]}}',
    "an empty member name": MAPPING[:-1] + ', "": 1}',
    "rows nested 3,000 deep": MAPPING.replace("[2, 1]", "[" * 3000 + "]" * 3000),
    "a bracket closed as a brace": MAPPING.replace("[2, 1]", "[2, 1}"),
    "a row with a fraction": MAPPING.replace("[2, 1]", "[2, 1.0]"),
    "a row with an exponent": MAPPING.replace("[2, 1]", "[2, 1e0]"),
    "a row of -0": MAPPING.replace("[2, 1]", "[2, -0]"),
    "-0 for a leg": MAPPING.replace('"leg": 1', '"leg": -0'),
}


def accepted_by_the_converter(data):
    try:
        canvas = mapping.loads(data)
    except errors.Rejection as rejection:
        if rejection.reason != "mapping-malformed":
            raise
        return None
    return tuple((leg.leg, leg.pin, canvas.width * len(leg.rows)) for leg in canvas.legs)


def as_bytes(text):
    return text if isinstance(text, bytes) else text.encode("utf-8")


class MappingTexts(unittest.TestCase):
    def judge(self, texts):
        """Checks that the core accepts exactly the texts the converter's reader accepts."""
        runs = support.start_each([{"mapping.json": text} for text in texts])
        accepted = 0
        for position, (text, run) in enumerate(zip(texts, runs)):
            expected = accepted_by_the_converter(as_bytes(text))
            what = f"text {position}: {as_bytes(text)[:300]!r}"
            if expected is None:
                self.assertEqual(run.error, "mapping-malformed", what)
                self.assertEqual(run.legs, (), what)
            else:
                self.assertNotEqual(run.error, "mapping-malformed", what)
                self.assertEqual(run.legs, expected, what)
                accepted += 1
        return accepted

    def test_the_core_accepts_exactly_the_texts_the_converter_accepts(self):
        self.assertGreaterEqual(len(MAPPING_TEXTS), 40)
        runs = support.start_each([{"mapping.json": text} for text in MAPPING_TEXTS.values()])
        verdicts = set()
        for (name, text), run in zip(MAPPING_TEXTS.items(), runs):
            with self.subTest(text=name):
                expected = accepted_by_the_converter(as_bytes(text))
                verdicts.add(expected is None)
                if expected is None:
                    self.assertEqual(run.error, "mapping-malformed")
                    self.assertEqual(run.legs, ())
                else:
                    self.assertNotEqual(run.error, "mapping-malformed")
                    self.assertEqual(run.legs, expected)
        self.assertEqual(verdicts, {True, False})

    def test_the_texts_it_must_accept_are_accepted(self):
        for name in ("the plain text", "white space of every kind", "members in another order", "-0 for a pin", "an escaped member name", "an escaped value"):
            with self.subTest(text=name):
                self.assertIsNotNone(accepted_by_the_converter(as_bytes(MAPPING_TEXTS[name])))

    def test_the_texts_it_must_refuse_are_refused(self):
        for name in ("a repeated member", "a byte-order mark", "60.0", "6e1", "060", "true", "text after the closing brace", "a very long number"):
            with self.subTest(text=name):
                self.assertIsNone(accepted_by_the_converter(as_bytes(MAPPING_TEXTS[name])))

    def test_copies_with_one_character_changed_are_judged_as_the_converter_judges_them(self):
        rng = random.Random(1)
        originals = [MAPPING, support.mapping_texts()["legs-2"], support.mapping_texts()["another-order"]]
        pieces = list('"\'{}[],:.-+eE0123456789 \n\t\\/ulrx') + ["\x00", "é", "true", "null", "1e1", "\\u0031", '"', "[]", "{}", ",,"]
        copies = []
        while len(copies) < 250:
            text = rng.choice(originals)
            at = rng.randrange(len(text) + 1)
            change = rng.randrange(4)
            if change == 0:
                copy = text[:at] + text[at + 1:]
            elif change == 1:
                copy = text[:at] + rng.choice(pieces) + text[at:]
            elif change == 2:
                copy = text[:at] + rng.choice(pieces) + text[at + 1:]
            else:
                other = rng.randrange(len(text) + 1)
                low, high = min(at, other), max(at, other)
                copy = text[:low] + text[low:high] * 2 + text[high:]
            if copy != text:
                copies.append(copy)
        accepted = self.judge(copies)
        self.assertGreater(accepted, 10)
        self.assertLess(accepted, 150)


SHOW = (
    '{"version": 1, "brightness": 128, "items": [{"id": 1, "file": "hello.odrg"}, {"id": 2, "file": "dvd.odrg"}, '
    '{"id": 3, "cycle": [1, 2], "seconds": 15}], "start": 3}'
)


def with_brightness(text):
    return SHOW.replace('"brightness": 128', f'"brightness": {text}')


def with_first_id(text):
    return SHOW.replace('{"id": 1,', f'{{"id": {text},')


def with_file(text):
    return SHOW.replace('"hello.odrg"', text)


def with_cycle(text):
    return SHOW.replace("[1, 2]", text)


def with_seconds(text):
    return SHOW.replace('"seconds": 15', f'"seconds": {text}')


def with_start(text):
    return SHOW.replace('"start": 3', f'"start": {text}')


def with_first_item(text):
    return SHOW.replace('{"id": 1, "file": "hello.odrg"}', text)


# Texts used as show.json. Each is judged by the core and by the converter's reader.
SHOW_TEXTS = {
    "the plain text": SHOW,
    "no start": SHOW.replace(', "start": 3', ""),
    "white space of every kind": "\n" + SHOW.replace(" ", "\t\r\n ") + " ",
    "members in another order": '{"start": 2, "items": [{"file": "b.odrg", "id": 1}, {"seconds": 1, "cycle": [1], "id": 2}], "brightness": 0, "version": 1}',
    "a repeated member": SHOW[:-1] + ', "start": 3}',
    "a repeated member in an item": with_first_item('{"id": 1, "file": "hello.odrg", "id": 1}'),
    "a byte-order mark": b"\xef\xbb\xbf" + SHOW.encode(),
    "text after the closing brace": SHOW + "]",
    "an empty file": "",
    "an array at the top": "[" + SHOW + "]",
    "an unknown member": SHOW[:-1] + ', "name": "west"}',
    "version 2": SHOW.replace('"version": 1', '"version": 2'),
    "version as text": SHOW.replace('"version": 1', '"version": "1"'),
    "version 1.0": SHOW.replace('"version": 1', '"version": 1.0'),
    "no version": SHOW.replace('"version": 1, ', ""),
    "no brightness": SHOW.replace('"brightness": 128, ', ""),
    "brightness 0": with_brightness("0"),
    "brightness 255": with_brightness("255"),
    "brightness 256": with_brightness("256"),
    "brightness -0": with_brightness("-0"),
    "brightness -1": with_brightness("-1"),
    "brightness 128.0": with_brightness("128.0"),
    "brightness 1e2": with_brightness("1e2"),
    "brightness 0128": with_brightness("0128"),
    "brightness as text": with_brightness('"128"'),
    "brightness true": with_brightness("true"),
    "brightness null": with_brightness("null"),
    "no items": SHOW.replace('"items"', '"item"'),
    "items is empty": '{"version": 1, "brightness": 128, "items": []}',
    "items is an object": '{"version": 1, "brightness": 128, "items": {}}',
    "an item that is a number": with_first_item("1"),
    "an item that is an array": with_first_item("[]"),
    "an item that is null": with_first_item("null"),
    "an item without id": with_first_item('{"file": "hello.odrg"}'),
    "an item with id only": with_first_item('{"id": 1}'),
    "an empty item": with_first_item("{}"),
    "an item with file and seconds": with_first_item('{"id": 1, "file": "hello.odrg", "seconds": 5}'),
    "an item with file and cycle": with_first_item('{"id": 1, "file": "hello.odrg", "cycle": [2], "seconds": 5}'),
    "an item with a member too many": with_first_item('{"id": 1, "file": "hello.odrg", "loop": true}'),
    "a cycle without seconds": SHOW.replace(', "seconds": 15', ""),
    "seconds without a cycle": SHOW.replace('"cycle": [1, 2], ', ""),
    "id 0": with_first_id("0"),
    "id -0": with_first_id("-0"),
    "id 65535": with_first_id("65535").replace("[1, 2]", "[65535, 2]"),
    "id 65536": with_first_id("65536"),
    "id as text": with_first_id('"1"'),
    "id 1.0": with_first_id("1.0"),
    "id 01": with_first_id("01"),
    "a file name in capitals": with_file('"HELLO.odrg"'),
    "an ending in capitals": with_file('"hello.ODRG"'),
    "a file name without ending": with_file('"hello"'),
    "a file name that is the ending": with_file('".odrg"'),
    "a file name of 32 characters": with_file('"' + "a" * 27 + '.odrg"'),
    "a file name of 33 characters": with_file('"' + "a" * 28 + '.odrg"'),
    "a file name of 300 characters": with_file('"' + "a" * 295 + '.odrg"'),
    "a file name with every allowed character": with_file('"az09-_..odrg"'),
    "a file name with a slash": with_file('"a/b.odrg"'),
    "a file name with a space": with_file('"a b.odrg"'),
    "a file name with a space after it": with_file('"hello.odrg "'),
    "a file name with text after the ending": with_file('"hello.odrg.bak"'),
    "a file name with a letter outside ASCII": with_file('"h\u00e9llo.odrg"'),
    "a file name with an escaped letter": with_file('"\\u0068ello.odrg"'),
    "a file name with an escaped slash": with_file('"a\\/b.odrg"'),
    "a file name with an escaped zero": with_file('"hello.odrg\\u0000"'),
    "a file name with an escaped line feed": with_file('"hello.odrg\\n"'),
    "a file name that is a number": with_file("7"),
    "a file name that is null": with_file("null"),
    "an empty file name": with_file('""'),
    "an empty cycle": with_cycle("[]"),
    "a cycle that is a number": with_cycle("1"),
    "a cycle of one entry": with_cycle("[2]"),
    "a cycle that names one item three times": with_cycle("[1, 1, 1]"),
    "a cycle entry with a fraction": with_cycle("[1.0]"),
    "a cycle entry as text": with_cycle('["1"]'),
    "a cycle entry that is true": with_cycle("[true]"),
    "a cycle entry that is an array": with_cycle("[[1]]"),
    "a cycle entry of 0": with_cycle("[1, 0]"),
    "a cycle entry of -0": with_cycle("[-0]"),
    "a cycle entry of -1": with_cycle("[2, -1, 9]"),
    "a cycle entry of 65536": with_cycle("[65536]"),
    "a cycle entry of 21 digits": with_cycle("[1, 100000000000000000000, -7]"),
    "a cycle entry of 4294967295": with_cycle("[4294967295]"),
    "a cycle entry of 4294967297, which is 1 in 32 bits": with_cycle("[4294967297]"),
    "a cycle entry no item has": with_cycle("[2, 7, 8]"),
    "a cycle that names itself": with_cycle("[3]"),
    "a cycle that names a cycle": SHOW.replace('], "start"', ', {"id": 4, "cycle": [2, 3], "seconds": 1}], "start"'),
    "seconds 0": with_seconds("0"),
    "seconds 1": with_seconds("1"),
    "seconds 65535": with_seconds("65535"),
    "seconds 65536": with_seconds("65536"),
    "seconds -0": with_seconds("-0"),
    "seconds as text": with_seconds('"15"'),
    "seconds 15.0": with_seconds("15.0"),
    "start that names an animation": with_start("2"),
    "start that no item has": with_start("9"),
    "start 0": with_start("0"),
    "start -0": with_start("-0"),
    "start -3": with_start("-3"),
    "start 3.0": with_start("3.0"),
    "start as text": with_start('"3"'),
    "start true": with_start("true"),
    "start null": with_start("null"),
    "start of 41 digits": with_start("1" + "0" * 40),
    "start of 41 digits below zero": with_start("-1" + "0" * 40),
    "an id used twice": with_first_id("2"),
    "an id used twice and an entry no item has": with_first_id("2").replace("[1, 2]", "[1, 9]"),
    "an id used three times": SHOW.replace('{"id": 2,', '{"id": 1,').replace('{"id": 3,', '{"id": 1,'),
    "an entry no item has and a cycle that names a cycle": with_cycle("[3, 9]"),
    "an entry no item has after a cycle that names a cycle": with_cycle("[3, 1]").replace('"start": 3', '"start": 8'),
}


def judged_by_the_converter(data):
    """What the core reports for a show file when no `.odrg` file is installed."""
    try:
        listed = show.loads(data)
    except errors.Rejection as rejection:
        return support.show_refusal(rejection)
    return f"file-missing {show.files(listed)[0]}"


class ShowTexts(unittest.TestCase):
    def reported(self, texts):
        mapping_text = support.mapping_texts()["legs-2"]
        runs = support.start_each([{"mapping.json": mapping_text, "show.json": text} for text in texts])
        return [run.error for run in runs]

    def test_the_core_judges_every_text_as_the_converter_judges_it(self):
        self.assertGreaterEqual(len(SHOW_TEXTS), 40)
        kinds = set()
        for (name, text), reported in zip(SHOW_TEXTS.items(), self.reported(list(SHOW_TEXTS.values()))):
            with self.subTest(text=name):
                expected = judged_by_the_converter(as_bytes(text))
                kinds.add(expected.split()[0])
                self.assertEqual(reported, expected)
        self.assertEqual(kinds, {"show-malformed", "duplicate-id", "undefined-id", "nested-cycle", "file-missing"})

    def test_the_texts_it_must_accept_are_accepted(self):
        for name in ("the plain text", "no start", "members in another order", "brightness -0", "a file name that is the ending", "a file name with an escaped letter", "seconds 65535"):
            with self.subTest(text=name):
                self.assertTrue(judged_by_the_converter(as_bytes(SHOW_TEXTS[name])).startswith("file-missing "))

    def test_the_ids_it_must_name_are_named(self):
        for name, expected in (
            ("a cycle entry of -1", "undefined-id -1"),
            ("a cycle entry of 0", "undefined-id 0"),
            ("a cycle entry of 21 digits", "undefined-id 4294967295"),
            ("a cycle entry of 4294967297, which is 1 in 32 bits", "undefined-id 4294967295"),
            ("start of 41 digits below zero", "undefined-id -4294967295"),
            ("an id used three times", "duplicate-id 1"),
            ("a cycle that names a cycle", "nested-cycle 4"),
            ("an entry no item has and a cycle that names a cycle", "undefined-id 9"),
        ):
            with self.subTest(text=name):
                self.assertEqual(judged_by_the_converter(as_bytes(SHOW_TEXTS[name])), expected)

    def test_copies_with_one_character_changed_are_judged_as_the_converter_judges_them(self):
        rng = random.Random(2)
        originals = [SHOW, SHOW_TEXTS["members in another order"], SHOW_TEXTS["a cycle that names a cycle"]]
        pieces = list('"\'{}[],:.-+eE0123456789 \n\t\\/uodrg') + ["\x00", "\u00e9", "true", "null", "1e1", "\\u0031", '"', "[]", "{}", ",,", "65536", "-"]
        copies = []
        while len(copies) < 250:
            text = rng.choice(originals)
            at = rng.randrange(len(text) + 1)
            change = rng.randrange(4)
            if change == 0:
                copy = text[:at] + text[at + 1:]
            elif change == 1:
                copy = text[:at] + rng.choice(pieces) + text[at:]
            elif change == 2:
                copy = text[:at] + rng.choice(pieces) + text[at + 1:]
            else:
                other = rng.randrange(len(text) + 1)
                low, high = min(at, other), max(at, other)
                copy = text[:low] + text[low:high] * 2 + text[high:]
            if copy != text:
                copies.append(copy)
        kinds = {}
        for position, (copy, reported) in enumerate(zip(copies, self.reported(copies))):
            expected = judged_by_the_converter(copy.encode("utf-8"))
            self.assertEqual(reported, expected, f"copy {position}: {copy!r}")
            kinds[expected.split()[0]] = kinds.get(expected.split()[0], 0) + 1
        self.assertGreater(kinds["show-malformed"], 50)
        self.assertGreater(kinds["file-missing"], 5)
        self.assertGreater(len(kinds), 3)


if __name__ == "__main__":
    unittest.main()
