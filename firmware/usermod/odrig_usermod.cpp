// The usermod that makes WLED the platform of the player. It hosts the core: it gives it
// memory, the time, the files of the installed show and those of a USB drive on the
// chip's own socket, carries bytes between the USB serial port and the core, and command
// lines between the board's UART and the core and between WLED's web server and the core,
// sets WLED's outputs from the core's legs, keeps WLED from the LEDs, sends the core's LED
// data to the outputs, puts the lines the player logs into the log the UART writes, refuses
// an update over Wi-Fi on a board without a second firmware slot, and reports its state in
// WLED's information. Every decision about files, time, the layout
// and commands is the core's.
#include "wled.h"

#include "odrig_core.h"
#include "odrig_drive.h"
#include "odrig_files.h"
#include "odrig_http.h"
#include "odrig_leds.h"
#include "odrig_mini_output.h"
#include "odrig_routing.h"
#include "odrig_log.h"
#include "odrig_sd_config.h"
#include "odrig_serial.h"
#include "odrig_uart.h"
#include "odrig_update.h"

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

void syncLegs();

// The name the firmware gives itself in `status`: WLED's release name, the date and time of
// its build, its storage and the reason of the chip's last reset.
int aboutHost(void *, char *buffer, size_t capacity) {
  const char *reset;
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON: reset = "power-on"; break;
    case ESP_RST_SW: reset = "software"; break;
    case ESP_RST_PANIC: reset = "panic"; break;
    case ESP_RST_TASK_WDT: reset = "task-watchdog"; break;
    case ESP_RST_INT_WDT: reset = "interrupt-watchdog"; break;
    case ESP_RST_BROWNOUT: reset = "brownout"; break;
    case ESP_RST_DEEPSLEEP: reset = "deep-sleep"; break;
    default: reset = "other"; break;
  }
#if ODRIG_SD_CS >= 0
  const char *storage = "internal+microsd";
#else
  const char *storage = "internal+usb";
#endif
  snprintf(buffer, capacity, "%s %s %s %s reset %s", WLED_RELEASE_NAME, __DATE__, __TIME__, storage, reset);
  return 1;
}

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

// Bytes of the port for the core, up to the end of a line at most, under one hold of the
// lock: a command so waits for one request for a refresh at most. The timestamp is read
// after the lock is taken.
size_t feedBytes(const uint8_t *bytes, size_t length, char *reply, size_t capacity) {
  if (core == nullptr) return 0;
  Reply kept = {reply, capacity, 0};
  Locked held;
  odrig_core_feed(core, OdrigFiles::nowMs(), bytes, length, keepReply, &kept);
  syncLegs();
  return kept.length;
}

// One command line of the web server, or of the UART, for the core. The web server's
// runs on the network task; the lock is what lets it call the core. While the pacing
// holds lines back, it waits before it takes the lock.
size_t commandLine(const char *line, size_t length, char *reply, size_t capacity) {
  if (core == nullptr) return 0;
  while (OdrigFiles::holding()) delay(1);
  Locked held;
  const size_t answered = odrig_core_command(core, OdrigFiles::nowMs(), line, length, reply, capacity);
  syncLegs();
  return answered;
}

// Physical output resources remain fixed. The cached RGB pointers follow the
// logical leg currently assigned to each pin, under the core lock.
OdrigLeg *legs = nullptr;
uint32_t legsRead = 0;
const uint8_t *miniPixels = nullptr;
bool miniature = false;
bool outputsDark = false;
uint64_t lastDarkMs = 0;
OdrigMiniOutput miniOutput;
volatile bool refreshReady = false;
volatile bool outputChanging = false;
// While WLED writes a new firmware, no file is read and nothing is sent to LEDs.
volatile bool updating = false;

void readLegs() {
  if (core == nullptr) return;
  Locked held;
  const uint32_t count = odrig_core_leg_count(core);
  if (count == 0) return;
  legs = static_cast<OdrigLeg *>(malloc(count * sizeof(OdrigLeg)));
  if (legs == nullptr) return;
  for (uint32_t i = 0; i < count; i++) {
    odrig_leg leg;
    if (!odrig_core_leg(core, i, &leg)) return;
    legs[i].leg = leg.leg;
    legs[i].pin = leg.pin;
    legs[i].led_count = leg.led_count;
    legs[i].rgb = leg.rgb;
  }
  legsRead = count;
}

void enableMiniSupport() {
  if (core == nullptr || legsRead == 0) return;
  Locked held;
  odrig_core_mini_support(core);
  odrig_mini mini = {};
  if (odrig_core_mini(core, &mini)) miniPixels = mini.rgb;
}

uint32_t legCount() { return miniature ? 1 : legsRead; }

bool legAt(uint32_t index, OdrigLeg *out) {
  if (miniature) {
    if (index != 0 || miniPixels == nullptr) return false;
    *out = OdrigLeg{1, 1, 60, miniPixels};
    return true;
  }
  if (index >= legsRead) return false;
  *out = legs[index];
  return true;
}

// Called with the core lock held, including for a complete refresh copy.
void syncLegs() {
  for (uint32_t i = 0; i < legsRead; i++) {
    odrig_leg leg;
    if (!OdrigRouting::onPin(core, legs[i].pin, &leg)) continue;
    legs[i].leg = leg.leg;
    legs[i].rgb = leg.rgb;
  }
}

// Asks the core for a refresh. The timestamp is read after the lock is taken.
bool refreshDue() {
#ifdef ODRIG_PROBE
  const uint32_t readsBefore = OdrigFiles::secondReads();
  const int64_t pollStart = esp_timer_get_time();
#endif
  Locked held;
  if (outputChanging) return false;
  const bool due = odrig_core_poll(core, OdrigFiles::nowMs()) == 1;
#ifdef ODRIG_PROBE
  OdrigProbe::polled((uint32_t)(esp_timer_get_time() - pollStart), OdrigFiles::secondReads() != readsBefore);
#endif
  if (due) refreshReady = true;
  return due;
}

// The request for a refresh has a task of its own on the chip's other processor core, so
// that the core's work for the next frame, reading, decoding and placing every LED, runs
// beside the send of the last one. The core keeps one picture of LED data: the task asks
// again only when the loop has copied that picture into the outputs.
const char TASK_NAME[] = "odrig";
const uint32_t TASK_STACK = 8192;
const UBaseType_t TASK_PRIORITY = 1;
const BaseType_t TASK_PROCESSOR = 0;
TaskHandle_t requester = nullptr;

void requestRefreshes(void *) {
  for (;;) {
    if (refreshReady || updating || outputChanging) {
      // The loop wakes the task when it has taken the refresh.
      ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(50));
      continue;
    }
    const bool due = refreshDue();
    if (!due) {
      vTaskDelay(1);
    }
  }
}

struct MiniDriver {
  bool ready() const { return BusManager::canAllShow(); }
  void dark() const { OdrigLeds::dark(); }
  void select(bool enabled) const { miniature = enabled; }
  bool apply() const {
    OdrigLeds::apply();
    return OdrigLeds::matches() && OdrigLeds::legs() != 0 && OdrigLeds::working() == OdrigLeds::legs();
  }
};

// Capturing a request pauses the producer under the same lock that publishes a
// completed refresh. No output operation or transfer wait owns that lock.
bool serviceMini(bool &refreshFilled) {
  if (core == nullptr) return false;
  if (!miniOutput.busy()) {
    Locked held;
    odrig_mini mini = {};
    if (odrig_core_mini(core, &mini) && mini.pending) {
      outputChanging = true;
      refreshReady = false;
      refreshFilled = false;
      miniOutput.begin(mini.revision, mini.requested != 0);
    }
  }
  if (miniOutput.busy()) {
    MiniDriver driver;
    if (miniOutput.step(driver)) {
      {
        Locked held;
        const bool acknowledged = odrig_core_mini_complete(core, miniOutput.revision(), miniOutput.success()) == 1;
        outputsDark = !miniOutput.success() || !acknowledged;
        refreshReady = false;
        outputChanging = false;
      }
      lastDarkMs = OdrigFiles::nowMs();
      miniOutput.finish();
      if (requester != nullptr) xTaskNotifyGive(requester);
    }
    return true;
  }
  if (!outputsDark) return false;
  const uint64_t now = OdrigFiles::nowMs();
  if (BusManager::canAllShow()) {
    OdrigLeds::hold();
    if (now - lastDarkMs >= 20 && BusManager::canAllShow()) {
      OdrigLeds::dark();
      lastDarkMs = now;
    }
  }
  {
    Locked held;
    refreshReady = false;
  }
  if (requester != nullptr) xTaskNotifyGive(requester);
  return true;
}

#ifdef ODRIG_PROBE
const char *errorNow() {
  if (core == nullptr) return "no core";
  Locked held;
  return odrig_core_error(core);
}

uint32_t microsSince(int64_t from) { return (uint32_t)(esp_timer_get_time() - from); }
#endif

#ifdef ODRIG_DEBUG_LOG
// A build for finding faults: ESP-IDF's messages go to the USB serial port as well, where
// WLED's debug lines go, so that what the Wi-Fi and the network do can be read there.
int debugVprintf(const char *format, va_list arguments) {
  char line[256];
  const int length = vsnprintf(line, sizeof(line), format, arguments);
  if (length > 0) OdrigSerial::write(line, length < (int)sizeof(line) ? length : (int)sizeof(line) - 1);
  return length;
}
#endif

}  // namespace

class OdrigUsermod : public Usermod {
 public:
  void setup() override {
#ifdef ODRIG_DEBUG_LOG
    esp_log_set_vprintf(debugVprintf);
    esp_log_level_set("*", ESP_LOG_INFO);
#endif
    lock = xSemaphoreCreateMutex();
    OdrigSerial::begin();
    OdrigUart::begin();
    const uint64_t before = OdrigFiles::nowMs();
#ifndef ODRIG_PROBE
    // The probe build keeps the chip's own socket a serial port, which the board's suite
    // talks to it on.
    OdrigDrive::begin();
#endif
    // What the player logged last before a reset goes to the log before it starts again.
    OdrigLog::retained();
    odrig_host host = OdrigLog::withLog(OdrigDrive::withDrive(OdrigFiles::host()));
    host.about = aboutHost;
    core = odrig_core_begin(&host);
    startMs = (uint32_t)(OdrigFiles::nowMs() - before);
#ifdef ODRIG_PROBE
    OdrigProbe::started(startMs, errorNow);
#endif
    readLegs();
    enableMiniSupport();
    const OdrigLegSource source = {legCount, legAt};
    OdrigLeds::source(source);
    OdrigLeds::hold();
    if (OdrigLeds::legs() == 0) OdrigLeds::dark();
    OdrigHttp::begin(commandLine);
    OdrigUpdate::begin();
    if (core != nullptr) {
      xTaskCreatePinnedToCore(requestRefreshes, TASK_NAME, TASK_STACK, nullptr, TASK_PRIORITY, &requester, TASK_PROCESSOR);
    }
  }

  void loop() override {
    if (updating) return;
#ifdef ODRIG_PROBE
    OdrigProbe::pass(OdrigFiles::nowMs());
#endif
    OdrigLeds::keepLive();
    // WLED answers the lookups of its captive portal only outside its live mode.
    if (apActive) dnsServer.processNextRequest();
    OdrigSerial::poll(feedBytes);
    OdrigUart::poll(commandLine);
    if (serviceMini(refreshFilled)) return;
    OdrigLeds::hold();
#ifdef ODRIG_PROBE
    // A step of the store trial is made as a command's storage calls are: when the pacing
    // holds no line back, and with the lock held.
    if (OdrigProbe::storing() && !OdrigFiles::holding()) {
      Locked held;
      OdrigProbe::storeStep();
    }
#endif
    if (requester == nullptr) return;
    // A refresh the task has ready is copied into the outputs at once, also while the
    // last one is still on the wire. Then the task may ask for the next one, and the
    // copy is sent as soon as the outputs can take data. So every refresh the core
    // counts reaches the outputs, and neither decoding nor the copy waits for the LEDs.
    if (!refreshFilled) {
      if (!refreshReady) return;
      {
        Locked held;
        syncLegs();
#ifdef ODRIG_PROBE
      OdrigProbe::beforeFill();
      const int64_t fillStart = esp_timer_get_time();
      OdrigLeds::fill();
      fillUs = microsSince(fillStart);
#else
      OdrigLeds::fill();
#endif
      }
      refreshFilled = true;
      refreshReady = false;
      xTaskNotifyGive(requester);
    }
    if (!BusManager::canAllShow()) return;
#ifdef ODRIG_PROBE
    OdrigProbe::beforeShow();
    const int64_t showStart = esp_timer_get_time();
    OdrigLeds::show();
    OdrigProbe::afterShow(OdrigFiles::nowMs(), fillUs + microsSince(showStart));
#else
    OdrigLeds::show();
#endif
    refreshFilled = false;
  }

  // WLED's information page: whether the show is valid, how many outputs work, how long
  // the core took to start, what there is of a USB drive, and whether an update over
  // Wi-Fi is refused.
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
    user.createNestedArray(F("odrig drive")).add(String(OdrigDrive::summary()));
    user.createNestedArray(F("odrig update")).add(OdrigUpdate::refusing() ? F("refused: no second slot") : F("WLED's"));
  }

  void onUpdateBegin(bool begins) override { updating = begins; }

  // The usermod's settings in WLED's settings file, which WLED's page "Usermods" shows and
  // changes: how many seconds the chip's own USB socket is looked at for a computer as the
  // board starts.
  void addToConfig(JsonObject &root) override {
    JsonObject own = root.createNestedObject(F("odrig"));
    own[F("computer_wait_s")] = OdrigDrive::wait() / 1000;
  }

  // A setting that is missing or out of range leaves the default. It is answered as
  // complete either way, so that WLED writes nothing to its settings file on its own.
  bool readFromConfig(JsonObject &root) override {
    JsonObject own = root[F("odrig")];
    if (own.isNull() || !own[F("computer_wait_s")].is<int>()) return true;
    const int seconds = own[F("computer_wait_s")].as<int>();
    if (seconds >= 0 && seconds <= 60) OdrigDrive::setWait((uint32_t)seconds * 1000);
    return true;
  }

 private:
  uint32_t startMs = 0;
  bool refreshFilled = false;
#ifdef ODRIG_PROBE
  uint32_t fillUs = 0;
#endif
};

static OdrigUsermod odrigUsermod;
REGISTER_USERMOD(odrigUsermod);
