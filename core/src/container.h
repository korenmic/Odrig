#ifndef ODRIG_CONTAINER_H
#define ODRIG_CONTAINER_H

#include <stdint.h>

#include "file_source.h"
#include "inflate.h"
#include "odrg_decoder.h"
#include "reasons.h"

namespace odrig {

// The content types of an ODRGX container (docs/format.md, "ODRGX"). An ODRG file holds
// frames.
const uint8_t kTypeFrames = 1;
const uint8_t kTypeText = 2;
const uint8_t kTypeWidget = 3;

const uint32_t kContainerHeaderSize = 20;

// What a file holds, as its first bytes say.
struct ContentHeader {
    uint8_t container;  // 1 for an ODRGX container whose header was read whole, 0 for an ODRG file
    uint8_t type;       // kTypeFrames, kTypeText or kTypeWidget
    uint16_t width;
    uint16_t height;
    uint32_t loop_ms;   // the container's loop, 0 for an ODRG file
    uint32_t payload;   // the container's payload in bytes, 0 for an ODRG file
};

// Whether a type is drawn by the core rather than decoded from frames.
inline bool is_drawn(uint8_t type) {
    return type == kTypeText || type == kTypeWidget;
}

// Reads the header of a file that was just opened, from its first byte: an ODRG file's
// with the decoder, or a container's and then, for frames, the decoder's on its payload,
// whose canvas must be the container's. The decoder is then where `next` reads the first
// frame record; for a drawn type the source is at the payload.
Reason content_open(FileSource *file, Inflate *inflate, uint8_t *window, OdrgDecoder *decoder, ContentHeader *header);

// After the last frame record of a file of frames: nothing may follow, and a container's
// payload has the length and its frames the loop its header gives. A drawn type's payload
// was read to its end and checked whole by its own reader: nothing is left to do.
Reason content_finish(FileSource *file, OdrgDecoder *decoder, const ContentHeader &header, uint64_t total_ms);

// What decodes the picture of a picture widget as its payload is read: a decoder, its
// inflate state and window, and a pixel buffer of W * H bytes at least, which holds the
// picture's palette indices afterwards. The window serves the inflate only while the
// picture is read.
struct Picture {
    OdrgDecoder *decoder;
    Inflate *inflate;
    uint8_t *window;
    uint8_t *pixels;
};

// Reads and checks the payload of a drawn type whole, from where the header left the
// source to the end of the file, and keeps it in `into` when that is given: a text's or a
// widget's, by its own reader. A picture widget's picture is decoded with `picture`, and
// `into` keeps its head and its parts.
Reason drawn_read(FileSource *file, const ContentHeader &header, uint8_t *into, const Picture &picture);

// The name `list` writes for a type.
const char *type_name(uint8_t type);

}  // namespace odrig

#endif
