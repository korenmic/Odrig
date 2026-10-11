#include "odrig_serial.h"

#include "wled.h"

#ifdef ODRIG_PROBE
#include "odrig_probe.h"
#endif

namespace {

const int BYTES_PER_PASS = 256;

// A byte that is no part of a line the usermod answers itself. Nothing takes it yet.
void pass(uint8_t byte) { (void)byte; }

}  // namespace

void OdrigSerial::poll() {
  for (int taken = 0; taken < BYTES_PER_PASS && Serial.available() > 0; taken++) {
    const int byte = Serial.read();
    if (byte < 0) break;
#ifdef ODRIG_PROBE
    OdrigProbe::feed((uint8_t)byte, pass);
#else
    pass((uint8_t)byte);
#endif
  }
}
