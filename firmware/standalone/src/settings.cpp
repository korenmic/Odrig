#include "settings.h"

#include <string.h>

namespace {

const int DEEPEST = 32;
const size_t LONGEST_PATH = 3;

// One thing looked for in a file: a member at a path of names, as a text or as a whole
// number. `seen` says that the member was met; `usable` that its value could be taken.
struct Wanted {
  const char *path[LONGEST_PATH];
  size_t depth;
  bool text;
  char *into;
  size_t capacity;
  size_t length;
  uint32_t number;
  bool seen;
  bool usable;
};

struct Walk {
  const char *at;
  const char *end;
  Wanted *wanted;
  size_t count;
  // The names of the members the walk is inside of, as they stand in the text.
  const char *names[LONGEST_PATH];
  size_t lengths[LONGEST_PATH];
};

void skipSpace(Walk &walk) {
  while (walk.at < walk.end && (*walk.at == ' ' || *walk.at == '\t' || *walk.at == '\n' || *walk.at == '\r')) walk.at++;
}

bool isDigit(char byte) { return byte >= '0' && byte <= '9'; }

bool isHex(char byte) { return isDigit(byte) || (byte >= 'a' && byte <= 'f') || (byte >= 'A' && byte <= 'F'); }

// What is wanted at the place the walk stands at, `depth` names deep, or a null pointer.
// A member that was met before is not taken again: the first one counts.
Wanted *wantedAt(Walk &walk, size_t depth) {
  if (depth == 0 || depth > LONGEST_PATH) return nullptr;
  for (size_t i = 0; i < walk.count; i++) {
    Wanted &wanted = walk.wanted[i];
    if (wanted.depth != depth || wanted.seen) continue;
    bool same = true;
    for (size_t n = 0; n < depth && same; n++) {
      same = strlen(wanted.path[n]) == walk.lengths[n] && memcmp(wanted.path[n], walk.names[n], walk.lengths[n]) == 0;
    }
    if (same) return &wanted;
  }
  return nullptr;
}

// Reads a string, the walk standing on its opening mark. With `wanted`, its bytes are
// taken: a mark, a backslash and a slash may be written with a backslash, and a string
// with any other escape, or one too long, is read and not taken.
bool readString(Walk &walk, Wanted *wanted, const char **start, size_t *length) {
  walk.at++;
  if (start != nullptr) *start = walk.at;
  bool takes = wanted != nullptr && wanted->text;
  size_t taken = 0;
  for (;;) {
    if (walk.at >= walk.end) return false;
    const unsigned char byte = (unsigned char)*walk.at;
    if (byte == '"') break;
    if (byte < 0x20) return false;
    char plain = (char)byte;
    if (byte == '\\') {
      if (walk.end - walk.at < 2) return false;
      const char escaped = walk.at[1];
      if (escaped == 'u') {
        if (walk.end - walk.at < 6 || !isHex(walk.at[2]) || !isHex(walk.at[3]) || !isHex(walk.at[4]) || !isHex(walk.at[5])) return false;
        walk.at += 6;
        takes = false;
        continue;
      }
      if (strchr("\"\\/bfnrt", escaped) == nullptr) return false;
      if (escaped != '"' && escaped != '\\' && escaped != '/') takes = false;
      plain = escaped;
      walk.at += 2;
    } else {
      walk.at++;
    }
    if (takes) {
      if (taken < wanted->capacity) {
        wanted->into[taken++] = plain;
      } else {
        takes = false;
      }
    }
  }
  if (length != nullptr) *length = (size_t)(walk.at - *start);
  walk.at++;
  if (wanted != nullptr) {
    wanted->seen = true;
    wanted->usable = takes;
    wanted->length = takes ? taken : 0;
  }
  return true;
}

// Reads a number. With `wanted`, it is taken when it is a whole number written in digits
// alone, and small enough to count.
bool readNumber(Walk &walk, Wanted *wanted) {
  const char *start = walk.at;
  if (walk.at < walk.end && *walk.at == '-') walk.at++;
  if (walk.at >= walk.end || !isDigit(*walk.at)) return false;
  if (*walk.at == '0') {
    walk.at++;
  } else {
    while (walk.at < walk.end && isDigit(*walk.at)) walk.at++;
  }
  const char *whole = walk.at;
  if (walk.at < walk.end && *walk.at == '.') {
    walk.at++;
    if (walk.at >= walk.end || !isDigit(*walk.at)) return false;
    while (walk.at < walk.end && isDigit(*walk.at)) walk.at++;
  }
  if (walk.at < walk.end && (*walk.at == 'e' || *walk.at == 'E')) {
    walk.at++;
    if (walk.at < walk.end && (*walk.at == '+' || *walk.at == '-')) walk.at++;
    if (walk.at >= walk.end || !isDigit(*walk.at)) return false;
    while (walk.at < walk.end && isDigit(*walk.at)) walk.at++;
  }
  if (wanted != nullptr) {
    wanted->seen = true;
    wanted->usable = !wanted->text && *start != '-' && whole == walk.at && whole - start <= 9;
    wanted->number = 0;
    for (const char *digit = start; wanted->usable && digit < whole; digit++) wanted->number = wanted->number * 10 + (uint32_t)(*digit - '0');
  }
  return true;
}

bool readWord(Walk &walk, const char *word) {
  const size_t length = strlen(word);
  if ((size_t)(walk.end - walk.at) < length || memcmp(walk.at, word, length) != 0) return false;
  walk.at += length;
  return true;
}

// Reads one value. `depth` is the number of member names the value lies under, or more
// than a path can have where no path leads: inside an array, or too deep.
bool readValue(Walk &walk, size_t depth, int nesting) {
  if (nesting > DEEPEST) return false;
  skipSpace(walk);
  if (walk.at >= walk.end) return false;
  Wanted *wanted = wantedAt(walk, depth);
  const char first = *walk.at;
  if (first == '"') return readString(walk, wanted, nullptr, nullptr);
  if (first == '-' || isDigit(first)) return readNumber(walk, wanted);
  if (wanted != nullptr) wanted->seen = true;
  if (first == 't') return readWord(walk, "true");
  if (first == 'f') return readWord(walk, "false");
  if (first == 'n') return readWord(walk, "null");
  if (first == '[') {
    walk.at++;
    skipSpace(walk);
    if (walk.at < walk.end && *walk.at == ']') {
      walk.at++;
      return true;
    }
    for (;;) {
      if (!readValue(walk, LONGEST_PATH + 1, nesting + 1)) return false;
      skipSpace(walk);
      if (walk.at >= walk.end) return false;
      if (*walk.at == ']') break;
      if (*walk.at != ',') return false;
      walk.at++;
    }
    walk.at++;
    return true;
  }
  if (first != '{') return false;
  walk.at++;
  skipSpace(walk);
  if (walk.at < walk.end && *walk.at == '}') {
    walk.at++;
    return true;
  }
  for (;;) {
    skipSpace(walk);
    if (walk.at >= walk.end || *walk.at != '"') return false;
    const char *name = nullptr;
    size_t length = 0;
    if (!readString(walk, nullptr, &name, &length)) return false;
    skipSpace(walk);
    if (walk.at >= walk.end || *walk.at != ':') return false;
    walk.at++;
    if (depth < LONGEST_PATH) {
      walk.names[depth] = name;
      walk.lengths[depth] = length;
    }
    if (!readValue(walk, depth < LONGEST_PATH ? depth + 1 : LONGEST_PATH + 1, nesting + 1)) return false;
    skipSpace(walk);
    if (walk.at >= walk.end) return false;
    if (*walk.at == '}') break;
    if (*walk.at != ',') return false;
    walk.at++;
  }
  walk.at++;
  return true;
}

// Walks a whole file, which must be one JSON object and nothing else. When it is not,
// nothing of it counts.
void readFile(const char *text, size_t length, Wanted *wanted, size_t count) {
  bool whole = text != nullptr && length <= ODRIG_SETTINGS_LONGEST;
  if (whole) {
    Walk walk = {text, text + length, wanted, count, {nullptr, nullptr, nullptr}, {0, 0, 0}};
    skipSpace(walk);
    whole = walk.at < walk.end && *walk.at == '{' && readValue(walk, 0, 0);
    skipSpace(walk);
    whole = whole && walk.at == walk.end;
  }
  if (!whole) {
    for (size_t i = 0; i < count; i++) wanted[i].seen = wanted[i].usable = false;
  }
}

bool numberIn(const Wanted &wanted, uint32_t lowest, uint32_t highest) {
  return wanted.seen && wanted.usable && wanted.number >= lowest && wanted.number <= highest;
}

}  // namespace

OdrigSettings odrigSettings(const char *config, size_t configLength, const char *secrets, size_t secretsLength) {
  OdrigSettings settings;
  memset(&settings, 0, sizeof(settings));

  Wanted ofConfig[] = {
    {{"ap", "ssid", nullptr}, 2, true, settings.name, ODRIG_NAME_LONGEST, 0, 0, false, false},
    {{"ap", "chan", nullptr}, 2, false, nullptr, 0, 0, 0, false, false},
    {{"ap", "hide", nullptr}, 2, false, nullptr, 0, 0, 0, false, false},
    {{"hw", "led", "maxpwr"}, 3, false, nullptr, 0, 0, 0, false, false},
  };
  readFile(config, configLength, ofConfig, sizeof(ofConfig) / sizeof(ofConfig[0]));
  Wanted ofSecrets[] = {
    {{"ap", "psk", nullptr}, 2, true, settings.password, ODRIG_PASSWORD_LONGEST, 0, 0, false, false},
  };
  readFile(secrets, secretsLength, ofSecrets, sizeof(ofSecrets) / sizeof(ofSecrets[0]));

  const Wanted &name = ofConfig[0], &password = ofSecrets[0];
  const bool named = name.seen && name.usable && name.length >= 1;
  const bool locked = password.seen && password.usable && password.length >= ODRIG_PASSWORD_SHORTEST;
  settings.network = named && locked;
  settings.name[settings.network ? name.length : 0] = 0;
  settings.password[settings.network ? password.length : 0] = 0;
  if (!settings.network) {
    memset(settings.name, 0, sizeof(settings.name));
    memset(settings.password, 0, sizeof(settings.password));
  }
  settings.channel = numberIn(ofConfig[1], 1, 13) ? (uint8_t)ofConfig[1].number : ODRIG_CHANNEL_DEFAULT;
  settings.hidden = numberIn(ofConfig[2], 1, 0xFFFFFFFF);
  settings.limit_ma = numberIn(ofConfig[3], 0, 65535) ? (uint16_t)ofConfig[3].number : ODRIG_LIMIT_DEFAULT_MA;
  return settings;
}
