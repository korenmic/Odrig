import os
import pathlib
import unittest

from fwtool import env, paths

FOLDER_VARIABLES = ("PLATFORMIO_CORE_DIR", "PLATFORMIO_BUILD_CACHE_DIR", "npm_config_cache", "PIP_CACHE_DIR")
SWITCHES = {"PLATFORMIO_SETTING_ENABLE_TELEMETRY": "No", "npm_config_update_notifier": "false"}


class ChildEnvironment(unittest.TestCase):
    def test_each_folder_variable_is_an_absolute_path_inside_the_work_folder(self):
        made = env.child()
        for name in FOLDER_VARIABLES:
            self.assertTrue(name in made, f"{name} is not set")
            folder = pathlib.Path(made[name])
            self.assertTrue(folder.is_absolute(), f"{name} is {folder}")
            self.assertTrue(paths.inside(folder, paths.WORK) and folder != paths.WORK, f"{name} is {folder}")

    def test_the_folders_are_all_different(self):
        made = env.child()
        self.assertEqual(len({made[name] for name in FOLDER_VARIABLES}), len(FOLDER_VARIABLES))

    def test_the_two_switches_are_set(self):
        made = env.child()
        for name, value in SWITCHES.items():
            self.assertEqual(made.get(name), value, name)

    def test_the_programs_of_the_work_folder_come_first_on_the_path(self):
        made = env.child({"PATH": "/usr/bin:/bin", "HOME": "/Users/somebody"})
        self.assertEqual(made["PATH"].split(os.pathsep), [str(paths.VENV / "bin"), "/usr/bin", "/bin"])
        self.assertEqual(env.child({"HOME": "/Users/somebody"})["PATH"], str(paths.VENV / "bin"))

    def test_the_path_does_not_grow_from_one_process_to_the_next(self):
        once = env.child({"PATH": "/usr/bin:/bin"})
        self.assertEqual(env.child(once)["PATH"], once["PATH"])

    def test_home_and_everything_else_of_the_caller_stays(self):
        caller = {"PATH": "/usr/bin", "HOME": "/Users/somebody", "LANG": "en_US.UTF-8", "PIP_CACHE_DIR": "/Users/somebody/Library/Caches/pip"}
        made = env.child(caller)
        self.assertEqual(made["HOME"], "/Users/somebody")
        self.assertEqual(made["LANG"], "en_US.UTF-8")
        self.assertNotEqual(made["PIP_CACHE_DIR"], caller["PIP_CACHE_DIR"])
        self.assertEqual(caller["PATH"], "/usr/bin")
        self.assertEqual(env.child()["HOME"], os.environ["HOME"])

    def test_no_variable_names_a_folder_in_the_home_folder(self):
        home = pathlib.Path(os.environ["HOME"]).resolve()
        made = env.child({"PATH": "/usr/bin", "HOME": str(home)})
        for name in set(FOLDER_VARIABLES) | set(SWITCHES):
            value = pathlib.Path(made[name])
            if value.is_absolute():
                self.assertTrue(paths.inside(value, paths.ROOT), f"{name} is {value}")
