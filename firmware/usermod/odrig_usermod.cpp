// The usermod that makes WLED the platform of the player. It hosts the core: it gives it
// memory, the time and the files of the installed show, carries bytes between the USB
// serial port and the core and command lines between WLED's web server and the core, sets
// WLED's outputs from the core's legs, keeps WLED from the LEDs, sends the core's LED data
// to the outputs, and reports its state in WLED's information. Every decision about files,
// time, the layout and commands is the core's.
#include "wled.h"

#include "odrig_core.h"
#include "odrig_files.h"
#include "odrig_http.h"
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

// One command line of the web server for the core. It runs on the network task; the lock
// is what lets it call the core.
size_t commandLine(const char *line, size_t length, char *reply, size_t capacity) {
  if (core == nullptr) return 0;
  Locked held;
  return odrig_core_command(core, OdrigFiles::nowMs(), line, length, reply, capacity);
}

// The legs as the core lists them, for the outputs.
uint32_t legCount() {
  if (core == nullptr) return 0;
  Locked held;
  return odrig_core_leg_count(core);
}

bool legAt(uint32_t index, OdrigLeg *out) {
  if (core == nullptr) return false;
  odrig_leg leg;
  {
    Locked held;
    if (!odrig_core_leg(core, index, &leg)) return false;
  }
  out->leg = leg.leg;
  out->pin = leg.pin;
  out->led_count = leg.led_count;
  out->rgb = leg.rgb;
  return true;
}

// Asks the core for a refresh. The timestamp is read after the lock is taken.
bool refreshDue() {
  Locked held;
  return odrig_core_poll(core, OdrigFiles::nowMs()) == 1;
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
    const OdrigLegSource legs = {legCount, legAt};
    OdrigLeds::source(legs);
    OdrigLeds::hold();
    if (OdrigLeds::legs() == 0) OdrigLeds::dark();
    OdrigHttp::begin(commandLine);
  }

  void loop() override {
    // While WLED writes a new firmware, no file is read and nothing is sent to the LEDs.
    if (updating) return;
#ifdef ODRIG_PROBE
    OdrigProbe::pass(OdrigFiles::nowMs());
#endif
    OdrigLeds::hold();
    // WLED answers the lookups of its captive portal only outside its live mode.
    if (apActive) dnsServer.processNextRequest();
    OdrigSerial::poll(feedByte);
    if (core == nullptr) return;
    // The core is asked for the next refresh while the outputs may still be busy with
    // the last one, and not again before that refresh is sent: so every refresh the core
    // counts reaches the outputs, and decoding does not wait for the LEDs.
    if (!refreshWaits) {
#ifdef ODRIG_PROBE
      const int64_t pollStart = esp_timer_get_time();
      refreshWaits = refreshDue();
      OdrigProbe::polled(microsSince(pollStart));
#else
      refreshWaits = refreshDue();
#endif
    }
    if (!refreshWaits || !BusManager::canAllShow()) return;
#ifdef ODRIG_PROBE
    OdrigProbe::beforeSend();
    const int64_t sendStart = esp_timer_get_time();
    OdrigLeds::send();
    OdrigProbe::afterSend(OdrigFiles::nowMs(), microsSince(sendStart));
#else
    OdrigLeds::send();
#endif
    refreshWaits = false;
  }

  // WLED's information page: whether the show is valid, how many outputs work, and how
  // long the core took to start.
  void addToJsonInfo(JsonObject &root) override {
    JsonObject user = root["u"];
    if (user.isNull()) user = root.createNestedObject("u");
    String show = F("ok");
    if (core == nullptr) {
      show = F("no core");
    } else {
      Locked held;
      const char *error = odrig_core_error(core);
      if (error != nullptr) show = error;
    }
    user.createNestedArray(F("odrig show")).add(show);
    user.createNestedArray(F("odrig outputs")).add(String(OdrigLeds::summary()));
    JsonArray start = user.createNestedArray(F("odrig start"));
    start.add(startMs);
    start.add(F(" ms"));
  }

  void onUpdateBegin(bool begins) override { updating = begins; }

 private:
  uint32_t startMs = 0;
  bool refreshWaits = false;
  bool updating = false;
};

static OdrigUsermod odrigUsermod;
REGISTER_USERMOD(odrigUsermod);
