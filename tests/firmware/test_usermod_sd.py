"""The real SPI-card backend, compiled with a card and task scheduler stand-in."""

import functools
import pathlib
import subprocess
import tempfile
import unittest

from . import FIRMWARE, ROOT


WLED = r"""
#pragma once
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
using BaseType_t = int;
using UBaseType_t = unsigned;
using TickType_t = unsigned;
struct FakeMutex { bool held = false; };
using SemaphoreHandle_t = FakeMutex *;
static FakeMutex fakeMutex;
static void (*fakeTask)(void *) = nullptr;
static unsigned fakeDelay = 0;
static const BaseType_t pdTRUE = 1;
static const unsigned portMAX_DELAY = ~0u;
static const unsigned MALLOC_CAP_SPIRAM = 1;
static const unsigned MALLOC_CAP_8BIT = 2;
static const unsigned MALLOC_CAP_DMA = 4;
struct TaskYield {};
inline SemaphoreHandle_t xSemaphoreCreateMutex() { return &fakeMutex; }
inline BaseType_t xSemaphoreTake(SemaphoreHandle_t mutex, unsigned) {
  assert(mutex && !mutex->held); mutex->held = true; return pdTRUE;
}
inline void xSemaphoreGive(SemaphoreHandle_t mutex) { assert(mutex->held); mutex->held = false; }
inline unsigned pdMS_TO_TICKS(unsigned ms) { return ms; }
inline void vTaskDelay(unsigned ticks) { fakeDelay = ticks; throw TaskYield(); }
inline void vTaskDelete(void *) {}
inline BaseType_t xTaskCreatePinnedToCore(void (*task)(void *), const char *, unsigned, void *, unsigned, void *, int) {
  fakeTask = task; return pdTRUE;
}
inline void *heap_caps_malloc(size_t size, unsigned) { return malloc(size); }
FILE *fakeOpen(const char *, const char *);
size_t fakeRead(void *, size_t, size_t, FILE *);
int fakeError(FILE *);
int fakeSeek(FILE *, long, int);
int fakeClose(FILE *);
#define fopen fakeOpen
#define fread fakeRead
#define ferror fakeError
#define fseek fakeSeek
#define fclose fakeClose
"""

SPI = r"""
#pragma once
static const int FSPI = 0;
static bool fakeSpiFailure = false;
class SPIClass {
 public:
  unsigned starts = 0;
  int clock = -1, input = -1, output = -1, select = -1;
  explicit SPIClass(int) {}
  bool begin(int sck, int miso, int mosi, int cs) {
    ++starts; clock = sck; input = miso; output = mosi; select = cs;
    return !fakeSpiFailure;
  }
};
"""

SD = r"""
#pragma once
#include <assert.h>
#include <string.h>
#include "SPI.h"
void fakeBeforeUnmount();
struct FakeSD {
  bool present = true, readable = true, mounted = false;
  unsigned mounts = 0, unmounts = 0, probes = 0, frequency = 0, maxFiles = 0;
  int select = -1;
  bool formatting = true;
  uint64_t total = 0, used = 0;
  SPIClass *bus = nullptr;
  bool begin(int cs, SPIClass &spi, unsigned hz, const char *path, unsigned count, bool format) {
    ++mounts; select = cs; bus = &spi; frequency = hz; maxFiles = count; formatting = format;
    assert(strcmp(path, ".") == 0);
    mounted = present && readable;
    return mounted;
  }
  void end() { fakeBeforeUnmount(); ++unmounts; mounted = false; }
  bool readRAW(uint8_t *buffer, unsigned sector) {
    ++probes; assert(sector == 0); memset(buffer, 0, 512); return present && readable;
  }
  int cardType() { return mounted ? 3 : 0; }
  uint64_t totalBytes() { return mounted && present ? total : 0; }
  uint64_t usedBytes() { return mounted && present ? used : 0; }
};
static FakeSD SD;
"""

PROGRAM = r"""
#include <algorithm>
#include <set>
#include <string>
#include <vector>
#include "@DRIVE@"
#undef fopen
#undef fread
#undef ferror
#undef fseek
#undef fclose

static bool failRead = false, failSeek = false, failOpen = false;
static std::set<FILE *> openFiles, failedFiles;
static unsigned fallbackOpens = 0, fallbackReads = 0, fallbackParts = 0;
static std::vector<std::string> logs;

namespace OdrigLog {
void add(const char *kind, const char *text) { logs.push_back(std::string(kind) + ": " + text); }
}

FILE *fakeOpen(const char *path, const char *mode) {
  assert(strcmp(mode, "rb") == 0);
  if (failOpen) { errno = EIO; return nullptr; }
  FILE *file = fopen(path, mode);
  if (file) openFiles.insert(file);
  return file;
}
size_t fakeRead(void *buffer, size_t width, size_t count, FILE *file) {
  assert(openFiles.count(file));
  if (failRead) { failedFiles.insert(file); errno = EIO; return 0; }
  return fread(buffer, width, count, file);
}
int fakeError(FILE *file) { return failedFiles.count(file) ? 1 : ferror(file); }
int fakeSeek(FILE *file, long at, int whence) {
  assert(openFiles.count(file));
  if (failSeek) { errno = EIO; return -1; }
  return fseek(file, at, whence);
}
int fakeClose(FILE *file) {
  assert(openFiles.erase(file) == 1); failedFiles.erase(file); return fclose(file);
}
void fakeBeforeUnmount() { assert(openFiles.empty()); assert(played == nullptr && second == nullptr); }

int fallbackOpen(void *, const char *) { ++fallbackOpens; return 1; }
int32_t fallbackRead(void *, uint8_t *bytes, size_t room) {
  ++fallbackReads; if (room) bytes[0] = 42; return room ? 1 : 0;
}
void fallbackClose(void *) {}
int32_t fallbackPart(void *, const char *, uint32_t, uint8_t *bytes, size_t room) {
  ++fallbackParts; if (room) bytes[0] = 24; return room ? 1 : 0;
}

odrig_host started() {
  odrig_host host = {};
  host.open = fallbackOpen; host.read = fallbackRead; host.close = fallbackClose; host.read_at = fallbackPart;
  OdrigDrive::begin();
  host = OdrigDrive::withDrive(host);
  if (fakeTask) {
    try { fakeTask(nullptr); } catch (TaskYield &) {}
    assert(!fakeMutex.held);
  }
  return host;
}

std::string named(const odrig_host &host, uint32_t generation, unsigned at) {
  char text[256];
  if (!host.drive_name(nullptr, generation, at, text, sizeof text)) return "";
  return text;
}

void cleanup(const odrig_host &host) {
  host.close(nullptr);
  closeSecond();
  free(names); free(playedBuffer); free(secondBuffer);
  assert(openFiles.empty()); assert(!fakeMutex.held);
}

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string mode(argv[1]);
  if (mode == "pins") {
    assert(OdrigSdConfig::pinsValid(39, 40, 41, 42));
    assert(OdrigSdConfig::pinsValid(42, 41, 40, 39));
    for (int pin = -1; pin <= 60; ++pin) {
      if (pin >= 39 && pin <= 42) continue;
      assert(!OdrigSdConfig::pinsValid(pin, 40, 41, 42));
      assert(!OdrigSdConfig::pinsValid(39, pin, 41, 42));
      assert(!OdrigSdConfig::pinsValid(39, 40, pin, 42));
      assert(!OdrigSdConfig::pinsValid(39, 40, 41, pin));
    }
    assert(!OdrigSdConfig::pinsValid(39, 39, 41, 42));
    assert(!OdrigSdConfig::pinsValid(39, 40, 40, 42));
    assert(!OdrigSdConfig::pinsValid(39, 40, 41, 39));
    puts("ok"); return 0;
  }
  if (mode == "absent") SD.present = false;
  if (mode == "filesystem") SD.readable = false;
  if (mode == "spi-failure") fakeSpiFailure = true;
  odrig_host host = started();
  if (mode == "spi-failure") {
    assert(fakeTask != nullptr && SD.mounts == 0);
    assert(strstr(OdrigDrive::summary(), "no SD reader"));
    assert(host.drive(nullptr) == 0);
    cleanup(host); puts("ok"); return 0;
  }
  if (mode == "disabled") {
    assert(fakeTask == nullptr); assert(SD.mounts == 0); assert(host.drive == nullptr);
    assert(host.drive_space == nullptr);
    assert(strstr(OdrigDrive::summary(), "configured"));
    assert(host.open(nullptr, "mapping.json") == 1); assert(fallbackOpens == 1);
    puts("ok"); return 0;
  }
  assert(host.drive && host.drive_name && host.drive_space);
  assert(SD.bus && SD.bus->starts == 1);
  assert(SD.bus->clock == ODRIG_SD_SCK && SD.bus->input == ODRIG_SD_MISO);
  assert(SD.bus->output == ODRIG_SD_MOSI && SD.select == ODRIG_SD_CS);
  assert(SD.frequency == ODRIG_SD_FREQUENCY && SD.maxFiles >= 3 && !SD.formatting);
  assert(fakeDelay >= 100);
  if (mode == "absent" || mode == "filesystem") {
    assert(host.drive(nullptr) == 0);
    uint8_t byte;
    assert(host.open(nullptr, "mapping.json") == 1);
    assert(host.read(nullptr, &byte, 1) == 1 && byte == 42);
    assert(host.read_at(nullptr, "show.json", 0, &byte, 1) == 1 && byte == 24);
    SD.present = true; SD.readable = true; sdStep();
    assert(host.drive(nullptr) != 0);
    cleanup(host); puts("ok"); return 0;
  }
  const uint32_t generation = host.drive(nullptr);
  assert(generation != 0);
  if (mode == "names") {
    assert(named(host, generation, 0) == "A.ODRG");
    assert(named(host, generation, 1) == "D.ODRGX");
    assert(named(host, generation, 2) == "b.odrg");
    assert(named(host, generation, 3) == "c.odrgx");
    assert(named(host, generation, 4).empty());
    assert(named(host, generation + 1, 0).empty());
    assert(host.drive_name(nullptr, generation, 0, nullptr, 0) == 0);
    assert(host.open(nullptr, "drive/../b.odrg") == 0);
    uint8_t byte;
    assert(host.read_at(nullptr, "drive/256", 0, &byte, 1) == -1);
  } else if (mode == "limit") {
    for (unsigned at = 0; at < 256; ++at) {
      char expected[32]; snprintf(expected, sizeof expected, "q%03u.odrg", at);
      assert(named(host, generation, at) == expected);
    }
    assert(named(host, generation, 256).empty());
  } else if (mode == "empty") {
    assert(named(host, generation, 0).empty());
    assert(strstr(OdrigDrive::summary(), "0"));
  } else if (mode == "space") {
    uint64_t freeBytes = 1, totalBytes = 1;
    SD.total = 31914983424ull; SD.used = 16475328ull;
    assert(host.drive_space(nullptr, generation, &freeBytes, &totalBytes) == 1);
    assert(totalBytes == 31914983424ull && freeBytes == 31914983424ull - 16475328ull);
    assert(host.drive_space(nullptr, generation + 1, &freeBytes, &totalBytes) == -1);
    assert(host.drive_space(nullptr, 0, &freeBytes, &totalBytes) == -1);
    SD.total = 0;
    assert(host.drive_space(nullptr, generation, &freeBytes, &totalBytes) == -1);
    SD.total = 31914983424ull; SD.used = SD.total + 1;
    assert(host.drive_space(nullptr, generation, &freeBytes, &totalBytes) == -1);
    SD.used = 16475328ull; SD.present = false; sdStep();
    assert(host.drive(nullptr) == 0 && SD.unmounts == 1);
    assert(host.drive_space(nullptr, generation, &freeBytes, &totalBytes) == -1);
    assert(SD.mounts == 1);
  } else {
    assert(host.open(nullptr, "drive/0") == 1);
    uint8_t bytes[17];
    assert(host.read(nullptr, bytes, sizeof bytes) == 17 && bytes[0] == 'A');
    assert(host.read_at(nullptr, "drive/1", 2, bytes, 3) == 3 && memcmp(bytes, "cde", 3) == 0);
    assert(host.read(nullptr, bytes, sizeof bytes) == 17 && bytes[0] == 'A');
    assert(host.read_at(nullptr, "drive/1", 0, bytes, 3) == 3 && memcmp(bytes, "abc", 3) == 0);
    if (mode == "reads") {
      assert(host.read_at(nullptr, "drive/1", 6, bytes, 3) == 0);
      assert(host.open(nullptr, "mapping.json") == 1);
      assert(host.read(nullptr, bytes, 1) == 1 && bytes[0] == 42);
      assert(host.read_at(nullptr, "show.json", 0, bytes, 1) == 1 && bytes[0] == 24);
      assert(fallbackOpens == 1 && fallbackReads == 1 && fallbackParts == 1);
    } else {
      if (mode == "remove") SD.present = false;
      else if (mode == "read-error") {
        failRead = true;
        assert(host.read(nullptr, bytes, sizeof bytes) == -1);
        assert(SD.unmounts == 0);
      } else if (mode == "seek-error") {
        failSeek = true;
        assert(host.read_at(nullptr, "drive/1", 0, bytes, 1) == -1);
        assert(SD.unmounts == 0);
      } else if (mode == "open-error") {
        failOpen = true;
        assert(host.open(nullptr, "drive/0") == -1);
        assert(SD.unmounts == 0);
      } else assert(false);
      sdStep();
      assert(host.drive(nullptr) == 0 && SD.unmounts == 1);
      assert(named(host, generation, 0).empty());
      if (mode == "remove") assert(SD.probes >= 1);
      failRead = failSeek = failOpen = false;
      SD.present = true; sdStep();
      assert(host.drive(nullptr) != 0 && host.drive(nullptr) != generation);
      assert(host.open(nullptr, "drive/0") == 1);
      assert(host.read(nullptr, bytes, 1) == 1 && bytes[0] == 'A');
    }
  }
  cleanup(host); puts("ok"); return 0;
}
"""


class SpiCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.work = pathlib.Path(cls.folder.name)
        for name, content in (("wled.h", WLED), ("SPI.h", SPI), ("SD.h", SD)):
            (cls.work / name).write_text(content, encoding="utf-8")
        drive = FIRMWARE / "usermod" / "odrig_drive.cpp"
        (cls.work / "main.cpp").write_text(PROGRAM.replace("@DRIVE@", str(drive)), encoding="utf-8")

    @classmethod
    @functools.lru_cache(maxsize=None)
    def built(cls, pins=(39, 40, 41, 42), frequency=4000000):
        binary = cls.work / f"card-{'-'.join(map(str, pins))}-{frequency}"
        flags = ["-DODRIG_DRIVE_SD_SPI", '-DODRIG_SD_MOUNT_PATH="."']
        for name, value in zip(("SCK", "MISO", "MOSI", "CS"), pins):
            flags.append(f"-DODRIG_SD_{name}={value}")
        flags.append(f"-DODRIG_SD_FREQUENCY={frequency}")
        done = subprocess.run(
            ["c++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
             "-fno-sanitize-recover=all", *flags, f"-I{cls.work}", f"-I{ROOT / 'core' / 'include'}",
             str(cls.work / "main.cpp"), "-o", str(binary)], capture_output=True, text=True,
        )
        if done.returncode:
            raise AssertionError(f"the SD backend does not compile:\n{done.stderr}")
        return binary

    def case(self, name, files=None, pins=(39, 40, 41, 42), frequency=4000000, folder=True):
        with tempfile.TemporaryDirectory() as trial:
            root = pathlib.Path(trial)
            if folder:
                (root / "odrig").mkdir()
            given = {"A.ODRG": b"A" * 8192, "b.odrg": b"abcdef"} if files is None else files
            for path, content in given.items():
                target = root / "odrig" / path
                if content is None:
                    target.mkdir()
                else:
                    target.write_bytes(content)
            done = subprocess.run([str(self.built(pins, frequency)), name], cwd=trial, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), "ok")

    def test_unconfigured_or_unsafe_pins_never_start_a_task_or_touch_spi(self):
        for pins in ((-1, -1, -1, -1), (1, 40, 41, 42), (39, 39, 41, 42)):
            with self.subTest(pins=pins):
                self.case("disabled", pins=pins)

    def test_invalid_spi_frequencies_do_not_initialize_gpio(self):
        for frequency in (0, 399999, 20000001):
            with self.subTest(frequency=frequency):
                self.case("disabled", frequency=frequency)

    def test_all_reserved_gpio_are_rejected_and_every_pin_must_be_distinct(self):
        self.case("pins")

    def test_failed_custom_spi_setup_never_lets_sd_retry_with_default_pins(self):
        self.case("spi-failure")

    def test_absent_or_unmountable_card_keeps_internal_files_and_can_be_retried(self):
        self.case("absent")
        self.case("filesystem")

    def test_names_are_filtered_sorted_and_do_not_allow_traversal(self):
        self.case("names", {"b.odrg": b"b", "A.ODRG": b"a", "c.odrgx": b"c", "D.ODRGX": b"d", ".hidden.odrgx": b"h", "e.odrgx.txt": b"x",
                            "other.txt": b"x", "nested.odrg": None})

    def test_only_the_first_256_names_are_published(self):
        self.case("limit", {f"q{at:03}.odrg": b"x" for at in reversed(range(300))})

    def test_missing_or_empty_animation_folder_is_safe(self):
        self.case("empty", {})
        self.case("empty", {}, folder=False)

    def test_playback_and_validation_read_independently_and_internal_files_still_work(self):
        self.case("reads")

    def test_actual_card_read_detects_removal_and_reinsertion_gets_a_new_generation(self):
        self.case("remove")

    def test_io_errors_are_unmounted_only_after_both_files_are_closed_and_can_recover(self):
        for mode in ("read-error", "seek-error", "open-error"):
            with self.subTest(mode=mode):
                self.case(mode)

    def test_free_and_total_space_come_from_the_mounted_card_and_its_current_number_only(self):
        self.case("space")
