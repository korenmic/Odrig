#ifndef ODRIG_CORE_H
#define ODRIG_CORE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ODRIG_LINE_MAX   64     /* longest command line, in characters */
#define ODRIG_REPLY_MAX 192     /* longest reply, in bytes, with its newline */

typedef struct odrig_core odrig_core;

/* What the host supplies. Every function receives ctx as its first argument. */
typedef struct odrig_host {
    void *ctx;

    /* Memory, aligned for any object. Called only inside odrig_core_begin.
       Returns NULL when the host has none to give. The core never frees it. */
    void *(*alloc)(void *ctx, size_t bytes);

    /* Opens a file of the installed file set by its name, for reading from the start.
       Returns 1 when open, 0 when there is no such file, -1 on any other failure.
       The core has at most one file open. */
    int (*open)(void *ctx, const char *name);

    /* Reads the next bytes of the open file: 1 to capacity bytes read, 0 at the end of
       the file, -1 on failure. The core passes a capacity of at most 512. */
    int32_t (*read)(void *ctx, uint8_t *buffer, size_t capacity);

    /* Closes the open file. */
    void (*close)(void *ctx);

    /* Receives one line of diagnostic text, without a newline. May be NULL. */
    void (*log)(void *ctx, const char *text);
} odrig_host;

/* One leg, as the mapping file lists it, and its LED data from the last refresh:
   led_count * 3 bytes, red, green, blue per LED, in chain order. */
typedef struct odrig_leg {
    uint16_t leg;
    uint16_t pin;
    uint32_t led_count;
    const uint8_t *rgb;
} odrig_leg;

/* Called by odrig_core_feed once for every complete line. */
typedef void (*odrig_reply_fn)(void *ctx, const char *line, size_t line_length,
                               const char *reply, size_t reply_length);

/* Starts the core: reads and checks the installed file set. Returns NULL only when the
   host could not supply the first block of memory. */
odrig_core *odrig_core_begin(const odrig_host *host);

/* Asks for a refresh. Returns 1 when new LED data was produced, 0 when none was due. */
int odrig_core_poll(odrig_core *core, uint64_t now_ms);

/* The legs. Valid from odrig_core_begin on; rgb changes at every refresh. */
uint32_t odrig_core_leg_count(const odrig_core *core);
int odrig_core_leg(const odrig_core *core, uint32_t index, odrig_leg *out);

/* One command line in, one reply out. The line may end with a newline, with or without a
   carriage return before it. Writes the reply, with its newline and without a terminating
   zero, to reply and returns its length. capacity must be at least ODRIG_REPLY_MAX. */
size_t odrig_core_command(odrig_core *core, uint64_t now_ms,
                          const char *line, size_t length,
                          char *reply, size_t capacity);

/* For transports that deliver bytes. Splits them into lines, answers each line through
   odrig_core_command, and calls on_reply for each. Keeps an unfinished line for the
   next call. */
void odrig_core_feed(odrig_core *core, uint64_t now_ms,
                     const uint8_t *bytes, size_t length,
                     odrig_reply_fn on_reply, void *reply_ctx);

/* The reason the show is invalid, as status reports it, or NULL when it is valid. */
const char *odrig_core_error(const odrig_core *core);

#ifdef __cplusplus
}
#endif

#endif
