#ifndef ODRIG_COMMANDS_H
#define ODRIG_COMMANDS_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// Reads one command line, carries it out and writes its reply, which is one JSON object on
// one line of at most ODRIG_REPLY_MAX bytes with its newline. Returns the length of the
// reply. This is the only place where a command is interpreted.
uint32_t command_answer(Core &core, uint64_t now_ms, const char *line, uint32_t length, char *reply);

// The character of UTF-8 that begins at this byte, which is 0x80 or above: its code, and
// the number of its bytes as the return value, or 0 when the bytes there are not UTF-8. A
// 0 among them ends the reading.
inline uint32_t utf8_character(const uint8_t *at, uint32_t *code) {
    const uint8_t lead = at[0];
    uint32_t more;
    uint32_t value;
    uint8_t low = 0x80;
    uint8_t high = 0xBF;
    if (lead >= 0xC2 && lead <= 0xDF) {
        more = 1;
        value = lead & 0x1Fu;
    } else if (lead >= 0xE0 && lead <= 0xEF) {
        more = 2;
        value = lead & 0x0Fu;
        low = lead == 0xE0 ? 0xA0 : 0x80;
        high = lead == 0xED ? 0x9F : 0xBF;
    } else if (lead >= 0xF0 && lead <= 0xF4) {
        more = 3;
        value = lead & 0x07u;
        low = lead == 0xF0 ? 0x90 : 0x80;
        high = lead == 0xF4 ? 0x8F : 0xBF;
    } else {
        return 0;
    }
    for (uint32_t at_byte = 1; at_byte <= more; ++at_byte) {
        const uint8_t next = at[at_byte];
        if (next < low || next > high) {
            return 0;
        }
        low = 0x80;
        high = 0xBF;
        value = value << 6 | (next & 0x3Fu);
    }
    *code = value;
    return more + 1;
}

// Writes `\u` and four hexadecimal digits of a UTF-16 unit, when `out` is not null.
inline uint32_t json_unit(uint32_t unit, char *out) {
    if (out != nullptr) {
        out[0] = '\\';
        out[1] = 'u';
        for (uint32_t digit = 0; digit < 4; ++digit) {
            out[2 + digit] = "0123456789abcdef"[unit >> (12 - 4 * digit) & 0xFu];
        }
    }
    return 6;
}

// Writes a text as the inside of a JSON string in printable ASCII, or only counts its
// bytes when `out` is null. Returns the count. A quotation mark and a backslash come after
// a backslash, and any other byte from 32 to 126 is written as it is. Every other
// character is written as `\u` and its code: a control byte and DEL by their value, a
// character of UTF-8 above U+FFFF as two units, and a byte that is not UTF-8 as U+FFFD.
inline uint32_t json_escaped(const char *text, char *out) {
    uint32_t size = 0;
    const uint8_t *at = reinterpret_cast<const uint8_t *>(text);
    while (*at != 0) {
        uint32_t code = *at;
        uint32_t taken = 1;
        if (code >= 0x80) {
            taken = utf8_character(at, &code);
            if (taken == 0) {
                taken = 1;
                code = 0xFFFD;
            }
        }
        at += taken;
        char *here = out != nullptr ? out + size : nullptr;
        if (code == '"' || code == '\\') {
            if (here != nullptr) {
                here[0] = '\\';
                here[1] = static_cast<char>(code);
            }
            size += 2;
        } else if (code >= 0x20 && code < 0x7F) {
            if (here != nullptr) {
                here[0] = static_cast<char>(code);
            }
            size += 1;
        } else if (code > 0xFFFF) {
            size += json_unit(0xD800 + ((code - 0x10000) >> 10), here);
            size += json_unit(0xDC00 + ((code - 0x10000) & 0x3FFu), here != nullptr ? here + 6 : nullptr);
        } else {
            size += json_unit(code, here);
        }
    }
    return size;
}

// A reply while it is written, into room for ODRIG_REPLY_MAX bytes.
struct Reply {
    // Whether this many bytes more can be written.
    bool fits(uint32_t more) const {
        return more <= ODRIG_REPLY_MAX - length;
    }

    void text(const char *more) {
        while (*more != '\0') {
            bytes[length++] = *more++;
        }
    }

    void number(uint64_t value) {
        char digits[20];
        uint32_t count = 0;
        do {
            digits[count++] = static_cast<char>('0' + value % 10);
            value /= 10;
        } while (value != 0);
        while (count != 0) {
            bytes[length++] = digits[--count];
        }
    }

    // The id of the item at a position of the item table or of the drive's animation at a
    // position of the playlist, `null` for no item, or `"all"` for the playlist.
    void id_or_null(const Core &core, uint32_t item) {
        if (item == kNothing) {
            text("null");
        } else if (item == kPlaylist) {
            text("\"all\"");
        } else if (is_drive(item)) {
            number(core.drive[item - kDriveBase].id);
        } else {
            number(core.items[item].id);
        }
    }

    // Writes bytes as base64 with the alphabet of RFC 4648, section 5, without padding: as
    // `upload data` takes them.
    void base64(const uint8_t *data, uint32_t count) {
        const char *alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        for (uint32_t at = 0; at < count; at += 3) {
            const uint32_t left = count - at;
            const uint32_t group = static_cast<uint32_t>(data[at]) << 16 | (left > 1 ? static_cast<uint32_t>(data[at + 1]) << 8 : 0) |
                                   (left > 2 ? data[at + 2] : 0);
            const uint32_t characters = left >= 3 ? 4 : left + 1;
            for (uint32_t one = 0; one < characters; ++one) {
                bytes[length++] = alphabet[(group >> (18 - 6 * one)) & 0x3Fu];
            }
        }
    }

    // Writes a text as the inside of a JSON string, as json_escaped has it.
    void escaped(const char *more) {
        length += json_escaped(more, bytes + length);
    }

    char *bytes;
    uint32_t length;
};

// Ends a reply as the one of a command that did its work and has nothing to report.
inline uint32_t succeed(Reply &reply) {
    reply.text("{\"ok\":true}\n");
    return reply.length;
}

// Ends a reply as a refusal with this error code.
inline uint32_t refuse(Reply &reply, const char *code) {
    reply.text("{\"ok\":false,\"error\":\"");
    reply.text(code);
    reply.text("\"}\n");
    return reply.length;
}

}  // namespace odrig

#endif
