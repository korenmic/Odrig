#include "odrig_drive.h"

#include <dirent.h>

#include "soc/usb_serial_jtag_struct.h"
#include "usb/msc_host.h"
#include "usb/msc_host_vfs.h"
#include "usb/usb_host.h"
#include "wled.h"

#include "odrig_log.h"

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
// The events the watcher of devices keeps, and how often the host's task serves it.
const int WATCHER_EVENTS = 4;
const uint32_t SERVE_EVERY_MS = 20;
// What the list of a drive is when its folder odrig could not be opened.
const int32_t NO_FOLDER = -1;
const int32_t NOT_LISTED = -2;

// How long the drive's task looks for a computer on the port before it takes the port
// for a stick, unless the settings say otherwise, the most the settings may say, and how
// often it looks.
const uint32_t COMPUTER_WAIT_MS = 5000;
const uint32_t MOST_WAIT_MS = 60000;
const uint32_t LOOK_EVERY_MS = 10;
uint32_t waitMs = COMPUTER_WAIT_MS;

enum State : uint8_t { NO_HOST, LOOKING, COMPUTER, NO_DRIVE, NOT_READ, MOUNTED };
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

// The host's second client, which only says what comes and goes: it opens each device
// that comes and keeps it open, since the library tells only the clients that opened a
// device that it went.
usb_host_client_handle_t watcher = nullptr;
usb_device_handle_t watched = nullptr;

// The host functions for every name that is not the drive's.
odrig_host files;

// A line of the log of the kind `usb`.
void say(const char *format, ...) {
  char text[OdrigLog::LINE_ROOM];
  va_list values;
  va_start(values, format);
  vsnprintf(text, sizeof(text), format, values);
  va_end(values);
  OdrigLog::add("usb", text);
}

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

int driveSpace(void *, uint32_t drive, uint64_t *freeBytes, uint64_t *totalBytes) {
  Guarded held;
  if (drive == 0 || drive != number || mounted == nullptr) return -1;
  return msc_host_vfs_space(mounted, freeBytes, totalBytes) == ESP_OK ? 1 : -1;
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

// The list of the drive's folder odrig, made while the number is 0. Its length, NO_FOLDER
// when the drive has no folder odrig, or NOT_LISTED when the folder could not be read.
int32_t listFolder() {
  uint32_t kept = 0;
  DIR *folder = opendir(FOLDER);
  if (folder == nullptr) return errno == ENOENT ? NO_FOLDER : NOT_LISTED;
  while (const dirent *entry = readdir(folder)) {
    if (entry->d_type == DT_REG && isAnimation(entry->d_name)) keepName(entry->d_name, &kept);
  }
  closedir(folder);
  return (int32_t)kept;
}

void setSummary() {
  if (state == NO_HOST) {
    strcpy(summaryText, "no USB host");
  } else if (state == LOOKING) {
    strcpy(summaryText, "looking for a computer");
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

// A drive came: it is mounted read as it is, never formatted, and its list is published
// with a new number.
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
  const int32_t found = listFolder();
  if (found == NO_FOLDER) {
    say("the stick has no folder odrig");
  } else if (found == NOT_LISTED) {
    say("stick not opened: a fault in reading the folder odrig");
  } else {
    say("stick opened: %u animation files in odrig", (unsigned)found);
  }
  Guarded held;
  listed = found < 0 ? 0 : (uint32_t)found;
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
// interface. The first device is kept open until it goes.
void describe(uint8_t address) {
  usb_device_handle_t opened = nullptr;
  const esp_err_t result = usb_host_device_open(watcher, address, &opened);
  if (result != ESP_OK) {
    say("a device came that could not be opened (%s)", esp_err_to_name(result));
    return;
  }
  const usb_device_desc_t *about = nullptr;
  if (usb_host_get_device_descriptor(opened, &about) != ESP_OK) about = nullptr;
  unsigned kind = about != nullptr ? about->bDeviceClass : 0;
  const usb_config_desc_t *config = nullptr;
  if (usb_host_get_active_config_descriptor(opened, &config) == ESP_OK && config != nullptr) {
    const usb_intf_desc_t *first = usb_parse_interface_descriptor(config, 0, 0, nullptr);
    if (first != nullptr) kind = first->bInterfaceClass;
  }
  char other[32];
  snprintf(other, sizeof(other), "another device (class %u)", kind);
  const char *named = kind == USB_CLASS_HUB ? "a hub" : kind == USB_CLASS_MASS_STORAGE ? "a stick" : other;
  say("a device came: maker %04x, product %04x, %s", about != nullptr ? about->idVendor : 0u, about != nullptr ? about->idProduct : 0u, named);
  if (watched == nullptr) {
    watched = opened;
  } else {
    usb_host_device_close(watcher, opened);
  }
}

void watcherEvent(const usb_host_client_event_msg_t *event, void *) {
  if (event->event == USB_HOST_CLIENT_EVENT_NEW_DEV) {
    describe(event->new_dev.address);
  } else if (event->event == USB_HOST_CLIENT_EVENT_DEV_GONE) {
    say("a device went");
    usb_host_device_close(watcher, event->dev_gone.dev_hdl);
    if (event->dev_gone.dev_hdl == watched) watched = nullptr;
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

}  // namespace

void OdrigDrive::begin() {
  guard = xSemaphoreCreateMutex();
  events = xQueueCreate(EVENTS, sizeof(msc_host_event_t));
  names = static_cast<char (*)[NAME_ROOM]>(heap_caps_malloc(MOST_FILES * NAME_ROOM, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  playedBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  secondBuffer = static_cast<char *>(heap_caps_malloc(READ_BUFFER, MALLOC_CAP_DMA | MALLOC_CAP_8BIT));
  if (guard == nullptr || events == nullptr || names == nullptr || playedBuffer == nullptr || secondBuffer == nullptr) return;
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
  return made;
}

const char *OdrigDrive::summary() { return summaryText; }
