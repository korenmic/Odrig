#ifdef ODRIG_PROBE

#include "odrig_probe.h"

#include "wled.h"

#include "driver/pcnt.h"
#include "esp_rom_gpio.h"
#include "soc/lcd_cam_struct.h"
#include "soc/pcnt_periph.h"

#include "odrig_files.h"
#include "odrig_leds.h"
#include "odrig_serial.h"

namespace {

const char LINE[] = "#probe\n";
const size_t LINE_LENGTH = sizeof(LINE) - 1;
// The line of the store trial: this word, a number of bytes in decimal digits, a newline.
const char STORE_WORD[] = "#store ";
const size_t STORE_WORD_LENGTH = sizeof(STORE_WORD) - 1;
const size_t STORE_DIGITS = 10;
const uint32_t MAX_OUTPUTS = 32;
// What the outputs hold is read back after a send and again before the next one, for
// some of the outputs at each send, each in its turn: as many as have this many LEDs
// together, and one at least. So the reading takes little of the time it is there to
// measure, however many outputs there are.
const uint32_t READ_BACK_LEDS = 200;

// The bytes at the start of a line that are held back while they can still become a line
// of the probe build.
char heldBack[STORE_WORD_LENGTH + STORE_DIGITS + 1];
size_t heldBytes = 0;
bool atLineStart = true;

uint32_t startMs = 0;
const char *(*errorNow)() = nullptr;
bool counting = false;
uint64_t secondStart = 0;
uint32_t loopsNow = 0, loopsLast = 0;
uint32_t sentNow = 0, sentLast = 0;
uint32_t pollUsNow = 0, pollUsLast = 0, sendUsNow = 0, sendUsLast = 0;
// The requests for a refresh in which the core read a second file, since the last report:
// their number, the longest and the sum of their times.
uint32_t checkSteps = 0, checkLongestUs = 0, checkTotalUs = 0;
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

// With a maximum of 0 WLED's limiter is off: it dims nothing and estimates nothing.
bool limiterOn() { return BusManager::ablMilliampsMax() > 0; }

// The current the limiter allows the LEDs, and the current it estimated for the last send.
uint32_t limitMa() {
  const uint32_t all = BusManager::ablMilliampsMax();
  return all > MA_FOR_ESP ? all - MA_FOR_ESP : 0;
}
uint32_t usedMa() { return BusManager::currentMilliamps() - MA_FOR_ESP; }

// The store trial. `#store <bytes>` writes a file of that size into the folder of the show
// through the host functions the core is given, renames it onto a name that has a file,
// reads it back and removes it, a step in each pass of the loop that the pacing allows,
// and then answers with the times.
enum StoreStep { STORE_IDLE, STORE_SEED, STORE_OPEN, STORE_WRITE, STORE_CLOSE, STORE_RENAME, STORE_READ, STORE_REMOVE };
const char STORE_PART[] = "probe.part";
const char STORE_NAME[] = "probe.odrg";
const size_t STORE_PIECE = 1500;
const size_t STORE_READ_PIECE = 512;
const uint32_t STORE_READS_IN_A_STEP = 4;
const size_t STORE_SEED_BYTES = 16;

// The shortest, the longest and the sum of some times, in microseconds.
struct Spread {
  void add(uint32_t us) {
    if (count == 0 || us < shortest) shortest = us;
    if (us > longest) longest = us;
    total += us;
    count++;
  }
  uint32_t mean() const { return count ? (uint32_t)(total / count) : 0; }
  uint32_t count, shortest, longest;
  uint64_t total;
};

odrig_host storeHost;
StoreStep storeAt = STORE_IDLE;
uint32_t storeBytes = 0, storeWritten = 0, storeRead = 0;
uint32_t storeCrcWritten = 0, storeCrcRead = 0;
Spread storeWrites, storeReads;
uint32_t storeSeedUs = 0, storeOpenUs = 0, storeCloseUs = 0, storeRenameUs = 0, storeRemoveUs = 0;
int64_t storeWriteBeganUs = 0, storeWriteEndedUs = 0;
uint8_t storePiece[STORE_PIECE];

uint32_t sinceUs(int64_t from) { return (uint32_t)(esp_timer_get_time() - from); }

// The byte the trial writes at a place of its file.
uint8_t storeByteAt(uint32_t place) { return (uint8_t)(place * 31u + (place >> 8) * 7u + 0x5Au); }

void addSpread(String &line, const __FlashStringHelper *name, const Spread &spread) {
  line += name;
  line += '[';
  line += spread.shortest;
  line += ',';
  line += spread.mean();
  line += ',';
  line += spread.longest;
  line += ']';
}

// Ends the trial: removes what is left of it when it failed, and writes the answer.
void storeAnswer(const char *failed) {
  if (failed != nullptr) {
    storeHost.remove(storeHost.ctx, STORE_PART);
    storeHost.remove(storeHost.ctx, STORE_NAME);
  }
  const uint32_t writeMs = (uint32_t)((storeWriteEndedUs - storeWriteBeganUs) / 1000);
  String line;
  line.reserve(512);
  line += F("{\"store\":1,\"bytes\":");
  line += storeBytes;
  line += F(",\"ok\":");
  line += failed == nullptr ? F("true") : F("false");
  line += F(",\"failed\":");
  if (failed != nullptr) {
    line += '"';
    line += failed;
    line += '"';
  } else {
    line += F("null");
  }
  line += F(",\"written\":");
  line += storeWritten;
  line += F(",\"read\":");
  line += storeRead;
  line += F(",\"writes\":");
  line += storeWrites.count;
  addSpread(line, F(",\"write_us\":"), storeWrites);
  line += F(",\"write_ms\":");
  line += writeMs;
  line += F(",\"bytes_per_second\":");
  line += writeMs ? (uint32_t)((uint64_t)storeWritten * 1000 / writeMs) : 0;
  line += F(",\"seed_us\":");
  line += storeSeedUs;
  line += F(",\"open_us\":");
  line += storeOpenUs;
  line += F(",\"close_us\":");
  line += storeCloseUs;
  line += F(",\"rename_us\":");
  line += storeRenameUs;
  line += F(",\"reads\":");
  line += storeReads.count;
  addSpread(line, F(",\"read_us\":"), storeReads);
  line += F(",\"remove_us\":");
  line += storeRemoveUs;
  line += F("}\n");
  OdrigSerial::writeLong(line.c_str(), line.length());
  storeAt = STORE_IDLE;
}

void storeBegin(uint32_t bytes) {
  if (storeAt != STORE_IDLE) return;
  storeHost = OdrigFiles::host();
  storeBytes = bytes;
  storeWritten = storeRead = 0;
  storeCrcWritten = storeCrcRead = 0xFFFFFFFF;
  storeWrites = Spread();
  storeReads = Spread();
  storeSeedUs = storeOpenUs = storeCloseUs = storeRenameUs = storeRemoveUs = 0;
  storeWriteBeganUs = storeWriteEndedUs = esp_timer_get_time();
  storeAt = STORE_SEED;
}

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
  const OdrigFiles::StoreTimes stored = OdrigFiles::takeStoreTimes();
  portENTER_CRITICAL(&pollGuard);
  const uint32_t steps = checkSteps, stepLongestUs = checkLongestUs, stepTotalUs = checkTotalUs;
  checkSteps = checkLongestUs = checkTotalUs = 0;
  portEXIT_CRITICAL(&pollGuard);
  line += F(",\"space_us\":");
  line += OdrigFiles::spaceAskedMicros();
  line += F(",\"store\":{\"calls\":");
  line += stored.calls;
  line += F(",\"longest_us\":");
  line += stored.longestUs;
  line += F(",\"total_us\":");
  line += stored.totalUs;
  line += F(",\"check_steps\":");
  line += steps;
  line += F(",\"check_longest_us\":");
  line += stepLongestUs;
  line += F(",\"check_total_us\":");
  line += stepTotalUs;
  line += '}';
  line += F(",\"ap\":");
  line += apActive ? 1 : 0;
  // What the radio holds for its access point. Until WLED has opened the access point,
  // that is the configuration of the start before.
  wifi_config_t radio;
  const bool known = apActive && esp_wifi_get_config(WIFI_IF_AP, &radio) == ESP_OK;
  line += F(",\"ap_name\":");
  if (known) {
    size_t length = radio.ap.ssid_len;
    if (length == 0) length = strnlen((const char *)radio.ap.ssid, sizeof(radio.ap.ssid));
    length = std::min(length, sizeof(radio.ap.ssid));
    line += '"';
    for (size_t i = 0; i < length; i++) {
      const uint8_t byte = radio.ap.ssid[i];
      if (byte < 0x20 || byte > 0x7E || byte == '"' || byte == '\\') {
        char escaped[7];
        snprintf(escaped, sizeof(escaped), "\\u%04x", (unsigned)byte);
        line += escaped;
      } else {
        line += (char)byte;
      }
    }
    line += '"';
  } else {
    line += F("null");
  }
  line += F(",\"ap_auth\":");
  if (known) {
    line += (uint32_t)radio.ap.authmode;
  } else {
    line += F("null");
  }
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

void OdrigProbe::polled(uint32_t poll_us, bool read_second) {
  portENTER_CRITICAL(&pollGuard);
  pollUsNow += poll_us;
  if (poll_us > longestPollUs) longestPollUs = poll_us;
  if (read_second) {
    checkSteps++;
    checkTotalUs += poll_us;
    if (poll_us > checkLongestUs) checkLongestUs = poll_us;
  }
  portEXIT_CRITICAL(&pollGuard);
}

bool OdrigProbe::storing() { return storeAt != STORE_IDLE; }

void OdrigProbe::storeStep() {
  void *ctx = storeHost.ctx;
  const int64_t began = esp_timer_get_time();
  if (storeAt == STORE_SEED) {
    // A small file under the name the trial's file is renamed onto.
    memset(storePiece, 0xEE, STORE_SEED_BYTES);
    const bool seeded = storeHost.write_open(ctx, STORE_NAME) == 1 && storeHost.write(ctx, storePiece, STORE_SEED_BYTES) == 1 &&
                        storeHost.write_close(ctx) == 1;
    storeSeedUs = sinceUs(began);
    if (!seeded) return storeAnswer("seed");
    storeAt = STORE_OPEN;
  } else if (storeAt == STORE_OPEN) {
    const bool opened = storeHost.write_open(ctx, STORE_PART) == 1;
    storeOpenUs = sinceUs(began);
    if (!opened) return storeAnswer("open");
    storeWriteBeganUs = storeWriteEndedUs = esp_timer_get_time();
    storeAt = storeBytes ? STORE_WRITE : STORE_CLOSE;
  } else if (storeAt == STORE_WRITE) {
    const size_t length = std::min((size_t)(storeBytes - storeWritten), STORE_PIECE);
    for (size_t i = 0; i < length; i++) {
      storePiece[i] = storeByteAt(storeWritten + i);
      storeCrcWritten = crcOf(storeCrcWritten, storePiece[i]);
    }
    const int64_t writeBegan = esp_timer_get_time();
    const bool taken = storeHost.write(ctx, storePiece, length) == 1;
    storeWrites.add(sinceUs(writeBegan));
    storeWriteEndedUs = esp_timer_get_time();
    if (!taken) return storeAnswer("write");
    storeWritten += length;
    if (storeWritten == storeBytes) storeAt = STORE_CLOSE;
  } else if (storeAt == STORE_CLOSE) {
    const bool closed = storeHost.write_close(ctx) == 1;
    storeCloseUs = sinceUs(began);
    if (!closed) return storeAnswer("close");
    storeAt = STORE_RENAME;
  } else if (storeAt == STORE_RENAME) {
    const bool renamed = storeHost.rename(ctx, STORE_PART, STORE_NAME) == 1;
    storeRenameUs = sinceUs(began);
    if (!renamed) return storeAnswer("rename");
    storeAt = STORE_READ;
  } else if (storeAt == STORE_READ) {
    for (uint32_t n = 0; n < STORE_READS_IN_A_STEP && storeAt == STORE_READ; n++) {
      const int64_t readBegan = esp_timer_get_time();
      const int32_t count = storeHost.read_at(ctx, STORE_NAME, storeRead, storePiece, STORE_READ_PIECE);
      storeReads.add(sinceUs(readBegan));
      if (count < 0) return storeAnswer("read");
      for (int32_t i = 0; i < count; i++) storeCrcRead = crcOf(storeCrcRead, storePiece[i]);
      storeRead += (uint32_t)count;
      if (count == 0) storeAt = STORE_REMOVE;
    }
  } else if (storeAt == STORE_REMOVE) {
    // What was read back is the trial's file when the rename replaced the small one.
    const bool same = storeRead == storeBytes && storeCrcRead == storeCrcWritten;
    const bool removed = storeHost.remove(ctx, STORE_NAME) == 1;
    storeRemoveUs = sinceUs(began);
    if (!same) return storeAnswer("read-back");
    if (!removed) return storeAnswer("delete");
    storeAnswer(nullptr);
  }
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
  if (limiterOn() && usedMa() >= limitMa()) limited++;
  readBackTheNextOutputs();
  filledNotShown = false;
  if (reportWaits) {
    reportWaits = false;
    report();
  }
}

namespace {

enum Fit { FIT_NONE, FIT_PART, FIT_PROBE, FIT_STORE };

// What the bytes at the start of a line are: a beginning of a line of the probe build,
// one of its two lines whole, or neither.
Fit fitOf(const char *text, size_t length) {
  if (length <= LINE_LENGTH && memcmp(text, LINE, length) == 0) return length == LINE_LENGTH ? FIT_PROBE : FIT_PART;
  if (length <= STORE_WORD_LENGTH) return memcmp(text, STORE_WORD, length) == 0 ? FIT_PART : FIT_NONE;
  if (memcmp(text, STORE_WORD, STORE_WORD_LENGTH) != 0) return FIT_NONE;
  for (size_t at = STORE_WORD_LENGTH; at < length; at++) {
    if (text[at] == '\n') return at > STORE_WORD_LENGTH && at == length - 1 ? FIT_STORE : FIT_NONE;
    if (text[at] < '0' || text[at] > '9' || at - STORE_WORD_LENGTH >= STORE_DIGITS) return FIT_NONE;
  }
  return FIT_PART;
}

}  // namespace

void OdrigProbe::feed(uint8_t byte, void (*pass)(uint8_t byte)) {
  if (heldBytes > 0 || atLineStart) {
    heldBack[heldBytes] = (char)byte;
    const Fit fit = fitOf(heldBack, heldBytes + 1);
    if (fit == FIT_PART) {
      heldBytes++;
      return;
    }
    if (fit == FIT_PROBE) {
      heldBytes = 0;
      if (filledNotShown) {
        reportWaits = true;
      } else {
        report();
      }
      return;
    }
    if (fit == FIT_STORE) {
      uint64_t bytes = 0;
      for (size_t at = STORE_WORD_LENGTH; at < heldBytes; at++) bytes = bytes * 10 + (uint64_t)(heldBack[at] - '0');
      heldBytes = 0;
      storeBegin(bytes > 0xFFFFFFFFull ? 0xFFFFFFFFu : (uint32_t)bytes);
      return;
    }
    for (size_t i = 0; i < heldBytes; i++) pass((uint8_t)heldBack[i]);
    heldBytes = 0;
  }
  pass(byte);
  atLineStart = byte == '\n';
}

#endif
