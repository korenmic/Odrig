// The usermod that makes WLED the platform of the player: it sets WLED's outputs from the
// legs, keeps WLED from the LEDs, and sends the LED data to the outputs.
#include "wled.h"

#include "odrig_leds.h"
#include "odrig_pattern.h"
#include "odrig_serial.h"

#ifdef ODRIG_PROBE
#include "odrig_probe.h"
#endif

namespace {

// Milliseconds since the chip started, from a 64-bit clock that does not wrap.
uint64_t nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }

#ifdef ODRIG_PROBE
uint32_t microsSince(int64_t from) { return (uint32_t)(esp_timer_get_time() - from); }
#endif

}  // namespace

class OdrigUsermod : public Usermod {
 public:
  void setup() override {
    const uint64_t before = nowMs();
    OdrigPattern::begin();
    OdrigLeds::source(OdrigPattern::legs());
#ifdef ODRIG_PROBE
    OdrigProbe::started((uint32_t)(nowMs() - before));
#else
    (void)before;
#endif
    OdrigLeds::hold();
    if (OdrigLeds::legs() == 0) OdrigLeds::dark();
  }

  void loop() override {
#ifdef ODRIG_PROBE
    OdrigProbe::pass(nowMs());
#endif
    OdrigLeds::hold();
    OdrigSerial::poll();
    if (!BusManager::canAllShow()) return;
#ifdef ODRIG_PROBE
    const int64_t pollStart = esp_timer_get_time();
    const bool due = OdrigPattern::poll(nowMs());
    OdrigProbe::polled(microsSince(pollStart));
    if (!due) return;
    OdrigProbe::beforeSend();
    const int64_t sendStart = esp_timer_get_time();
    OdrigLeds::send();
    OdrigProbe::afterSend(nowMs(), microsSince(sendStart));
#else
    if (OdrigPattern::poll(nowMs())) OdrigLeds::send();
#endif
  }
};

static OdrigUsermod odrigUsermod;
REGISTER_USERMOD(odrigUsermod);
