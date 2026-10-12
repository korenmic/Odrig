#ifndef ODRIG_COMMANDS_H
#define ODRIG_COMMANDS_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// Reads one command line, carries it out and writes its reply, which is one JSON object on
// one line of at most ODRIG_REPLY_MAX bytes with its newline. Returns the length of the
// reply. This is the only place where a command is interpreted.
uint32_t command_answer(Core &core, uint64_t now_ms, const char *line, uint32_t length, char *reply);

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

    void number(uint32_t value) {
        char digits[10];
        uint32_t count = 0;
        do {
            digits[count++] = static_cast<char>('0' + value % 10);
            value /= 10;
        } while (value != 0);
        while (count != 0) {
            bytes[length++] = digits[--count];
        }
    }

    // The id of the item at a position of the item table, or `null` for no item.
    void id_or_null(const Core &core, uint32_t item) {
        if (item == kNothing) {
            text("null");
        } else {
            number(core.items[item].id);
        }
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
