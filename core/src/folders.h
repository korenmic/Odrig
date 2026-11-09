#ifndef ODRIG_FOLDERS_H
#define ODRIG_FOLDERS_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The folders of the internal storage, docs/core.md, "Internal folders". Each folder is a
// folder of the storage named by its number, 1 to 255, and a file in it has the stored name
// `<number>/<name>`. Their paths, ids and Ignore are lines of `folders.txt`, in the tree's
// order, which the core reads through `read_at` whenever it needs them and never keeps:
//
//     odrig-folders 1 <next number>
//     <number> <id> <ignored> <path>
//
// `folders.part` is its next version until it is renamed.
const char kFoldersFile[] = "folders.txt";
const char kFoldersPart[] = "folders.part";

// The longest path of a folder, and the highest id one may have.
const uint32_t kFolderPathMost = 93;
const uint32_t kFolderIdMost = 60000;

// The depth of a path a folder may have, 1 to 3, or 0 for one it may not: names joined by
// `/` under the card's naming rule, kFolderPathMost bytes at most, the last not ending in
// `.odrg` or `.odrgx`.
uint32_t folder_path_depth(const char *path, uint32_t length);

// One line of `folders.txt`: the folder's number, id and own Ignore, the depth of its path,
// 1 to 3, the index of its line, and whether it or a folder above it is ignored.
struct FolderLine {
    uint32_t number;
    uint32_t id;
    uint32_t ignored;
    uint32_t depth;
    uint32_t index;
    uint32_t held;
};

// The folder with this number or this id: its line and, when `path` is given, its path
// with its 0, in room for kFolderPathMost + 1 characters. False when there is none.
bool folder_by_number(const Core &core, uint32_t number, FolderLine &line, char *path);
bool folder_by_id(const Core &core, uint32_t id, FolderLine &line, char *path);

// Whether an internal folder has this id.
bool internal_folder_id(const Core &core, uint32_t id);

// The folder with this path, of so many bytes: 1 with its line when there is one, 0 when
// there is none, -1 when `folders.txt` cannot be read. `twin` is set when a folder of the
// same parent has a name that differs from the path's last only in the case of its letters.
int32_t folder_by_path(const Core &core, const char *path, uint32_t length, FolderLine &line, bool *twin);

// The path the operator sees of a stored name, into room for kDrivePathRoom characters: the
// path of its folder, `/` and its file name, or the stored name itself for a file at the root,
// for one whose folder has no line and for one whose path would pass 100 bytes, which is no
// file of that folder.
void logical_path(const Core &core, const char *stored, char *into);

// The start, once the show's files are known: reads `folders.txt`, gives a new id to a folder
// whose id an item has, and marks each file with its folder's rank and Ignore. A file that is
// damaged or cannot be read is left as it is: the boot has no folders, and logs `folders
// unreadable`.
void folders_start(Core &core);

// Marks each file of the show with the rank of its folder and whether that folder or one
// above it is ignored, and finds the current internal playlist's ranks again.
void folders_derive(Core &core);

// `folder make internal <path>`: makes the folder, its line and its folder of the storage.
uint32_t internal_folder_make(Core &core, const char *path, Reply &reply);

// `ignore <id> 0|1` of an internal folder.
uint32_t internal_folder_ignore(Core &core, uint32_t id, bool ignored, Reply &reply);

// A file of the folder with this number left the show: when the folder holds no file and no
// sub-folder now, its line goes, and so do those of the folders above it that are left
// empty the same way, and then their folders of the storage.
void internal_folders_prune(Core &core, uint32_t number);

// `move internal <folder id> <path>`: gives an internal folder the new path, another parent,
// another name or both, and its sub-folders with it, by one rewrite of `folders.txt`. Every
// number, id, Ignore, stored name and file is kept; the current playlist follows.
uint32_t internal_folder_move(Core &core, uint32_t id, const char *path, Reply &reply);

// Makes the internal folder with this id the current playlist. False when there is none.
bool internal_choose(Core &core, uint32_t id);

// The id of the internal folder at a rank, 0 when there is none.
uint32_t internal_id_at(const Core &core, uint32_t rank);

// Writes the rows of `list` of the internal folders whose parent is the folder `parent`,
// 0 for the root, from the `skip`-th on, as long as they fit with `tail` bytes after them:
// gives the number written. `first` says whether a row was written before.
uint32_t internal_folder_rows(const Core &core, uint32_t parent, uint32_t skip, uint32_t total, uint32_t from, Reply &reply, bool *first);

// The number of the internal folders whose parent is the folder `parent`, 0 for the root.
uint32_t internal_folder_children(const Core &core, uint32_t parent);

// The rows of `list in <id>` of an internal folder's level.
uint32_t internal_list_level(const Core &core, uint32_t number, uint32_t from, Reply &reply);

}  // namespace odrig

#endif
