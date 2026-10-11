#ifdef ODRIG_PROBE

#include "odrig_probe.h"

#include "wled.h"

#include "driver/pcnt.h"
#include "esp_rom_gpio.h"
#include "soc/lcd_cam_struct.h"
#include "soc/pcnt_periph.h"

#include "odrig_leds.h"
#include "odrig_serial.h"

namespace {

const char LINE[] = "#probe\n";
const size_t LINE_LENGTH = sizeof(LINE) - 1;
const uint32_t MAX_OUTPUTS = 32;
// What the outputs hold is read back after a send and again before the next one, for
// some of the outputs at each send, each in its turn: as many as have this many LEDs
// together, and one at least. So the reading takes little of the time it is there to
// measure, however many outputs there are.
const uint32_t READ_BACK_LEDS = 200;

size_t matched = 0;
bool atLineStart = true;

uint32_t startMs = 0;
const char *(*errorNow)() = nullptr;
bool counting = false;
uint64_t secondStart = 0;
uint32_t loopsNow = 0, loopsLast = 0;
uint32_t sentNow = 0, sentLast = 0;
uint32_t pollUsNow = 0, pollUsLast = 0, sendUsNow = 0, sendUsLast = 0;
// The requests for a refresh are timed on the task that makes them, on the chip's other
// processor core; their sums are kept under this guard.
portMUX_TYPE pollGuard = portMUX_INITIALIZER_UNLOCKED;
uint64_t lastSendMs = 0;
bool sentBefore = false;
uint32_t longestGapMs = 0, longestPollUs = 0, longestSendUs = 0;
uint32_t overwritten = 0, limited = 0;
// The CRC of what each output held when it was last read back after a send, and the
// outputs that were read back after the last one.
uint32_t held[MAX_OUTPUTS];
bool heldKnown[MAX_OUTPUTS];
uint32_t firstRead = 0, readOutputs = 0, nextToRead = 0;
// Between the fill and the show of a refresh the outputs hold what they have not sent
// yet. A report that is asked for then is written after the show.
bool filledNotShown = false, reportWaits = false;

// The wire time: from the end of a send until the parallel driver, the chip's LCD unit,
// has finished its transfer and can take data again; shortest and longest since the last
// report. A timer looks every tenth of a millisecond, so that the measure does not depend
// on how long a pass of the loop is.
const uint64_t WIRE_WATCH_US = 100;
esp_timer_handle_t wireWatch = nullptr;
int64_t sendEndUs = 0;
volatile uint32_t wireUs = 0;
volatile bool wireEnded = false;
bool wireMeasured = false;
uint32_t shortestWireUs = 0, longestWireUs = 0;

// The pulses: the rising edges on the pin of one output during one refresh, counted by
// the chip's pulse counter, for one output at each send. The counter has 15 bits, enough
// for the 24 pulses of each of 1,365 LEDs.
const pcnt_unit_t COUNTER = PCNT_UNIT_0;
const int32_t NOT_COUNTED = -1;
const uint32_t NO_OUTPUT = MAX_OUTPUTS;
bool counterReady = false;
int32_t pulses[MAX_OUTPUTS];
uint32_t countedOutput = NO_OUTPUT, nextToCount = 0;

uint32_t crcOf(uint32_t crc, uint8_t byte) {
  static const uint32_t table[16] = {
    0x00000000, 0x1DB71064, 0x3B6E20C8, 0x26D930AC, 0x76DC4190, 0x6B6B51F4, 0x4DB26158, 0x5005713C,
    0xEDB88320, 0xF00F9344, 0xD6D6A3E8, 0xCB61B38C, 0x9B64C2B0, 0x86D3D2D4, 0xA00AE278, 0xBDBDF21C};
  crc = table[(crc ^ byte) & 0x0F] ^ (crc >> 4);
  crc = table[(crc ^ (byte >> 4)) & 0x0F] ^ (crc >> 4);
  return crc;
}

// The CRC-32 of the colours an output holds, as WLED gives them back: red, green and
// blue for each of its LEDs.
uint32_t crcOfOutput(Bus *bus) {
  uint32_t crc = 0xFFFFFFFF;
  if (bus && bus->isOk()) {
    const unsigned length = bus->getLength();
    for (unsigned n = 0; n < length; n++) {
      const uint32_t colour = bus->getPixelColor(n);
      crc = crcOf(crc, R(colour));
      crc = crcOf(crc, G(colour));
      crc = crcOf(crc, B(colour));
    }
  }
  return ~crc;
}

uint32_t outputs() { return std::min((uint32_t)BusManager::getNumBusses(), MAX_OUTPUTS); }

bool sendsASignal(Bus *bus) { return bus && bus->isOk() && bus->isDigital() && !bus->isPlaceholder(); }

bool isParallel(Bus *bus) { return sendsASignal(bus) && static_cast<BusDigital *>(bus)->isI2S(); }

bool hasParallelOutputs() {
  const uint32_t count = outputs();
  for (uint32_t i = 0; i < count; i++) {
    if (isParallel(BusManager::getBus(i))) return true;
  }
  return false;
}

// Runs on the timer's task while a transfer is on the wire.
void watchTheWire(void *) {
  if (LCD_CAM.lcd_user.lcd_start) return;
  wireUs = (uint32_t)(esp_timer_get_time() - sendEndUs);
  wireEnded = true;
  esp_timer_stop(wireWatch);
}

void startTheWireWatch() {
  if (wireWatch == nullptr) {
    esp_timer_create_args_t made = {};
    made.callback = watchTheWire;
    made.name = "odrig wire";
    if (esp_timer_create(&made, &wireWatch) != ESP_OK) return;
  }
  esp_timer_stop(wireWatch);
  sendEndUs = esp_timer_get_time();
  esp_timer_start_periodic(wireWatch, WIRE_WATCH_US);
}

// Takes a wire time the timer has measured into the shortest and the longest.
void keepTheWireTime() {
  if (!wireEnded) return;
  const uint32_t measured = wireUs;
  wireEnded = false;
  if (!wireMeasured || measured < shortestWireUs) shortestWireUs = measured;
  if (!wireMeasured || measured > longestWireUs) longestWireUs = measured;
  wireMeasured = true;
}

// Puts the pulse counter on a pin and starts it at 0. The input of the pin's pad is
// turned on and routed to the counter; what the pad puts out is not touched.
void countPulsesOn(uint8_t pin) {
  if (!counterReady) {
    pcnt_config_t config = {};
    config.pulse_gpio_num = PCNT_PIN_NOT_USED;
    config.ctrl_gpio_num = PCNT_PIN_NOT_USED;
    config.lctrl_mode = PCNT_MODE_KEEP;
    config.hctrl_mode = PCNT_MODE_KEEP;
    config.pos_mode = PCNT_COUNT_INC;
    config.neg_mode = PCNT_COUNT_DIS;
    config.counter_h_lim = INT16_MAX;
    config.counter_l_lim = -1;
    config.unit = COUNTER;
    config.channel = PCNT_CHANNEL_0;
    pcnt_unit_config(&config);
    pcnt_filter_disable(COUNTER);
    for (uint32_t i = 0; i < MAX_OUTPUTS; i++) pulses[i] = NOT_COUNTED;
    counterReady = true;
  }
  pcnt_counter_pause(COUNTER);
  PIN_INPUT_ENABLE(GPIO_PIN_MUX_REG[pin]);
  esp_rom_gpio_connect_in_signal(pin, pcnt_periph_signals.groups[0].units[COUNTER].channels[0].pulse_sig, false);
  pcnt_counter_clear(COUNTER);
  pcnt_counter_resume(COUNTER);
}

// Chooses the output whose pulses the next send is counted for: the next one in turn
// that sends a signal.
void countTheNextOutput() {
  const uint32_t count = outputs();
  countedOutput = NO_OUTPUT;
  for (uint32_t tried = 0; tried < count; tried++) {
    const uint32_t i = nextToCount % count;
    nextToCount = i + 1;
    Bus *bus = BusManager::getBus(i);
    uint8_t pins[OUTPUT_MAX_PINS] = {255, 255, 255, 255, 255};
    if (!sendsASignal(bus) || bus->getPins(pins) == 0 || pins[0] >= SOC_GPIO_PIN_COUNT) continue;
    countPulsesOn(pins[0]);
    countedOutput = i;
    return;
  }
}

// Reads back the outputs whose turn it is and keeps the CRC of what each holds.
void readBackTheNextOutputs() {
  const uint32_t count = outputs();
  firstRead = count ? nextToRead % count : 0;
  readOutputs = 0;
  uint32_t leds = 0;
  while (readOutputs < count) {
    const uint32_t i = (firstRead + readOutputs) % count;
    Bus *bus = BusManager::getBus(i);
    const uint32_t length = bus && bus->isOk() ? bus->getLength() : 0;
    if (readOutputs > 0 && leds + length > READ_BACK_LEDS) break;
    held[i] = crcOfOutput(bus);
    heldKnown[i] = true;
    leds += length;
    readOutputs++;
  }
  nextToRead = firstRead + readOutputs;
}

// Reads the pulses of the output that was counted during the last send. Every output
// has finished sending when this is called.
void readTheCountedOutput() {
  if (countedOutput == NO_OUTPUT) return;
  int16_t counted = 0;
  pcnt_counter_pause(COUNTER);
  pcnt_get_counter_value(COUNTER, &counted);
  pulses[countedOutput] = counted;
  countedOutput = NO_OUTPUT;
}

// The current the limiter allows the LEDs, and the current it estimated for the last send.
uint32_t limitMa() {
  const uint32_t all = BusManager::ablMilliampsMax();
  return all > MA_FOR_ESP ? all - MA_FOR_ESP : 0;
}
uint32_t usedMa() { return BusManager::currentMilliamps() - MA_FOR_ESP; }

void report() {
  String line;
  line.reserve(4096);
  line += F("{\"probe\":1,\"start_ms\":");
  line += startMs;
  line += F(",\"heap\":");
  line += (uint32_t)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  line += F(",\"realtime\":");
  line += (realtimeMode == REALTIME_MODE_GENERIC && realtimeOverride == REALTIME_OVERRIDE_NONE) ? 1 : 0;
  line += F(",\"loops\":");
  line += loopsLast;
  line += F(",\"sent\":");
  line += sentLast;
  line += F(",\"gap_ms\":");
  line += longestGapMs;
  line += F(",\"poll_us\":");
  line += longestPollUs;
  line += F(",\"send_us\":");
  line += longestSendUs;
  line += F(",\"poll_total_us\":");
  line += pollUsLast;
  line += F(",\"send_total_us\":");
  line += sendUsLast;
  line += F(",\"overwritten\":");
  line += overwritten;
  line += F(",\"limited\":");
  line += limited;
  line += F(",\"limit_ma\":");
  line += limitMa();
  line += F(",\"used_ma\":");
  line += usedMa();
  line += F(",\"wire_us\":");
  if (wireMeasured) {
    line += '[';
    line += shortestWireUs;
    line += ',';
    line += longestWireUs;
    line += ']';
  } else {
    line += F("null");
  }
  line += F(",\"ap\":");
  line += apActive ? 1 : 0;
  line += F(",\"error\":");
  const char *error = errorNow != nullptr ? errorNow() : nullptr;
  if (error != nullptr) {
    line += '"';
    line += error;
    line += '"';
  } else {
    line += F("null");
  }
  line += F(",\"outputs\":[");
  const uint32_t count = outputs();
  for (uint32_t i = 0; i < count; i++) {
    Bus *bus = BusManager::getBus(i);
    uint8_t pins[OUTPUT_MAX_PINS] = {255, 255, 255, 255, 255};
    bus->getPins(pins);
    const bool parallel = bus->isOk() && bus->isDigital() && !bus->isPlaceholder() && static_cast<BusDigital *>(bus)->isI2S();
    char crc[9];
    snprintf(crc, sizeof(crc), "%08x", (unsigned)(heldKnown[i] ? held[i] : crcOfOutput(bus)));
    if (i) line += ',';
    line += F("{\"leg\":");
    line += i + 1;
    line += F(",\"pin\":");
    line += pins[0];
    line += F(",\"count\":");
    line += bus->getLength();
    line += F(",\"ok\":");
    line += bus->isOk() ? F("true") : F("false");
    line += F(",\"driver\":\"");
    line += !bus->isOk() ? F("none") : parallel ? F("parallel") : F("rmt");
    line += F("\",\"crc\":\"");
    line += crc;
    line += F("\",\"pulses\":");
    if (counterReady && pulses[i] != NOT_COUNTED) {
      line += pulses[i];
    } else {
      line += F("null");
    }
    line += '}';
  }
  line += F("]}\n");
  OdrigSerial::writeLong(line.c_str(), line.length());
  longestGapMs = longestSendUs = 0;
  portENTER_CRITICAL(&pollGuard);
  longestPollUs = 0;
  portEXIT_CRITICAL(&pollGuard);
  limited = 0;
  wireMeasured = false;
}

}  // namespace

void OdrigProbe::started(uint32_t start_ms, const char *(*error)()) {
  startMs = start_ms;
  errorNow = error;
}

void OdrigProbe::pass(uint64_t now_ms) {
  if (!counting) {
    counting = true;
    secondStart = now_ms;
  }
  while (now_ms - secondStart >= 1000) {
    loopsLast = loopsNow;
    sentLast = sentNow;
    sendUsLast = sendUsNow;
    loopsNow = sentNow = sendUsNow = 0;
    portENTER_CRITICAL(&pollGuard);
    pollUsLast = pollUsNow;
    pollUsNow = 0;
    portEXIT_CRITICAL(&pollGuard);
    secondStart += 1000;
  }
  loopsNow++;
  keepTheWireTime();
}

void OdrigProbe::polled(uint32_t poll_us) {
  portENTER_CRITICAL(&pollGuard);
  pollUsNow += poll_us;
  if (poll_us > longestPollUs) longestPollUs = poll_us;
  portEXIT_CRITICAL(&pollGuard);
}

void OdrigProbe::beforeFill() {
  filledNotShown = true;
  const uint32_t count = outputs();
  for (uint32_t read = 0; read < readOutputs; read++) {
    const uint32_t i = count ? (firstRead + read) % count : 0;
    if (count && crcOfOutput(BusManager::getBus(i)) == held[i]) continue;
    overwritten++;
    break;
  }
  readOutputs = 0;
}

void OdrigProbe::beforeShow() {
  keepTheWireTime();
  readTheCountedOutput();
  countTheNextOutput();
}

void OdrigProbe::afterShow(uint64_t now_ms, uint32_t send_us) {
  if (hasParallelOutputs()) startTheWireWatch();
  sentNow++;
  sendUsNow += send_us;
  if (send_us > longestSendUs) longestSendUs = send_us;
  if (sentBefore && now_ms - lastSendMs > longestGapMs) longestGapMs = (uint32_t)(now_ms - lastSendMs);
  sentBefore = true;
  lastSendMs = now_ms;
  if (usedMa() >= limitMa()) limited++;
  readBackTheNextOutputs();
  filledNotShown = false;
  if (reportWaits) {
    reportWaits = false;
    report();
  }
}

void OdrigProbe::feed(uint8_t byte, void (*pass)(uint8_t byte)) {
  if ((matched > 0 || atLineStart) && byte == (uint8_t)LINE[matched]) {
    if (++matched == LINE_LENGTH) {
      matched = 0;
      if (filledNotShown) {
        reportWaits = true;
      } else {
        report();
      }
    }
    return;
  }
  for (size_t i = 0; i < matched; i++) pass((uint8_t)LINE[i]);
  matched = 0;
  pass(byte);
  atLineStart = byte == '\n';
}

#endif
