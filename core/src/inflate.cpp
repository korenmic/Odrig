#include "inflate.h"

namespace odrig {

namespace {

enum State { kBlockStart = 0, kStored, kCodes, kCopying, kEnded, kFailed };

const uint32_t kMostLengthCodes = 286;
const uint32_t kMostDistanceCodes = 30;
const uint32_t kLongestCode = 15;

const uint16_t kLengthBase[29] = {3,  4,  5,  6,  7,  8,  9,  10, 11,  13,  15,  17,  19,  23, 27,
                                  31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
const uint8_t kLengthExtra[29] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2,
                                  2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
const uint16_t kDistanceBase[30] = {1,   2,   3,   4,   5,   7,    9,    13,   17,   25,
                                    33,  49,  65,  97,  129, 193,  257,  385,  513,  769,
                                    1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
const uint8_t kDistanceExtra[30] = {0, 0, 0, 0, 1, 1, 2, 2,  3,  3,  4,  4,  5,  5,  6,
                                    6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};

// The order in which a dynamic block lists the lengths of its code-length code.
const uint8_t kCodeLengthOrder[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};

int input_failure(int got) {
    return got == -kEnd ? -kTruncated : -kReadError;
}

// Builds the two tables of a code from the length of each of its `n` symbols; a length of
// zero means the symbol has no code. Sets `longest` to the longest length in use. Returns
// 0 for a complete code, a positive number for a code that leaves bit patterns unused, and
// a negative number for lengths no code can have.
int construct(const uint8_t *lengths, uint32_t n, uint16_t *count, uint16_t *symbols, uint32_t *longest) {
    uint16_t offset[kLongestCode + 1];
    for (uint32_t length = 0; length <= kLongestCode; ++length) {
        count[length] = 0;
    }
    for (uint32_t i = 0; i < n; ++i) {
        ++count[lengths[i]];
    }
    *longest = 0;
    int left = 1;
    for (uint32_t length = 1; length <= kLongestCode; ++length) {
        if (count[length] != 0) {
            *longest = length;
        }
        left <<= 1;
        left -= count[length];
        if (left < 0) {
            return left;
        }
    }
    offset[1] = 0;
    for (uint32_t length = 1; length < kLongestCode; ++length) {
        offset[length + 1] = static_cast<uint16_t>(offset[length] + count[length]);
    }
    for (uint32_t i = 0; i < n; ++i) {
        if (lengths[i] != 0) {
            symbols[offset[lengths[i]]++] = static_cast<uint16_t>(i);
        }
    }
    return left;
}

}  // namespace

void Inflate::start(FileSource *from, uint8_t *the_window) {
    in = from;
    window = the_window;
    window_position = 0;
    produced = 0;
    hold = 0;
    held = 0;
    state = kBlockStart;
    last_block = 0;
    stored_left = 0;
    match_left = 0;
    match_distance = 0;
    failure = 0;
}

int Inflate::fail(int negative_reason) {
    failure = negative_reason;
    state = kFailed;
    return failure;
}

int Inflate::put(int byte) {
    window[window_position] = static_cast<uint8_t>(byte);
    window_position = (window_position + 1) & (kWindowSize - 1);
    if (produced < kWindowSize) {
        ++produced;
    }
    return byte;
}

// The next `count` bits of the input as a number, the first bit lowest; `count` is at most
// 16. A byte of input is taken only when a bit of it is needed.
int Inflate::bits(uint32_t count) {
    while (held < count) {
        int byte = in->get();
        if (byte < 0) {
            return input_failure(byte);
        }
        hold |= static_cast<uint32_t>(byte) << held;
        held += 8;
    }
    int value = static_cast<int>(hold & ((1u << count) - 1));
    hold >>= count;
    held -= count;
    return value;
}

// Decodes one symbol of a code, a bit at a time. A bit pattern that is no code of the set
// is refused as soon as it is as long as the longest code, and after one bit when the set
// has no code at all.
int Inflate::symbol(const uint16_t *count, const uint16_t *symbols, uint32_t longest) {
    int code = 0;
    int first = 0;
    int index = 0;
    for (uint32_t length = 1;; ++length) {
        if (held == 0) {
            int byte = in->get();
            if (byte < 0) {
                return input_failure(byte);
            }
            hold = static_cast<uint32_t>(byte);
            held = 8;
        }
        code |= static_cast<int>(hold & 1);
        hold >>= 1;
        --held;
        int codes = count[length];
        if (code - codes < first) {
            return symbols[index + (code - first)];
        }
        if (length >= longest) {
            return -kBadDeflate;
        }
        index += codes;
        first += codes;
        first <<= 1;
        code <<= 1;
    }
}

void Inflate::fixed_tables() {
    uint32_t i = 0;
    for (; i < 144; ++i) {
        lengths[i] = 8;
    }
    for (; i < 256; ++i) {
        lengths[i] = 9;
    }
    for (; i < 280; ++i) {
        lengths[i] = 7;
    }
    for (; i < 288; ++i) {
        lengths[i] = 8;
    }
    construct(lengths, 288, length_count, length_symbol, &length_longest);
    for (i = 0; i < kMostDistanceCodes; ++i) {
        lengths[i] = 5;
    }
    construct(lengths, kMostDistanceCodes, distance_count, distance_symbol, &distance_longest);
}

Reason Inflate::dynamic_tables() {
    int value = bits(14);
    if (value < 0) {
        return static_cast<Reason>(-value);
    }
    uint32_t length_codes = (static_cast<uint32_t>(value) & 31) + 257;
    uint32_t distance_codes = ((static_cast<uint32_t>(value) >> 5) & 31) + 1;
    uint32_t listed = (static_cast<uint32_t>(value) >> 10) + 4;
    if (length_codes > kMostLengthCodes || distance_codes > kMostDistanceCodes) {
        return kBadDeflate;
    }

    uint8_t code_lengths[19];
    for (uint32_t i = 0; i < 19; ++i) {
        code_lengths[i] = 0;
    }
    for (uint32_t i = 0; i < listed; ++i) {
        value = bits(3);
        if (value < 0) {
            return static_cast<Reason>(-value);
        }
        code_lengths[kCodeLengthOrder[i]] = static_cast<uint8_t>(value);
    }
    uint16_t code_count[kLongestCode + 1];
    uint16_t code_symbol[19];
    uint32_t code_longest;
    int left = construct(code_lengths, 19, code_count, code_symbol, &code_longest);
    if (code_longest != 0 && left != 0) {
        return kBadDeflate;
    }

    uint32_t total = length_codes + distance_codes;
    uint32_t have = 0;
    while (have < total) {
        int coded;
        if (code_longest == 0) {
            // A code-length code without codes: every length takes one bit and is zero.
            coded = bits(1);
            if (coded > 0) {
                coded = 0;
            }
        } else {
            coded = symbol(code_count, code_symbol, code_longest);
        }
        if (coded < 0) {
            return static_cast<Reason>(-coded);
        }
        if (coded < 16) {
            lengths[have++] = static_cast<uint8_t>(coded);
            continue;
        }
        uint8_t repeated = 0;
        uint32_t times;
        if (coded == 16) {
            value = bits(2);
            if (value < 0) {
                return static_cast<Reason>(-value);
            }
            if (have == 0) {
                return kBadDeflate;
            }
            repeated = lengths[have - 1];
            times = 3 + static_cast<uint32_t>(value);
        } else if (coded == 17) {
            value = bits(3);
            if (value < 0) {
                return static_cast<Reason>(-value);
            }
            times = 3 + static_cast<uint32_t>(value);
        } else {
            value = bits(7);
            if (value < 0) {
                return static_cast<Reason>(-value);
            }
            times = 11 + static_cast<uint32_t>(value);
        }
        if (have + times > total) {
            return kBadDeflate;
        }
        while (times-- != 0) {
            lengths[have++] = repeated;
        }
    }

    if (lengths[256] == 0) {
        return kBadDeflate;
    }
    left = construct(lengths, length_codes, length_count, length_symbol, &length_longest);
    if (left < 0 || (left > 0 && length_longest != 1)) {
        return kBadDeflate;
    }
    left = construct(lengths + length_codes, distance_codes, distance_count, distance_symbol,
                     &distance_longest);
    if (left < 0 || (left > 0 && distance_longest > 1)) {
        return kBadDeflate;
    }
    return kNone;
}

Reason Inflate::block_start() {
    int header = bits(3);
    if (header < 0) {
        return static_cast<Reason>(-header);
    }
    last_block = static_cast<uint32_t>(header) & 1;
    switch (header >> 1) {
        case 0: {
            // A stored block starts at the next whole byte with its length, twice.
            hold = 0;
            held = 0;
            uint32_t four[4];
            for (uint32_t i = 0; i < 4; ++i) {
                int byte = in->get();
                if (byte < 0) {
                    return static_cast<Reason>(-input_failure(byte));
                }
                four[i] = static_cast<uint32_t>(byte);
            }
            uint32_t length = four[0] | (four[1] << 8);
            uint32_t complement = four[2] | (four[3] << 8);
            if (length != (complement ^ 0xFFFFu)) {
                return kBadDeflate;
            }
            stored_left = length;
            state = kStored;
            return kNone;
        }
        case 1:
            fixed_tables();
            state = kCodes;
            return kNone;
        case 2: {
            Reason reason = dynamic_tables();
            if (reason == kNone) {
                state = kCodes;
            }
            return reason;
        }
        default:
            return kBadDeflate;
    }
}

int Inflate::get() {
    for (;;) {
        if (state == kCopying) {
            if (match_left != 0) {
                --match_left;
                return put(window[(window_position - match_distance) & (kWindowSize - 1)]);
            }
            state = kCodes;
        }
        if (state == kCodes) {
            int coded = symbol(length_count, length_symbol, length_longest);
            if (coded < 0) {
                return fail(coded);
            }
            if (coded < 256) {
                return put(coded);
            }
            if (coded == 256) {
                state = last_block ? kEnded : kBlockStart;
                continue;
            }
            if (coded > 285) {
                return fail(-kBadDeflate);
            }
            coded -= 257;
            int extra = bits(kLengthExtra[coded]);
            if (extra < 0) {
                return fail(extra);
            }
            match_left = kLengthBase[coded] + static_cast<uint32_t>(extra);
            coded = symbol(distance_count, distance_symbol, distance_longest);
            if (coded < 0) {
                return fail(coded);
            }
            if (coded > 29) {
                return fail(-kBadDeflate);
            }
            extra = bits(kDistanceExtra[coded]);
            if (extra < 0) {
                return fail(extra);
            }
            match_distance = kDistanceBase[coded] + static_cast<uint32_t>(extra);
            if (match_distance > produced) {
                return fail(-kBadDeflate);
            }
            state = kCopying;
            continue;
        }
        if (state == kStored) {
            if (stored_left != 0) {
                int byte = in->get();
                if (byte < 0) {
                    return fail(input_failure(byte));
                }
                --stored_left;
                return put(byte);
            }
            state = last_block ? kEnded : kBlockStart;
            continue;
        }
        if (state == kBlockStart) {
            Reason reason = block_start();
            if (reason != kNone) {
                return fail(-reason);
            }
            continue;
        }
        if (state == kEnded) {
            return -kEnd;
        }
        return failure;
    }
}

}  // namespace odrig
