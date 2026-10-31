import struct
import pathlib
import tempfile
import unittest

from odrig import errors, odrgx
from . import support
from .test_pictures import converter_pictures


def message_file(messages=(('hello', 0),), tab=1):
    texts = [text.encode('utf-8') for text, _ in messages]
    text_size = sum(map(len, texts))
    mask_at = 24 + 12 * len(messages) + text_size
    glyph_at = mask_at + 900 * len(messages)
    size = glyph_at + 3968
    loop = sum(2000 if flags & 1 else 6100 for _, flags in messages)
    data = bytearray(struct.pack('<BBBBIHHIII', 6, 1, tab, len(messages), loop,
        text_size, 0, mask_at, glyph_at, size))
    offset = 0
    for text, (_, flags) in zip(texts, messages):
        data += struct.pack('<IBBHHH', 2000 if flags & 1 else 6100, flags, 0, offset, len(text), 0)
        offset += len(text)
    data += b''.join(texts)
    for _ in messages:
        mask = bytearray(900)
        pixel = 15 * 60 + 5
        mask[pixel // 2] = 15 if pixel & 1 else 240
        data += mask
    data += bytes(3968)
    return odrgx.wrap(3, 60, 60, loop, data)


class MessageClock(unittest.TestCase):
    def test_delivered_message_assets_match_converter_at_each_caption_and_loop(self):
        from odrig import messageclock
        folder = support.ROOT / 'collection/card/clocks/message'
        paths = sorted(folder.glob('v7-*.odrgx'))
        self.assertEqual(len(paths), 7)
        for path in paths:
            data = path.read_bytes()
            decoded = messageclock.decode(data)
            times, at = [0, 300, 600, 2000, 2250, 2500], 0
            for message in decoded['messages']:
                times.extend([at, at + 700, at + message['duration'] - 1])
                if message['flags'] & 4:
                    times.extend([at + 3499, at + 3500, at + 5000])
                at += message['duration']
            times.extend([at, at + 700])
            for seed in (12345, 0xffffffff):
                with self.subTest(path=path.name, seed=seed):
                    pictures = support.rendered(data, times, seed)
                    self.assertEqual(pictures, converter_pictures(path, times, seed))
                    self.assertEqual(pictures[0], pictures[-2])

    def test_valid_message_clock_is_accepted_by_the_shared_decoder(self):
        decoded, = support.decode_each([message_file()])
        self.assertIsNone(decoded.reason)

    def test_payload_can_be_read_by_the_python_library(self):
        from odrig import messageclock
        decoded = messageclock.decode(message_file())
        self.assertEqual(decoded['messages'][0]['text'], 'hello')
        self.assertEqual(decoded['loopMs'], 6100)

    def test_largest_legal_payload_and_caption_capacity_fit_the_existing_window(self):
        from odrig import messageclock
        messages = [('x' * (171 if i < 16 else 170), 0) for i in range(24)]
        data = message_file(messages)
        self.assertEqual(len(data) - 20, 29976)
        self.assertIsNone(support.decode_each([data])[0].reason)
        self.assertEqual(len(messageclock.decode(data)['messages']), 24)
        for messages in ([('x', 0)] * 25, [('x' * 257, 0)], [('x' * 256, 0)] * 17):
            bad = message_file(messages)
            self.assertEqual(support.decode_each([bad])[0].reason, 'bad-settings')
            with self.assertRaises(errors.Rejection): messageclock.decode(bad)

    def test_malformed_payloads_have_the_same_strict_python_and_core_rejections(self):
        from odrig import messageclock
        good = message_file()
        cases = []
        for at, value, reason in [(21, 2, 'bad-settings'), (22, 0, 'bad-settings'),
                (23, 25, 'bad-settings'), (30, 1, 'bad-settings'), (32, 0, 'bad-settings'),
                (40, 0, 'payload-size'), (48, 32, 'bad-settings'), (49, 1, 'bad-settings'),
                (50, 1, 'bad-settings'), (54, 1, 'bad-settings'), (56, 255, 'bad-text'),
                (56, 0, 'bad-text'), (56, 127, 'bad-text')]:
            data = bytearray(good); data[at] = value
            cases.append((bytes(data), reason))
        for text in (b'\xed\xa0\x80', b'\xf4\x90\x80\x80', b'\xc0\xaf'):
            data = bytearray(good); data[56:56 + len(text)] = text
            cases.append((bytes(data), 'bad-text'))
        for end in (20, 23, 43, 45, 55, 56, 61, 961, len(good) - 1):
            cases.append((good[:end], 'truncated'))
        cases.append((good + b'\x00', 'trailing-bytes'))
        loop = bytearray(good); loop[12] ^= 1
        cases.append((bytes(loop), 'loop-mismatch'))
        results = support.decode_each([data for data, _ in cases])
        for (data, reason), result in zip(cases, results):
            with self.subTest(reason=reason, bytes=len(data)):
                self.assertEqual(result.reason, reason)
                with self.assertRaises(errors.Rejection) as caught:
                    messageclock.decode(data)
                self.assertEqual(caught.exception.reason, reason)

    def test_all_sequence_roles_match_converter_pixels_and_restart_at_complete_loop(self):
        roles = [[0, 0, 0, 4, 0, 0], [0] * 4, [0] * 6, [0] * 6,
            [1] * 11 + [2] * 3 + [0] * 6, [0, 0, 16, 8], [0] * 9]
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory, 'message.odrgx')
            for tab, flags in enumerate(roles, 1):
                data = bytearray(message_file([(str(i), f) for i, f in enumerate(flags)], tab))
                masks = struct.unpack_from('<I', data, 32)[0] + 20
                glyphs = struct.unpack_from('<I', data, 36)[0] + 20
                for i in range(masks, glyphs): data[i] = (i * 37 + tab * 19) & 255
                for i in range(glyphs, len(data)): data[i] = (i * 17 + tab * 11) & 255
                path.write_bytes(data)
                loop = struct.unpack_from('<I', data, 12)[0]
                times = [0, 1, 300, 599, 600, 1999, 2000, 2001, 2250, 2499, 2500,
                    3499, 3500, 3501, 5599, 5600, 6099, 6100, 12200, 18300,
                    18301, 19999, 20000, 21799, 21800, 21801,
                    loop - 1, loop, loop + 1, 4294967296 + 123]
                for seed in (1, 0xffffffff):
                    with self.subTest(tab=tab, seed=seed):
                        rendered = support.rendered(bytes(data), times, seed)
                        self.assertEqual(rendered, converter_pictures(path, times, seed))
                        self.assertEqual(rendered[0], rendered[-3])
