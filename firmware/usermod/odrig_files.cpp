#include "odrig_files.h"

#include "odrig_platform.h"

namespace {

const char FOLDER[] = "/odrig/";
// The folder itself, as the file system names it. A storage that was formatted and never
// had a show has none, and the file system makes no folder for a file.
const char FOLDER_PATH[] = "/odrig";
const size_t LONGEST_NAME = 32;
// The longest name the core gives a file: a name in a numbered folder of the storage, after
// `255/`.
const size_t LONGEST_STORED = LONGEST_NAME + 4;
const size_t LOG_LENGTH = 96;
// The shortest time a command line waits after a storage call, in microseconds.
const int64_t SHORTEST_HOLD_US = 20000;

File openFile;
char lastLine[LOG_LENGTH] = "";

// The file being written, with its name and the bytes given to it so far.
File writtenFile;
char writtenName[LONGEST_STORED + 1] = "";
size_t writtenBytes = 0;

// The second file that is read, beside the open one, with its name and the place the
// next read begins at.
File secondFile;
char secondName[LONGEST_STORED + 1] = "";
uint32_t secondAt = 0;

// The space of storage. The file system walks its blocks to tell how many are in use,
// which takes a third of a second when storage is nearly full. So it is asked once, when
// the host functions are made, and the number is kept up from then on by what this file
// writes, renames and removes.
const size_t BLOCK_BYTES = 4096;
// The file system keeps a file of up to this many bytes beside its name, in no block.
const size_t INLINE_BYTES = 512;
bool spaceKnown = false;
uint32_t spaceTotal = 0, usedBlocks = 0;
uint32_t spaceAskedUs = 0;

// The times of the storage calls. They are set on the task that makes the call and read
// by whoever carries command lines, so they are kept under a guard of their own.
portMUX_TYPE paceGuard = portMUX_INITIALIZER_UNLOCKED;
int64_t lastCallEndUs = 0;
uint32_t busyUs = 0;
#ifdef ODRIG_PROBE
uint32_t timedCalls = 0, timedLongestUs = 0, timedTotalUs = 0;
volatile uint32_t readsOfTheSecondFile = 0;
#endif

// Times one storage call, from where it stands to the end of its block.
struct Timed {
  Timed() : startUs(esp_timer_get_time()) {}
  ~Timed() {
    const int64_t endUs = esp_timer_get_time();
    const uint32_t tookUs = (uint32_t)(endUs - startUs);
    portENTER_CRITICAL(&paceGuard);
    lastCallEndUs = endUs;
    busyUs += tookUs;
#ifdef ODRIG_PROBE
    timedCalls++;
    timedTotalUs += tookUs;
    if (tookUs > timedLongestUs) timedLongestUs = tookUs;
#endif
    portEXIT_CRITICAL(&paceGuard);
  }
  int64_t startUs;
};

// The blocks the file system needs for a file of some bytes. From its second block on, a
// block of a file begins with pointers to earlier blocks, one more for each time 2
// divides the block's number.
uint32_t blocksOf(size_t bytes) {
  if (bytes <= INLINE_BYTES) return 0;
  uint32_t blocks = 0;
  for (size_t held = 0; held < bytes; blocks++) {
    held += BLOCK_BYTES - (blocks == 0 ? 0 : 4 * (__builtin_ctz(blocks) + 1));
  }
  return blocks;
}

// A file of this size has come to storage, or has left it.
void blocksTaken(size_t bytes) { usedBlocks += blocksOf(bytes); }
void blocksFreed(size_t bytes) { usedBlocks -= std::min(usedBlocks, blocksOf(bytes)); }

// The size of the file at a path, or 0 when there is none.
size_t sizeAt(const char *path) {
  if (!ODRIG_FS.exists(path)) return 0;
  File file = ODRIG_FS.open(path, "r");
  if (!file) return 0;
  const size_t size = file.isDirectory() ? 0 : file.size();
  file.close();
  return size;
}

// Asks the file system for its size and for the blocks in use.
void askSpace() {
  const int64_t startUs = esp_timer_get_time();
  spaceTotal = (uint32_t)ODRIG_FS.totalBytes();
  usedBlocks = (uint32_t)(ODRIG_FS.usedBytes() / BLOCK_BYTES);
  spaceAskedUs = (uint32_t)(esp_timer_get_time() - startUs);
  spaceKnown = true;
}

#if ESP_IDF_VERSION_MAJOR >= 5
// The internal memory that stays for the LED outputs, the Wi-Fi and WLED's web server, which
// on ESP-IDF 5 take more of it: with less, WLED found its heap low and reset the network.
constexpr size_t INTERNAL_RESERVE = 192 * 1024;
#endif

// Memory from the chip's internal memory, and from the external memory when the internal
// memory has none, or on ESP-IDF 5 when the block would leave less than the reserve. It is
// never given back.
void *allocate(void *, size_t bytes) {
  void *block = nullptr;
#if ESP_IDF_VERSION_MAJOR >= 5
  if (heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT) >= bytes + INTERNAL_RESERVE)
#endif
  block = heap_caps_aligned_alloc(8, bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  if (block == nullptr) block = heap_caps_aligned_alloc(8, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return block;
}

// Whether a name is one a file of the folder can have: 1 to 32 characters of a-z, 0-9,
// '-', '_' and '.', and not made of dots alone.
bool isName(const char *name) {
  if (name == nullptr) return false;
  size_t length = 0;
  bool onlyDots = true;
  for (; name[length] != 0; length++) {
    const char c = name[length];
    if (length == LONGEST_NAME) return false;
    if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.')) return false;
    if (c != '.') onlyDots = false;
  }
  return length > 0 && !onlyDots;
}

// The length of the number of a numbered folder of the storage at the start of a text, 1 to
// 255 without a leading zero and followed by `after`, or 0 when it has none.
size_t numberLength(const char *name, char after) {
  if (name == nullptr) return 0;
  size_t length = 0;
  unsigned value = 0;
  for (; length < 3 && name[length] >= '0' && name[length] <= '9'; length++) value = value * 10 + (unsigned)(name[length] - '0');
  return length != 0 && name[0] != '0' && value <= 255 && name[length] == after ? length : 0;
}

// Whether a name is one the core gives a file: a name of the folder, alone or in one of its
// numbered folders, `<n>/<name>`.
bool isStored(const char *name) {
  const size_t number = numberLength(name, '/');
  return isName(number == 0 ? name : name + number + 1);
}

// The path of a file of the folder. `path` has room for the folder and the longest stored
// name.
bool pathOf(const char *name, char *path) {
  if (!isStored(name)) return false;
  strcpy(path, FOLDER);
  strcat(path, name);
  return true;
}

int openNamed(void *, const char *name) {
  char path[sizeof(FOLDER) + LONGEST_STORED];
  if (!pathOf(name, path)) return -1;
  if (openFile) openFile.close();
  openFile = ODRIG_FS.open(path, "r");
  if (openFile && !openFile.isDirectory()) return 1;
  if (openFile) openFile.close();
  return ODRIG_FS.exists(path) ? -1 : 0;
}

int32_t readSome(void *, uint8_t *buffer, size_t capacity) {
  if (!openFile) return -1;
  const int count = openFile.read(buffer, capacity);
  return count < 0 ? -1 : (int32_t)count;
}

void closeOpen(void *) {
  if (openFile) openFile.close();
}

void keepLine(void *, const char *text) {
  strncpy(lastLine, text, LOG_LENGTH - 1);
  lastLine[LOG_LENGTH - 1] = 0;
}

// Closes the second file when it has this name.
void dropSecond(const char *name) {
  if (strcmp(secondName, name) != 0) return;
  if (secondFile) secondFile.close();
  secondName[0] = 0;
}

// Gives up the file being written when it has this name: it is closed as far as it got.
void giveUpWritten(const char *name) {
  if (strcmp(writtenName, name) != 0) return;
  if (writtenFile) writtenFile.close();
  writtenName[0] = 0;
}

int beginFile(void *, const char *name) {
  Timed timed;
  char path[sizeof(FOLDER) + LONGEST_STORED];
  if (writtenName[0] != 0) {
    // A file that was being written is given up and removed.
    char given[sizeof(FOLDER) + LONGEST_STORED];
    strcpy(given, FOLDER);
    strcat(given, writtenName);
    if (writtenFile) writtenFile.close();
    writtenName[0] = 0;
    const size_t left = sizeAt(given);
    if (ODRIG_FS.remove(given)) blocksFreed(left);
  }
  if (!pathOf(name, path)) return -1;
  dropSecond(name);
  // A file that has the name is emptied. A storage without the folder gets it first.
  const size_t before = sizeAt(path);
  writtenFile = ODRIG_FS.open(path, "w");
  if (!writtenFile && ODRIG_FS.mkdir(FOLDER_PATH)) writtenFile = ODRIG_FS.open(path, "w");
  if (!writtenFile) return -1;
  blocksFreed(before);
  strcpy(writtenName, name);
  writtenBytes = 0;
  return 1;
}

int addBytes(void *, const uint8_t *bytes, size_t length) {
  Timed timed;
  if (!writtenFile) return -1;
  const size_t taken = writtenFile.write(bytes, length);
  blocksFreed(writtenBytes);
  writtenBytes += taken;
  blocksTaken(writtenBytes);
  return taken == length ? 1 : -1;
}

int endFile(void *) {
  Timed timed;
  char path[sizeof(FOLDER) + LONGEST_STORED];
  if (!writtenFile || !pathOf(writtenName, path)) return -1;
  writtenFile.close();
  writtenName[0] = 0;
  // The file is whole when storage holds as many bytes as were given.
  File whole = ODRIG_FS.open(path, "r");
  if (!whole) return -1;
  const size_t size = whole.size();
  whole.close();
  return size == writtenBytes ? 1 : -1;
}

int renameFile(void *, const char *from, const char *to) {
  Timed timed;
  char pathFrom[sizeof(FOLDER) + LONGEST_STORED], pathTo[sizeof(FOLDER) + LONGEST_STORED];
  if (!pathOf(from, pathFrom) || !pathOf(to, pathTo)) return -1;
  dropSecond(from);
  dropSecond(to);
  giveUpWritten(from);
  giveUpWritten(to);
  // The file that had the new name leaves storage.
  const size_t replaced = sizeAt(pathTo);
  if (!ODRIG_FS.rename(pathFrom, pathTo)) return -1;
  blocksFreed(replaced);
  return 1;
}

// The path of a numbered folder of the storage, `<n>`.
bool folderPathOf(const char *name, char *path) {
  if (numberLength(name, 0) == 0) return false;
  strcpy(path, FOLDER);
  strcat(path, name);
  return true;
}

// Whether a path is a folder of the file system.
bool isFolder(const char *path) {
  if (!ODRIG_FS.exists(path)) return false;
  File found = ODRIG_FS.open(path, "r");
  const bool folder = found && found.isDirectory();
  if (found) found.close();
  return folder;
}

// Makes the numbered folder of the storage `<n>`, which the file system gives two blocks: 1
// when it is there afterwards, made now or before, -1 when it could not be made. A storage
// without the folder of the show has none: the first write makes that folder.
int makeFolder(void *, const char *name) {
  Timed timed;
  char path[sizeof(FOLDER) + LONGEST_STORED];
  if (!folderPathOf(name, path)) return -1;
  if (isFolder(path)) return 1;
  if (!ODRIG_FS.mkdir(path)) return -1;
  usedBlocks += 2;
  return 1;
}

int removeFile(void *, const char *name) {
  Timed timed;
  char path[sizeof(FOLDER) + LONGEST_STORED];
  dropSecond(name);
  giveUpWritten(name);
  if (folderPathOf(name, path)) {
    // A numbered folder of the storage goes only while it is empty.
    if (!ODRIG_FS.exists(path)) return 0;
    if (!ODRIG_FS.rmdir(path)) return -1;
    usedBlocks -= std::min(usedBlocks, (uint32_t)2);
    return 1;
  }
  if (!pathOf(name, path)) return -1;
  if (!ODRIG_FS.exists(path)) return 0;
  const size_t removed = sizeAt(path);
  if (!ODRIG_FS.remove(path)) return -1;
  blocksFreed(removed);
  return 1;
}

// The space is told from the numbers kept, without a call to the file system.
int tellSpace(void *, uint32_t *free_bytes, uint32_t *total_bytes) {
  if (!spaceKnown || spaceTotal == 0) return -1;
  const uint64_t used = (uint64_t)usedBlocks * BLOCK_BYTES;
  *free_bytes = used < spaceTotal ? (uint32_t)(spaceTotal - used) : 0;
  *total_bytes = spaceTotal;
  return 1;
}

int32_t readAt(void *, const char *name, uint32_t offset, uint8_t *buffer, size_t capacity) {
  char path[sizeof(FOLDER) + LONGEST_STORED];
  if (!pathOf(name, path)) return -1;
#ifdef ODRIG_PROBE
  readsOfTheSecondFile++;
#endif
  if (!secondFile || strcmp(secondName, name) != 0) {
    if (secondFile) secondFile.close();
    secondName[0] = 0;
    secondFile = ODRIG_FS.open(path, "r");
    if (!secondFile || secondFile.isDirectory()) {
      if (secondFile) secondFile.close();
      return -1;
    }
    strcpy(secondName, name);
    secondAt = 0;
  }
  if (secondAt != offset) {
    if (!secondFile.seek(offset)) return -1;
    secondAt = offset;
  }
  const int count = secondFile.read(buffer, capacity);
  if (count < 0) return -1;
  secondAt += (uint32_t)count;
  return (int32_t)count;
}

}  // namespace

odrig_host OdrigFiles::host() {
  if (!spaceKnown) askSpace();
  odrig_host made;
  made.ctx = nullptr;
  made.alloc = allocate;
  made.open = openNamed;
  made.read = readSome;
  made.close = closeOpen;
  made.log = keepLine;
  made.write_open = beginFile;
  made.write = addBytes;
  made.write_close = endFile;
  made.rename = renameFile;
  made.remove = removeFile;
  made.space = tellSpace;
  made.read_at = readAt;
  made.drive = nullptr;
  made.drive_name = nullptr;
  made.drive_space = nullptr;
  made.about = nullptr;
  made.drive_list = nullptr;
  made.drive_bind = nullptr;
  made.drive_writable = nullptr;
  made.identity = nullptr;
  made.make_folder = makeFolder;
  return made;
}

uint64_t OdrigFiles::nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }

const char *OdrigFiles::lastLog() { return lastLine; }

bool OdrigFiles::holding() {
  const int64_t nowUs = esp_timer_get_time();
  bool held = false;
  portENTER_CRITICAL(&paceGuard);
  if (busyUs != 0) {
    const int64_t holdUs = std::max(SHORTEST_HOLD_US, 2 * (int64_t)busyUs);
    if (nowUs - lastCallEndUs < holdUs) {
      held = true;
    } else {
      busyUs = 0;
    }
  }
  portEXIT_CRITICAL(&paceGuard);
  return held;
}

OdrigFiles::StorageCall::StorageCall() : startUs(esp_timer_get_time()) {}

// Timed by a Timed that began when the call did.
OdrigFiles::StorageCall::~StorageCall() {
  Timed timed;
  timed.startUs = startUs;
}

#ifdef ODRIG_PROBE
OdrigFiles::StoreTimes OdrigFiles::takeStoreTimes() {
  portENTER_CRITICAL(&paceGuard);
  const StoreTimes taken = {timedCalls, timedLongestUs, timedTotalUs};
  timedCalls = timedLongestUs = timedTotalUs = 0;
  portEXIT_CRITICAL(&paceGuard);
  return taken;
}

uint32_t OdrigFiles::secondReads() { return readsOfTheSecondFile; }

uint32_t OdrigFiles::spaceAskedMicros() { return spaceAskedUs; }
#endif
