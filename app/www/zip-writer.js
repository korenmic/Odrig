// A zip archive written in the page, one entry after the other, to a sink that takes its
// bytes in their order. A file is a stored entry, its bytes as they are: its CRC-32 is
// counted while its pieces pass, and its CRC-32 and sizes follow them in a data descriptor,
// general-purpose bit 3. A folder is an entry of its own, a name that ends in `/`. The
// central directory and its end come last. No zip64: an archive of 65,535 entries or more,
// or of 4 GiB or more, is refused, since those values mean zip64 to a reader.

import {crc32More} from "./crc32.js";

// The most entries, and the most bytes of an archive and of each entry, that need no zip64.
export const MOST_ENTRIES = 0xfffe;
export const MOST_BYTES = 0xfffffffe;

const LOCAL = 0x04034b50;
const DESCRIPTOR = 0x08074b50;
const CENTRAL = 0x02014b50;
const END = 0x06054b50;
// Version 2.0: stored entries, folders and data descriptors.
const VERSION = 20;
const DESCRIBED = 0x0008;
const UTF8 = 0x0800;
const FOLDER_ATTRIBUTE = 0x10;
const names = new TextEncoder();

// The bytes an archive of these entries takes, `{name, size}` each, a folder's size null:
// a local header, the bytes and a descriptor for a file, a local header for a folder, a
// header of the central directory for each, and the end of the directory.
export function measure(entries) {
  let total = 22;
  for (const entry of entries) {
    const name = names.encode(entry.name).length;
    total += 30 + name + 46 + name + (entry.size === null ? 0 : entry.size + 16);
  }
  return total;
}

// Whether an archive of these entries needs no zip64.
export function fits(entries) {
  return entries.length <= MOST_ENTRIES && measure(entries) <= MOST_BYTES;
}

// The date and the time of MS-DOS, which a zip names its entries' times in, of a moment of
// local time; 1980-01-01 for a moment before it.
function dosTime(when) {
  if (when.getFullYear() < 1980) return {time: 0, date: 33};
  return {
    time: (when.getHours() << 11) | (when.getMinutes() << 5) | (when.getSeconds() >> 1),
    date: ((when.getFullYear() - 1980) << 9) | ((when.getMonth() + 1) << 5) | when.getDate(),
  };
}

class Bytes {
  constructor(size) {
    this.bytes = new Uint8Array(size);
    this.view = new DataView(this.bytes.buffer);
    this.at = 0;
  }

  u16(value) {
    this.view.setUint16(this.at, value, true);
    this.at += 2;
    return this;
  }

  u32(value) {
    this.view.setUint32(this.at, value >>> 0, true);
    this.at += 4;
    return this;
  }

  put(bytes) {
    this.bytes.set(bytes, this.at);
    this.at += bytes.length;
    return this;
  }
}

// Writes an archive to `sink`, an object whose `write(bytes)` takes the next bytes and may
// give a promise. Every entry has the time `when`.
export class ZipWriter {
  constructor(sink, when = new Date()) {
    this.sink = sink;
    this.stamp = dosTime(when);
    this.entries = [];
    this.taken = new Set();
    this.offset = 0;
    this.finished = false;
  }

  // The bytes written so far.
  get size() {
    return this.offset;
  }

  async write(bytes) {
    if (this.offset + bytes.length > MOST_BYTES) throw new RangeError("The archive would reach 4 GiB, which needs zip64.");
    await this.sink.write(bytes);
    this.offset += bytes.length;
  }

  // The name as an entry names it, and its flags: UTF-8 when it is not ASCII alone.
  entryName(name, folder) {
    if (typeof name !== "string" || name === "" || name.startsWith("/") || name.includes("\\") || name.includes("\0") ||
        name.split("/").some((part, at, parts) => (part === "" && !(folder && at === parts.length - 1)) || part === "." || part === "..")) {
      throw new RangeError(`"${name}" is not a name an entry may have.`);
    }
    if (this.finished) throw new Error("The archive is finished.");
    if (this.entries.length >= MOST_ENTRIES) throw new RangeError("The archive would have 65,535 entries, which needs zip64.");
    if (this.taken.has(name)) throw new RangeError(`The archive has an entry "${name}" already.`);
    const encoded = names.encode(name);
    return {encoded, flags: encoded.some((byte) => byte >= 0x80) ? UTF8 : 0};
  }

  header(encoded, flags) {
    return new Bytes(30 + encoded.length).u32(LOCAL).u16(VERSION).u16(flags).u16(0).u16(this.stamp.time).u16(this.stamp.date)
      .u32(0).u32(0).u32(0).u16(encoded.length).u16(0).put(encoded).bytes;
  }

  // Adds a folder, its name ending in `/`.
  async directory(name) {
    const folder = name.endsWith("/") ? name : `${name}/`;
    const {encoded, flags} = this.entryName(folder, true);
    const offset = this.offset;
    await this.write(this.header(encoded, flags));
    this.entries.push({name: folder, encoded, flags, crc: 0, size: 0, offset, attributes: FOLDER_ATTRIBUTE});
    this.taken.add(folder);
  }

  // Adds a file of these pieces, an iterable of byte arrays, in their order, and gives its
  // CRC-32 and its size.
  async file(name, pieces) {
    const {encoded, flags} = this.entryName(name, false);
    const offset = this.offset;
    await this.write(this.header(encoded, flags | DESCRIBED));
    let crc = 0;
    let size = 0;
    for await (const piece of pieces) {
      crc = crc32More(crc, piece);
      size += piece.length;
      await this.write(piece);
    }
    await this.write(new Bytes(16).u32(DESCRIPTOR).u32(crc).u32(size).u32(size).bytes);
    this.entries.push({name, encoded, flags: flags | DESCRIBED, crc, size, offset, attributes: 0});
    this.taken.add(name);
    return {crc, size};
  }

  // Writes the central directory and its end. Gives the size of the archive.
  async finish() {
    if (this.finished) throw new Error("The archive is finished.");
    const start = this.offset;
    for (const entry of this.entries) {
      await this.write(new Bytes(46 + entry.encoded.length).u32(CENTRAL).u16(VERSION).u16(VERSION).u16(entry.flags).u16(0)
        .u16(this.stamp.time).u16(this.stamp.date).u32(entry.crc).u32(entry.size).u32(entry.size).u16(entry.encoded.length)
        .u16(0).u16(0).u16(0).u16(0).u32(entry.attributes).u32(entry.offset).put(entry.encoded).bytes);
    }
    const count = this.entries.length;
    await this.write(new Bytes(22).u32(END).u16(0).u16(0).u16(count).u16(count).u32(this.offset - start).u32(start).u16(0).bytes);
    this.finished = true;
    return this.offset;
  }
}
