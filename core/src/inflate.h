#ifndef ODRIG_INFLATE_H
#define ODRIG_INFLATE_H

#include <stdint.h>

#include "file_source.h"
#include "reasons.h"

namespace odrig {

// The size of the window a raw DEFLATE stream may refer back into.
const uint32_t kWindowSize = 32768;

// A decoder of one raw DEFLATE stream (RFC 1951) that is pulled one byte at a time. It
// takes a byte of input only when it needs a bit of it, so when the stream has ended the
// file stands at the first byte after the stream.
struct Inflate {
    // Begins a stream at the current position of the file. The window holds kWindowSize
    // bytes.
    void start(FileSource *from, uint8_t *the_window);

    // The next byte of output, 0 to 255; or -kEnd at the end of the stream; or -kBadDeflate,
    // -kTruncated or -kReadError. After any of these, every later call returns the same.
    int get();

    int fail(int negative_reason);
    int put(int byte);
    int bits(uint32_t count);
    int symbol(const uint16_t *count, const uint16_t *symbols, uint32_t longest);
    Reason block_start();
    Reason dynamic_tables();
    void fixed_tables();

    FileSource *in;
    uint8_t *window;
    uint32_t window_position;
    uint32_t produced;
    uint32_t hold;
    uint32_t held;
    uint32_t state;
    uint32_t last_block;
    uint32_t stored_left;
    uint32_t match_left;
    uint32_t match_distance;
    int failure;

    // Two tables for each of the two codes of a block: the number of codes of each length,
    // and the symbols in the order of their codes.
    uint16_t length_count[16];
    uint16_t length_symbol[288];
    uint16_t distance_count[16];
    uint16_t distance_symbol[30];
    uint32_t length_longest;
    uint32_t distance_longest;

    // The code lengths of a block's header while its tables are built.
    uint8_t lengths[320];
};

}  // namespace odrig

#endif
