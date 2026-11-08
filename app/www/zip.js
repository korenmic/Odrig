// A zip archive read in the page: its central directory, and each entry stored or deflated,
// the deflated ones through the converter's inflate. Nothing of it leaves the page.

import {inflate} from "./converter/index.js";
import {crc32} from "./crc32.js";

// The most entries read, and the most bytes they unpack to.
export const MOST_ENTRIES = 512;
export const MOST_BYTES = 64 * 1024 * 1024;
const END = 0x06054b50;
const END64 = 0x07064b50;
const CENTRAL = 0x02014b50;
const LOCAL = 0x04034b50;
const FULL = 0xffffffff;

const u16 = (bytes, at) => bytes[at] | (bytes[at + 1] << 8);
const u32 = (bytes, at) => (bytes[at] | (bytes[at + 1] << 8) | (bytes[at + 2] << 16) | (bytes[at + 3] << 24)) >>> 0;
const names = new TextDecoder("utf-8");

// Whether an extra field holds a zip64 record, header id 1.
function zip64Extra(bytes, from, length) {
  for (let at = from; at + 4 <= from + length;) {
    if (u16(bytes, at) === 1) return true;
    at += 4 + u16(bytes, at + 2);
  }
  return false;
}

// The entries of a zip: `{path, method, encrypted, crc, packed, size, offset, unreadable}`,
// folders left out, at most 512; `left`, the entries past those; and `tooLarge`, whether the
// entries unpack to more than 64 MB, the ones past that being unreadable. A file that is no
// zip throws its reason.
export function readZip(bytes) {
  let end = -1;
  for (let at = bytes.length - 22; at >= Math.max(0, bytes.length - 22 - 65535); at -= 1) {
    if (u32(bytes, at) === END) {
      end = at;
      break;
    }
  }
  if (end < 0) throw new Error("The file is not a zip archive.");
  const count = u16(bytes, end + 10);
  const size = u32(bytes, end + 12);
  const offset = u32(bytes, end + 16);
  if ((end >= 20 && u32(bytes, end - 20) === END64) || count === 0xffff || offset === FULL || size === FULL) {
    throw new Error("The archive is a zip64 archive, which the app does not read.");
  }
  if (offset + size > end) throw new Error("The archive's directory is damaged.");
  const entries = [];
  let left = 0;
  let unpacked = 0;
  let tooLarge = false;
  let at = offset;
  for (let number = 0; number < count; number += 1) {
    if (at + 46 > end || u32(bytes, at) !== CENTRAL) throw new Error("The archive's directory is damaged.");
    const flags = u16(bytes, at + 8);
    const method = u16(bytes, at + 10);
    const crc = u32(bytes, at + 16);
    const packed = u32(bytes, at + 20);
    const unpackedSize = u32(bytes, at + 24);
    const nameLength = u16(bytes, at + 28);
    const extraLength = u16(bytes, at + 30);
    const commentLength = u16(bytes, at + 32);
    const local = u32(bytes, at + 42);
    const path = names.decode(bytes.subarray(at + 46, at + 46 + nameLength));
    const zip64 = packed === FULL || unpackedSize === FULL || local === FULL || zip64Extra(bytes, at + 46 + nameLength, extraLength);
    at += 46 + nameLength + extraLength + commentLength;
    if (path.endsWith("/")) continue;
    if (entries.length === MOST_ENTRIES) {
      left += 1;
      continue;
    }
    let unreadable = null;
    if ((flags & 1) !== 0) unreadable = "The entry is encrypted.";
    else if (zip64) unreadable = "The entry is in zip64, which the app does not read.";
    else if (method !== 0 && method !== 8) unreadable = `The entry is packed in a way the app does not read (method ${method}).`;
    else if (unpacked + unpackedSize > MOST_BYTES) {
      unreadable = "The archive unpacks to more than 64 MB; the app does not read the entries past that.";
      tooLarge = true;
    } else unpacked += unpackedSize;
    entries.push({path, method, encrypted: (flags & 1) !== 0, crc, packed, size: unpackedSize, offset: local, unreadable});
  }
  return {entries, left, tooLarge};
}

// The bytes of an entry, checked against its size and its CRC-32; a damaged entry throws its
// reason.
export function extract(bytes, entry) {
  if (entry.unreadable !== null) throw new Error(entry.unreadable);
  const at = entry.offset;
  if (at + 30 > bytes.length || u32(bytes, at) !== LOCAL) throw new Error("The entry is damaged: its header is not where the directory says.");
  if (u32(bytes, at + 18) === FULL || u32(bytes, at + 22) === FULL) throw new Error("The entry is in zip64, which the app does not read.");
  const start = at + 30 + u16(bytes, at + 26) + u16(bytes, at + 28);
  if (start + entry.packed > bytes.length) throw new Error("The entry is damaged: the archive ends inside it.");
  const packed = bytes.subarray(start, start + entry.packed);
  let data;
  if (entry.method === 0) {
    data = packed;
  } else {
    try {
      data = inflate.inflateRaw(packed).data;
    } catch (error) {
      throw new Error(`The entry is damaged: ${error.message}.`);
    }
  }
  if (data.length !== entry.size) throw new Error("The entry is damaged: it unpacks to another size than the directory says.");
  if (parseInt(crc32(data), 16) !== entry.crc) throw new Error("The entry is damaged: its CRC-32 is not the one the directory says.");
  return data;
}
