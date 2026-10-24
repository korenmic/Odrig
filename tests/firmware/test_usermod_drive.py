import json
import re
import unittest

from . import FIRMWARE

USERMOD = FIRMWARE / "usermod"
DRIVER = FIRMWARE / "usb_host_msc"


def text_of(path):
    return path.read_text(encoding="utf-8")


class TheDrive(unittest.TestCase):
    """The usermod's code for a USB drive, read in its sources."""

    @classmethod
    def setUpClass(cls):
        cls.drive = text_of(USERMOD / "odrig_drive.cpp")
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_nothing_is_written_to_the_drive_and_it_is_never_formatted(self):
        self.assertIn("mount.format_if_mount_failed = false;", self.drive)
        self.assertEqual(re.findall(r'fopen\([^,]+, "([^"]*)"\)', self.drive), ["rb"])
        self.assertNotRegex(self.drive, r"\b(fwrite|fputs|fprintf|unlink|rename|remove|mkdir|rmdir|f_mkfs|truncate)\(")

    def test_its_list_is_the_animation_files_of_the_folder_odrig_the_first_256_in_the_order_of_their_bytes(self):
        self.assertIn('const char FOLDER[] = "/usb/odrig";', self.drive)
        self.assertIn("const uint32_t MOST_FILES = 256;", self.drive)
        named = self.drive[self.drive.index("bool isAnimation(const char *name) {"):self.drive.index("void keepName(")]
        for expected in ("name[0] != '.'", 'strcasecmp(name + length - 5, ".odrg") == 0'):
            self.assertIn(expected, named)
        self.assertIn("strcmp(names[at - 1], name) > 0", self.drive)
        self.assertIn("entry->d_type == DT_REG", self.drive)

    def test_only_the_names_the_core_gives_the_drives_files_reach_the_drive(self):
        self.assertIn('const char PREFIX[] = "drive/";', self.drive)
        for function in ("openFile", "readPart"):
            body = self.drive[self.drive.index(f" {function}(void *"):]
            body = body[:body.index("\n}\n")]
            self.assertIn("placeOf(name)", body, function)
            self.assertRegex(body, r"files\.(open|read_at)\(ctx, name", function)

    def test_a_list_is_made_while_the_number_is_0_and_published_with_the_guard_held(self):
        plug = self.drive[self.drive.index("void plugIn(uint8_t address) {"):self.drive.index("void pullOut() {")]
        self.assertLess(plug.index("listFolder()"), plug.index("Guarded held;"))
        self.assertLess(plug.index("Guarded held;"), plug.index("number = ++plugged;"))
        pull = self.drive[self.drive.index("void pullOut() {"):self.drive.index("void driverEvent(")]
        self.assertLess(pull.index("Guarded held;"), pull.index("number = 0;"))
        self.assertLess(pull.index("number = 0;"), pull.index("msc_host_vfs_unregister"))
        for function in ("driveNumber", "driveName"):
            body = self.drive[self.drive.index(f" {function}(void *"):]
            self.assertIn("Guarded held;", body[:body.index("\n}\n")], function)

    def test_the_drive_is_started_before_the_core_and_its_functions_are_the_cores_host(self):
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertLess(setup.index("OdrigDrive::begin();"), setup.index("core = odrig_core_begin(&host);"))
        self.assertRegex(setup, r"odrig_host host = (\w+::\w+\()?OdrigDrive::withDrive\(OdrigFiles::host\(\)\)\)?;")
        for member, function in (("drive", "driveNumber"), ("drive_name", "driveName"), ("read_at", "readPart")):
            self.assertIn(f"made.{member} = {function};", self.drive)

    def test_the_drives_task_looks_for_a_computer_before_it_installs_the_usb_host(self):
        begin = self.drive[self.drive.index("void OdrigDrive::begin() {"):]
        begin = begin[:begin.index("\n}\n")]
        self.assertNotIn("usb_host_install", begin)
        self.assertIn("xTaskCreatePinnedToCore(driveEvents", begin)
        task = self.drive[self.drive.index("void driveEvents(void *) {"):]
        task = task[:task.index("\n}\n")]
        self.assertLess(task.index("computerThere()"), task.index("startHost()"))
        look = self.drive[self.drive.index("bool computerThere() {"):]
        look = look[:look.index("\n}\n")]
        self.assertIn("USB_SERIAL_JTAG.fram_num.sof_frame_index", look)
        self.assertIn("if (waitMs == 0) return false;", look)

    def test_the_wait_is_5_seconds_unless_the_settings_say_from_0_to_60(self):
        self.assertIn("const uint32_t COMPUTER_WAIT_MS = 5000;", self.drive)
        self.assertIn("const uint32_t MOST_WAIT_MS = 60000;", self.drive)
        self.assertIn('"computer_wait_s"', self.usermod)
        read = self.usermod[self.usermod.index("bool readFromConfig(JsonObject &root) override {"):]
        read = read[:read.index("\n  }\n")]
        self.assertIn("OdrigDrive::setWait(", read)
        self.assertIn("seconds <= 60", read)
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertIn("OdrigDrive::begin();", setup)
        self.assertIn('strcpy(summaryText, "computer");', self.drive)

    def test_the_driver_is_a_library_of_the_build_with_its_licence(self):
        library = json.loads(text_of(DRIVER / "library.json"))
        self.assertEqual((library["name"], library["version"]), ("usb_host_msc", "1.1.1"))
        self.assertIn("Apache License", text_of(DRIVER / "LICENCE"))
        override = text_of(FIRMWARE / "platformio_override.ini.in")
        self.assertRegex(override, r"(?m)^  usb_host_msc = symlink://@REPO@/firmware/usb_host_msc$")
        self.assertRegex(override, r"(?m)^  -I@REPO@/firmware/usb_host_msc/include$")
        self.assertEqual(sorted(path.name for path in (DRIVER / "src").iterdir()), ["diskio_usb.c", "msc_host.c", "msc_host_vfs.c", "msc_scsi_bot.c"])
