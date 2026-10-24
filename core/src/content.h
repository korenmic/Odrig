#ifndef ODRIG_CONTENT_H
#define ODRIG_CONTENT_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The reply to `space`: the free and the total bytes of the host's storage and the number
// of animation items of the show, which is 0 while the show is invalid. `storage-error`
// when the host cannot tell the space.
uint32_t content_space(const Core &core, Reply &reply);

// The reply to `list`: the items of a valid show in its order, from a position on, as many
// as fit into one reply, and the position of the first one left out.
uint32_t content_list(const Core &core, uint32_t from, Reply &reply);

// Carries out `remove` on a valid show and writes the reply: the item with this id leaves
// the show, in storage and in the tables.
uint32_t content_remove(Core &core, uint32_t id, Reply &reply);
uint32_t content_remove_many(Core &core, const uint16_t *ids, uint32_t count, Reply &reply);
uint32_t content_ignore(Core &core, uint32_t id, bool ignored, Reply &reply);
struct ShowChange;
bool content_removed(const Core &core, uint32_t position, const ShowChange &change);

// How the show that is written differs from the show the tables hold. Without a
// difference the show is written as it is.
struct ShowChange {
    const uint16_t *removed = nullptr;
    uint32_t removed_count = 0;
    uint32_t inclusion = kNothing;
    bool ignored = false;
    uint32_t without = kNothing;    // the position of an item that is left out
    uint32_t renamed = kNothing;    // the position of an animation item that names another file,
    const char *name = nullptr;     // which is this one
    uint32_t added_id = 0;          // the id of an animation item that is added at the end, or 0,
    const char *added_name = nullptr;   // and its file
};

// Writes the show, with a change, as the file `show.part`: one line without spaces and a
// line feed, as docs/show.md has it. The text goes through the chunk buffer. False when
// the host could not take it; the file may then be there in part, and being written.
bool content_write_show(Core &core, const ShowChange &change);

// Adds an animation item with a file of its own at the end of the tables. There is room.
void content_add_item(Core &core, uint32_t id, const char *name, uint32_t bytes, uint64_t total_ms);

// Gives the animation item at a position another file: its name, its size and its total
// duration. When another item names the item's old file too, the item gets an entry of
// its own at the end of the file table.
void content_change_file(Core &core, uint32_t position, const char *name, uint32_t bytes, uint64_t total_ms);

// Takes the item at a position out of the tables: the items after it move up, its
// entries leave the entry table when it is a cycle, and its file leaves the file table
// when no other item names it. Every position the tables hold follows.
void content_take_out(Core &core, uint32_t position);

}  // namespace odrig

#endif
