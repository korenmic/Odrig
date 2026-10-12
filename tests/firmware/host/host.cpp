// A program for the tests of the parts of the standalone firmware that know nothing of
// the chip. It reads one case from standard input and prints the result as one line of
// JSON.
//
//   host settings
//     input:  "config <bytes>\n" and that many bytes, or "config absent\n";
//             then the same for "secrets".
//     output: the settings; the name and the password in hexadecimal.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>
#include <vector>

#include "settings.h"

namespace {

bool readFile(const char *label, std::vector<char> &bytes, bool &present) {
  char word[16], amount[16];
  if (scanf("%15s %15s", word, amount) != 2 || strcmp(word, label) != 0) return false;
  if (getchar() != '\n') return false;
  present = strcmp(amount, "absent") != 0;
  if (!present) return true;
  bytes.resize((size_t)strtoul(amount, nullptr, 10));
  return bytes.empty() || fread(bytes.data(), 1, bytes.size(), stdin) == bytes.size();
}

std::string hex(const char *text) {
  std::string made;
  char pair[3];
  for (const char *at = text; *at; at++) {
    snprintf(pair, sizeof(pair), "%02x", (unsigned char)*at);
    made += pair;
  }
  return made;
}

int settings() {
  std::vector<char> config, secrets;
  bool hasConfig = false, hasSecrets = false;
  if (!readFile("config", config, hasConfig) || !readFile("secrets", secrets, hasSecrets)) return 2;
  // Each file is handed over in a block of exactly its size, so that a read past its end
  // is seen by the checks this program is built with.
  char *exactConfig = hasConfig ? (char *)malloc(config.size() ? config.size() : 1) : nullptr;
  char *exactSecrets = hasSecrets ? (char *)malloc(secrets.size() ? secrets.size() : 1) : nullptr;
  if (hasConfig && !config.empty()) memcpy(exactConfig, config.data(), config.size());
  if (hasSecrets && !secrets.empty()) memcpy(exactSecrets, secrets.data(), secrets.size());
  const OdrigSettings found = odrigSettings(exactConfig, config.size(), exactSecrets, secrets.size());
  free(exactConfig);
  free(exactSecrets);
  printf("{\"network\":%s,\"name\":\"%s\",\"password\":\"%s\",\"channel\":%u,\"hidden\":%s,\"limit_ma\":%u}\n",
         found.network ? "true" : "false", hex(found.name).c_str(), hex(found.password).c_str(), (unsigned)found.channel,
         found.hidden ? "true" : "false", (unsigned)found.limit_ma);
  return 0;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc == 2 && strcmp(argv[1], "settings") == 0) return settings();
  fprintf(stderr, "usage: host settings\n");
  return 2;
}
