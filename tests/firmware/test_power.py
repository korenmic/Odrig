import pathlib
import subprocess
import tempfile
import unittest

from . import ROOT
from .compiler import compiled


class PowerBridge(unittest.TestCase):
    def test_wled_power_hooks_are_connected_to_the_shared_core(self):
        text = (ROOT / 'firmware/usermod/odrig_usermod.cpp').read_text(encoding='utf-8')
        self.assertIn('void onStateChange(uint8_t mode) override', text)
        self.assertIn('void readFromJsonState(JsonObject &root) override', text)
        self.assertIn('host.identity = identityHost;', text)
        self.assertIn('ESP.getEfuseMac()', text)
        self.assertIn('odrig_core_power(core)', text)

    def test_scheduled_visibility_never_creates_a_manual_override(self):
        source = r'''
#include "odrig_power.h"
int main() {
    OdrigPower power;
    bool on = false;
    power.publish(true);
    if (power.take(true, false, &on)) return 1;
    power.publish(false);
    if (power.take(false, false, &on)) return 2;
    if (!power.take(true, false, &on) || !on) return 3;
    power.publish(true);
    power.explicitRequest(true);
    if (!power.take(true, false, &on) || !on) return 4;
    if (power.take(true, false, &on)) return 5;
    power.explicitRequest(false);
    power.publish(true);
    if (!power.take(true, false, &on) || on) return 6;
    power.explicitRequest(true);
    if (power.take(true, true, &on)) return 7;
    power.publish(false);
    if (power.take(false, false, &on)) return 8;
    if (!power.take(true, false, &on) || !on) return 9;
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            program = root / 'power.cpp'
            program.write_text(source, encoding='utf-8', newline='\n')
            binary = compiled([program], root / 'power', [ROOT / 'firmware/usermod'])
            result = subprocess.run([str(binary)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
