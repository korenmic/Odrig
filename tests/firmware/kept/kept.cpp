// A program for the tests of the firmware's kept record, which knows nothing of the chip.
//
//   kept <case> [text]
//
// writes the text into a record, or leaves it as the case says, takes the record once
// and twice, and prints one line of JSON: whether each take gave a text, and the text.
// The cases: `sound`, `mark` (the mark is changed), `crc` (a byte of the text is changed),
// `length` (the length is past the room), `zero` (a record of zeros).
#include <stdio.h>
#include <string.h>

#include "odrig_kept.h"

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  OdrigKept kept;
  memset(&kept, 0, sizeof(kept));
  const char *text = argc > 2 ? argv[2] : "";
  if (strcmp(argv[1], "zero") != 0) OdrigKeep::put(kept, text);
  if (strcmp(argv[1], "mark") == 0) kept.mark ^= 1;
  if (strcmp(argv[1], "crc") == 0) kept.text[0] ^= 1;
  if (strcmp(argv[1], "length") == 0) kept.length = 60000;
  char out[96];
  const bool first = OdrigKeep::take(kept, out);
  printf("{\"first\":%s,\"text\":\"", first ? "true" : "false");
  for (const char *at = first ? out : ""; *at != 0; ++at) {
    if (*at == '"' || *at == '\\') putchar('\\');
    putchar(*at);
  }
  char again[96];
  const bool second = OdrigKeep::take(kept, again);
  printf("\",\"second\":%s}\n", second ? "true" : "false");
  return 0;
}
