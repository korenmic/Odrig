"""The files of a mirror: a key's local file among what was fetched before and in the
collections, the share named by `env`, and the fetch of a file found nowhere."""

import base64
import binascii
import pathlib
import tempfile
import threading
import unittest

from emulator.mirror import files

from . import support

FRAMES = b"ODRG" + bytes(60)
TEXT = b"ODRX\x01\x02\x01\x00" + bytes(40)


def key_of(data):
    return f"{binascii.crc32(data):08x}-{len(data)}"


class TheFilesOfKeys(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))
        (self.root / "collection" / "card").mkdir(parents=True)

    def test_a_file_of_the_collection_whose_size_and_crc_are_the_keys_is_found_with_its_type(self):
        (self.root / "collection" / "card" / "a.odrg").write_bytes(FRAMES)
        (self.root / "collection" / "card" / "b.odrgx").write_bytes(TEXT)
        found = files.Files(self.root)
        self.assertIsNone(found.known(key_of(FRAMES)))
        self.assertEqual(found.find(key_of(FRAMES)), (self.root / "collection" / "card" / "a.odrg", 1))
        self.assertEqual(found.known(key_of(FRAMES)), (self.root / "collection" / "card" / "a.odrg", 1))
        self.assertEqual(found.find(key_of(TEXT)), (self.root / "collection" / "card" / "b.odrgx", 2))

    def test_a_file_of_the_same_size_and_another_crc_is_not_it(self):
        other = bytearray(FRAMES)
        other[-1] = 1
        (self.root / "collection" / "card" / "a.odrg").write_bytes(bytes(other))
        self.assertIsNone(files.Files(self.root).find(key_of(FRAMES)))

    def test_the_share_that_env_names_is_looked_in_too(self):
        share = self.root / "share"
        share.mkdir()
        (share / "c.odrg").write_bytes(FRAMES)
        (self.root / "env").write_text(f"OTHER=1\nODRIG_ANIMATIONS={share}\n", encoding="utf-8")
        self.assertEqual(files.Files(self.root).find(key_of(FRAMES)), (share / "c.odrg", 1))

    def test_what_was_kept_is_found_first_and_kept_whole_under_its_key(self):
        found = files.Files(self.root)
        path = found.keep(key_of(FRAMES), FRAMES)
        self.assertEqual(path, self.root / files.KEPT / f"{key_of(FRAMES)}.odrg")
        self.assertEqual(path.read_bytes(), FRAMES)
        self.assertEqual(list((self.root / files.KEPT).iterdir()), [path])
        self.assertEqual(files.Files(self.root).find(key_of(FRAMES)), (path, 1))

    def test_what_is_no_key_finds_nothing(self):
        found = files.Files(self.root)
        for key in (None, "", "12345678", "1234567-5", "zz345678-5", "12345678-x"):
            self.assertIsNone(found.find(key), key)


class Board:
    """Stands in for the man in the middle before a board: answers `read` from a file."""

    def __init__(self, data, refuse=False):
        self.data = data
        self.refuse = refuse
        self.asked = []

    def ask(self, line, seconds=30):
        self.asked.append(line)
        if self.refuse:
            return b'{"ok":false,"error":"busy"}\n'
        words = line.split(b" ")
        offset, count = int(words[2]), int(words[3])
        piece = self.data[offset:offset + count]
        return b'{"ok":true,"bytes":%d,"data":"%s"}\n' % (len(self.data), base64.urlsafe_b64encode(piece).rstrip(b"="))


class TheFetch(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(support.entered(self, tempfile.TemporaryDirectory()))

    def fetched(self, board, key):
        found = files.Files(self.root)
        fetcher = files.Fetcher(board, found)
        fetcher.start()
        self.addCleanup(fetcher.stop)
        fetcher.want(7, key)
        done = threading.Event()
        for _ in range(200):
            if found.known(key) is not None:
                break
            done.wait(0.02)
        return found

    def test_a_file_found_nowhere_is_read_720_bytes_at_a_time_checked_and_kept(self):
        data = FRAMES + bytes(range(256)) * 8
        board = Board(data)
        found = self.fetched(board, key_of(data))
        self.assertEqual(found.known(key_of(data)), (self.root / files.KEPT / f"{key_of(data)}.odrg", 1))
        self.assertEqual(board.asked, [b"read 7 0 720", b"read 7 720 720", b"read 7 1440 720"])
        self.assertEqual((self.root / files.KEPT / f"{key_of(data)}.odrg").read_bytes(), data)

    def test_a_file_whose_bytes_are_not_the_keys_is_not_kept(self):
        data = FRAMES * 3
        board = Board(data[:-1] + b"\x01")
        found = self.fetched(board, key_of(data))
        self.assertIsNone(found.known(key_of(data)))
        self.assertFalse((self.root / files.KEPT / f"{key_of(data)}.odrg").exists())

    def test_a_refused_read_ends_the_fetch(self):
        board = Board(FRAMES, refuse=True)
        found = self.fetched(board, key_of(FRAMES))
        self.assertIsNone(found.known(key_of(FRAMES)))
        self.assertEqual(board.asked, [b"read 7 0 720"])


if __name__ == "__main__":
    unittest.main()
