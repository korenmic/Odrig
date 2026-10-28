#ifndef ODRIG_FIELDS_H
#define ODRIG_FIELDS_H

#include <stdint.h>

namespace odrig {

// The fields of the lines of a catalog and of its index, read from a text at `*at` and
// written into a buffer at `*length`. A reader moves `*at` past what it read and gives
// false, moving nothing, when the text there is not in its form.

// A word of exactly these characters.
inline bool word(const char *line, uint32_t *at, const char *expected) {
    uint32_t place = *at;
    for (; *expected != '\0'; ++expected, ++place) {
        if (line[place] != *expected) {
            return false;
        }
    }
    *at = place;
    return true;
}

// A decimal number of at most `most_digits` digits without a leading zero, and not above
// `most`.
inline bool decimal(const char *line, uint32_t *at, uint32_t most_digits, uint64_t most, uint64_t *value) {
    uint32_t place = *at;
    uint64_t found = 0;
    uint32_t digits = 0;
    while (line[place] >= '0' && line[place] <= '9') {
        if (digits == most_digits || (digits == 1 && found == 0)) {
            return false;
        }
        const uint64_t digit = static_cast<uint64_t>(line[place] - '0');
        if (found > (most - digit) / 10) {
            return false;
        }
        found = found * 10 + digit;
        ++digits;
        ++place;
    }
    if (digits == 0) {
        return false;
    }
    *value = found;
    *at = place;
    return true;
}

// A decimal number of 32 bits, as `decimal` reads it.
inline bool decimal32(const char *line, uint32_t *at, uint32_t *value) {
    uint64_t found = 0;
    if (!decimal(line, at, 10, 0xFFFFFFFFu, &found)) {
        return false;
    }
    *value = static_cast<uint32_t>(found);
    return true;
}

// `count` lowercase hexadecimal digits.
inline bool hexadecimal(const char *line, uint32_t *at, uint32_t count, uint32_t *value) {
    uint32_t found = 0;
    for (uint32_t digit = 0; digit < count; ++digit) {
        const char c = line[*at + digit];
        uint32_t nibble;
        if (c >= '0' && c <= '9') {
            nibble = static_cast<uint32_t>(c - '0');
        } else if (c >= 'a' && c <= 'f') {
            nibble = static_cast<uint32_t>(c - 'a' + 10);
        } else {
            return false;
        }
        found = found << 4 | nibble;
    }
    *at += count;
    *value = found;
    return true;
}

// `count` decimal digits, leading zeros allowed.
inline bool fixed_decimal(const char *line, uint32_t *at, uint32_t count, uint32_t *value) {
    uint32_t found = 0;
    for (uint32_t digit = 0; digit < count; ++digit) {
        const char c = line[*at + digit];
        if (c < '0' || c > '9') {
            return false;
        }
        found = found * 10 + static_cast<uint32_t>(c - '0');
    }
    *at += count;
    *value = found;
    return true;
}

// Writes a text.
inline void put_text(uint8_t *into, uint32_t *length, const char *text) {
    while (*text != '\0') {
        into[(*length)++] = static_cast<uint8_t>(*text++);
    }
}

// Writes so many bytes of a text.
inline void put_bytes(uint8_t *into, uint32_t *length, const char *text, uint32_t size) {
    for (uint32_t at = 0; at < size; ++at) {
        into[(*length)++] = static_cast<uint8_t>(text[at]);
    }
}

// Writes a number in decimal without leading zeros.
inline void put_decimal(uint8_t *into, uint32_t *length, uint64_t value) {
    char digits[20];
    uint32_t count = 0;
    do {
        digits[count++] = static_cast<char>('0' + value % 10);
        value /= 10;
    } while (value != 0);
    while (count != 0) {
        into[(*length)++] = static_cast<uint8_t>(digits[--count]);
    }
}

// Writes a number as so many lowercase hexadecimal digits.
inline void put_hexadecimal(uint8_t *into, uint32_t *length, uint32_t value, uint32_t digits) {
    for (uint32_t digit = 0; digit < digits; ++digit) {
        into[(*length)++] = static_cast<uint8_t>("0123456789abcdef"[value >> (4 * (digits - 1 - digit)) & 0xFu]);
    }
}

// The length of a text, without its 0.
inline uint32_t text_length(const char *text) {
    uint32_t length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

// Copies a text with its 0, and gives its length.
inline uint32_t copy_text(char *into, const char *from) {
    uint32_t length = 0;
    for (; from[length] != '\0'; ++length) {
        into[length] = from[length];
    }
    into[length] = '\0';
    return length;
}

// Pads a line begun at `start` with spaces to `width` bytes, its line feed the last.
inline void put_padding(uint8_t *into, uint32_t *length, uint32_t start, uint32_t width) {
    while (*length < start + width - 1) {
        into[(*length)++] = ' ';
    }
    into[(*length)++] = '\n';
}

}  // namespace odrig

#endif
