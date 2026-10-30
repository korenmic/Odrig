#include "file_source.h"

#include "crc32.h"

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

void FileSource::open_at(const odrig_host &from, const char *name) {
    close();
    host = &from;
    at_name = name;
    taken = 0;
    crc = kCrcStart;
    is_open = 1;
}

void FileSource::close() {
    if (is_open && at_name == nullptr) {
        host->close(host->ctx);
    }
    is_open = 0;
    at_name = nullptr;
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
    int32_t count;
    if (at_name != nullptr) {
        count = host->read_at(host->ctx, at_name, taken, buffer, sizeof buffer);
    } else {
        count = host->read(host->ctx, buffer, sizeof buffer);
    }
    if (count == 0) {
        stopped = -kEnd;
        return stopped;
    }
    if (count < 0 || count > static_cast<int32_t>(sizeof buffer)) {
        stopped = -kReadError;
        return stopped;
    }
    for (int32_t at = 0; at_name != nullptr && at < count; ++at) {
        crc = crc_add(crc, buffer[at]);
    }
    taken += static_cast<uint32_t>(count);
    length = static_cast<uint16_t>(count);
    position = 1;
    return buffer[0];
}

int32_t FileSource::look(uint32_t want) {
    if (want > sizeof buffer) return -1;
    while (is_open && stopped == 0 && length < want) {
        const size_t room = sizeof buffer - length;
        int32_t count;
        if (at_name != nullptr) {
            count = host->read_at(host->ctx, at_name, taken, buffer + length, room);
        } else {
            count = host->read(host->ctx, buffer + length, room);
        }
        if (count == 0) {
            break;
        }
        if (count < 0 || count > static_cast<int32_t>(room)) {
            stopped = -kReadError;
            return -1;
        }
        for (int32_t at = 0; at_name != nullptr && at < count; ++at) {
            crc = crc_add(crc, buffer[length + at]);
        }
        taken += static_cast<uint32_t>(count);
        length = static_cast<uint16_t>(length + count);
    }
    return length;
}

}  // namespace odrig
