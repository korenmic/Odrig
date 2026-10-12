#ifndef ODRIG_FILE_SOURCE_H
#define ODRIG_FILE_SOURCE_H

#include <stdint.h>

#include "odrig_core.h"
#include "reasons.h"

namespace odrig {

// The most bytes the core asks the host for in one read.
const uint32_t kFileBufferSize = 512;

// One file of the host, read from its first byte to its last without going back. The core
// has one of these for the file that `open`, `read` and `close` hold, so one such file is
// open at a time, and a second one that reads another file beside it with `read_at`.
struct FileSource {
    // Closes the file that is open, if any, and opens the named one. Returns kNone,
    // kFileMissing when the host has no such file, or kReadError.
    Reason open(const odrig_host &from, const char *name);

    // Begins to read the named file with the host's `read_at`, from its first byte. The
    // host is asked for nothing yet. The name must stay where it is while the file is
    // read. A CRC-32 of the bytes taken from the host is kept in `crc`.
    void open_at(const odrig_host &from, const char *name);

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
    const char *at_name;    // the file read with `read_at`, or null
    uint32_t taken;         // the bytes the host has handed out since the file was opened
    uint32_t crc;           // the running CRC-32 of those bytes, for a file read with `read_at`
    uint16_t position;
    uint16_t length;
    uint8_t is_open;
    int8_t stopped;
    uint8_t buffer[kFileBufferSize];
};

}  // namespace odrig

#endif
