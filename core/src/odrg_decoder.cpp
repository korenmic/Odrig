#include "odrg_decoder.h"

#include <string.h>

namespace odrig {

namespace {

const uint32_t kHeaderSize = 16;
const uint32_t kRecordStart = 5;
const uint8_t kCompressedFlag = 0x01;
const uint8_t kRunBit = 0x08;
const uint8_t kStoredBit = 0x40;
const uint8_t kReservedModeBit = 0x80;
const uint32_t kLargestCode = 255;

// The number of one-bits at the top of each byte value.
const uint8_t kLeadingOnes[256] = {
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 7, 8,
};

// The data bytes of a coded frame as a string of bits, the most significant bit of each
// byte first. A byte is taken from the body only when one of its bits is needed.
struct RecordBits {
    // Takes bytes until more than 24 bits are held or the record has no more. Returns false
    // when the body gives no byte, with the reason in `stopped`.
    bool fill() {
        while (have <= 24 && left != 0) {
            int byte = decoder->body_get();
            if (byte < 0) {
                stopped = decoder->body_stopped(byte);
                return false;
            }
            held = (held << 8) | static_cast<uint32_t>(byte);
            have += 8;
            --left;
        }
        return true;
    }

    // The next bit, or a negative Reason.
    int bit() {
        if (have == 0) {
            if (left == 0) {
                return -kOutOfBits;
            }
            if (!fill()) {
                return -stopped;
            }
        }
        --have;
        return static_cast<int>((held >> have) & 1);
    }

    // One Rice(k) value, read whole: 0 to 1,023, or a negative Reason. It is decoded from
    // the next 16 bits, with zero bits standing in for bits the record does not have.
    int rice(uint32_t k) {
        if (have < 16 && left != 0 && !fill()) {
            return -stopped;
        }
        uint32_t ahead = have >= 16 ? (held >> (have - 16)) & 0xFFFF : (held << (16 - have)) & 0xFFFF;
        uint32_t ones = kLeadingOnes[ahead >> 8];
        uint32_t used;
        uint32_t value;
        if (ones == 8) {
            used = 16;
            value = ahead & 0xFF;
        } else {
            used = ones + 1 + k;
            value = (ones << k) | ((ahead >> (16 - used)) & ((1u << k) - 1));
        }
        if (used > have) {
            return -kOutOfBits;
        }
        have -= used;
        return static_cast<int>(value);
    }

    // One Gamma value, read bit by bit to its end. A value too large to matter is given as
    // a number above every picture size.
    Reason gamma(uint32_t *value) {
        uint32_t zeros = 0;
        int got;
        while ((got = bit()) == 0) {
            ++zeros;
        }
        if (got < 0) {
            return static_cast<Reason>(-got);
        }
        uint32_t g = 1;
        for (; zeros != 0; --zeros) {
            got = bit();
            if (got < 0) {
                return static_cast<Reason>(-got);
            }
            if (g <= 0xFFFFFF) {
                g = (g << 1) | static_cast<uint32_t>(got);
            }
        }
        *value = g;
        return kNone;
    }

    OdrgDecoder *decoder;
    uint32_t held;      // its lowest `have` bits are the bits taken and not yet used
    uint32_t have;
    uint32_t left;      // data bytes of the record not yet taken from the body
    Reason stopped;
};

// The pixel buffer while a coded frame turns it from the picture before into the new one,
// one residual at a time, in increasing position.
struct Picture {
    // Applies the predictor to the residual of the next position.
    void put(uint8_t residual) {
        switch (predictor) {
            case 0:
                pixels[index] = static_cast<uint8_t>(pixels[index] + residual);
                break;
            case 1: {
                // The neighbour of the first pixel of a row is the first pixel of the row
                // before it; both running values start as zero.
                bool first_of_row = column < bpp;
                uint8_t neighbour = first_of_row ? row_start[channel] : before[channel];
                uint8_t change = static_cast<uint8_t>(residual + neighbour);
                if (first_of_row) {
                    row_start[channel] = change;
                }
                before[channel] = change;
                pixels[index] = static_cast<uint8_t>(pixels[index] + change);
                break;
            }
            case 2: {
                uint8_t neighbour = 0;
                if (column >= bpp) {
                    neighbour = pixels[index - bpp];
                } else if (index >= stride) {
                    neighbour = pixels[index - stride];
                }
                pixels[index] = static_cast<uint8_t>(residual + neighbour);
                break;
            }
            default:
                pixels[index] = residual;
                break;
        }
        ++index;
        if (++column == stride) {
            column = 0;
        }
        if (++channel == bpp) {
            channel = 0;
        }
    }

    // Applies the predictor to `count` residuals of zero.
    void zeros(uint32_t count) {
        if (predictor == 1 || predictor == 2) {
            for (; count != 0; --count) {
                put(0);
            }
            return;
        }
        if (predictor == 3) {
            memset(pixels + index, 0, count);
        }
        index += count;
        column = (column + count) % stride;
        channel = (channel + count) % bpp;
    }

    uint8_t *pixels;
    uint32_t stride;
    uint32_t bpp;
    uint32_t predictor;
    uint32_t index;      // the next position, i
    uint32_t column;     // i mod stride
    uint32_t channel;    // i mod bpp
    uint8_t before[3];      // predictor 1: the change of the pixel to the left
    uint8_t row_start[3];   // predictor 1: the change of the first pixel of the row
};

// The residual a code stands for: codes 0, 1, 2, 3, 4 mean 0, -1, +1, -2, +2.
uint8_t residual_of(uint32_t code) {
    return static_cast<uint8_t>((code >> 1) ^ (0u - (code & 1)));
}

}  // namespace

Reason OdrgDecoder::open(FileSource *from, Inflate *with, uint8_t *window) {
    file = from;
    inflate = with;
    records_left = 0;
    palette_pending = 0;
    compressed = 0;

    uint8_t header[kHeaderSize];
    for (uint32_t i = 0; i < kHeaderSize; ++i) {
        int byte = file->get();
        if (byte < 0) {
            return byte == -kEnd ? kTruncated : kReadError;
        }
        header[i] = static_cast<uint8_t>(byte);
    }
    if (header[0] != 0x4F || header[1] != 0x44 || header[2] != 0x52 || header[3] != 0x47) {
        return kBadMagic;
    }
    if (header[4] != 1) {
        return kBadVersion;
    }
    if ((header[5] & ~kCompressedFlag) != 0) {
        return kReservedBits;
    }
    width = static_cast<uint16_t>(header[6] | (header[7] << 8));
    height = static_cast<uint16_t>(header[8] | (header[9] << 8));
    colours = static_cast<uint16_t>(header[10] | (header[11] << 8));
    frames = static_cast<uint32_t>(header[12]) | (static_cast<uint32_t>(header[13]) << 8) |
             (static_cast<uint32_t>(header[14]) << 16) | (static_cast<uint32_t>(header[15]) << 24);
    if (width == 0 || height == 0) {
        return kZeroSize;
    }
    if (colours > 256) {
        return kBadPaletteSize;
    }
    bpp = colours != 0 ? 1 : 3;
    uint64_t picture = static_cast<uint64_t>(width) * height * bpp;
    if (picture > kLargestPicture) {
        return kCanvasTooLarge;
    }
    n = static_cast<uint32_t>(picture);
    if (frames == 0) {
        return kNoFrames;
    }

    compressed = header[5] & kCompressedFlag;
    if (compressed) {
        inflate->start(file, window);
    }
    records_left = frames;
    palette_pending = colours != 0;
    return kNone;
}

// What it means that the body gave no byte where one is needed. A compressed body that
// ends early has a whole stream, so bytes after the stream are found before the short body.
Reason OdrgDecoder::body_stopped(int got) {
    if (got != -kEnd) {
        return static_cast<Reason>(-got);
    }
    if (compressed) {
        int after = file->get();
        if (after >= 0) {
            return kTrailingBytes;
        }
        if (after != -kEnd) {
            return kReadError;
        }
    }
    return kTruncated;
}

// The reason to report for a defect found inside the body. A reader that holds the whole
// file inflates a compressed body before it looks at a record, and has every data byte of
// a record before it looks at a bit. This reads on to find what such a reader meets first:
// a defect of the stream, bytes after the stream, or a record whose data is cut short.
Reason OdrgDecoder::settled(Reason found, uint32_t record_bytes_left) {
    uint32_t missing = record_bytes_left;
    if (!compressed) {
        for (; missing != 0; --missing) {
            int byte = file->get();
            if (byte < 0) {
                return body_stopped(byte);
            }
        }
        return found;
    }
    for (;;) {
        int byte = inflate->get();
        if (byte == -kEnd) {
            break;
        }
        if (byte < 0) {
            return static_cast<Reason>(-byte);
        }
        if (missing != 0) {
            --missing;
        }
    }
    int after = file->get();
    if (after >= 0) {
        return kTrailingBytes;
    }
    if (after != -kEnd) {
        return kReadError;
    }
    return missing != 0 ? kTruncated : found;
}

Reason OdrgDecoder::read_palette() {
    uint32_t size = 3u * colours;
    for (uint32_t i = 0; i < size; ++i) {
        int byte = body_get();
        if (byte < 0) {
            return body_stopped(byte);
        }
        palette[i] = static_cast<uint8_t>(byte);
    }
    palette_pending = 0;
    return kNone;
}

Reason OdrgDecoder::coded(uint8_t *pixels, uint32_t mode, uint32_t data_bytes) {
    RecordBits bits;
    bits.decoder = this;
    bits.held = 0;
    bits.have = 0;
    bits.left = data_bytes;
    bits.stopped = kNone;

    Picture picture;
    memset(&picture, 0, sizeof picture);
    picture.pixels = pixels;
    picture.bpp = bpp;
    picture.stride = static_cast<uint32_t>(width) * bpp;
    picture.predictor = (mode >> 4) & 3;

    const uint32_t k = mode & 7;
    Reason found = kNone;
    if ((mode & kRunBit) != 0) {
        while (picture.index < n) {
            uint32_t g;
            found = bits.gamma(&g);
            if (found != kNone) {
                break;
            }
            if (g - 1 > n - picture.index) {
                found = kRunPastEnd;
                break;
            }
            picture.zeros(g - 1);
            if (picture.index == n) {
                break;
            }
            int value = bits.rice(k);
            if (value < 0) {
                found = static_cast<Reason>(-value);
                break;
            }
            if (static_cast<uint32_t>(value) + 1 > kLargestCode) {
                found = kBadCode;
                break;
            }
            picture.put(residual_of(static_cast<uint32_t>(value) + 1));
        }
    } else {
        while (picture.index < n) {
            int value = bits.rice(k);
            if (value < 0) {
                found = static_cast<Reason>(-value);
                break;
            }
            if (static_cast<uint32_t>(value) > kLargestCode) {
                found = kBadCode;
                break;
            }
            picture.put(residual_of(static_cast<uint32_t>(value)));
        }
    }
    if (bits.stopped != kNone) {
        return bits.stopped;
    }
    if (found == kNone && bits.have + 8 * bits.left >= 8) {
        found = kTooMuchPadding;
    }
    if (found == kNone) {
        return kNone;
    }
    return settled(found, bits.left);
}

Reason OdrgDecoder::next(uint8_t *pixels, uint16_t *duration) {
    if (records_left == 0) {
        return kTruncated;
    }
    if (palette_pending) {
        Reason reason = read_palette();
        if (reason != kNone) {
            return reason;
        }
    }

    uint8_t start[kRecordStart];
    for (uint32_t i = 0; i < kRecordStart; ++i) {
        int byte = body_get();
        if (byte < 0) {
            return body_stopped(byte);
        }
        start[i] = static_cast<uint8_t>(byte);
    }
    uint32_t milliseconds = start[0] | (static_cast<uint32_t>(start[1]) << 8);
    uint32_t length = start[2] | (static_cast<uint32_t>(start[3]) << 8);
    uint32_t mode = start[4];
    if (milliseconds == 0) {
        return settled(kZeroDuration, 0);
    }
    if (length < 2 || length > n + 1) {
        return settled(kBadLength, 0);
    }
    if ((mode & kReservedModeBit) != 0 || ((mode & kStoredBit) != 0 && mode != kStoredBit)) {
        return settled(kReservedBits, 0);
    }
    if (mode == kStoredBit) {
        if (length != n + 1) {
            return settled(kBadStoredLength, 0);
        }
        for (uint32_t i = 0; i < n; ++i) {
            int byte = body_get();
            if (byte < 0) {
                return body_stopped(byte);
            }
            pixels[i] = static_cast<uint8_t>(byte);
        }
    } else {
        Reason reason = coded(pixels, mode, length - 1);
        if (reason != kNone) {
            return reason;
        }
    }

    // Every palette index of the picture is below C. This is judged last in a record.
    if (colours != 0 && colours < 256) {
        uint32_t outside = 0;
        for (uint32_t i = 0; i < n; ++i) {
            outside |= static_cast<uint32_t>(pixels[i] >= colours);
        }
        if (outside != 0) {
            return settled(kBadPaletteIndex, 0);
        }
    }

    --records_left;
    *duration = static_cast<uint16_t>(milliseconds);
    return kNone;
}

Reason OdrgDecoder::finish() {
    int byte = body_get();
    if (byte >= 0) {
        return settled(kTrailingBytes, 0);
    }
    if (byte != -kEnd) {
        return static_cast<Reason>(-byte);
    }
    if (compressed) {
        int after = file->get();
        if (after >= 0) {
            return kTrailingBytes;
        }
        if (after != -kEnd) {
            return kReadError;
        }
    }
    return kNone;
}

}  // namespace odrig
