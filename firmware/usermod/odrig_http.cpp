#include "odrig_http.h"

#include "wled.h"

#include "odrig_core.h"

namespace {

const char PATH[] = "/odrig";
const char FORM_FIELD[] = "body";
// Of a longer body the first bytes are passed on, which the player answers with
// `line-too-long`.
const size_t BODY_BYTES = 128;

struct Body {
  uint8_t length;
  char bytes[BODY_BYTES];
};

OdrigHttp::Command commandNow = nullptr;

// Keeps the first bytes of a request body with the request, which frees them.
void onBody(AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t) {
  if (request->_tempObject == nullptr) request->_tempObject = calloc(1, sizeof(Body));
  Body *body = static_cast<Body *>(request->_tempObject);
  if (body == nullptr) return;
  for (size_t i = 0; i < len && index + i < BODY_BYTES; i++) {
    body->bytes[index + i] = (char)data[i];
    body->length = (uint8_t)(index + i + 1);
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
  char line[BODY_BYTES];
  size_t length = 0;
  const Body *body = static_cast<const Body *>(request->_tempObject);
  if (body != nullptr) {
    length = body->length;
    memcpy(line, body->bytes, length);
  } else if (request->hasParam(FORM_FIELD, true)) {
    // The server took the body apart as a form before any handler saw it.
    const String &value = request->getParam(FORM_FIELD, true)->value();
    length = std::min((size_t)value.length(), BODY_BYTES);
    memcpy(line, value.c_str(), length);
  }
  char reply[ODRIG_REPLY_MAX + 1];
  const size_t replied = commandNow != nullptr ? commandNow(line, length, reply, ODRIG_REPLY_MAX) : 0;
  if (replied == 0) {
    request->send(503);
    return;
  }
  reply[replied] = 0;
  request->send(200, F("application/json"), reply);
}

}  // namespace

void OdrigHttp::begin(Command command) {
  commandNow = command;
  server.on(PATH, HTTP_ANY, onRequest, nullptr, onBody);
}
