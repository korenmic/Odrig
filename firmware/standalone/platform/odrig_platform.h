// What the sources that both firmwares compile take from their platform: the Arduino
// core, the file system of the board's storage as ODRIG_FS, and the web server as
// `server`. Here the platform is the Arduino core with its own file system library and
// the web server library; the program defines the server.
#pragma once

#include <Arduino.h>
#include <LittleFS.h>
#include <ESPAsyncWebServer.h>

#define ODRIG_FS LittleFS

extern AsyncWebServer server;
