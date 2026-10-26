// What the core needs from its host on the board: memory, the time, the files of the
// installed show in the folder /odrig of storage, which it reads, writes, renames and
// removes there and nowhere else, and a place for its diagnostic text.
#pragma once

#include <stdint.h>

#include "odrig_core.h"

namespace OdrigFiles {

// The host functions to start the core with. The first call asks the file system for
// its space, once; afterwards the space is kept up from the storage calls.
odrig_host host();

// Milliseconds since the chip started, from a 64-bit clock that does not go backwards
// and does not wrap.
uint64_t nowMs();

// The core's last line of diagnostic text, or an empty text.
const char *lastLog();

// The pacing. A storage call stops the task that makes it for as long as the flash takes,
// and the request for a refresh waits behind it. So every storage call is timed, and
// after storage calls that took d together no further command line is to reach the core
// before twice that time has passed, and 20 ms at least. This is true while a line has
// to wait. Whoever carries lines asks it before handing one on, and does not look into
// the line.
bool holding();

// A storage call made apart from these functions, a change of the drive's files: it is
// timed as theirs are, from its making to the end of its block, so that `holding` holds the
// command lines back after it too.
class StorageCall {
 public:
  StorageCall();
  ~StorageCall();

 private:
  int64_t startUs;
};

#ifdef ODRIG_PROBE
// The storage calls since the last call of this function: their number, the longest and
// the sum of their times in microseconds.
struct StoreTimes {
  uint32_t calls;
  uint32_t longestUs;
  uint32_t totalUs;
};
StoreTimes takeStoreTimes();

// The number of reads of a second file so far.
uint32_t secondReads();

// How long the file system took to tell its space, the one time it was asked.
uint32_t spaceAskedMicros();
#endif

}  // namespace OdrigFiles
