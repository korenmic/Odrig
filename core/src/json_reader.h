#ifndef ODRIG_JSON_READER_H
#define ODRIG_JSON_READER_H

#include <stdint.h>

#include "file_source.h"

namespace odrig {

// Whether two texts that end in a zero are the same.
inline bool same_text(const char *a, const char *b) {
    while (*a != '\0' && *a == *b) {
        ++a;
        ++b;
    }
    return *a == *b;
}

// A reader of a JSON text that hands out one piece at a time. The reader of a file calls it
// in the order the file's format dictates, so the nesting is in that code and nothing here
// calls itself.
//
// It reads as strictly as the converter does. A text it does not refuse is JSON, and every
// string in it is made of the characters of ASCII from the space on: a byte outside ASCII
// cannot be part of a name or a value of the files the core reads, so the text that holds
// one is refused where the byte stands.
//
// Once a call has failed, `failed` is set and every later call fails.
struct JsonReader {
    void start(FileSource *from);

    // An object begins here.
    bool object_begin();

    // The next member of the object: its name is put into `name`, and its value is read
    // next. False at the closing brace, and on failure.
    bool object_next(char *name, uint8_t capacity);

    // An array begins here.
    bool array_begin();

    // The array has one more entry, which is read next. False at the closing bracket, and
    // on failure.
    bool array_next();

    // An integer without a sign, or `-0`: a JSON number written without a fraction and
    // without an exponent. A value above 4,294,967,295 is given as 4,294,967,295.
    bool integer(uint32_t *value);

    // An integer that may be below zero, given as a sign and a size.
    bool any_integer(bool *negative, uint32_t *size);

    // A string of fewer than `capacity` characters, put into `text` with a zero after it.
    // An escape that stands for a character outside the printable part of ASCII is given
    // as a byte that no name and no value of the core's files contains.
    bool string(char *text, uint8_t capacity);

    // Nothing but white space is left in the file.
    bool end();

    int peek();
    void take();
    void skip_space();
    bool fail();

    bool failed;
    bool read_failed;   // the failure is the host's: it could not read the file
    bool fresh;         // an object or an array has just begun
    int ahead;          // the next byte, when it has been looked at
    FileSource *in;
};

}  // namespace odrig

#endif
