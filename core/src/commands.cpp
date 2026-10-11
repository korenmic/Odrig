#include "commands.h"

#include "odrig_core.h"
#include "player.h"

namespace odrig {

namespace {

// A reply while it is written.
struct Reply {
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

uint32_t succeed(Reply &reply) {
    reply.text("{\"ok\":true}\n");
    return reply.length;
}

uint32_t refuse(Reply &reply, const char *code) {
    reply.text("{\"ok\":false,\"error\":\"");
    reply.text(code);
    reply.text("\"}\n");
    return reply.length;
}

uint32_t status(const Core &core, uint64_t now, Reply &reply) {
    reply.text("{\"ok\":true,\"on\":");
    reply.text(core.on ? "true" : "false");
    reply.text(",\"brightness\":");
    reply.number(core.brightness);
    reply.text(",\"playing\":");
    reply.id_or_null(core, core.playing);
    reply.text(",\"animation\":");
    reply.id_or_null(core, core.playing == kNothing ? kNothing : core.shown);
    reply.text(",\"fps\":");
    reply.number(player_fps(core, now));
    reply.text(",\"error\":");
    if (core.invalid) {
        reply.text("\"");
        reply.text(core.error_text);
        reply.text("\"");
    } else {
        reply.text("null");
    }
    reply.text("}\n");
    return reply.length;
}

// Whether the first `length` bytes of the line are this word, byte for byte.
bool is_word(const char *line, uint32_t length, const char *word) {
    uint32_t at = 0;
    while (at < length && word[at] != '\0' && line[at] == word[at]) {
        ++at;
    }
    return at == length && word[at] == '\0';
}

// The value of an argument made of decimal digits only. False for an empty argument and for
// any other character. A value above `most` is given as `most` + 1.
bool decimal(const char *text, uint32_t length, uint32_t most, uint32_t *value) {
    if (length == 0) {
        return false;
    }
    uint32_t result = 0;
    for (uint32_t at = 0; at < length; ++at) {
        if (text[at] < '0' || text[at] > '9') {
            return false;
        }
        if (result <= most) {
            result = result * 10 + static_cast<uint32_t>(text[at] - '0');
        }
    }
    *value = result > most ? most + 1 : result;
    return true;
}

}  // namespace

uint32_t command_answer(Core &core, uint64_t now_ms, const char *line, uint32_t length, char *bytes) {
    const uint64_t now = clock_touch(core, now_ms);
    Reply reply;
    reply.bytes = bytes;
    reply.length = 0;

    if (length != 0 && line[length - 1] == '\n') {
        --length;
    }
    if (length != 0 && line[length - 1] == '\r') {
        --length;
    }
    if (length > ODRIG_LINE_MAX) {
        return refuse(reply, "line-too-long");
    }

    // The line is split at every space, so it has one word more than it has spaces.
    uint32_t first = 0;
    while (first < length && line[first] != ' ') {
        ++first;
    }
    uint32_t more_words = 0;
    for (uint32_t at = 0; at < length; ++at) {
        if (line[at] == ' ') {
            ++more_words;
        }
    }
    // With two words, the second one is the argument.
    const char *argument = more_words == 1 ? line + first + 1 : line;
    const uint32_t argument_length = more_words == 1 ? length - first - 1 : 0;

    if (is_word(line, first, "status")) {
        if (more_words != 0) {
            return refuse(reply, "bad-argument");
        }
        return status(core, now, reply);
    }
    const bool switch_on = is_word(line, first, "on");
    if (switch_on || is_word(line, first, "off")) {
        if (more_words != 0) {
            return refuse(reply, "bad-argument");
        }
        core.on = switch_on ? 1 : 0;
        return succeed(reply);
    }
    if (is_word(line, first, "brightness")) {
        uint32_t value;
        if (more_words != 1 || !decimal(argument, argument_length, 255, &value) || value > 255) {
            return refuse(reply, "bad-argument");
        }
        player_set_brightness(core, static_cast<uint8_t>(value));
        return succeed(reply);
    }
    if (is_word(line, first, "play")) {
        uint32_t id;
        if (more_words != 1 || !decimal(argument, argument_length, 65535, &id) || id < 1 || id > 65535) {
            return refuse(reply, "bad-argument");
        }
        if (core.invalid) {
            return refuse(reply, "show-invalid");
        }
        uint32_t item = 0;
        while (item < core.item_count && core.items[item].id != id) {
            ++item;
        }
        if (item == core.item_count) {
            return refuse(reply, "unknown-id");
        }
        player_play(core, item);
        return succeed(reply);
    }
    return refuse(reply, "unknown-command");
}

}  // namespace odrig

size_t odrig_core_command(odrig_core *core, uint64_t now_ms, const char *line, size_t length,
                          char *reply, size_t capacity) {
    if (core == nullptr || (line == nullptr && length != 0) || reply == nullptr || capacity < ODRIG_REPLY_MAX) {
        return 0;
    }
    // A line is refused for its length long before its length could not be counted.
    const uint32_t counted = length > 0xFFFFu ? 0xFFFFu : static_cast<uint32_t>(length);
    return odrig::command_answer(core->state, now_ms, line, counted, reply);
}

void odrig_core_feed(odrig_core *core, uint64_t now_ms, const uint8_t *bytes, size_t length,
                     odrig_reply_fn on_reply, void *reply_ctx) {
    if (core == nullptr || (bytes == nullptr && length != 0)) {
        return;
    }
    odrig::Core &state = core->state;
    odrig::clock_touch(state, now_ms);
    char reply[ODRIG_REPLY_MAX];
    for (size_t at = 0; at < length; ++at) {
        const char byte = static_cast<char>(bytes[at]);
        if (byte != '\n') {
            // Room for 64 characters and the carriage return of a line that ends in one.
            if (state.line_length < ODRIG_LINE_MAX + 1) {
                state.line[state.line_length++] = byte;
            } else {
                state.line_over = 1;
            }
            continue;
        }
        // A line that outgrew the room is longer than 64 characters whatever it ends in.
        // The host is handed the line as the command entry reads it: without one carriage
        // return at its end, and its first 64 characters when it is longer.
        uint32_t kept = state.line_length;
        uint32_t reply_length;
        if (state.line_over) {
            odrig::Reply refusal;
            refusal.bytes = reply;
            refusal.length = 0;
            reply_length = odrig::refuse(refusal, "line-too-long");
        } else {
            reply_length = odrig::command_answer(state, now_ms, state.line, kept, reply);
            if (kept != 0 && state.line[kept - 1] == '\r') {
                --kept;
            }
        }
        if (kept > ODRIG_LINE_MAX) {
            kept = ODRIG_LINE_MAX;
        }
        state.line_length = 0;
        state.line_over = 0;
        if (on_reply != nullptr) {
            on_reply(reply_ctx, state.line, kept, reply, reply_length);
        }
    }
}
