// A program for the tests of the wall's default budget, which knows nothing of the chip.
//
//   limit_default <maximum> ...
//   limit_default all
//
// prints one line of JSON: the default budget in mA for each maximum given, in their
// order, or with `all` for every maximum from 0 to 65,535, WLED's whole range.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "odrig_limit_default.h"

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  const bool every = strcmp(argv[1], "all") == 0;
  const unsigned long count = every ? 65536ul : (unsigned long)(argc - 1);
  putchar('[');
  for (unsigned long i = 0; i < count; ++i) {
    const unsigned long maximum = every ? i : strtoul(argv[i + 1], nullptr, 10);
    printf("%s%lu", i == 0 ? "" : ",", (unsigned long)odrigWallDefault((uint32_t)maximum));
  }
  printf("]\n");
  return 0;
}
