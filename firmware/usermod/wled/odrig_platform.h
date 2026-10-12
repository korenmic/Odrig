// What the sources that both firmwares compile take from their platform: the Arduino
// core, the file system of the board's storage as ODRIG_FS, and the web server as
// `server`. Here the platform is WLED, which has all three.
#pragma once

#include "wled.h"

#define ODRIG_FS WLED_FS
