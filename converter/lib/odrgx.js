// ODRGX, the container of docs/format.md: a header of 20 bytes that names what the
// payload is, frames, a text or a widget, and the payload.
//
// The reasons come in the order in which the core meets them reading a file front to
// back: the header, the payload, and last the length the header gives the payload.

import {
  BAD_CONTAINER,
  BAD_MAGIC,
  CANVAS_MISMATCH,
  LOOP_MISMATCH,
  PAYLOAD_SIZE,
  Rejection,
  TRUNCATED,
  UNKNOWN_TYPE,
  UNKNOWN_TYPE_VERSION,
  ZERO_SIZE,
} from "./errors.js";
import * as odrg from "./odrg.js";

export const MAGIC = Uint8Array.of(0x4f, 0x44, 0x52, 0x58);
export const VERSION = 1;
export const HEADER_SIZE = 20;
export const ENDING = ".odrgx";

// The content types this library reads, by name and by number, and the version of each.
export const TYPES = {frames: 1};
export const TYPE_NAMES = {1: "frames"};
export const TYPE_VERSIONS = {1: 1};
// The most bytes a payload of each type may have; frames have no limit of their own.
export const LARGEST_PAYLOAD = {1: 0xffffffff};
export const LONGEST_LOOP = 0xffffffff;

function u16(bytes, at) {
  return bytes[at] | (bytes[at + 1] << 8);
}

function u32(bytes, at) {
  return u16(bytes, at) + 65536 * u16(bytes, at + 2);
}

function putU16(bytes, at, value) {
  bytes[at] = value & 0xff;
  bytes[at + 1] = (value >>> 8) & 0xff;
}

function putU32(bytes, at, value) {
  putU16(bytes, at, value & 0xffff);
  putU16(bytes, at + 2, Math.floor(value / 65536));
}

function hex2(value) {
  return value.toString(16).padStart(2, "0");
}

// Whether the bytes begin with the magic of a container. A reader goes by this, never by a
// file's name: a file that begins with `ODRG` is an ODRG file.
export function isContainer(data) {
  return data.length >= 4 && MAGIC.every((byte, at) => data[at] === byte);
}

// The header of a container given as bytes, checked:
// `{version, type, typeVersion, width, height, loopMs, payloadSize}`.
export function readHeader(data) {
  if (data.length < HEADER_SIZE) {
    throw new Rejection(TRUNCATED, `the file ends inside the ${HEADER_SIZE}-byte header`);
  }
  const header = {
    version: data[4],
    type: data[5],
    typeVersion: data[6],
    reserved: data[7],
    width: u16(data, 8),
    height: u16(data, 10),
    loopMs: u32(data, 12),
    payloadSize: u32(data, 16),
  };
  if (!isContainer(data)) {
    throw new Rejection(BAD_MAGIC, `the file starts with ${Array.from(data.subarray(0, 4), hex2).join(" ")}, not 4f 44 52 58`);
  }
  if (header.version !== VERSION || header.reserved !== 0) {
    throw new Rejection(BAD_CONTAINER, `the container's version is ${header.version} and its reserved byte ${header.reserved}, not ${VERSION} and 0`);
  }
  if (!(header.type in TYPE_NAMES)) {
    throw new Rejection(UNKNOWN_TYPE, `the content type is ${header.type}, not one of ${Object.keys(TYPE_NAMES).join(", ")}`);
  }
  if (header.typeVersion !== TYPE_VERSIONS[header.type]) {
    throw new Rejection(UNKNOWN_TYPE_VERSION, `the ${TYPE_NAMES[header.type]} version is ${header.typeVersion}, not ${TYPE_VERSIONS[header.type]}`);
  }
  if (header.width === 0 || header.height === 0) {
    throw new Rejection(ZERO_SIZE, `the canvas is ${header.width} x ${header.height}`);
  }
  if (header.payloadSize > LARGEST_PAYLOAD[header.type]) {
    throw new Rejection(PAYLOAD_SIZE, `a ${TYPE_NAMES[header.type]} payload of ${header.payloadSize} bytes is above ${LARGEST_PAYLOAD[header.type]}`);
  }
  delete header.reserved;
  return header;
}

// The payload of a container after its header, and the check that it is as long as the
// header says, made once the payload was read.
export function payloadOf(data) {
  return data.subarray(HEADER_SIZE);
}

export function checkPayloadSize(header, data) {
  const actual = data.length - HEADER_SIZE;
  if (actual !== header.payloadSize) {
    throw new Rejection(PAYLOAD_SIZE, `the header gives the payload ${header.payloadSize} bytes and it has ${actual}`);
  }
}

export function checkLoop(header, loopMs) {
  if (header.loopMs !== loopMs) {
    throw new Rejection(LOOP_MISMATCH, `the header gives a loop of ${header.loopMs} ms and the payload one of ${loopMs} ms`);
  }
}

// Reads a container of frames given as bytes: its header and the ODRG file of its payload,
// decoded as `odrg.decode` does. The canvas of the payload's header is compared before its
// frame records are read.
export function decodeFrames(data, header = readHeader(data)) {
  const payload = payloadOf(data);
  const inner = odrg.header(payload);
  if (inner.width !== header.width || inner.height !== header.height) {
    throw new Rejection(CANVAS_MISMATCH, `the container's canvas is ${header.width} x ${header.height} and its frames' ${inner.width} x ${inner.height}`);
  }
  const decoded = odrg.decode(payload);
  checkPayloadSize(header, data);
  checkLoop(header, decoded.records.reduce((sum, record) => sum + record.ms, 0));
  return {...decoded, header};
}

// A container of a type with this canvas, loop and payload.
export function wrap(type, width, height, loopMs, payload) {
  const made = new Uint8Array(HEADER_SIZE + payload.length);
  made.set(MAGIC, 0);
  made[4] = VERSION;
  made[5] = TYPES[type];
  made[6] = TYPE_VERSIONS[TYPES[type]];
  putU16(made, 8, width);
  putU16(made, 10, height);
  putU32(made, 12, loopMs);
  putU32(made, 16, payload.length);
  made.set(payload, HEADER_SIZE);
  return made;
}

// A container of frames for an animation of JSON frames, its payload the ODRG file
// `odrg.encode` writes. A loop longer than the header can hold is refused.
export function encodeFrames(animation, {compressed = true} = {}) {
  const payload = odrg.encode(animation, {compressed});
  const loopMs = animation.frames.reduce((sum, frame) => sum + frame.ms, 0);
  if (loopMs > LONGEST_LOOP) {
    throw new Rejection(LOOP_MISMATCH, `a loop of ${loopMs} ms is longer than ${LONGEST_LOOP} ms`);
  }
  return wrap("frames", animation.width, animation.height, loopMs, payload);
}
