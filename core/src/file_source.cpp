#include "file_source.h"

namespace odrig {

Reason FileSource::open(const odrig_host &from, const char *name) {
    close();
    host = &from;
    taken = 0;
    int opened = host->open(host->ctx, name);
    if (opened == 1) {
        is_open = 1;
        return kNone;
    }
    return opened == 0 ? kFileMissing : kReadError;
}

void FileSource::close() {
    if (is_open) {
        host->close(host->ctx);
        is_open = 0;
    }
    position = 0;
    length = 0;
    stopped = 0;
}

int FileSource::refill() {
    if (!is_open) {
        return -kEnd;
    }
    if (stopped != 0) {
        return stopped;
    }
    int32_t count = host->read(host->ctx, buffer, kFileBufferSize);
    if (count == 0) {
        stopped = -kEnd;
        return stopped;
    }
    if (count < 0 || count > static_cast<int32_t>(kFileBufferSize)) {
        stopped = -kReadError;
        return stopped;
    }
    taken += static_cast<uint32_t>(count);
    length = static_cast<uint16_t>(count);
    position = 1;
    return buffer[0];
}

}  // namespace odrig
