#include "odrig_log.h"

#include "wled.h"

namespace {

// The queue: the most lines that wait, each with its length.
const size_t LINES = 32;
char lines[LINES][OdrigLog::LINE_ROOM];
size_t lengths[LINES];
size_t first = 0;
size_t waiting = 0;
uint32_t dropped = 0;
portMUX_TYPE guard = portMUX_INITIALIZER_UNLOCKED;

// The host's own `log`, which the wrapper calls first.
void (*playerLog)(void *ctx, const char *text) = nullptr;

// A whole line into `into`, LINE_ROOM bytes: the mark, the time, the kind and the text,
// every byte of the text that is not printable ASCII as `?`, cut so that the line feed
// fits. Its length.
size_t made(char *into, uint64_t ms, const char *kind, const char *text) {
  const int begun = snprintf(into, OdrigLog::LINE_ROOM, "#log %u.%03u %s: ", (unsigned)(ms / 1000), (unsigned)(ms % 1000), kind);
  if (begun < 0) return 0;
  size_t length = std::min((size_t)begun, OdrigLog::LINE_ROOM - 1);
  for (; *text != 0 && length < OdrigLog::LINE_ROOM - 1; text++) {
    const char c = *text;
    into[length++] = c < 0x20 || c > 0x7e ? '?' : c;
  }
  into[length++] = '\n';
  return length;
}

uint64_t nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }

void logLine(void *ctx, const char *text) {
  if (playerLog != nullptr) playerLog(ctx, text);
  OdrigLog::add("player", text);
}

}  // namespace

void OdrigLog::add(const char *kind, const char *text) {
  char line[LINE_ROOM];
  const size_t length = made(line, nowMs(), kind, text);
  if (length == 0) return;
  portENTER_CRITICAL(&guard);
  if (waiting == LINES) {
    first = (first + 1) % LINES;
    waiting--;
    dropped++;
  }
  const size_t at = (first + waiting) % LINES;
  memcpy(lines[at], line, length);
  lengths[at] = length;
  waiting++;
  portEXIT_CRITICAL(&guard);
}

size_t OdrigLog::take(char *line, size_t room, size_t most) {
  const size_t fits = std::min(room, most);
  uint32_t lost = 0;
  size_t length = 0;
  portENTER_CRITICAL(&guard);
  if (dropped != 0) {
    if (fits >= LINE_ROOM) {
      lost = dropped;
      dropped = 0;
    }
  } else if (waiting > 0 && lengths[first] <= fits) {
    length = lengths[first];
    memcpy(line, lines[first], length);
    first = (first + 1) % LINES;
    waiting--;
  }
  portEXIT_CRITICAL(&guard);
  if (lost == 0) return length;
  char text[32];
  snprintf(text, sizeof(text), "%u lines dropped", (unsigned)lost);
  return made(line, nowMs(), "log", text);
}

odrig_host OdrigLog::withLog(const odrig_host &given) {
  odrig_host wrapped = given;
  playerLog = given.log;
  wrapped.log = logLine;
  return wrapped;
}
