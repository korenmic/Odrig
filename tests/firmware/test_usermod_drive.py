import json
import re
import unittest

from . import FIRMWARE

USERMOD = FIRMWARE / "usermod"
DRIVER = FIRMWARE / "usb_host_msc"


def text_of(path):
    return path.read_text(encoding="utf-8")


def builds(text, sd):
    """The lines of the drive's source that one backend compiles: the card's with
    ODRIG_DRIVE_SD_SPI, the stick's without it. Other conditions are kept as they are."""
    kept, stack = [], []
    for line in text.splitlines():
        stripped = line.strip()
        chosen = re.fullmatch(r"#(ifdef|ifndef)\s+ODRIG_DRIVE_SD_SPI", stripped)
        if chosen:
            stack.append(("sd", (chosen.group(1) == "ifdef") == sd))
            continue
        if stripped.startswith("#if"):
            stack.append(("other", True))
        elif stripped.startswith("#else") and stack and stack[-1][0] == "sd":
            stack[-1] = ("sd", not stack[-1][1])
            continue
        elif stripped.startswith("#endif"):
            if stack.pop()[0] == "sd":
                continue
        if all(taking for _, taking in stack):
            kept.append(line)
    return "\n".join(kept) + "\n"


def function_body(text, name):
    """The definition of a function, from its first line to the end of its block."""
    found = re.search(rf"(?m)^[\w:*& ]+[ *&]{name}\(", text)
    rest = text[found.start():]
    return rest[:rest.index("\n}\n")]


class TheDrive(unittest.TestCase):
    """The usermod's code for a USB drive, read in its sources."""

    @classmethod
    def setUpClass(cls):
        cls.drive = text_of(USERMOD / "odrig_drive.cpp")
        cls.usermod = text_of(USERMOD / "odrig_usermod.cpp")

    def test_the_stick_is_never_written_and_never_formatted(self):
        stick = builds(self.drive, sd=False)
        self.assertIn("mount.format_if_mount_failed = false;", stick)
        self.assertEqual(re.findall(r'fopen\([^,]+, "([^"]*)"\)', stick), ["rb"])
        self.assertNotRegex(stick, r"(?<![\w.])(fwrite|fputs|fprintf|fsync|unlink|rename|remove|mkdir|rmdir|f_mkfs|truncate)\(")
        self.assertIn("int driveWritable(void *, uint32_t) { return 0; }", stick)

    def test_the_card_is_never_formatted_and_is_changed_only_by_the_names_the_core_gives_in_its_folder(self):
        card = builds(self.drive, sd=True)
        self.assertIn("SD.begin(ODRIG_SD_CS, cardBus, ODRIG_SD_FREQUENCY, MOUNT, 3, false)", card)
        self.assertEqual(sorted(re.findall(r'fopen\([^,]+, "([^"]*)"\)', card)), ["rb", "wb"])
        self.assertNotRegex(card, r"(?<![\w.])(fputs|fprintf|mkdir|rmdir|f_mkfs|truncate)\(")
        for function in ("beginDriveFile", "renameDriveFile", "removeDriveFile"):
            self.assertIn("changedPath(", function_body(card, function), function)
        self.assertIn("return cardMounted && !cardFailed && cardFolder && !namesAPlace(name) && drivePath(name, path);", function_body(card, "changedPath"))
        made = function_body(card, "drivePath")
        self.assertIn("if (namesAPlace(name)) return pathAt(placeOf(name), path);", made)
        self.assertIn("if (number == 0 || !isDriveName(given)) return false;", made)
        named = function_body(card, "isDriveName")
        for expected in ("length > LONGEST_DRIVE_NAME", "name[0] == '.'", 'strchr("\\\\:*?\\"<>|", c)', "c < 0x20 || c > 0x7e", "++folders > DEEPEST",
                         "atStart && c == '.'"):
            self.assertIn(expected, named)
        self.assertIn("const uint32_t DEEPEST = 3;", self.drive)
        self.assertIn("const uint32_t MOST_FOLDERS = 32;", self.drive)
        self.assertIn("const size_t LONGEST_DRIVE_NAME = 100;", self.drive)

    def test_a_rename_on_the_card_removes_the_file_that_has_the_new_name_only_once_the_old_one_is_there(self):
        renamed = function_body(builds(self.drive, sd=True), "renameDriveFile")
        steps = [renamed.index(step) for step in ("stat(pathFrom, &found) != 0", "unlink(pathTo)", "rename(pathFrom, pathTo)")]
        self.assertEqual(steps, sorted(steps))

    def test_every_change_of_the_card_is_timed_as_the_storage_calls_are(self):
        card = builds(self.drive, sd=True)
        for function in ("dropDriveFile", "beginDriveFile", "addDriveBytes", "endDriveFile", "renameDriveFile", "removeDriveFile"):
            body = function_body(card, function)
            first = [line.strip() for line in body.splitlines()[1:] if line.strip()][0]
            self.assertEqual(first, "OdrigFiles::StorageCall call;", function)

    def test_its_list_is_the_animation_files_of_the_folder_odrig_the_first_256_in_the_order_of_their_bytes(self):
        self.assertIn('const char FOLDER[] = "/usb/odrig";', self.drive)
        self.assertIn("const uint32_t MOST_FILES = 256;", self.drive)
        named = self.drive[self.drive.index("bool isAnimation(const char *name) {"):self.drive.index("bool keepName(")]
        for expected in ("name[0] == '.'", 'strcasecmp(name + length - 5, ".odrg") == 0', 'strcasecmp(name + length - 6, ".odrgx") == 0'):
            self.assertIn(expected, named)
        self.assertIn("strcmp(names[at - 1], name) > 0", self.drive)
        self.assertIn("entry->d_type == DT_REG", self.drive)
        self.assertIn("entry->d_type == DT_DIR", self.drive)
        self.assertIn("depth >= DEEPEST || !isFolderName(entry->d_name)", self.drive)

    def test_only_the_names_the_core_gives_the_drives_files_reach_the_drive(self):
        self.assertIn('const char PREFIX[] = "drive/";', self.drive)
        for function in ("openFile", "readPart"):
            body = self.drive[self.drive.index(f" {function}(void *"):]
            body = body[:body.index("\n}\n")]
            self.assertIn("placeOf(name)", body, function)
            self.assertRegex(body, r"files\.(open|read_at)\(ctx, name", function)
        for function, member in (("beginFile", "write_open"), ("renameFile", "rename"), ("removeFile", "remove")):
            body = self.drive[self.drive.index(f" {function}(void *"):]
            body = body[:body.index("\n}\n")]
            self.assertIn("placeOf(", body, function)
            self.assertIn(f"files.{member}(ctx, ", body, function)

    def test_a_list_is_made_only_when_the_core_asks_and_with_the_guard_held(self):
        for start, end in (("void plugIn(uint8_t address) {", "void pullOut() {"), ("void mountCard() {", "// One worker pass.")):
            mounted = self.drive[self.drive.index(start):self.drive.index(end)]
            self.assertNotIn("listFolder()", mounted, start)
            self.assertLess(mounted.index("Guarded held;"), mounted.index("listed = 0;"), start)
        listing = function_body(self.drive, "driveList")
        self.assertIn("if (drive == 0 || drive != number) return -1;", listing)
        self.assertLess(listing.index("Guarded held;"), listing.index("listFolder()"))
        self.assertEqual(self.drive.count("listFolder()"), 2)
        plug = self.drive[self.drive.index("void plugIn(uint8_t address) {"):self.drive.index("void pullOut() {")]
        self.assertLess(plug.index("Guarded held;"), plug.index("number = ++plugged;"))
        pull = self.drive[self.drive.index("void pullOut() {"):self.drive.index("void driverEvent(")]
        self.assertLess(pull.index("Guarded held;"), pull.index("number = 0;"))
        self.assertLess(pull.index("number = 0;"), pull.index("msc_host_vfs_unregister"))
        for function in ("driveNumber", "driveName", "driveList", "driveBind"):
            body = self.drive[self.drive.index(f" {function}(void *"):]
            self.assertIn("Guarded held;", body[:body.index("\n}\n")], function)

    def test_the_drive_is_started_before_the_core_and_its_functions_are_the_cores_host(self):
        setup = self.usermod[self.usermod.index("void setup() override {"):self.usermod.index("void loop() override {")]
        self.assertLess(setup.index("OdrigDrive::begin();"), setup.index("core = odrig_core_begin(&host);"))
        self.assertRegex(setup, r"odrig_host host = (\w+::\w+\()?OdrigDrive::withDrive\(OdrigFiles::host\(\)\)\)?;")
        for member, function in (("drive", "driveNumber"), ("drive_name", "driveName"), ("read_at", "readPart"), ("drive_list", "driveList"),
                                 ("drive_bind", "driveBind"), ("drive_writable", "driveWritable"), ("write_open", "beginFile"), ("write", "addBytes"),
                                 ("write_close", "endFile"), ("rename", "renameFile"), ("remove", "removeFile")):
            self.assertIn(f"made.{member} = {function};", self.drive)
        self.assertIn("if (given.write_open != nullptr) {", self.drive)

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
