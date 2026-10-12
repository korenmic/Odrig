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

// How the show that is written differs from the show the tables hold. Without a
// difference the show is written as it is.
struct ShowChange {
    uint32_t without = kNothing;    // the position of an item that is left out
};

// Writes the show, with a change, as the file `show.part`: one line without spaces and a
// line feed, as docs/show.md has it. The text goes through the chunk buffer. False when
// the host could not take it; the file may then be there in part, and being written.
bool content_write_show(Core &core, const ShowChange &change);

// Takes the item at a position out of the tables: the items after it move up, its
// entries leave the entry table when it is a cycle, and its file leaves the file table
// when no other item names it. Every position the tables hold follows.
void content_take_out(Core &core, uint32_t position);

}  // namespace odrig

#endif
