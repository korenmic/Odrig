#ifndef ODRIG_PLAYLIST_H
#define ODRIG_PLAYLIST_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The file of the current playlist and the time spent in its window, and the file its next
// version is written into until it is renamed. Three lines: `odrig-playlist 1`, the
// playlist's path or an empty line for the root, and the milliseconds spent. An absent file
// means the root with a fresh window.
const char kPlaylistFile[] = "playlist.txt";
const char kPlaylistPart[] = "playlist.part";

// How often the file is written while a playlist plays and the tree has a folder.
const uint64_t kPlaylistSaveEveryMs = 900000;

// The start, once the show is read, for a host with a drive whose storage can be changed:
// reads the file through the second source, and keeps the path and the time spent; the
// root is current until a tree is known.
void playlist_start(Core &core);

// The current playlist changed, by a choice or by the rotation: the file is written now
// when it can be, else at the next refresh that is free.
void playlist_changed(Core &core);

// A refresh: writes the file when a change waits for it, or when the tree has a folder and
// kPlaylistSaveEveryMs have passed since the last write; not while an upload receives or a
// rebuild holds a page open, and never while the tree has no folder and no file exists.
void playlist_touch(Core &core, uint64_t now);

}  // namespace odrig

#endif
