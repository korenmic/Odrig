import functools
import json
import pathlib
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT

USERMOD = FIRMWARE / "usermod"
PROGRAM = ROOT / "tests" / "firmware" / "kept" / "kept.cpp"
FLAGS = ("-std=c++11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-g")

_folder = tempfile.TemporaryDirectory()


@functools.lru_cache(maxsize=None)
def built():
    program = pathlib.Path(_folder.name, "kept")
    done = subprocess.run(["c++", *FLAGS, f"-I{USERMOD}", str(PROGRAM), "-o", str(program)], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"the program of the kept record does not compile:\n{done.stderr}")
    return program


def kept(case, text=None):
    done = subprocess.run([str(built()), case, *([] if text is None else [text])], capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"kept {case}: status {done.returncode}: {done.stderr[-2000:]}")
    return json.loads(done.stdout)


class TheKeptRecord(unittest.TestCase):
    """The latest reason text the player logged, kept across a software or watchdog reset."""

    def test_a_sound_record_gives_its_text_once(self):
        text = "file dvd.odrg unavailable: truncated"
        self.assertEqual(kept("sound", text), {"first": True, "text": text, "second": False})

    def test_a_long_text_is_cut_to_95_bytes(self):
        self.assertEqual(kept("sound", "x" * 200)["text"], "x" * 95)

    def test_a_damaged_or_absent_record_gives_nothing(self):
        for case in ("mark", "crc", "length", "zero"):
            with self.subTest(case):
                self.assertEqual(kept(case, "drive file a.odrg left out: bad-code"), {"first": False, "text": "", "second": False})

    def test_the_firmware_keeps_every_line_of_the_player_and_logs_it_at_its_next_start(self):
        log = (USERMOD / "odrig_log.cpp").read_text(encoding="utf-8")
        self.assertIn("RTC_NOINIT_ATTR OdrigKept kept;", log)
        self.assertIn("OdrigKeep::put(kept, text);", log)
        self.assertIn('"before this start: "', log)
        usermod = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")
        self.assertIn("OdrigLog::retained();", usermod)
        self.assertNotRegex(log, r"OdrigKeep[^\n]*(LittleFS|SD\.|File )")


class TheAbout(unittest.TestCase):
    """The name the firmware gives itself in `status`."""

    def test_it_names_the_release_the_build_the_storage_and_the_reset(self):
        usermod = (USERMOD / "odrig_usermod.cpp").read_text(encoding="utf-8")
        self.assertIn("host.about = aboutHost;", usermod)
        for word in ('"power-on"', '"software"', '"panic"', '"task-watchdog"', '"interrupt-watchdog"', '"brownout"', '"deep-sleep"', '"other"',
                     "WLED_RELEASE_NAME", "__DATE__", "__TIME__", '"internal+microsd"', '"internal+usb"', "esp_reset_reason()"):
            self.assertIn(word, usermod, word)


if __name__ == "__main__":
    unittest.main()
