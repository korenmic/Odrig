// The settings the standalone firmware takes from the board's storage: the name and the
// password of the network it hosts, its channel, and the limit on LED current. They are
// read from the two files WLED keeps its settings in, /cfg.json and /wsec.json, which the
// firmware tool writes. This code knows nothing of the chip, so that it is tested on a
// computer.
#pragma once

#include <stddef.h>
#include <stdint.h>

const size_t ODRIG_NAME_LONGEST = 32;
const size_t ODRIG_PASSWORD_SHORTEST = 8;
const size_t ODRIG_PASSWORD_LONGEST = 63;
// A file longer than this counts as absent.
const size_t ODRIG_SETTINGS_LONGEST = 16384;
// What WLED takes where its settings name no channel, and no limit.
const uint8_t ODRIG_CHANNEL_DEFAULT = 6;
const uint16_t ODRIG_LIMIT_DEFAULT_MA = 850;

struct OdrigSettings {
  // A name of 1 to 32 bytes and a password of 8 to 63 were found. Without both, no
  // network is hosted, and the name and the password are empty.
  bool network;
  char name[ODRIG_NAME_LONGEST + 1];
  char password[ODRIG_PASSWORD_LONGEST + 1];
  // 1 to 13.
  uint8_t channel;
  // The network does not announce its name.
  bool hidden;
  // The most current all LEDs together may be estimated to draw, in milliamps. 0 means
  // that there is no limit.
  uint16_t limit_ma;
};

// The settings in the bytes of the two files. A null pointer stands for a file that is
// absent. A file that is not one JSON object, or is longer than the longest allowed,
// counts as absent too. Of a member that is named twice the first counts.
//
// From /cfg.json: ap.ssid, the name; ap.chan, the channel, when it is a whole number
// from 1 to 13; ap.hide, hidden when it is a whole number above 0; hw.led.maxpwr, the
// limit, when it is a whole number from 0 to 65,535. From /wsec.json: ap.psk, the
// password. A text is taken with its bytes as they are; a mark, a backslash and a slash
// may be written with a backslash, and a text with any other escape is not taken.
OdrigSettings odrigSettings(const char *config, size_t configLength, const char *secrets, size_t secretsLength);
