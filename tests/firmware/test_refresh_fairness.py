"""The production refresh task under a continuously busy renderer and consumer."""
import functools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from . import FIRMWARE
from .compiler import compiled


PROGRAM = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
bool refreshReady = false, updating = false, outputChanging = false;
const bool pdTRUE = true;
unsigned polls = 0, waits = 0, ticks = 0, now = 0, lastIdle = 0, longest = 0;
unsigned mode = 0;
struct Finished {};
unsigned pdMS_TO_TICKS(unsigned ms) { return ms; }
void idle(unsigned duration) {
  if (now - lastIdle > longest) longest = now - lastIdle;
  ticks += duration; now += duration; lastIdle = now;
}
void vTaskDelay(unsigned duration) { idle(duration); }
unsigned ulTaskNotifyTake(bool, unsigned duration) {
  ++waits;
  if (mode == 2 || mode == 3) { idle(duration); throw Finished(); }
  refreshReady = false;
  return 1;
}
bool refreshDue() {
  if (polls == 200) throw Finished();
  ++polls;
  now += mode == 4 ? 1 : 32;
  if (now - lastIdle > longest) longest = now - lastIdle;
  refreshReady = mode == 1;
  return mode != 4;
}
@TASK@
int main(int argc, char **argv) {
  if (argc != 2) return 2;
  mode = static_cast<unsigned>(strtoul(argv[1], nullptr, 10));
  updating = mode == 2;
  outputChanging = mode == 3;
  try { requestRefreshes(nullptr); } catch (const Finished &) {}
  printf("{\"polls\":%u,\"ticks\":%u,\"waits\":%u,\"longest\":%u}\n", polls,ticks,waits,longest);
}
'''


@functools.lru_cache(maxsize=1)
def program():
    folder = tempfile.TemporaryDirectory(prefix='odrig-refresh-fairness-')
    root = Path(folder.name)
    source = (FIRMWARE/'usermod/odrig_usermod.cpp').read_text(encoding='utf-8')
    start = source.index('void requestRefreshes(void *) {')
    end = source.index('\n}\n', start) + 3
    path = root/'task.cpp'
    path.write_text(PROGRAM.replace('@TASK@',source[start:end]),encoding='utf-8',newline='\n')
    return folder, compiled([path],root/'task')


class RefreshFairness(unittest.TestCase):
    def run_case(self, mode):
        _, executable = program()
        run = subprocess.run([str(executable),str(mode)],capture_output=True,timeout=5)
        self.assertEqual(run.returncode,0,run.stderr.decode('utf-8',errors='replace'))
        return json.loads(run.stdout)

    def test_overdue_frames_with_an_immediate_consumer_leave_idle_time(self):
        state = self.run_case(0)
        self.assertEqual(state['polls'],200)
        self.assertLess(state['longest'],5000,state)
        self.assertGreaterEqual(state['ticks'],state['polls'])

    def test_already_queued_notifications_cannot_replace_a_blocking_tick(self):
        state = self.run_case(1)
        self.assertEqual(state['polls'],200)
        self.assertGreater(state['waits'],0)
        self.assertLess(state['longest'],5000,state)
        self.assertGreaterEqual(state['ticks'],state['polls'])

    def test_idle_polls_and_suspended_output_still_block(self):
        state = self.run_case(4)
        self.assertEqual(state['polls'],200)
        self.assertEqual(state['ticks'],200)
        for mode in (2,3):
            with self.subTest(mode=mode):
                state = self.run_case(mode)
                self.assertEqual(state['polls'],0)
                self.assertEqual(state['waits'],1)
                self.assertGreater(state['ticks'],0)
