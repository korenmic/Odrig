#include "odrig_drive.h"

#include <dirent.h>

#include "usb/msc_host.h"
#include "usb/msc_host_vfs.h"
#include "usb/usb_host.h"
#include "wled.h"

namespace {

// Where the drive is mounted, the folder of its animations, and the beginning of the name
// the core gives a file of the drive.
const char MOUNT[] = "/usb";
const char FOLDER[] = "/usb/odrig";
const char PREFIX[] = "drive/";
const size_t PREFIX_LENGTH = sizeof(PREFIX) - 1;
// The most files of the list, and the room for a name with its 0: a file with a longer
// name is passed over.
const uint32_t MOST_FILES = 256;
const size_t NAME_ROOM = 256;
const size_t PATH_ROOM = sizeof(FOLDER) + 1 + NAME_ROOM;
// The buffer of each file that is read, in memory the USB unit reaches: one request to
// the drive brings this many bytes.
const size_t READ_BUFFER = 4096;
// The room for a name `drive/<place>`.
const size_t SHORT_NAME = 16;

// The tasks: the events of the USB host library, those of the driver, and the one that
// mounts a drive, lists it and drops it. They run on the processor of WLED's loop.
const uint32_t HOST_STACK = 4096;
const UBaseType_t HOST_PRIORITY = 2;
const uint32_t DRIVER_STACK = 4096;
const UBaseType_t DRIVER_PRIORITY = 2;
const uint32_t DRIVE_STACK = 6144;
const UBaseType_t DRIVE_PRIORITY = 1;
const BaseType_t DRIVE_PROCESSOR = 1;
const UBaseType_t EVENTS = 4;

enum State : uint8_t { NO_HOST, NO_DRIVE, NOT_READ, MOUNTED };
volatile State state = NO_HOST;
char summaryText[24] = "no USB host";

// Held for the number, the list and every file of the drive: by the core's calls, and by
// the task while it publishes a list or drops a drive. A list is made while the number is
// 0, when the core reads none of it.
SemaphoreHandle_t guard = nullptr;

struct Guarded {
  Guarded() { xSemaphoreTake(guard, portMAX_DELAY); }
  ~Guarded() { xSemaphoreGive(guard); }
};

uint32_t number = 0;
uint32_t plugged = 0;
uint32_t listed = 0;
char (*names)[NAME_ROOM] = nullptr;

// The file `open` holds and the one `read_at` holds, with the name the core gave the
// second and the place its next read begins at.
FILE *played = nullptr;
FILE *second = nullptr;
char secondName[SHORT_NAME] = "";
uint32_t secondAt = 0;
char *playedBuffer = nullptr;
char *secondBuffer = nullptr;

QueueHandle_t events = nullptr;
msc_host_device_handle_t device = nullptr;
msc_host_vfs_handle_t mounted = nullptr;

// The host functions for every name that is not the drive's.
odrig_host files;

// The place a name `drive/<place>` stands for, MOST_FILES for a place beyond the list's
// room, or -1 for a name that is not the drive's.
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

// The path of the file at a place of the list of the drive that is plugged in. With the
// guard held.
bool pathAt(long place, char *path) {
  if (number == 0 || place < 0 || (uint32_t)place >= listed) return false;
  snprintf(path, PATH_ROOM, "%s/%s", FOLDER, names[place]);
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

int driveName(void *, uint32_t drive, uint32_t place, char *buffer, size_t capacity) {
  Guarded held;
  if (drive == 0 || drive != number || place >= listed || capacity == 0) return 0;
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
      if (!pathAt(place, path)) return 0;
      played = opened(path, playedBuffer);
      if (played != nullptr) return 1;
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
      return count == 0 && ferror(played) ? -1 : (int32_t)count;
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
    if (strlen(name) >= SHORT_NAME || !pathAt(place, path)) return -1;
    second = opened(path, secondBuffer);
    if (second == nullptr) return -1;
    strcpy(secondName, name);
    secondAt = 0;
  }
  if (secondAt != offset) {
    if (fseek(second, (long)offset, SEEK_SET) != 0) return -1;
    secondAt = offset;
  }
  const size_t count = fread(buffer, 1, capacity, second);
  if (count == 0 && ferror(second)) return -1;
  secondAt += (uint32_t)count;
  return (int32_t)count;
}

// Whether a name is one of an animation file: it ends in .odrg, in any case, and does not
// begin with a dot.
bool isAnimation(const char *name) {
  const size_t length = strlen(name);
  return length >= 5 && length < NAME_ROOM && name[0] != '.' && strcasecmp(name + length - 5, ".odrg") == 0;
}

// Puts a name into the list, which holds the first MOST_FILES names in the order of their
// bytes.
void keepName(const char *name, uint32_t *kept) {
  uint32_t at = *kept;
  while (at > 0 && strcmp(names[at - 1], name) > 0) at--;
  if (at >= MOST_FILES) return;
  const uint32_t moved = (*kept < MOST_FILES ? *kept : MOST_FILES - 1) - at;
  memmove(names[at + 1], names[at], moved * NAME_ROOM);
  strcpy(names[at], name);
  if (*kept < MOST_FILES) (*kept)++;
}

// The list of the drive's folder odrig, made while the number is 0. Its length.
uint32_t listFolder() {
  uint32_t kept = 0;
  DIR *folder = opendir(FOLDER);
  if (folder == nullptr) return 0;
  while (const dirent *entry = readdir(folder)) {
    if (entry->d_type == DT_REG && isAnimation(entry->d_name)) keepName(entry->d_name, &kept);
  }
  closedir(folder);
  return kept;
}

void setSummary() {
  if (state == NO_HOST) {
    strcpy(summaryText, "no USB host");
  } else if (state == NO_DRIVE) {
    strcpy(summaryText, "none");
  } else if (state == NOT_READ) {
    strcpy(summaryText, "not readable");
  } else {
    snprintf(summaryText, sizeof summaryText, "%u files", (unsigned)listed);
  }
}

// A drive came: it is mounted read as it is, never formatted, and its list is published
// with a new number.
void plugIn(uint8_t address) {
  if (device != nullptr) return;
  if (msc_host_install_device(address, &device) != ESP_OK) {
    device = nullptr;
    state = NOT_READ;
    setSummary();
    return;
  }
  esp_vfs_fat_mount_config_t mount = {};
  mount.format_if_mount_failed = false;
  mount.max_files = 3;
  mount.allocation_unit_size = 0;
  if (msc_host_vfs_register(device, MOUNT, &mount, &mounted) != ESP_OK) {
    mounted = nullptr;
    state = NOT_READ;
    setSummary();
    return;
  }
  const uint32_t found = listFolder();
  Guarded held;
  listed = found;
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

void hostEvents(void *) {
  for (;;) {
    uint32_t flags = 0;
    usb_host_lib_handle_events(portMAX_DELAY, &flags);
    if (flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) usb_host_device_free_all();
  }
}

void driveEvents(void *) {
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

}  // namespace

void OdrigDrive::begin() {
  guard = xSemaphoreCreateMutex();
  events = xQueueCreate(EVENTS, sizeof(msc_host_event_t));
  names = static_cast<char (*)[NAME_ROOM]>(heap_caps_malloc(MOST_FILES * NAME_ROOM, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  playedBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  secondBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  if (guard == nullptr || events == nullptr || names == nullptr || playedBuffer == nullptr || secondBuffer == nullptr) return;
  usb_host_config_t host = {};
  host.skip_phy_setup = false;
  host.intr_flags = ESP_INTR_FLAG_LEVEL1;
  if (usb_host_install(&host) != ESP_OK) return;
  xTaskCreatePinnedToCore(hostEvents, "odrig-usb", HOST_STACK, nullptr, HOST_PRIORITY, nullptr, DRIVE_PROCESSOR);
  msc_host_driver_config_t driver = {};
  driver.create_backround_task = true;
  driver.task_priority = DRIVER_PRIORITY;
  driver.stack_size = DRIVER_STACK;
  driver.core_id = DRIVE_PROCESSOR;
  driver.callback = driverEvent;
  driver.callback_arg = nullptr;
  if (msc_host_install(&driver) != ESP_OK) return;
  xTaskCreatePinnedToCore(driveEvents, "odrig-drive", DRIVE_STACK, nullptr, DRIVE_PRIORITY, nullptr, DRIVE_PROCESSOR);
  state = NO_DRIVE;
  setSummary();
}

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
  return made;
}

const char *OdrigDrive::summary() { return summaryText; }
