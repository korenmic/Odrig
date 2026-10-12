#include "odrig_http.h"

#include "odrig_platform.h"

#include "odrig_core.h"

namespace {

const char PATH[] = "/odrig";
const char FORM_FIELD[] = "body";
// Of a longer body the first bytes are passed on, which the player answers with
// `line-too-long`.
const size_t BODY_BYTES = 4096;

// What a request keeps until it is answered: the first bytes of its body and the reply.
// It is memory of the request, which frees it; neither stands on a stack.
struct Kept {
  uint16_t length;
  bool hasBody;
  char bytes[BODY_BYTES];
  char reply[ODRIG_REPLY_MAX + 1];
};

OdrigHttp::Command commandNow = nullptr;

Kept *keptOf(AsyncWebServerRequest *request) {
  if (request->_tempObject == nullptr) request->_tempObject = calloc(1, sizeof(Kept));
  return static_cast<Kept *>(request->_tempObject);
}

// Keeps the first bytes of a request body with the request.
void onBody(AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t) {
  Kept *kept = keptOf(request);
  if (kept == nullptr) return;
  kept->hasBody = true;
  for (size_t i = 0; i < len && index + i < BODY_BYTES; i++) {
    kept->bytes[index + i] = (char)data[i];
    kept->length = (uint16_t)(index + i + 1);
  }
}

void onRequest(AsyncWebServerRequest *request) {
  if (request->url() != PATH) {
    request->send(404);
    return;
  }
  if (request->method() != HTTP_POST) {
    AsyncWebServerResponse *response = request->beginResponse(405);
    response->addHeader(F("Allow"), F("POST"));
    request->send(response);
    return;
  }
  Kept *kept = keptOf(request);
  if (kept == nullptr) {
    request->send(503);
    return;
  }
  if (!kept->hasBody && request->hasParam(FORM_FIELD, true)) {
    // The server took the body apart as a form before any handler saw it.
    const String &value = request->getParam(FORM_FIELD, true)->value();
    kept->length = (uint16_t)std::min((size_t)value.length(), BODY_BYTES);
    memcpy(kept->bytes, value.c_str(), kept->length);
  }
  const size_t replied = commandNow != nullptr ? commandNow(kept->bytes, kept->length, kept->reply, ODRIG_REPLY_MAX) : 0;
  if (replied == 0) {
    request->send(503);
    return;
  }
  kept->reply[replied] = 0;
  request->send(200, F("application/json"), kept->reply);
}

}  // namespace

void OdrigHttp::begin(Command command) {
  commandNow = command;
  server.on(PATH, HTTP_ANY, onRequest, nullptr, onBody);
}
