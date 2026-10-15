// The CRC-32 of zlib and PNG, which `upload end` names a file by.

const TABLE = new Uint32Array(256);
for (let value = 0; value < 256; value += 1) {
  let crc = value;
  for (let bit = 0; bit < 8; bit += 1) {
    crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  }
  TABLE[value] = crc >>> 0;
}

// The CRC-32 of some bytes, as eight hexadecimal digits.
export function crc32(bytes) {
  let crc = 0xffffffff;
  for (let at = 0; at < bytes.length; at += 1) {
    crc = TABLE[(crc ^ bytes[at]) & 0xff] ^ (crc >>> 8);
  }
  return ((crc ^ 0xffffffff) >>> 0).toString(16).padStart(8, "0");
}
