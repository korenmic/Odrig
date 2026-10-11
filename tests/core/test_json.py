import random
import unittest

from odrig import errors, mapping

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


if __name__ == "__main__":
    unittest.main()
