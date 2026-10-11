/* The board: the labels of its two rows of pins, from the antenna end to the USB end,
   as in the drawing of docs/mapping.md. A label made of digits is the GPIO of that
   number. The order of the pins is a fact of the hardware; it is not in mapping.json. */

var OdrigBoard = {
  name: "ESP32-S3 N16R8",
  left: ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18", "8", "3", "46", "9", "10",
         "11", "12", "13", "14", "5Vin", "GND"],
  right: ["GND", "TX", "RX", "1", "2", "42", "41", "40", "39", "38", "37", "36", "35", "0", "45", "48",
          "47", "21", "20", "19", "GND", "GND"]
};
