#ifndef ODRIG_CORE_H
#define ODRIG_CORE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ODRIG_LINE_MAX  2048    /* longest command line, in characters */
#define ODRIG_REPLY_MAX 1024    /* longest reply, in bytes, with its newline */

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

    /* Storage that can be changed. A host without it sets write_open to NULL.
       A name is 1 to 32 characters of a-z, 0-9, '-', '_' and '.'. */

    /* Begins a new, empty file of this name, in place of one that has it. A file that was
       being written is given up and removed. Returns 1, or -1 on failure. The core has at
       most one file being written. */
    int (*write_open)(void *ctx, const char *name);

    /* Adds bytes to the file being written. length is 1 to 1500. Returns 1, or -1. */
    int (*write)(void *ctx, const uint8_t *bytes, size_t length);

    /* Ends the writing. When it has returned 1, the file is whole in storage and stays so
       through a power cut. Returns 1, or -1 on failure. */
    int (*write_close)(void *ctx);

    /* Gives the file `from` the name `to`, in place of a file that has it. After a power
       cut during the call, `to` is its old file or the new one, whole. Neither file is
       open or being written when the core calls this. Returns 1, or -1. */
    int (*rename)(void *ctx, const char *from, const char *to);

    /* Removes the file of this name. A file being written under it is given up.
       Returns 1 when it removed one, 0 when there was none, -1 on failure. */
    int (*remove)(void *ctx, const char *name);

    /* The free and the total bytes of the storage the files are in. A value above
       4294967295 is given as that. Returns 1, or -1 when the host cannot tell. */
    int (*space)(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes);

    /* Reads a file apart from the one that open, read and close hold: up to capacity
       bytes from this offset. Returns the number read, 0 at or after the end of the
       file, -1 on failure and when there is no such file. capacity is at most 512.
       The core reads a file with it from offset 0 on, each call where the last ended, but
       for the commands `read` and `catalog page` and for the files of a drive's index and
       of its rebuild, `drive/index-...` and `drive/rebuild...`, which it reads at any
       offset. */
    int32_t (*read_at)(void *ctx, const char *name, uint32_t offset,
                       uint8_t *buffer, size_t capacity);

    /* A drive of animations. A host without one sets drive to NULL. The core names the file
       at place p of the drive's list as `drive/p` to open and read_at, and the file of the
       drive's folder `odrig` with the name n as `drive/n`, n not made of digits alone, to
       open, read_at, write_open, rename and remove; no name of the installed file set has a
       slash. A name of the drive is the path of a file from the folder odrig: the names of
       at most three folders and the file's, joined by /, 1 to 100 bytes in all, each part
       printable ASCII other than \ : * ? " < > | that neither begins nor ends with a space
       or a dot. */

    /* The number of the drive that is plugged in now: a number other than 0 that changes
       each time a drive is plugged in, or 0 while none is. Called at refreshes. */
    uint32_t (*drive)(void *ctx);

    /* The name of the animation file at this place of the drive's list, as the drive has it,
       into buffer with a 0 after it, cut to capacity - 1 bytes. The list is the files of the
       drive's folder `odrig` and of its sub-folders to three levels whose names end in
       `.odrg` or `.odrgx`, in any case, and do not begin with a dot: depth first, a folder's
       files by the bytes of their names and then its sub-folders by the bytes of their
       names; a file in a sub-folder is named by its path from odrig. A host may end the
       list at its 256th file, or before the first file whose folder would be the 33rd
       sub-folder in it. Returns 1, or 0 when that drive has no file at that place or is not
       plugged in any more. */
    int (*drive_name)(void *ctx, uint32_t drive, uint32_t place, char *buffer, size_t capacity);
    /* Optional capacity of this mounted drive, in bytes. Returns 1, or -1 when
       unavailable or the generation changed. No writes are performed. */
    int (*drive_space)(void *ctx, uint32_t drive, uint64_t *free_bytes, uint64_t *total_bytes);
    /* Optional: a text that names the host, its build, its storage and the reason of its
       last start, into buffer with a 0 after it, cut to capacity - 1 bytes. Returns 1, or
       0 when it has none. */
    int (*about)(void *ctx, char *buffer, size_t capacity);

    /* Optional: lists the drive's folder `odrig` now, as drive_name describes the list. A
       host that has this function lists the folder only when it is called. Returns the
       number of animation files, or -1 when that drive is not plugged in any more. */
    int32_t (*drive_list)(void *ctx, uint32_t drive);

    /* Optional: gives the place to the file of the drive's folder with this name, so that
       drive_name gives the name and `drive/<place>` opens the file. Returns 1, or 0 when
       that drive is not plugged in any more or the name is not one of the drive. A host
       without it is listed for every drive. */
    int (*drive_bind)(void *ctx, uint32_t drive, uint32_t place, const char *name);

    /* Optional: 1 when the core may change the files of this drive with the storage
       functions, 0 otherwise. A host without it has a drive that is read only. */
    int (*drive_writable)(void *ctx, uint32_t drive);
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

/* Temporary 10x6 output state. RGB holds 60 pixels in physical chain order,
 * index=x*6+y with bottom-left coordinates. It lives until the next core call.
 * Normal legs and canvas geometry remain unchanged. */
typedef struct odrig_mini {
    uint32_t revision;
    uint8_t active;
    uint8_t requested;
    uint8_t pending;
    uint8_t failed;
    const uint8_t *rgb;
} odrig_mini;

/* Opt in only when the host implements dark, checked output transitions. */
void odrig_core_mini_support(odrig_core *core);
/* Returns 1 for a supported host and 60x60 canvas, otherwise 0. */
int odrig_core_mini(const odrig_core *core, odrig_mini *out);
/* Acknowledge only the matching pending revision; stale acknowledgements return 0.
 * Failed setup requires the host to keep all outputs dark until a successful retry. */
int odrig_core_mini_complete(odrig_core *core, uint32_t revision, int success);

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
