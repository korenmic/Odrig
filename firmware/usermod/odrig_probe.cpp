#ifdef ODRIG_PROBE

#include "odrig_probe.h"

#include "wled.h"

#include "odrig_leds.h"
#include "odrig_serial.h"

namespace {

const char LINE[] = "#probe\n";
const size_t LINE_LENGTH = sizeof(LINE) - 1;
const uint32_t MAX_OUTPUTS = 32;

size_t matched = 0;
bool atLineStart = true;

uint32_t startMs = 0;
const char *(*errorNow)() = nullptr;
bool counting = false;
uint64_t secondStart = 0;
uint32_t loopsNow = 0, loopsLast = 0;
uint32_t sentNow = 0, sentLast = 0;
uint64_t lastSendMs = 0;
bool sentBefore = false;
uint32_t longestGapMs = 0, longestPollUs = 0, longestSendUs = 0;
uint32_t overwritten = 0, limited = 0;
uint32_t held[MAX_OUTPUTS];
bool heldValid = false;

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

// The current the limiter allows the LEDs, and the current it estimated for the last send.
uint32_t limitMa() {
  const uint32_t all = BusManager::ablMilliampsMax();
  return all > MA_FOR_ESP ? all - MA_FOR_ESP : 0;
}
uint32_t usedMa() { return BusManager::currentMilliamps() - MA_FOR_ESP; }

void report() {
  String line;
  line.reserve(1536);
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
  line += F(",\"overwritten\":");
  line += overwritten;
  line += F(",\"limited\":");
  line += limited;
  line += F(",\"limit_ma\":");
  line += limitMa();
  line += F(",\"used_ma\":");
  line += usedMa();
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
    snprintf(crc, sizeof(crc), "%08x", (unsigned)crcOfOutput(bus));
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
    line += F("\"}");
  }
  line += F("]}\n");
  OdrigSerial::write(line.c_str(), line.length());
  longestGapMs = longestPollUs = longestSendUs = 0;
  limited = 0;
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
    loopsNow = sentNow = 0;
    secondStart += 1000;
  }
  loopsNow++;
}

void OdrigProbe::polled(uint32_t poll_us) {
  if (poll_us > longestPollUs) longestPollUs = poll_us;
}

void OdrigProbe::beforeSend() {
  if (!heldValid) return;
  const uint32_t count = outputs();
  for (uint32_t i = 0; i < count; i++) {
    if (crcOfOutput(BusManager::getBus(i)) != held[i]) {
      overwritten++;
      return;
    }
  }
}

void OdrigProbe::afterSend(uint64_t now_ms, uint32_t send_us) {
  sentNow++;
  if (send_us > longestSendUs) longestSendUs = send_us;
  if (sentBefore && now_ms - lastSendMs > longestGapMs) longestGapMs = (uint32_t)(now_ms - lastSendMs);
  sentBefore = true;
  lastSendMs = now_ms;
  if (usedMa() >= limitMa()) limited++;
  const uint32_t count = outputs();
  for (uint32_t i = 0; i < count; i++) held[i] = crcOfOutput(BusManager::getBus(i));
  heldValid = true;
}

void OdrigProbe::feed(uint8_t byte, void (*pass)(uint8_t byte)) {
  if ((matched > 0 || atLineStart) && byte == (uint8_t)LINE[matched]) {
    if (++matched == LINE_LENGTH) {
      matched = 0;
      report();
    }
    return;
  }
  for (size_t i = 0; i < matched; i++) pass((uint8_t)LINE[i]);
  matched = 0;
  pass(byte);
  atLineStart = byte == '\n';
}

#endif
