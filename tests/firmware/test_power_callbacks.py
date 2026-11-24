"""Run the production WLED callback while storage pacing cannot become idle."""
import functools
import pathlib
import subprocess
import tempfile
import unittest

from . import FIRMWARE
from .compiler import compiled


PROGRAM = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include "odrig_power.h"
int board = 1;
int *core = &board;
bool updating = false, busy = true;
unsigned commands = 0, locks = 0, delays = 0;
bool lastOn = false;
uint8_t bri = 40;
const uint8_t CALL_MODE_INIT = 0;
const size_t ODRIG_REPLY_MAX = 1024;
OdrigPower powerState;
struct WouldBlock {};
struct Locked { Locked() { ++locks; } };
struct PowerLocked { PowerLocked() {} ~PowerLocked() {} };
void delay(unsigned) { ++delays; throw WouldBlock(); }
namespace OdrigFiles {
bool holding() { return busy; }
uint64_t nowMs() { return 100; }
}
size_t odrig_core_command(int *, uint64_t, const char *line, size_t, char *, size_t) {
    ++commands; lastOn = line[1] == 'n'; return 0;
}
void syncLegs() { powerState.publish(lastOn); bri = lastOn ? 40 : 0; }
@CALLBACK@
@APPLY@
int main(int argc, char **argv) {
    if (argc != 2) return 90;
    const int mode = atoi(argv[1]);
    powerState.publish(true);
    if (mode == 2 || mode == 3 || mode == 6) powerState.explicitRequest(false);
    if (mode == 4) updating = true;
    if (mode == 5) bri = 0;
    try { manualPower(mode == 0 || mode == 6 ? CALL_MODE_INIT : 1); }
    catch (const WouldBlock &) { return 10; }
    if (commands || locks || delays) return 11;
    applyPower();
    if (commands || locks || delays) return 12;
    if (mode == 3) {
        powerState.explicitRequest(true);
        manualPower(1);
    }
    busy = false;
    applyPower();
    const bool wanted = mode == 2 || mode == 3 || mode == 5;
    if (commands != static_cast<unsigned>(wanted)) return 13;
    if (wanted && lastOn != (mode == 3)) return 14;
    applyPower();
    if (commands != static_cast<unsigned>(wanted)) return 15;
    if (mode == 6) {
        manualPower(1); applyPower();
        if (commands != 0) return 16;
    }
    return 0;
}
'''


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


@functools.lru_cache(maxsize=1)
def program():
    holder = tempfile.TemporaryDirectory(prefix='odrig-power-callback-')
    root = pathlib.Path(holder.name)
    source = (FIRMWARE / 'usermod/odrig_usermod.cpp').read_text(encoding='utf-8')
    callback = function(source, 'void manualPower(uint8_t mode) {')
    apply = function(source, 'void applyPower() {') if 'void applyPower() {' in source else 'void applyPower() {}'
    path = root / 'power.cpp'
    path.write_text(PROGRAM.replace('@CALLBACK@', callback).replace('@APPLY@', apply), encoding='utf-8', newline='\n')
    return holder, compiled([path], root / 'power', [FIRMWARE / 'usermod'])


class PowerCallbacks(unittest.TestCase):
    def run_case(self, mode):
        _, executable = program()
        run = subprocess.run([str(executable), str(mode)], capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, f'callback result {run.returncode}: 10 means storage wait blocked WLED; {run.stderr!r}')

    def test_initial_and_unchanged_callbacks_never_wait_for_busy_storage(self):
        for mode in (0, 1):
            with self.subTest(mode=mode):
                self.run_case(mode)

    def test_manual_requests_are_deferred_until_storage_is_available(self):
        for mode in (2, 5):
            with self.subTest(mode=mode):
                self.run_case(mode)

    def test_latest_explicit_request_wins_and_is_applied_once(self):
        self.run_case(3)

    def test_updates_and_initial_state_do_not_create_manual_overrides(self):
        for mode in (4, 6):
            with self.subTest(mode=mode):
                self.run_case(mode)
