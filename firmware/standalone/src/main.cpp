// A trial of what the standalone firmware stands on, without WLED: the board's storage
// mounted and not formatted, twenty LED outputs of 180 LEDs, four on the RMT driver and
// sixteen on the parallel driver, sent 50 times a second, and the USB serial port. It
// answers the line `#probe` with what it found, as one line of JSON.
#include <Arduino.h>
#include <LittleFS.h>
#include <NeoPixelBus.h>

#include "driver/pcnt.h"
#include "esp_heap_caps.h"
#include "esp_rom_gpio.h"
#include "esp_timer.h"
#include "soc/pcnt_periph.h"

namespace {

const uint32_t LEGS = 20;
const uint32_t RMT_LEGS = 4;
const uint16_t LEDS = 180;
// The pins of the legs of the target mapping, in the order of the legs.
const uint8_t PINS[LEGS] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 47};
const uint32_t REFRESH_MS = 20;
// Dim enough for a strip that is fed from the board's 3.3 V pin.
const uint8_t LEVEL = 6;
const char FOLDER[] = "/odrig";

typedef NeoPixelBus<NeoGrbFeature, NeoEsp32RmtNWs2812xMethod> RmtOutput;
typedef NeoPixelBus<NeoGrbFeature, NeoEsp32LcdX16Ws2812xMethod> ParallelOutput;

RmtOutput *rmt[RMT_LEGS];
ParallelOutput *parallel[LEGS - RMT_LEGS];

bool mounted = false;
uint64_t lastSendMs = 0;
uint32_t frame = 0;
uint32_t sentNow = 0, sentLast = 0, longestSendUs = 0;
uint64_t secondStartMs = 0;

// The pulses: the rising edges on the pin of one output during one send, counted by the
// chip's pulse counter, for one output at each send.
const pcnt_unit_t COUNTER = PCNT_UNIT_0;
const int32_t NOT_COUNTED = -1;
const uint32_t NO_OUTPUT = LEGS;
bool counterReady = false;
int32_t pulses[LEGS];
uint32_t countedOutput = NO_OUTPUT, nextToCount = 0;

char line[16];
size_t lineLength = 0;

uint64_t nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }

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
    counterReady = true;
  }
  pcnt_counter_pause(COUNTER);
  PIN_INPUT_ENABLE(GPIO_PIN_MUX_REG[pin]);
  esp_rom_gpio_connect_in_signal(pin, pcnt_periph_signals.groups[0].units[COUNTER].channels[0].pulse_sig, false);
  pcnt_counter_clear(COUNTER);
  pcnt_counter_resume(COUNTER);
}

void readTheCountedOutput() {
  if (countedOutput == NO_OUTPUT) return;
  int16_t counted = 0;
  pcnt_counter_pause(COUNTER);
  pcnt_get_counter_value(COUNTER, &counted);
  pulses[countedOutput] = counted;
  countedOutput = NO_OUTPUT;
}

bool canAllShow() {
  for (uint32_t i = 0; i < RMT_LEGS; i++) {
    if (!rmt[i]->CanShow()) return false;
  }
  for (uint32_t i = 0; i < LEGS - RMT_LEGS; i++) {
    if (!parallel[i]->CanShow()) return false;
  }
  return true;
}

// A dim point of light that walks along every leg, a step at each refresh.
void fill() {
  const RgbColor lit(LEVEL, LEVEL, LEVEL), dark(0, 0, 0);
  for (uint32_t i = 0; i < LEGS; i++) {
    for (uint16_t n = 0; n < LEDS; n++) {
      const RgbColor &colour = (n + frame) % 12 == 0 ? lit : dark;
      if (i < RMT_LEGS) {
        rmt[i]->SetPixelColor(n, colour);
      } else {
        parallel[i - RMT_LEGS]->SetPixelColor(n, colour);
      }
    }
  }
  frame++;
}

void show() {
  for (uint32_t i = 0; i < RMT_LEGS; i++) rmt[i]->Show();
  for (uint32_t i = 0; i < LEGS - RMT_LEGS; i++) parallel[i]->Show();
}

void report() {
  String text;
  text.reserve(2048);
  text += F("{\"probe\":1,\"firmware\":\"standalone-trial\",\"mounted\":");
  text += mounted ? F("true") : F("false");
  text += F(",\"files\":[");
  if (mounted) {
    File folder = LittleFS.open(FOLDER);
    bool first = true;
    for (File file = folder ? folder.openNextFile() : File(); file; file = folder.openNextFile()) {
      if (!first) text += ',';
      first = false;
      text += F("[\"");
      text += file.name();
      text += F("\",");
      text += (uint32_t)file.size();
      text += ']';
    }
  }
  text += F("],\"sent\":");
  text += sentLast;
  text += F(",\"send_us\":");
  text += longestSendUs;
  text += F(",\"heap\":");
  text += (uint32_t)heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  text += F(",\"external\":");
  text += (uint32_t)heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
  text += F(",\"outputs\":[");
  for (uint32_t i = 0; i < LEGS; i++) {
    if (i) text += ',';
    text += F("{\"leg\":");
    text += i + 1;
    text += F(",\"pin\":");
    text += PINS[i];
    text += F(",\"count\":");
    text += LEDS;
    text += F(",\"driver\":\"");
    text += i < RMT_LEGS ? F("rmt") : F("parallel");
    text += F("\",\"pulses\":");
    if (pulses[i] == NOT_COUNTED) {
      text += F("null");
    } else {
      text += pulses[i];
    }
    text += '}';
  }
  text += F("]}\n");
  longestSendUs = 0;
  Serial.print(text);
}

void readThePort() {
  while (Serial.available() > 0) {
    const int byte = Serial.read();
    if (byte == '\n') {
      line[lineLength] = 0;
      if (strcmp(line, "#probe") == 0) report();
      lineLength = 0;
    } else if (byte != '\r' && lineLength < sizeof(line) - 1) {
      line[lineLength++] = (char)byte;
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  mounted = LittleFS.begin(false);
  for (uint32_t i = 0; i < LEGS; i++) pulses[i] = NOT_COUNTED;
  for (uint32_t i = 0; i < RMT_LEGS; i++) {
    rmt[i] = new RmtOutput(LEDS, PINS[i], (NeoBusChannel)i);
    rmt[i]->Begin();
  }
  for (uint32_t i = 0; i < LEGS - RMT_LEGS; i++) {
    parallel[i] = new ParallelOutput(LEDS, PINS[RMT_LEGS + i]);
    parallel[i]->Begin();
  }
  secondStartMs = lastSendMs = nowMs();
}

void loop() {
  readThePort();
  const uint64_t now = nowMs();
  if (now - secondStartMs >= 1000) {
    sentLast = sentNow;
    sentNow = 0;
    secondStartMs += 1000;
  }
  if (now - lastSendMs < REFRESH_MS || !canAllShow()) return;
  readTheCountedOutput();
  lastSendMs += REFRESH_MS;
  if (now - lastSendMs > 5 * REFRESH_MS) lastSendMs = now;
  fill();
  countedOutput = nextToCount % LEGS;
  nextToCount = countedOutput + 1;
  countPulsesOn(PINS[countedOutput]);
  const int64_t start = esp_timer_get_time();
  show();
  const uint32_t took = (uint32_t)(esp_timer_get_time() - start);
  if (took > longestSendUs) longestSendUs = took;
  sentNow++;
}
