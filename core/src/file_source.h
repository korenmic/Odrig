#ifndef ODRIG_FILE_SOURCE_H
#define ODRIG_FILE_SOURCE_H

#include <stdint.h>

#include "odrig_core.h"
#include "reasons.h"

namespace odrig {

// The most bytes the core asks the host for in one read.
const uint32_t kFileBufferSize = 512;

// One file of the host, read from its first byte to its last without going back. The core
// has one of these, so one file is open at a time.
struct FileSource {
    // Closes the file that is open, if any, and opens the named one. Returns kNone,
    // kFileMissing when the host has no such file, or kReadError.
    Reason open(const odrig_host &from, const char *name);

    // The next byte, 0 to 255; or -kEnd at the end of the file; or -kReadError when the
    // host reports a failure. After either, every later call returns the same.
    int get() {
        if (position < length) {
            return buffer[position++];
        }
        return refill();
    }

    void close();

    int refill();

    const odrig_host *host;
    uint16_t position;
    uint16_t length;
    uint8_t is_open;
    int8_t stopped;
    uint8_t buffer[kFileBufferSize];
};

}  // namespace odrig

#endif
