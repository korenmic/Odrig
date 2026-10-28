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

// Takes the block of the order's keys and of the drive's tree, for a host whose storage can
// be changed, once the item table is known. False when the host has no memory for it.
bool order_begin(Core &core);

// The key of an animation item of the show at a position of the item table: the show's
// animations play in the order of the keys. An item that `order.txt` names has the number
// of its entry, from 0; one it does not name 0x10000 and its position. The drive's files
// have no key: they play in the order of the drive's walk.
uint32_t order_key(const Core &core, uint32_t position);

// The start, once the show is read: the keys of the show's animations from the file.
void order_start(Core &core);

// Reads the whole file again at once and sets every key.
void order_reload(Core &core);

// The item at a position is about to leave the item table; the keys follow the items.
void order_item_leaves(Core &core, uint32_t position);

// An item was added at the end of the item table: the file does not name it yet.
void order_item_added(Core &core, uint32_t position);

// Builds the tree of the folders of a drive without a catalog from the names of its places,
// which are in the listing's order: the table in that order, each folder with the place of
// its first file at or below it and its number of own files, and without its id, which the
// drive's taking up gives it after the files'. The places from the first whose folder would
// be past the 32nd sub-folder on are dropped.
void tree_build(Core &core);

// Drops the tree: no folder, the root current.
void tree_clear(Core &core);

// Makes a folder of the tree the current playlist, kept as its ordinal, its record and its
// path; the root for 0.
void tree_choose(Core &core, uint32_t folder);

// The current playlist's folder found again by its path, in a tree just read: the root when
// the tree has no folder of that path, with a fresh window, saved as such.
void tree_find_current(Core &core);

// A level of the drive's tree, as `list` and `order get` give it: the root, 0, which holds
// the show's items too, or a folder of the tree by its ordinal. The level a position of the
// playlist is at: 0 for an item of the show, the folder of a file of the drive.
uint32_t level_of(const Core &core, uint32_t position);

// The reply to `order get` and `order get in`: the ids of a level's listed animations in
// the saved order, from a position on, as many as fit, the position of the first one left
// out, and the revision of the level.
uint32_t order_get(const Core &core, uint32_t level, uint32_t from, Reply &reply);

// The reply to `order move`: the listed animation with the id `id` goes before the one with
// the id `before`, or last when `before` is 0, and the whole order is saved before the
// reply. `order-conflict` when `revision` is not that of the level of `id`.
uint32_t order_move(Core &core, uint32_t revision, uint32_t id, uint32_t before, Reply &reply);

}  // namespace odrig

#endif
