#include "odrig_files.h"

#include "wled.h"

namespace {

const char FOLDER[] = "/odrig/";
const size_t LONGEST_NAME = 32;
const size_t LOG_LENGTH = 96;

File openFile;
char lastLine[LOG_LENGTH] = "";

// Memory from the chip's internal memory, and from the external memory only when the
// internal memory has none. It is never given back.
void *allocate(void *, size_t bytes) {
  void *block = heap_caps_aligned_alloc(8, bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  if (block == nullptr) block = heap_caps_aligned_alloc(8, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return block;
}

int openNamed(void *, const char *name) {
  char path[sizeof(FOLDER) + LONGEST_NAME];
  if (name == nullptr || strlen(name) > LONGEST_NAME) return -1;
  strcpy(path, FOLDER);
  strcat(path, name);
  if (openFile) openFile.close();
  openFile = WLED_FS.open(path, "r");
  if (openFile && !openFile.isDirectory()) return 1;
  if (openFile) openFile.close();
  return WLED_FS.exists(path) ? -1 : 0;
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

}  // namespace

odrig_host OdrigFiles::host() {
  odrig_host made;
  made.ctx = nullptr;
  made.alloc = allocate;
  made.open = openNamed;
  made.read = readSome;
  made.close = closeOpen;
  made.log = keepLine;
  return made;
}

uint64_t OdrigFiles::nowMs() { return (uint64_t)esp_timer_get_time() / 1000; }

const char *OdrigFiles::lastLog() { return lastLine; }
