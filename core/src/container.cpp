#include "container.h"

#include <string.h>

#include "text.h"

namespace odrig {

namespace {

const uint8_t kMagic[4] = {0x4F, 0x44, 0x52, 0x58};
const uint8_t kContainerVersion = 1;

// The version of each content type the core reads, 0 for a type it does not read, and the
// most bytes its payload may have.
uint8_t version_of(uint8_t type) {
    return type == kTypeFrames || type == kTypeText ? 1 : 0;
}

uint32_t largest_payload(uint8_t type) {
    return type == kTypeText ? kLargestTextPayload : 0xFFFFFFFFu;
}

// The next byte of the header, or the reason the file ends.
Reason header_byte(FileSource *file, uint8_t *byte) {
    const int got = file->get();
    if (got >= 0) {
        *byte = static_cast<uint8_t>(got);
        return kNone;
    }
    return got == -kReadError ? kReadError : kTruncated;
}

}  // namespace

Reason content_open(FileSource *file, Inflate *inflate, uint8_t *window, OdrgDecoder *decoder, ContentHeader *header) {
    memset(header, 0, sizeof *header);
    header->type = kTypeFrames;
    const int32_t held = file->look(sizeof kMagic);
    if (held < 0) {
        return kReadError;
    }
    if (held < static_cast<int32_t>(sizeof kMagic) || memcmp(file->buffer, kMagic, sizeof kMagic) != 0) {
        const Reason reason = decoder->open(file, inflate, window);
        header->width = decoder->width;
        header->height = decoder->height;
        return reason;
    }
    uint8_t bytes[kContainerHeaderSize];
    for (uint32_t at = 0; at < kContainerHeaderSize; ++at) {
        const Reason reason = header_byte(file, &bytes[at]);
        if (reason != kNone) {
            return reason;
        }
    }
    header->type = bytes[5];
    header->width = static_cast<uint16_t>(bytes[8] | (bytes[9] << 8));
    header->height = static_cast<uint16_t>(bytes[10] | (bytes[11] << 8));
    header->loop_ms = static_cast<uint32_t>(bytes[12]) | (static_cast<uint32_t>(bytes[13]) << 8) |
                      (static_cast<uint32_t>(bytes[14]) << 16) | (static_cast<uint32_t>(bytes[15]) << 24);
    header->payload = static_cast<uint32_t>(bytes[16]) | (static_cast<uint32_t>(bytes[17]) << 8) |
                      (static_cast<uint32_t>(bytes[18]) << 16) | (static_cast<uint32_t>(bytes[19]) << 24);
    if (bytes[4] != kContainerVersion || bytes[7] != 0) {
        return kBadContainer;
    }
    if (version_of(header->type) == 0) {
        return kUnknownType;
    }
    if (bytes[6] != version_of(header->type)) {
        return kUnknownTypeVersion;
    }
    if (header->width == 0 || header->height == 0) {
        return kZeroSize;
    }
    if (header->payload > largest_payload(header->type)) {
        return kPayloadSize;
    }
    header->container = 1;
    if (is_drawn(header->type)) {
        return kNone;
    }
    const Reason reason = decoder->open(file, inflate, window);
    if (reason != kNone) {
        return reason;
    }
    if (decoder->width != header->width || decoder->height != header->height) {
        return kCanvasMismatch;
    }
    return kNone;
}

Reason content_finish(FileSource *file, OdrgDecoder *decoder, const ContentHeader &header, uint64_t total_ms) {
    if (is_drawn(header.type)) {
        return kNone;
    }
    const Reason reason = decoder->finish();
    if (reason != kNone || !header.container) {
        return reason;
    }
    if (file->taken != kContainerHeaderSize + static_cast<uint64_t>(header.payload)) {
        return kPayloadSize;
    }
    return total_ms == header.loop_ms ? kNone : kLoopMismatch;
}

const char *type_name(uint8_t type) {
    if (type == kTypeText) {
        return "text";
    }
    return type == kTypeWidget ? "widget" : "frames";
}

}  // namespace odrig
