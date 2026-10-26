#ifndef ODRIG_ORDER_H
#define ODRIG_ORDER_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The file of the saved playlist order, and the file its next version is written into
// until it is renamed. No show names them: a name in `show.json` ends in `.odrg`.
const char kOrderFile[] = "order.txt";
const char kOrderPart[] = "order.part";

// Takes the block of the order's keys, for a host whose storage can be changed, once the
// item table is known. False when the host has no memory for it.
bool order_begin(Core &core);

// The key of an animation at a position of the playlist, an item of the item table or
// kDriveBase and a place of the drive: the playlist goes in the order of the keys. An
// animation that `order.txt` names has the number of its entry, from 0; an internal one it
// does not name 0x10000 and its position, an external one 0x20000 and its place.
uint32_t order_key(const Core &core, uint32_t position);

// The start, once the show is read: the keys of the internal animations from the file.
void order_start(Core &core);

// A drive's places were counted: each one's key is cleared, and the drive's check reads the
// file before it checks a file of the drive.
void order_drive_found(Core &core);

// Takes the hash of the name of the file at a place of the drive, as it is counted.
void order_drive_named(Core &core, uint32_t place, const char *name);

// Whether the drive's check is to read the file before the drive's files.
bool order_drive_due(const Core &core);

// One step of the drive's part of the order: the bytes of one read of the file at most.
void order_drive_step(Core &core);

// The drive's part of the order is read again from the file's start when the source it
// reads with was taken meanwhile.
void order_drive_yields(Core &core);

// Reads the whole file again at once and sets every key, internal and external.
void order_reload(Core &core);

// The item at a position is about to leave the item table; the keys follow the items.
void order_item_leaves(Core &core, uint32_t position);

// An item was added at the end of the item table: the file does not name it yet.
void order_item_added(Core &core, uint32_t position);

// Builds the tree of the drive's folders from the names of its places, once every place
// has its name and its id: the table in the listing's order, each place's folder byte,
// and the folders' ids after the files', in table order. A place whose folder would be
// past the table is left out with kTooManyFolders: one of a listed drive at once, with
// its log line; a staged one by its fault, when it is published.
void tree_build(Core &core);

// Drops the tree: no folder, no place in one, the root current.
void tree_clear(Core &core);

// A place left the drive: the folders left without a place at or below them leave the
// table, the others keep their ids and their order.
void tree_place_gone(Core &core, uint32_t place);

// The path of a folder of the table, from the drive's folder, into `into` with a 0 after
// it: the name of its place cut to its depth. Returns its length, 0 for the root and when
// the host gives no name.
uint32_t tree_folder_path(const Core &core, uint32_t folder, char *into, uint32_t room);

// The reply to `order get`: the ids of the listed animations in the saved order, from a
// position on, as many as fit, the position of the first one left out, and the revision.
uint32_t order_get(const Core &core, uint32_t from, Reply &reply);

// The reply to `order move`: the listed animation with the id `id` goes before the one with
// the id `before`, or last when `before` is 0, and the whole order is saved before the
// reply. `order-conflict` when `revision` is not the order's.
uint32_t order_move(Core &core, uint32_t revision, uint32_t id, uint32_t before, Reply &reply);

}  // namespace odrig

#endif
