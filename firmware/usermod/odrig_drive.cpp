#include "odrig_drive.h"

#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>

#ifdef ODRIG_DRIVE_SD_SPI
#include <SD.h>
#include <SPI.h>
#include "odrig_sd_config.h"
#include "odrig_sd_capacity.h"
#else
#include "soc/usb_serial_jtag_struct.h"
#include "usb/msc_host.h"
#include "usb/msc_host_vfs.h"
#include "usb/usb_host.h"
#endif
#include "wled.h"

#include "odrig_files.h"
#include "odrig_log.h"

namespace {

// Where the drive is mounted, the folder of its animations, and the beginning of the name
// the core gives a file of the drive.
#ifdef ODRIG_DRIVE_SD_SPI
const char MOUNT[] = ODRIG_SD_MOUNT_PATH;
const char FOLDER[] = ODRIG_SD_MOUNT_PATH "/odrig";
#else
const char MOUNT[] = "/usb";
const char FOLDER[] = "/usb/odrig";
#endif
const char PREFIX[] = "drive/";
const size_t PREFIX_LENGTH = sizeof(PREFIX) - 1;
// The most files of the list, and the room for a name with its 0: a file with a longer
// name is passed over.
const uint32_t MOST_FILES = 256;
const size_t NAME_ROOM = 256;
const size_t PATH_ROOM = sizeof(FOLDER) + 1 + NAME_ROOM;
// The most sub-folders of the folder odrig that are taken, how deep below it a folder may
// lie, the folder of the file system that is never one of them, and the table of the
// folders still to be walked: so many paths of so much room each, with the 0.
const uint32_t MOST_FOLDERS = 32;
const uint32_t DEEPEST = 3;
const char SYSTEM_FOLDER[] = "System Volume Information";
const uint32_t MOST_PENDING = 256;
const size_t PENDING_ROOM = 104;
// The buffer of each file that is read: one request to the drive brings this many bytes.
const size_t READ_BUFFER = 4096;
// The longest name of a file of the drive that the core gives, and the room for a name
// `drive/<place>` or `drive/<name>` with its 0.
const size_t LONGEST_DRIVE_NAME = 100;
const size_t CORE_NAME_ROOM = sizeof(PREFIX) + LONGEST_DRIVE_NAME;
// The room for a name of the installed files with its 0.
const size_t FILES_NAME_ROOM = 33;

// The tasks run on the processor of WLED's loop. The drive's task mounts and lists media.
#ifndef ODRIG_DRIVE_SD_SPI
const uint32_t HOST_STACK = 4096;
const UBaseType_t HOST_PRIORITY = 2;
const uint32_t DRIVER_STACK = 4096;
const UBaseType_t DRIVER_PRIORITY = 2;
#endif
const uint32_t DRIVE_STACK = 6144;
const UBaseType_t DRIVE_PRIORITY = 1;
const BaseType_t DRIVE_PROCESSOR = 1;
#ifndef ODRIG_DRIVE_SD_SPI
const UBaseType_t EVENTS = 4;
// The events the watcher of devices keeps, and how often the host's task serves it.
const int WATCHER_EVENTS = 4;
const uint32_t SERVE_EVERY_MS = 20;
// The most devices the watcher keeps open at once, and the room for what one is with its 0.
const size_t MOST_DEVICES = 8;
const size_t ABOUT_ROOM = 96;
#endif
// What the list of a drive is when its folder odrig could not be opened.
const int32_t NO_FOLDER = -1;
const int32_t NOT_LISTED = -2;

// How long the drive's task looks for a computer on the port before it takes the port
// for a stick, unless the settings say otherwise, the most the settings may say, and how
// often it looks.
const uint32_t COMPUTER_WAIT_MS = 5000;
const uint32_t MOST_WAIT_MS = 60000;
#ifndef ODRIG_DRIVE_SD_SPI
const uint32_t LOOK_EVERY_MS = 10;
#endif
uint32_t waitMs = COMPUTER_WAIT_MS;

enum State : uint8_t { NO_HOST, LOOKING, COMPUTER, NO_DRIVE, NOT_READ, MOUNTED };
volatile State state = NO_HOST;
#ifdef ODRIG_DRIVE_SD_SPI
char summaryText[24] = "SD not configured";
#else
char summaryText[24] = "no USB host";
#endif

// Held for the number, the list and every file of the drive: by the core's calls, and by
// the task while it publishes a drive or drops one. The list is made when the core asks
// for it, and a place gets a name when the core gives one.
SemaphoreHandle_t guard = nullptr;

struct Guarded {
  Guarded() { xSemaphoreTake(guard, portMAX_DELAY); }
  ~Guarded() { xSemaphoreGive(guard); }
};

uint32_t number = 0;
uint32_t plugged = 0;
uint32_t listed = 0;
char (*names)[NAME_ROOM] = nullptr;
// The folders still to be walked while the folder is listed, and what the last listing
// counted: the sub-folders taken, and the files and the folders passed over.
char (*pending)[PENDING_ROOM] = nullptr;
uint32_t foldersListed = 0;
uint32_t passedFiles = 0;
uint32_t passedFolders = 0;

// The file `open` holds, with its path, and the one `read_at` holds, with the name the core
// gave it and the place its next read begins at.
FILE *played = nullptr;
char playedPath[PATH_ROOM] = "";
FILE *second = nullptr;
char secondName[CORE_NAME_ROOM] = "";
uint32_t secondAt = 0;
char *playedBuffer = nullptr;
char *secondBuffer = nullptr;

// Whether the file being written is the drive's, and the name of the installed file that is
// being written, when one is.
bool writingDrive = false;
char filesWritten[FILES_NAME_ROOM] = "";

#ifdef ODRIG_DRIVE_SD_SPI
SPIClass cardBus(FSPI);
void say(const char *format, ...);
bool cardMounted = false;
// Set only with the guard held. The worker closes the files before it unmounts the card.
bool cardFailed = false;
// Whether the card has its folder odrig, which the board never makes.
bool cardFolder = false;
const uint32_t CARD_POLL_MS = 1000;
const uint32_t CAPACITY_SLICE_MS = 5;
alignas(4) uint8_t cardProbe[512];
OdrigSdCapacity cardCapacity;
bool capacityUnsafe = false;

// Called with the guard held before any operation that might change allocation.
void invalidateCapacity() { cardCapacity.reset(cardMounted && !capacityUnsafe ? SD.numSectors() : 0); }

void capacityWriteFailed() {
  capacityUnsafe = true;
  cardCapacity.fail();
  say("capacity unavailable after failed storage mutation; waiting for remount");
}

// The file of the card being written, its path, and the bytes given to it so far.
FILE *written = nullptr;
char writtenPath[PATH_ROOM] = "";
size_t writtenBytes = 0;
#else
QueueHandle_t events = nullptr;
msc_host_device_handle_t device = nullptr;
msc_host_vfs_handle_t mounted = nullptr;

// The host's second client, which only says what comes and goes: it opens each device
// that comes and keeps it open with what it is, since the library tells only the clients
// that opened a device that it went.
usb_host_client_handle_t watcher = nullptr;

struct Watched {
  usb_device_handle_t handle;
  char about[ABOUT_ROOM];
};

Watched watched[MOST_DEVICES] = {};
#endif

// The host functions for every name that is not the drive's.
odrig_host files;

// A line of the log of the media's kind.
void say(const char *format, ...) {
  char text[OdrigLog::LINE_ROOM];
  va_list values;
  va_start(values, format);
  vsnprintf(text, sizeof(text), format, values);
  va_end(values);
#ifdef ODRIG_DRIVE_SD_SPI
  OdrigLog::add("sd", text);
#else
  OdrigLog::add("usb", text);
#endif
}

// Reading callbacks hold the guard and leave unmounting to the worker.
void readFailed() {
#ifdef ODRIG_DRIVE_SD_SPI
  cardFailed = true;
#endif
}

// The place a name `drive/<place>` stands for, MOST_FILES for a place beyond the list's
// room or a name of the drive that is no place, or -1 for a name that is not the drive's.
long placeOf(const char *name) {
  if (name == nullptr || strncmp(name, PREFIX, PREFIX_LENGTH) != 0) return -1;
  const char *digit = name + PREFIX_LENGTH;
  if (*digit == 0) return MOST_FILES;
  long place = 0;
  for (; *digit != 0; digit++) {
    if (*digit < '0' || *digit > '9' || place >= (long)MOST_FILES) return MOST_FILES;
    place = place * 10 + (*digit - '0');
  }
  return place < (long)MOST_FILES ? place : MOST_FILES;
}

// Whether a name of the drive stands for a place of its list, `drive/<digits>`, and not for
// a file of its folder by its name.
bool namesAPlace(const char *name) {
  const char *digit = name + PREFIX_LENGTH;
  if (*digit == 0) return false;
  for (; *digit != 0; digit++) {
    if (*digit < '0' || *digit > '9') return false;
  }
  return true;
}

// Whether a name is one the core may give a file of the drive: a path from the folder
// odrig, the names of at most DEEPEST folders and the file's name joined by /, 1 to 100
// bytes in all, each part printable ASCII other than \ : * ? " < > |, not empty and not
// beginning with a dot.
bool isDriveName(const char *name) {
  const size_t length = strlen(name);
  if (length == 0 || length > LONGEST_DRIVE_NAME || name[0] == '.') return false;
  uint32_t folders = 0;
  bool atStart = true;
  for (const char *at = name; *at != 0; at++) {
    const unsigned char c = (unsigned char)*at;
    if (c == '/') {
      if (atStart || ++folders > DEEPEST) return false;
      atStart = true;
      continue;
    }
    if (c < 0x20 || c > 0x7e || strchr("\\:*?\"<>|", c) != nullptr || (atStart && c == '.')) return false;
    atStart = false;
  }
  return !atStart;
}

// Whether a folder of the drive is walked: its name is sound as a part of a path, neither
// ends with a space or a dot, and is not the file system's own folder.
bool isFolderName(const char *name) {
  const size_t length = strlen(name);
  if (!isDriveName(name) || strchr(name, '/') != nullptr) return false;
  if (name[length - 1] == ' ' || name[length - 1] == '.') return false;
  return strcmp(name, SYSTEM_FOLDER) != 0;
}

// The path of the file at a place of the list of the drive that is plugged in. With the
// guard held.
bool pathAt(long place, char *path) {
  if (number == 0 || place < 0 || (uint32_t)place >= listed || names[place][0] == 0) return false;
  snprintf(path, PATH_ROOM, "%s/%s", FOLDER, names[place]);
  return true;
}

// The path of the file a name of the drive stands for: `drive/<place>` at that place of the
// list, `drive/<name>` by its name in the folder odrig, while a drive is plugged in. With the
// guard held.
bool drivePath(const char *name, char *path) {
  if (namesAPlace(name)) return pathAt(placeOf(name), path);
  const char *given = name + PREFIX_LENGTH;
  if (number == 0 || !isDriveName(given)) return false;
  snprintf(path, PATH_ROOM, "%s/%s", FOLDER, given);
  return true;
}

FILE *opened(const char *path, char *buffer) {
  FILE *file = fopen(path, "rb");
  if (file != nullptr) setvbuf(file, buffer, _IOFBF, READ_BUFFER);
  return file;
}

void closePlayed() {
  if (played != nullptr) fclose(played);
  played = nullptr;
  playedPath[0] = 0;
}

void closeSecond() {
  if (second != nullptr) fclose(second);
  second = nullptr;
  secondName[0] = 0;
}

uint32_t driveNumber(void *) {
  Guarded held;
  return number;
}

// Capacity queries never wait for the card worker or perform card IO.
int driveSpace(void *, uint32_t drive, uint64_t *freeBytes, uint64_t *totalBytes) {
#ifdef ODRIG_DRIVE_SD_SPI
  if (xSemaphoreTake(guard, 0) != pdTRUE) return -1;
  const bool known = drive != 0 && drive == number && cardMounted && !cardFailed &&
                     written == nullptr && cardCapacity.known();
  if (known) {
    *totalBytes = cardCapacity.total();
    *freeBytes = cardCapacity.free();
  }
  xSemaphoreGive(guard);
  return known ? 1 : -1;
#else
  Guarded held;
  if (drive == 0 || drive != number || mounted == nullptr) return -1;
  return msc_host_vfs_space(mounted, freeBytes, totalBytes) == ESP_OK ? 1 : -1;
#endif
}

int driveName(void *, uint32_t drive, uint32_t place, char *buffer, size_t capacity) {
  Guarded held;
  if (drive == 0 || drive != number || place >= listed || capacity == 0 || names[place][0] == 0) return 0;
  strncpy(buffer, names[place], capacity - 1);
  buffer[capacity - 1] = 0;
  return 1;
}

int openFile(void *ctx, const char *name) {
  const long place = placeOf(name);
  {
    Guarded held;
    closePlayed();
    if (place >= 0) {
      files.close(ctx);
      char path[PATH_ROOM];
      if (!drivePath(name, path)) return 0;
      played = opened(path, playedBuffer);
      if (played != nullptr) {
        strcpy(playedPath, path);
        return 1;
      }
      if (errno != ENOENT) readFailed();
      return errno == ENOENT ? 0 : -1;
    }
  }
  return files.open(ctx, name);
}

int32_t readSome(void *ctx, uint8_t *buffer, size_t capacity) {
  {
    Guarded held;
    if (played != nullptr) {
      const size_t count = fread(buffer, 1, capacity, played);
      const bool failed = ferror(played) != 0;
      if (failed) readFailed();
      return count == 0 && failed ? -1 : (int32_t)count;
    }
  }
  return files.read(ctx, buffer, capacity);
}

void closeFile(void *ctx) {
  {
    Guarded held;
    closePlayed();
  }
  files.close(ctx);
}

int32_t readPart(void *ctx, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity) {
  const long place = placeOf(name);
  if (place < 0) return files.read_at(ctx, name, offset, buffer, capacity);
  Guarded held;
  if (second == nullptr || strcmp(secondName, name) != 0) {
    closeSecond();
    char path[PATH_ROOM];
    if (strlen(name) >= CORE_NAME_ROOM || !drivePath(name, path)) return -1;
    second = opened(path, secondBuffer);
    if (second == nullptr) {
      if (errno != ENOENT) readFailed();
      return -1;
    }
    strcpy(secondName, name);
    secondAt = 0;
  }
  if (secondAt != offset) {
    if (fseek(second, (long)offset, SEEK_SET) != 0) {
      readFailed();
      return -1;
    }
    secondAt = offset;
  }
  const size_t count = fread(buffer, 1, capacity, second);
  const bool failed = ferror(second) != 0;
  if (failed) readFailed();
  if (count == 0 && failed) return -1;
  secondAt += (uint32_t)count;
  return (int32_t)count;
}

// Whether a name is one of an animation file: it ends in .odrg or .odrgx, in any case, and
// does not begin with a dot.
bool isAnimation(const char *name) {
  const size_t length = strlen(name);
  if (length >= NAME_ROOM || name[0] == '.') return false;
  return (length >= 5 && strcasecmp(name + length - 5, ".odrg") == 0) || (length >= 6 && strcasecmp(name + length - 6, ".odrgx") == 0);
}

// Puts a name into the list among the names of its folder, which fill the slots from
// `first` to `*kept`, in the order of their bytes, so that the list holds the first
// MOST_FILES names of the listing. False when a name is left out of the list for it: this
// one, or the last of a full list that it comes before.
bool keepName(const char *name, uint32_t *kept, uint32_t first) {
  uint32_t at = *kept;
  while (at > first && strcmp(names[at - 1], name) > 0) at--;
  if (at >= MOST_FILES) return false;
  const uint32_t moved = (*kept < MOST_FILES ? *kept : MOST_FILES - 1) - at;
  memmove(names[at + 1], names[at], moved * NAME_ROOM);
  strcpy(names[at], name);
  if (*kept >= MOST_FILES) return false;
  (*kept)++;
  return true;
}

// Puts a folder's path among the folders still to be walked, below those that come after
// it by their bytes, so that the first by bytes is taken next. False when there is no room.
bool pushPending(const char *path, uint32_t *count) {
  if (*count >= MOST_PENDING || strlen(path) >= PENDING_ROOM) return false;
  uint32_t at = *count;
  while (at > 0 && strcmp(pending[at - 1], path) < 0) at--;
  memmove(pending[at + 1], pending[at], (*count - at) * PENDING_ROOM);
  strcpy(pending[at], path);
  (*count)++;
  return true;
}

// The folders of the paths kept so far, counted as the limit counts them: a folder with
// its uncounted ancestors when the first file at or below it is kept. The names are cut
// at the first whose folder would be counted past MOST_FOLDERS; the rest are passed over.
// With the walk ended, the pending table is free and holds the folders counted.
void cutFolders(uint32_t *kept, uint32_t *folders, uint32_t *passedFiles) {
  uint32_t counted = 0;
  for (uint32_t at = 0; at < *kept; at++) {
    uint32_t added = 0;
    for (const char *slash = strchr(names[at], '/'); slash != nullptr; slash = strchr(slash + 1, '/')) {
      const size_t length = (size_t)(slash - names[at]);
      bool known = false;
      for (uint32_t folder = 0; folder < counted + added && !known; folder++) {
        known = strlen(pending[folder]) == length && memcmp(pending[folder], names[at], length) == 0;
      }
      if (known || counted + added >= MOST_PENDING) continue;
      memcpy(pending[counted + added], names[at], length);
      pending[counted + added][length] = 0;
      added++;
    }
    if (counted + added > MOST_FOLDERS) {
      *passedFiles += *kept - at;
      *kept = at;
      break;
    }
    counted += added;
  }
  *folders = counted;
}

// The list of the drive's folder odrig, made with the guard held: the paths of its
// animation files and of its sub-folders' to DEEPEST levels, depth first, a folder's files
// by the bytes of their names and then its sub-folders by the bytes of their names, at
// most MOST_FILES files and MOST_FOLDERS sub-folders. Its length, NO_FOLDER when the drive
// has no folder odrig, or NOT_LISTED when the folder could not be read. What was passed
// over is counted for the log: the files beyond the limits, and the folders beyond them,
// too deep, or not walked for their names.
int32_t listFolder() {
  uint32_t kept = 0;
  uint32_t pendingCount = 0;
  char path[PATH_ROOM];
  char relative[PENDING_ROOM + 1 + NAME_ROOM];
  pending[0][0] = 0;
  pendingCount = 1;
  bool rootRead = false;
  passedFiles = passedFolders = 0;
  while (pendingCount > 0) {
    pendingCount--;
    strcpy(relative, pending[pendingCount]);
    const bool root = relative[0] == 0;
    uint32_t depth = 0;
    for (const char *at = relative; *at != 0; at++) depth += *at == '/';
    if (!root) depth++;
    snprintf(path, PATH_ROOM, root ? "%s%s" : "%s/%s", FOLDER, relative);
    DIR *folder = opendir(path);
    if (folder == nullptr) {
      if (root) return errno == ENOENT ? NO_FOLDER : NOT_LISTED;
      passedFolders++;
      continue;
    }
    rootRead = true;
    const uint32_t first = kept;
    while (const dirent *entry = readdir(folder)) {
      const size_t relativeLength = strlen(relative);
      if (entry->d_type == DT_REG && isAnimation(entry->d_name)) {
        if (relativeLength + 1 + strlen(entry->d_name) >= NAME_ROOM) continue;
        snprintf(relative + (root ? 0 : relativeLength), NAME_ROOM, root ? "%s" : "/%s", entry->d_name);
        if (!keepName(relative, &kept, first)) passedFiles++;
        relative[relativeLength] = 0;
      } else if (entry->d_type == DT_DIR && strcmp(entry->d_name, ".") != 0 && strcmp(entry->d_name, "..") != 0) {
        if (depth >= DEEPEST || !isFolderName(entry->d_name)) {
          passedFolders++;
          continue;
        }
        snprintf(relative + (root ? 0 : relativeLength), NAME_ROOM, root ? "%s" : "/%s", entry->d_name);
        if (!pushPending(relative, &pendingCount)) passedFolders++;
        relative[relativeLength] = 0;
      }
    }
    closedir(folder);
  }
  if (!rootRead) return NOT_LISTED;
  cutFolders(&kept, &foldersListed, &passedFiles);
  return (int32_t)kept;
}

// Whether the drive has its folder odrig, told without reading the folder.
bool folderThere() {
  struct stat found;
  return stat(FOLDER, &found) == 0 && S_ISDIR(found.st_mode);
}

void setSummary() {
  if (state == NO_HOST) {
#ifdef ODRIG_DRIVE_SD_SPI
    strcpy(summaryText, OdrigSdConfig::valid() ? "no SD reader" : "SD not configured");
#else
    strcpy(summaryText, "no USB host");
#endif
  } else if (state == LOOKING) {
#ifdef ODRIG_DRIVE_SD_SPI
    strcpy(summaryText, "looking for SD");
#else
    strcpy(summaryText, "looking for a computer");
#endif
  } else if (state == COMPUTER) {
    strcpy(summaryText, "computer");
  } else if (state == NO_DRIVE) {
    strcpy(summaryText, "none");
  } else if (state == NOT_READ) {
    strcpy(summaryText, "not readable");
  } else {
    snprintf(summaryText, sizeof summaryText, "%u files", (unsigned)listed);
  }
}

// The line of the log for a list of the drive's folder: the number of its animation files,
// or why there is none. A drive without the folder was said when it was mounted.
void sayListed(int32_t found) {
#ifdef ODRIG_DRIVE_SD_SPI
  const char *medium = "card";
  if (found == NOT_LISTED) say("card folder odrig could not be read");
#else
  const char *medium = "stick";
  if (found == NOT_LISTED) say("stick not opened: a fault in reading the folder odrig");
#endif
  if (found < 0) return;
  char where[48];
  char passed[64];
  if (foldersListed == 0) {
    strcpy(where, "odrig");
  } else {
    snprintf(where, sizeof where, "%u folders of odrig", (unsigned)foldersListed);
  }
  if (passedFiles == 0 && passedFolders == 0) {
    passed[0] = 0;
  } else {
    snprintf(passed, sizeof passed, "; %u files and %u folders passed over", (unsigned)passedFiles, (unsigned)passedFolders);
  }
  say("%s opened: %u animation files in %s%s", medium, (unsigned)found, where, passed);
}

// Lists the folder of the drive that is plugged in, as the core asks: its names take the
// places of the list. A name the core gave read_at may stand for another file now.
int32_t driveList(void *, uint32_t drive) {
  Guarded held;
  if (drive == 0 || drive != number) return -1;
  closeSecond();
  const int32_t found = listFolder();
  listed = found < 0 ? 0 : (uint32_t)found;
  sayListed(found);
  setSummary();
  return (int32_t)listed;
}

// Gives a place of the list the file of the folder odrig with this name, as the core reads
// the drive's catalog. The places before it that have no name stay without one; read_at's
// file of that place is taken again at its next read.
int driveBind(void *, uint32_t drive, uint32_t place, const char *name) {
  Guarded held;
  if (drive == 0 || drive != number || place >= MOST_FILES || name == nullptr || !isDriveName(name)) return 0;
  for (uint32_t empty = listed; empty < place; empty++) names[empty][0] = 0;
  strcpy(names[place], name);
  if (place >= listed) listed = place + 1;
  if (placeOf(secondName) == (long)place) closeSecond();
  setSummary();
  return 1;
}

#ifdef ODRIG_DRIVE_SD_SPI
// The card is written while it is mounted with its folder odrig and no read of it failed.
int driveWritable(void *, uint32_t drive) {
  Guarded held;
  return drive != 0 && drive == number && cardMounted && !cardFailed && cardFolder ? 1 : 0;
}

// The path of the file of the card that a change of the core names, `drive/<name>`, while
// the card can be written. No place of the list is changed. With the guard held.
bool changedPath(const char *name, char *path) {
  return cardMounted && !cardFailed && cardFolder && !namesAPlace(name) && drivePath(name, path);
}

// Before a change of a file of the card: the file `open` holds is closed when it is that
// file, so that its reads fail and not those of the card; the one read_at holds is closed
// always, as its name may stand for another file afterwards. FAT tells no case apart.
void changing(const char *path) {
  if (played != nullptr && strcasecmp(playedPath, path) == 0) closePlayed();
  closeSecond();
}

// Gives up the card's file being written: closed as far as it got, and removed when asked.
// With the guard held.
void giveUpWritten(bool removing) {
  if (written == nullptr) return;
  invalidateCapacity();
  const bool closed = fclose(written) == 0;
  written = nullptr;
  const bool removed = !removing || unlink(writtenPath) == 0 || errno == ENOENT;
  if (!closed || !removed) capacityWriteFailed();
  writtenPath[0] = 0;
}

// The card's file being written is given up and removed.
void dropDriveFile() {
  OdrigFiles::StorageCall call;
  Guarded held;
  giveUpWritten(true);
}

int beginDriveFile(const char *name) {
  OdrigFiles::StorageCall call;
  Guarded held;
  giveUpWritten(true);
  char path[PATH_ROOM];
  if (!changedPath(name, path)) return -1;
  invalidateCapacity();
  changing(path);
  written = fopen(path, "wb");
  if (written == nullptr) { capacityWriteFailed(); return -1; }
  strcpy(writtenPath, path);
  writtenBytes = 0;
  return 1;
}

int addDriveBytes(const uint8_t *bytes, size_t length) {
  OdrigFiles::StorageCall call;
  Guarded held;
  if (written == nullptr) return -1;
  invalidateCapacity();
  writtenBytes += length;
  if (fwrite(bytes, 1, length, written) == length) return 1;
  capacityWriteFailed();
  return -1;
}

// The file is whole when its data and its directory entry are on the card and it holds as
// many bytes as were given.
int endDriveFile() {
  OdrigFiles::StorageCall call;
  Guarded held;
  if (written == nullptr) return -1;
  invalidateCapacity();
  struct stat found;
  bool whole = fflush(written) == 0 && fsync(fileno(written)) == 0 && fstat(fileno(written), &found) == 0 && (size_t)found.st_size == writtenBytes;
  whole = fclose(written) == 0 && whole;
  written = nullptr;
  writtenPath[0] = 0;
  if (!whole) capacityWriteFailed();
  return whole ? 1 : -1;
}

// FAT gives no file a name that another file has, so the file that has the new name is
// removed first, once the file to be renamed is known to be there. After a cut between the
// two, that file is there under its old name, and the catalog's commit renames it again.
int renameDriveFile(const char *from, const char *to) {
  OdrigFiles::StorageCall call;
  Guarded held;
  char pathFrom[PATH_ROOM], pathTo[PATH_ROOM];
  if (!changedPath(from, pathFrom) || !changedPath(to, pathTo)) return -1;
  invalidateCapacity();
  if (written != nullptr && (strcasecmp(writtenPath, pathFrom) == 0 || strcasecmp(writtenPath, pathTo) == 0)) giveUpWritten(false);
  changing(pathFrom);
  changing(pathTo);
  struct stat found;
  if (stat(pathFrom, &found) != 0 || !S_ISREG(found.st_mode)) return -1;
  if (strcasecmp(pathFrom, pathTo) != 0 && unlink(pathTo) != 0 && errno != ENOENT) {
    capacityWriteFailed(); return -1;
  }
  if (rename(pathFrom, pathTo) == 0) return 1;
  capacityWriteFailed();
  return -1;
}

int removeDriveFile(const char *name) {
  OdrigFiles::StorageCall call;
  Guarded held;
  char path[PATH_ROOM];
  if (!changedPath(name, path)) return -1;
  invalidateCapacity();
  if (written != nullptr && strcasecmp(writtenPath, path) == 0) giveUpWritten(false);
  changing(path);
  if (unlink(path) == 0) return 1;
  if (errno == ENOENT) return 0;
  capacityWriteFailed();
  return -1;
}
#else
// A stick is never written.
int driveWritable(void *, uint32_t) { return 0; }
void dropDriveFile() {}
int beginDriveFile(const char *) { return -1; }
int addDriveBytes(const uint8_t *, size_t) { return -1; }
int endDriveFile() { return -1; }
int renameDriveFile(const char *, const char *) { return -1; }
int removeDriveFile(const char *) { return -1; }
#endif

// The storage functions: a name of the drive goes to the drive, every other name to the
// functions of `files`. The core writes one file at a time, in either storage: beginning
// one gives up and removes the one being written in the other.
int beginFile(void *ctx, const char *name) {
  if (placeOf(name) < 0) {
    if (writingDrive) dropDriveFile();
    writingDrive = false;
    const int begun = files.write_open(ctx, name);
    filesWritten[0] = 0;
    if (begun == 1 && strlen(name) < FILES_NAME_ROOM) strcpy(filesWritten, name);
    return begun;
  }
  if (filesWritten[0] != 0) files.remove(ctx, filesWritten);
  filesWritten[0] = 0;
  writingDrive = true;
  return beginDriveFile(name);
}

int addBytes(void *ctx, const uint8_t *bytes, size_t length) {
  return writingDrive ? addDriveBytes(bytes, length) : files.write(ctx, bytes, length);
}

int endFile(void *ctx) {
  if (writingDrive) {
    writingDrive = false;
    return endDriveFile();
  }
  filesWritten[0] = 0;
  return files.write_close(ctx);
}

// An installed file that is renamed or removed is being written no more.
void letGoOf(const char *name) {
  if (strcmp(filesWritten, name) == 0) filesWritten[0] = 0;
}

int renameFile(void *ctx, const char *from, const char *to) {
  const bool fromDrive = placeOf(from) >= 0;
  if (fromDrive != (placeOf(to) >= 0)) return -1;
  if (fromDrive) return renameDriveFile(from, to);
  letGoOf(from);
  letGoOf(to);
  return files.rename(ctx, from, to);
}

int removeFile(void *ctx, const char *name) {
  if (placeOf(name) >= 0) return removeDriveFile(name);
  letGoOf(name);
  return files.remove(ctx, name);
}

#ifndef ODRIG_DRIVE_SD_SPI
// A drive came: it is mounted read as it is, never formatted, and published with a new
// number. Its folder is listed when the core asks.
void plugIn(uint8_t address) {
  if (device != nullptr) return;
  const esp_err_t installed = msc_host_install_device(address, &device);
  if (installed != ESP_OK) {
    say("stick not opened: a fault in reading (%s)", esp_err_to_name(installed));
    device = nullptr;
    state = NOT_READ;
    setSummary();
    return;
  }
  esp_vfs_fat_mount_config_t mount = {};
  mount.format_if_mount_failed = false;
  mount.max_files = 3;
  mount.allocation_unit_size = 0;
  const esp_err_t registered = msc_host_vfs_register(device, MOUNT, &mount, &mounted);
  if (registered != ESP_OK) {
    say("stick not opened: no file system it reads (%s)", esp_err_to_name(registered));
    mounted = nullptr;
    state = NOT_READ;
    setSummary();
    return;
  }
  if (folderThere()) {
    say("stick mounted");
  } else {
    say("the stick has no folder odrig");
  }
  Guarded held;
  listed = 0;
  number = ++plugged;
  state = MOUNTED;
  setSummary();
}

// The drive went: its number is 0 from now on, its files are closed, and it is unmounted.
void pullOut() {
  Guarded held;
  number = 0;
  listed = 0;
  closePlayed();
  closeSecond();
  if (mounted != nullptr) msc_host_vfs_unregister(mounted);
  mounted = nullptr;
  if (device != nullptr) msc_host_uninstall_device(device);
  device = nullptr;
  state = NO_DRIVE;
  setSummary();
}

void driverEvent(const msc_host_event_t *event, void *) { xQueueSend(events, event, 0); }

// A device came: what it is, by its device descriptor and the class of its first
// interface. It is kept open until it goes, while there is room for it.
void describe(uint8_t address) {
  usb_device_handle_t opened = nullptr;
  const esp_err_t result = usb_host_device_open(watcher, address, &opened);
  if (result != ESP_OK) {
    say("a device came that could not be opened (%s)", esp_err_to_name(result));
    return;
  }
  const usb_device_desc_t *descriptor = nullptr;
  if (usb_host_get_device_descriptor(opened, &descriptor) != ESP_OK) descriptor = nullptr;
  unsigned kind = descriptor != nullptr ? descriptor->bDeviceClass : 0;
  const usb_config_desc_t *config = nullptr;
  if (usb_host_get_active_config_descriptor(opened, &config) == ESP_OK && config != nullptr) {
    const usb_intf_desc_t *first = usb_parse_interface_descriptor(config, 0, 0, nullptr);
    if (first != nullptr) kind = first->bInterfaceClass;
  }
  char other[32];
  snprintf(other, sizeof(other), "another device (class %u)", kind);
  const char *named = kind == USB_CLASS_HUB ? "a hub" : kind == USB_CLASS_MASS_STORAGE ? "a stick" : other;
  char about[ABOUT_ROOM];
  snprintf(about, sizeof(about), "maker %04x, product %04x, %s", descriptor != nullptr ? descriptor->idVendor : 0u, descriptor != nullptr ? descriptor->idProduct : 0u, named);
  say("a device came: %s", about);
  Watched *place = nullptr;
  for (Watched &one : watched) {
    if (one.handle == nullptr) {
      place = &one;
      break;
    }
  }
  if (place == nullptr) {
    usb_host_device_close(watcher, opened);
    return;
  }
  place->handle = opened;
  strcpy(place->about, about);
}

void watcherEvent(const usb_host_client_event_msg_t *event, void *) {
  if (event->event == USB_HOST_CLIENT_EVENT_NEW_DEV) {
    describe(event->new_dev.address);
  } else if (event->event == USB_HOST_CLIENT_EVENT_DEV_GONE) {
    for (Watched &one : watched) {
      if (one.handle == event->dev_gone.dev_hdl) {
        say("a device went: %s", one.about);
        one.handle = nullptr;
        break;
      }
    }
    usb_host_device_close(watcher, event->dev_gone.dev_hdl);
  }
}

// The events of the USB host library, and between them those of the watcher of devices.
void hostEvents(void *) {
  for (;;) {
    uint32_t flags = 0;
    usb_host_lib_handle_events(pdMS_TO_TICKS(SERVE_EVERY_MS), &flags);
    if (flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) usb_host_device_free_all();
    usb_host_client_handle_events(watcher, 0);
  }
}

// Whether a computer shows itself on the port within the wait: a USB host sends a
// start-of-frame packet each millisecond to the device it serves, and the chip's unit for
// serial and JTAG keeps the frame index of the last one.
bool computerThere() {
  if (waitMs == 0) return false;
  const uint32_t first = USB_SERIAL_JTAG.fram_num.sof_frame_index;
  for (uint32_t waited = 0; waited < waitMs; waited += LOOK_EVERY_MS) {
    vTaskDelay(pdMS_TO_TICKS(LOOK_EVERY_MS));
    if (USB_SERIAL_JTAG.fram_num.sof_frame_index != first) return true;
  }
  return false;
}

// Switches the port to host mode, registers the watcher of devices and starts the driver
// of flash drives. ESP_OK, or the error of the step that failed.
esp_err_t startHost() {
  usb_host_config_t host = {};
  host.skip_phy_setup = false;
  host.intr_flags = ESP_INTR_FLAG_LEVEL1;
  esp_err_t result = usb_host_install(&host);
  if (result != ESP_OK) return result;
  usb_host_client_config_t client = {};
  client.is_synchronous = false;
  client.max_num_event_msg = WATCHER_EVENTS;
  client.async.client_event_callback = watcherEvent;
  client.async.callback_arg = nullptr;
  result = usb_host_client_register(&client, &watcher);
  if (result != ESP_OK) return result;
  xTaskCreatePinnedToCore(hostEvents, "odrig-usb", HOST_STACK, nullptr, HOST_PRIORITY, nullptr, DRIVE_PROCESSOR);
  msc_host_driver_config_t driver = {};
  driver.create_backround_task = true;
  driver.task_priority = DRIVER_PRIORITY;
  driver.stack_size = DRIVER_STACK;
  driver.core_id = DRIVE_PROCESSOR;
  driver.callback = driverEvent;
  driver.callback_arg = nullptr;
  return msc_host_install(&driver);
}

// The drive's task: it looks for a computer first, and leaves the port to one that is
// there. Otherwise it takes the port for a stick and takes up and drops drives.
void driveEvents(void *) {
  if (computerThere()) {
    say("a computer is on the port, which stays a serial port");
    state = COMPUTER;
    setSummary();
    vTaskDelete(nullptr);
    return;
  }
  say("no computer on the port within %u s", (unsigned)(waitMs / 1000));
  const esp_err_t started = startHost();
  if (started != ESP_OK) {
    say("host did not start: %s", esp_err_to_name(started));
    state = NO_HOST;
    setSummary();
    vTaskDelete(nullptr);
    return;
  }
  say("host started");
  state = NO_DRIVE;
  setSummary();
  msc_host_event_t event;
  for (;;) {
    if (xQueueReceive(events, &event, portMAX_DELAY) != pdTRUE) continue;
    if (event.event == msc_host_event_t::MSC_DEVICE_CONNECTED) {
      plugIn(event.device.address);
    } else {
      pullOut();
    }
  }
}
#else

// Called with no card published. The VFS is read and written only through the callbacks
// above. Its folder is listed when the core asks.
void mountCard() {
  if (!SD.begin(ODRIG_SD_CS, cardBus, ODRIG_SD_FREQUENCY, MOUNT, 3, false)) {
    if (state != NOT_READ) say("card not mounted; no card or unreadable file system");
    state = NOT_READ;
    setSummary();
    return;
  }
  cardMounted = true;
  const bool folder = folderThere();
  if (folder) {
    say("card mounted");
  } else {
    say("the card has no folder odrig");
  }
  Guarded held;
  listed = 0;
  // Zero always means absent, also when the generation counter wraps.
  if (++plugged == 0) ++plugged;
  number = plugged;
  capacityUnsafe = false;
  invalidateCapacity();
  cardFailed = false;
  cardFolder = folder;
  state = MOUNTED;
  setSummary();
}

// One worker pass. Card type and size are cached by Arduino and do not prove presence:
// a sector read does. It uses the same guard as the playback and validation handles.
void sdStep() {
  if (!cardMounted) {
    mountCard();
    return;
  }
  bool removed = false;
  {
    Guarded held;
    if (cardFailed || !SD.readRAW(cardProbe, 0)) {
      number = 0;
      listed = 0;
      closePlayed();
      closeSecond();
      giveUpWritten(false);
      SD.end();
      cardMounted = false;
      cardCapacity.fail();
      cardFailed = false;
      cardFolder = false;
      state = NO_DRIVE;
      setSummary();
      removed = true;
    }
  }
  if (removed) say("card unavailable; files closed, waiting for a card");
}

void capacityStep() {
  Guarded held;
  if (!cardMounted || cardFailed || written != nullptr || !cardCapacity.pending()) return;
  if (SD.sectorSize() != 512 || !SD.readRAW(cardProbe, cardCapacity.sector())) {
    cardCapacity.fail();
    say("capacity unavailable: sector read failed");
    return;
  }
  cardCapacity.consume(cardProbe);
  if (!cardCapacity.pending() && !cardCapacity.known()) say("capacity unavailable: unsupported volume geometry");
}

void driveEvents(void *) {
  // SD.begin calls SPI.begin without pin arguments. Never let it fall back to the
  // board's default SPI pins when our explicit assignment could not be started.
  if (!cardBus.begin(ODRIG_SD_SCK, ODRIG_SD_MISO, ODRIG_SD_MOSI, ODRIG_SD_CS)) {
    say("SPI did not start on the configured pins; reader disabled");
    state = NO_HOST;
    setSummary();
    vTaskDelete(nullptr);
    return;
  }
  uint32_t untilPoll = 0;
  for (;;) {
    if (untilPoll == 0) {
      sdStep();
      untilPoll = CARD_POLL_MS;
    } else {
      capacityStep();
    }
    bool scanning;
    {
      Guarded held;
      scanning = cardCapacity.pending() && written == nullptr;
    }
    const uint32_t pause = scanning ? CAPACITY_SLICE_MS : CARD_POLL_MS;
    untilPoll = pause >= untilPoll ? 0 : untilPoll - pause;
    const TickType_t ticks = pdMS_TO_TICKS(pause);
    vTaskDelay(ticks != 0 ? ticks : 1);
  }
}

#endif

}  // namespace

void OdrigDrive::begin() {
#ifdef ODRIG_DRIVE_SD_SPI
  if (!OdrigSdConfig::valid()) {
    say("SD pins or SPI frequency not configured safely; reader disabled");
    return;
  }
#endif
  guard = xSemaphoreCreateMutex();
#ifndef ODRIG_DRIVE_SD_SPI
  events = xQueueCreate(EVENTS, sizeof(msc_host_event_t));
#endif
  names = static_cast<char (*)[NAME_ROOM]>(heap_caps_malloc(MOST_FILES * NAME_ROOM, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  pending = static_cast<char (*)[PENDING_ROOM]>(heap_caps_malloc(MOST_PENDING * PENDING_ROOM, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  playedBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  secondBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  if (guard == nullptr || names == nullptr || pending == nullptr || playedBuffer == nullptr || secondBuffer == nullptr) return;
#ifndef ODRIG_DRIVE_SD_SPI
  if (events == nullptr) return;
#endif
  state = LOOKING;
  setSummary();
  xTaskCreatePinnedToCore(driveEvents, "odrig-drive", DRIVE_STACK, nullptr, DRIVE_PRIORITY, nullptr, DRIVE_PROCESSOR);
}

void OdrigDrive::setWait(uint32_t ms) { waitMs = ms <= MOST_WAIT_MS ? ms : COMPUTER_WAIT_MS; }

uint32_t OdrigDrive::wait() { return waitMs; }

odrig_host OdrigDrive::withDrive(const odrig_host &given) {
  odrig_host made = given;
  if (state == NO_HOST) return made;
  files = given;
  made.open = openFile;
  made.read = readSome;
  made.close = closeFile;
  made.read_at = readPart;
  made.drive = driveNumber;
  made.drive_name = driveName;
  made.drive_space = driveSpace;
  made.drive_list = driveList;
  made.drive_bind = driveBind;
  made.drive_writable = driveWritable;
  if (given.write_open != nullptr) {
    made.write_open = beginFile;
    made.write = addBytes;
    made.write_close = endFile;
    made.rename = renameFile;
    made.remove = removeFile;
  }
  return made;
}

const char *OdrigDrive::summary() { return summaryText; }
