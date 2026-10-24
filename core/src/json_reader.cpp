#include "json_reader.h"

#include "reasons.h"

namespace odrig {

namespace {

// The value of `ahead` when the next byte has not been looked at.
const int kNotLooked = -100;

// Stands for a character that an escape names and no expected text contains.
const char kOtherCharacter = 0x01;

int hex_value(int c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

}  // namespace

void JsonReader::start(FileSource *from) {
    in = from;
    ahead = kNotLooked;
    failed = false;
    read_failed = false;
    fresh = false;
}

// The next byte without taking it: 0 to 255, or a negative number at the end of the file
// and when the file cannot be read.
int JsonReader::peek() {
    if (ahead == kNotLooked) {
        ahead = in->get();
        if (ahead < 0 && ahead != -kEnd) {
            read_failed = true;
            failed = true;
        }
    }
    return ahead;
}

void JsonReader::take() {
    ahead = kNotLooked;
}

void JsonReader::skip_space() {
    for (;;) {
        int c = peek();
        if (c != ' ' && c != '\t' && c != '\n' && c != '\r') {
            return;
        }
        take();
    }
}

bool JsonReader::fail() {
    failed = true;
    return false;
}

bool JsonReader::object_begin() {
    skip_space();
    if (failed || peek() != '{') {
        return fail();
    }
    take();
    fresh = true;
    return true;
}

bool JsonReader::object_next(char *name, uint8_t capacity) {
    skip_space();
    if (failed) {
        return false;
    }
    int c = peek();
    if (c == '}') {
        take();
        fresh = false;
        return false;
    }
    if (!fresh) {
        if (c != ',') {
            return fail();
        }
        take();
    }
    if (!string(name, capacity)) {
        return false;
    }
    skip_space();
    if (failed || peek() != ':') {
        return fail();
    }
    take();
    return true;
}

bool JsonReader::array_begin() {
    skip_space();
    if (failed || peek() != '[') {
        return fail();
    }
    take();
    fresh = true;
    return true;
}

bool JsonReader::array_next() {
    skip_space();
    if (failed) {
        return false;
    }
    int c = peek();
    if (c == ']') {
        take();
        fresh = false;
        return false;
    }
    if (!fresh) {
        if (c != ',') {
            return fail();
        }
        take();
    }
    fresh = false;
    return true;
}

bool JsonReader::any_integer(bool *negative, uint32_t *size) {
    skip_space();
    if (failed) {
        return false;
    }
    bool minus = false;
    int c = peek();
    if (c == '-') {
        minus = true;
        take();
        c = peek();
    }
    if (c < '0' || c > '9') {
        return fail();
    }
    uint32_t value = 0;
    if (c == '0') {
        take();
    } else {
        while ((c = peek()) >= '0' && c <= '9') {
            take();
            uint32_t digit = static_cast<uint32_t>(c - '0');
            value = value > (0xFFFFFFFFu - digit) / 10 ? 0xFFFFFFFFu : value * 10 + digit;
        }
    }
    c = peek();
    if (failed || c == '.' || c == 'e' || c == 'E') {
        return fail();
    }
    *negative = minus && value != 0;
    *size = value;
    fresh = false;
    return true;
}

bool JsonReader::integer(uint32_t *value) {
    bool negative = false;
    if (!any_integer(&negative, value)) {
        return false;
    }
    if (negative) {
        return fail();
    }
    return true;
}

bool JsonReader::boolean(bool *value) {
    skip_space();
    const bool yes = peek() == 't';
    const char *word = yes ? "true" : "false";
    for (uint32_t at = 0; word[at] != '\0'; ++at) {
        if (peek() != word[at]) return fail();
        take();
    }
    *value = yes;
    fresh = false;
    return true;
}

bool JsonReader::string(char *text, uint8_t capacity) {
    skip_space();
    if (failed || peek() != '"') {
        return fail();
    }
    take();
    uint32_t length = 0;
    for (;;) {
        int c = peek();
        if (c < 0x20 || c >= 0x80) {
            return fail();
        }
        take();
        if (c == '"') {
            break;
        }
        if (c == '\\') {
            c = peek();
            take();
            if (c == 'u') {
                int code = 0;
                for (int i = 0; i < 4; ++i) {
                    int digit = hex_value(peek());
                    if (digit < 0) {
                        return fail();
                    }
                    take();
                    code = code * 16 + digit;
                }
                c = code >= 0x20 && code < 0x7F ? code : kOtherCharacter;
            } else if (c == 'b' || c == 'f' || c == 'n' || c == 'r' || c == 't') {
                c = kOtherCharacter;
            } else if (c != '"' && c != '\\' && c != '/') {
                return fail();
            }
        }
        if (length + 1 >= capacity) {
            return fail();
        }
        text[length++] = static_cast<char>(c);
    }
    text[length] = '\0';
    fresh = false;
    return true;
}

bool JsonReader::end() {
    skip_space();
    if (failed || peek() != -kEnd) {
        return fail();
    }
    return true;
}

}  // namespace odrig
