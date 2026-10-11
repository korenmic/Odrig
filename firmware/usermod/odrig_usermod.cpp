// The usermod that makes WLED the platform of the player. It hosts the core: it gives it
// memory, the time and the files of the installed show, carries bytes between the USB
// serial port and the core, and keeps WLED from the LEDs. Every decision about files, time
// and commands is the core's.
#include "wled.h"

#include "odrig_core.h"
#include "odrig_files.h"
#include "odrig_leds.h"
#include "odrig_serial.h"

#ifdef ODRIG_PROBE
#include "odrig_probe.h"
#endif

namespace {

odrig_core *core = nullptr;

// Held for every call to the core after its start, so that the calls follow one another
// whichever task makes them.
SemaphoreHandle_t lock = nullptr;

struct Locked {
  Locked() { xSemaphoreTake(lock, portMAX_DELAY); }
  ~Locked() { xSemaphoreGive(lock); }
};

struct Reply {
  char *text;
  size_t capacity;
  size_t length;
};

void keepReply(void *ctx, const char *, size_t, const char *reply, size_t reply_length) {
  Reply *kept = static_cast<Reply *>(ctx);
  kept->length = std::min(reply_length, kept->capacity);
  memcpy(kept->text, reply, kept->length);
}

// One byte of the port for the core. The timestamp is read after the lock is taken.
size_t feedByte(uint8_t byte, char *reply, size_t capacity) {
  if (core == nullptr) return 0;
  Reply kept = {reply, capacity, 0};
  Locked held;
  odrig_core_feed(core, OdrigFiles::nowMs(), &byte, 1, keepReply, &kept);
  return kept.length;
}

#ifdef ODRIG_PROBE
const char *errorNow() {
  if (core == nullptr) return "no core";
  Locked held;
  return odrig_core_error(core);
}

uint32_t microsSince(int64_t from) { return (uint32_t)(esp_timer_get_time() - from); }
#endif

}  // namespace

class OdrigUsermod : public Usermod {
 public:
  void setup() override {
    lock = xSemaphoreCreateMutex();
    const uint64_t before = OdrigFiles::nowMs();
    const odrig_host host = OdrigFiles::host();
    core = odrig_core_begin(&host);
    startMs = (uint32_t)(OdrigFiles::nowMs() - before);
#ifdef ODRIG_PROBE
    OdrigProbe::started(startMs, errorNow);
#endif
    OdrigLeds::hold();
    OdrigLeds::dark();
  }

  void loop() override {
#ifdef ODRIG_PROBE
    OdrigProbe::pass(OdrigFiles::nowMs());
#endif
    OdrigLeds::hold();
    OdrigSerial::poll(feedByte);
    if (core == nullptr) return;
#ifdef ODRIG_PROBE
    const int64_t pollStart = esp_timer_get_time();
#endif
    {
      Locked held;
      odrig_core_poll(core, OdrigFiles::nowMs());
    }
#ifdef ODRIG_PROBE
    OdrigProbe::polled(microsSince(pollStart));
#endif
  }

 private:
  uint32_t startMs = 0;
};

static OdrigUsermod odrigUsermod;
REGISTER_USERMOD(odrigUsermod);
