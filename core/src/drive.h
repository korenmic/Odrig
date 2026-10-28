#ifndef ODRIG_DRIVE_H
#define ODRIG_DRIVE_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The drive's files and folders as the rest of the core reads them, whatever keeps them:
// the table and the tree of a drive without a catalog, or the index of a drive whose
// catalog is read, docs/catalog.md, "The index of a drive". A file is known by its position
// in the drive's walk, a folder by its ordinal in the tree, the root's 0.

// The lines of a folder's file and of the table, and of the map, padded to these lengths.
const uint32_t kIndexRow = 180;
const uint32_t kIndexIdRow = 36;

// The host's names of the table and of the map, and of their new versions.
extern const char kIndexTable[];
extern const char kIndexTableNew[];
extern const char kIndexMap[];
extern const char kIndexMapNew[];

// The host's name of the file of a folder of the index by its id, or of its new version,
// into room for kIndexNameRoom characters.
void index_folder_name(uint32_t id, bool fresh, char *into);

// Reads line `number` of the index file the host names `name`, of lines of `width` bytes,
// through the cursor's room: gives its text without the padding, which stays where it is
// until the room is read into again, and sets its length; null when the host cannot give
// it or it is not a line of the index.
const char *index_line(const Core &core, const char *name, uint32_t width, uint32_t number, uint32_t *length);

// The index's files have changed, or the drive: the room and the rows read hold nothing.
void index_forget(const Core &core);

// Reads a line of the table, the folder at `ordinal`, into `folder`, with the position its
// path stands at in the line and its length: false when it is not in its form.
bool index_parse_folder(const char *line, uint32_t length, uint32_t ordinal, IndexFolder &folder, uint32_t *path_at, uint32_t *path_length);

// Reads a line of a folder's file into a row: a file's, `f`, or a folder's, `d`. False when
// it is not in its form.
bool index_parse_row(const char *line, uint32_t length, DriveRow &row);

// Reads a line of the map: an id, its kind, its folder's ordinal and its line there.
bool index_parse_id(const char *line, uint32_t length, uint32_t *id, uint8_t *kind, uint32_t *ordinal, uint32_t *row);

// The number of the drive's files in its walk: the places of a drive without a catalog,
// the index's files of one with a catalog; 0 without a drive.
uint32_t drive_files(const Core &core);

// The number of the folders of the tree, the root among them: 1 while the tree is not
// known.
uint32_t drive_folder_count(const Core &core);

// The file of the drive at a position of its walk, read into one of the cursor's two rows
// and kept there until two other reads; null when there is none or it cannot be read, an
// index that cannot be read being damaged from then on.
const DriveRow *drive_row(const Core &core, uint32_t position);

// Whether the file at a position of the walk plays: listed, and without a fault.
bool drive_plays(const Core &core, uint32_t position);

// The folder of the tree at an ordinal. False when there is none.
bool drive_folder(const Core &core, uint32_t ordinal, IndexFolder &folder);

// The path of the folder at an ordinal into `into`, with its 0: its length, 0 for the root
// and for a folder whose path cannot be read.
uint32_t drive_folder_path(const Core &core, uint32_t ordinal, char *into, uint32_t room);

// The sub-folder at a place among those of a folder, in the tree's order, as a row: its id,
// its own files and its path; null when there is none.
const DriveRow *drive_subfolder(const Core &core, const IndexFolder &folder, uint32_t at);

// The ordinal of the folder whose own files hold a position of the walk, kNoFolder for none.
uint32_t drive_folder_of(const Core &core, uint32_t position);

// What an id of the drive is: 'f' a file, with its position in the walk; 'd' a folder,
// with its ordinal; 0 for an id that the drive has none of.
uint8_t drive_find(const Core &core, uint32_t id, uint32_t *value);

// The ordinal of the folder of the tree with this path, from the drive's folder, or
// kNoFolder.
uint32_t drive_folder_with_path(const Core &core, const char *path);

// Room for the host's name of a file of the drive, `drive/<place>` or `drive/<path>`.
const uint32_t kDriveOpenRoom = 6 + kDrivePathRoom;

// The host's name of the file at a position of the walk, to open it by: `drive/<place>` for
// a drive without a catalog, `drive/<path>` for one with. False when there is none.
bool drive_open_name(const Core &core, uint32_t position, char *into);

// The file at a position of the walk could not be played: a drive without a catalog marks
// its place left out; for a drive with one it is remembered by its name and its entry's
// CRC-32 for the rest of the boot and counted. The host's log says so.
void drive_faulted(Core &core, uint32_t position, Reason reason);

// The file of a drive left out in this boot with this name, cut to 32 characters, and the
// CRC-32 of its entry, or null.
const Remembered *drive_remembered(const Core &core, const char *name, uint32_t crc);

}  // namespace odrig

#endif
