#include "odrig_update.h"

#include "esp_ota_ops.h"
#include "wled.h"

namespace {

// WLED's page for an update, the answer to one, and the reason. The message names the way
// that works: the USB cable and the firmware tool.
const char PATH[] = "/update";
const uint16_t STATUS = 501;
const char HEADLINE[] = "Update refused";
const char REASON[] = "This board has no second firmware slot: that room holds animations. Its firmware is updated over the USB cable with python3 firmware/fw.py flash.";
// WLED's message page: no button back to the main page.
const byte NO_BUTTON = 254;

bool refused = false;

// Whether an update could write a slot: there is one, and it is not the slot that runs.
bool secondSlot() {
  const esp_partition_t *next = esp_ota_get_next_update_partition(nullptr);
  return next != nullptr && next != esp_ota_get_running_partition();
}

// The answer, once the upload has arrived, which is thrown away piece by piece.
void refuse(AsyncWebServerRequest *request) { serveMessage(request, STATUS, HEADLINE, REASON, NO_BUTTON); }

void dropPiece(AsyncWebServerRequest *, String, size_t, uint8_t *, size_t, bool) {}

}  // namespace

void OdrigUpdate::begin() {
  if (secondSlot()) return;
  refused = true;
  server.on(PATH, HTTP_POST, refuse, dropPiece);
}

bool OdrigUpdate::refusing() { return refused; }
