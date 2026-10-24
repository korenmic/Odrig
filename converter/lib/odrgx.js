// ODRGX, the container of docs/format.md: a header of 20 bytes that names what the
// payload is, frames, a text or a widget, and the payload.
//
// The reasons come in the order in which the core meets them reading a file front to
// back: the header, the payload, and last the length the header gives the payload.

import * as draw from "./draw.js";
import {
  BAD_CONTAINER,
  BAD_GLYPH,
  BAD_JSON,
  BAD_MAGIC,
  BAD_SETTINGS,
  BAD_TEXT,
  BAD_TYPE,
  BAD_VERSION,
  CANVAS_MISMATCH,
  CANVAS_TOO_LARGE,
  DOES_NOT_FIT,
  LOOP_MISMATCH,
  MISSING_MEMBER,
  OUT_OF_RANGE,
  PAYLOAD_SIZE,
  Rejection,
  TRAILING_BYTES,
  TRUNCATED,
  UNKNOWN_FONT,
  UNKNOWN_TYPE,
  UNKNOWN_TYPE_VERSION,
  ZERO_SIZE,
} from "./errors.js";
import * as jsonframes from "./jsonframes.js";
import * as odrg from "./odrg.js";
import * as strictjson from "./strictjson.js";
import * as textlayout from "./textlayout.js";

export const MAGIC = Uint8Array.of(0x4f, 0x44, 0x52, 0x58);
export const VERSION = 1;
export const HEADER_SIZE = 20;
export const ENDING = ".odrgx";

// The content types this library reads, by name and by number, and the version of each.
export const TYPES = {frames: 1, text: 2};
export const TYPE_NAMES = {1: "frames", 2: "text"};
export const TYPE_VERSIONS = {1: 1, 2: 1};
// The most bytes a payload of each type may have; frames have no limit of their own.
export const LARGEST_PAYLOAD = {1: 0xffffffff, 2: 3612};
// The version of the JSON sources of a text and of a widget.
export const SOURCE_VERSION = 1;
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

// What a container holds, read by its type: for frames as `decodeFrames` gives it, for a
// text as `decodeText` does, each with `type`, the type's name.
export function decode(data) {
  const header = readHeader(data);
  const name = TYPE_NAMES[header.type];
  const decoded = name === "frames" ? decodeFrames(data, header) : decodeText(data, header);
  return {type: name, ...decoded};
}

// A JSON source, read by its member `type`: `{type: "frames", animation}` for JSON frames,
// which have no `type`, and `{type: "text", text}` for a text.
export function loadsSource(bytes) {
  const top = strictjson.loads(bytes);
  if (!(top instanceof Map)) {
    throw new Rejection(BAD_JSON, "the top level is not an object");
  }
  if (!top.has("type")) {
    return {type: "frames", animation: jsonframes.loads(bytes)};
  }
  if (!top.has("version")) {
    throw new Rejection(MISSING_MEMBER, 'the file has no member "version"');
  }
  const version = strictjson.integer(top.get("version"), null, null, "version");
  if (version !== SOURCE_VERSION) {
    throw new Rejection(BAD_VERSION, `version is ${version}, not ${SOURCE_VERSION}`);
  }
  const type = top.get("type");
  if (typeof type !== "string") {
    throw new Rejection(BAD_TYPE, "type is not a string");
  }
  if (type === "text") {
    return {type, text: loadsText(top)};
  }
  throw new Rejection(UNKNOWN_TYPE, `type is ${JSON.stringify(type)}, not "text"`);
}

// The container of a JSON source as `loadsSource` reads it.
export function encodeSource(source, {compressed = true} = {}) {
  if (source.type === "text") {
    return encodeText(source.text);
  }
  return encodeFrames(source.animation, {compressed});
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

// The text payload, version 1: 28 bytes of settings, the text and its glyphs.
export const TEXT_SETTINGS_SIZE = 28;
export const GLYPH_SIZE = 6;
// The largest picture the player can draw, in bytes: three for each pixel.
export const LARGEST_PICTURE = 65534;

// The members of the JSON source of a text, in the order in which it is written.
export const TEXT_MEMBERS = ["version", "type", "width", "height", "text", "font", "color", "background", "align", "valign", "direction", "wrap", "effect", "motion", "speed", "pause_ms"];

// The reader of a payload, front to back: `take` gives the next bytes or refuses a payload
// that ends first, as the core meets its end.
function cursor(bytes) {
  let at = 0;
  return {
    take(count, what) {
      if (at + count > bytes.length) {
        throw new Rejection(TRUNCATED, `the file ends inside ${what}`);
      }
      const taken = bytes.subarray(at, at + count);
      at += count;
      return taken;
    },
    left() {
      return bytes.length - at;
    },
  };
}

// Whether bytes are UTF-8 as the standard has it: no overlong form, no surrogate, nothing
// above U+10FFFF, and no character cut off at the end.
export function isUtf8(bytes) {
  let at = 0;
  while (at < bytes.length) {
    const first = bytes[at];
    let more;
    let low = 0x80;
    let high = 0xbf;
    if (first <= 0x7f) more = 0;
    else if (first >= 0xc2 && first <= 0xdf) more = 1;
    else if (first === 0xe0) [more, low] = [2, 0xa0];
    else if ((first >= 0xe1 && first <= 0xec) || first === 0xee || first === 0xef) more = 2;
    else if (first === 0xed) [more, high] = [2, 0x9f];
    else if (first === 0xf0) [more, low] = [3, 0x90];
    else if (first >= 0xf1 && first <= 0xf3) more = 3;
    else if (first === 0xf4) [more, high] = [3, 0x8f];
    else return false;
    for (let one = 1; one <= more; one += 1) {
      const next = bytes[at + one];
      if (next === undefined) return false;
      const [from, to] = one === 1 ? [low, high] : [0x80, 0xbf];
      if (next < from || next > to) return false;
    }
    at += 1 + more;
  }
  return true;
}

function colour(bytes, at) {
  return bytes[at] * 65536 + bytes[at + 1] * 256 + bytes[at + 2];
}

function putColour(bytes, at, value) {
  bytes[at] = (value >>> 16) & 0xff;
  bytes[at + 1] = (value >>> 8) & 0xff;
  bytes[at + 2] = value & 0xff;
}

function refuseLargeCanvas(width, height) {
  if (3 * width * height > LARGEST_PICTURE) {
    throw new Rejection(CANVAS_TOO_LARGE, `a picture of ${width} x ${height} is ${3 * width * height} bytes, above ${LARGEST_PICTURE}`);
  }
}

function badSettings(detail) {
  return new Rejection(BAD_SETTINGS, detail);
}

// The settings of a text payload's first 28 bytes, checked in the order of their offsets.
function readTextSettings(fixed) {
  const font = textlayout.fontOf(fixed[0]);
  if (font === null || font.version !== fixed[1]) {
    throw new Rejection(UNKNOWN_FONT, `font ${fixed[0]} of version ${fixed[1]} is none this player has`);
  }
  const names = [[2, draw.EFFECTS, "effect"], [3, draw.MOTIONS, "motion"], [4, draw.ALIGNS, "align"], [5, draw.VALIGNS, "valign"], [6, draw.DIRECTIONS, "direction"]];
  const settings = {font: font.name};
  for (const [at, list, name] of names) {
    if (fixed[at] >= list.length) throw badSettings(`${name} is ${fixed[at]}, not below ${list.length}`);
    settings[name] = list[fixed[at]];
  }
  if (fixed[7] > 1) throw badSettings(`wrap is ${fixed[7]}, not 0 or 1`);
  settings.wrap = fixed[7] === 1;
  settings.color = colour(fixed, 8);
  settings.background = colour(fixed, 11);
  settings.speed = u16(fixed, 14);
  if (settings.speed < 1 || settings.speed > draw.FASTEST) throw badSettings(`speed is ${settings.speed}, not 1 to ${draw.FASTEST}`);
  settings.pause = u16(fixed, 16);
  if (settings.effect === "static" && settings.pause < draw.SHORTEST_STATIC) throw badSettings(`a static text shows for ${settings.pause} ms, below ${draw.SHORTEST_STATIC}`);
  const textBytes = u16(fixed, 18);
  if (textBytes < 1 || textBytes > textlayout.LONGEST_TEXT) throw new Rejection(BAD_TEXT, `the text has ${textBytes} bytes, not 1 to ${textlayout.LONGEST_TEXT}`);
  const glyphs = u16(fixed, 20);
  if (glyphs > textlayout.MOST_GLYPHS) throw badSettings(`${glyphs} glyphs are more than ${textlayout.MOST_GLYPHS}`);
  const block = {width: u16(fixed, 22), height: u16(fixed, 24)};
  if (block.width === 0 || block.height === 0) throw badSettings(`the block is ${block.width} x ${block.height}`);
  if (u16(fixed, 26) !== 0) throw badSettings("the reserved bytes are not 0");
  return {settings, textBytes, glyphs, block};
}

// Reads a container of a text given as bytes: `{header, settings, text, glyphs, block}`,
// in the order in which the core checks it.
export function decodeText(data, header = readHeader(data)) {
  refuseLargeCanvas(header.width, header.height);
  const read = cursor(payloadOf(data));
  const fixed = read.take(TEXT_SETTINGS_SIZE, "the settings of the text");
  const {settings, textBytes, glyphs: count, block} = readTextSettings(fixed);
  const size = TEXT_SETTINGS_SIZE + textBytes + GLYPH_SIZE * count;
  if (header.payloadSize !== size) {
    throw new Rejection(PAYLOAD_SIZE, `the header gives the payload ${header.payloadSize} bytes and its settings ${size}`);
  }
  const canvas = {width: header.width, height: header.height};
  if (!draw.fits(settings, block, canvas)) {
    throw new Rejection(DOES_NOT_FIT, `a block of ${block.width} x ${block.height} cannot be seen whole on ${canvas.width} x ${canvas.height} with ${settings.effect} ${settings.motion}`);
  }
  const textData = read.take(textBytes, "the text");
  if (!isUtf8(textData)) throw new Rejection(BAD_TEXT, "the text is not UTF-8");
  const font = textlayout.fontOf(textlayout.FONTS[settings.font].id);
  const glyphs = [];
  for (let one = 0; one < count; one += 1) {
    const bytes = read.take(GLYPH_SIZE, `glyph ${one + 1}`);
    const glyph = {glyph: u16(bytes, 0), x: u16(bytes, 2), y: u16(bytes, 4)};
    const width = glyph.glyph < font.table.widths.length ? font.table.widths[glyph.glyph] : 0;
    if (width === 0 || glyph.x + width * font.scale > block.width || glyph.y + font.rows * font.scale > block.height) {
      throw new Rejection(BAD_GLYPH, `glyph ${one + 1}, ${glyph.glyph} at ${glyph.x}, ${glyph.y}, is not in its font or not in the block`);
    }
    glyphs.push(glyph);
  }
  if (read.left() !== 0) {
    throw new Rejection(TRAILING_BYTES, `${read.left()} bytes follow the last glyph`);
  }
  checkLoop(header, draw.passMs(settings, block, canvas));
  return {header, settings, text: new TextDecoder().decode(textData), glyphs, block};
}

// A text as the JSON source has it: `{width, height, text, font, color, background, align,
// valign, direction, wrap, effect, motion, speed, pause}`.
export function loadsText(top) {
  strictjson.members(top, TEXT_MEMBERS);
  const width = Number(strictjson.integer(top.get("width"), 1, 65535, "width"));
  const height = Number(strictjson.integer(top.get("height"), 1, 65535, "height"));
  const text = top.get("text");
  if (typeof text !== "string") throw new Rejection(BAD_TYPE, "text is not a string");
  const bytes = new TextEncoder().encode(text).length;
  if (bytes < 1 || bytes > textlayout.LONGEST_TEXT) throw new Rejection(OUT_OF_RANGE, `text has ${bytes} bytes of UTF-8, not 1 to ${textlayout.LONGEST_TEXT}`);
  const choice = (name, list) => {
    const value = top.get(name);
    if (typeof value !== "string") throw new Rejection(BAD_TYPE, `${name} is not a string`);
    if (!list.includes(value)) throw new Rejection(OUT_OF_RANGE, `${name} is ${JSON.stringify(value)}, not one of ${list.join(", ")}`);
    return value;
  };
  const font = choice("font", Object.keys(textlayout.FONTS));
  const color = Number(strictjson.integer(top.get("color"), 0, 0xffffff, "color"));
  const background = Number(strictjson.integer(top.get("background"), 0, 0xffffff, "background"));
  const align = choice("align", draw.ALIGNS);
  const valign = choice("valign", draw.VALIGNS);
  const direction = choice("direction", draw.DIRECTIONS);
  const wrap = top.get("wrap");
  if (typeof wrap !== "boolean") throw new Rejection(BAD_TYPE, "wrap is not true or false");
  const effect = choice("effect", draw.EFFECTS);
  const motion = choice("motion", draw.MOTIONS);
  const speed = Number(strictjson.integer(top.get("speed"), 1, draw.FASTEST, "speed"));
  const pause = Number(strictjson.integer(top.get("pause_ms"), effect === "static" ? draw.SHORTEST_STATIC : 0, draw.LONGEST_PAUSE, "pause_ms"));
  return {width, height, text, font, color, background, align, valign, direction, wrap, effect, motion, speed, pause};
}

// The canonical JSON source of a text, as `dumps` writes it.
export function dumpsText(text) {
  const source = {
    version: SOURCE_VERSION, type: "text", width: text.width, height: text.height, text: text.text, font: text.font,
    color: text.color, background: text.background, align: text.align, valign: text.valign, direction: text.direction,
    wrap: text.wrap, effect: text.effect, motion: text.motion, speed: text.speed, pause_ms: text.pause,
  };
  return new TextEncoder().encode(`${JSON.stringify(source, null, 2)}\n`);
}

// A container of a text: its layout made, its block checked against the canvas, its pass
// measured.
export function encodeText(text) {
  refuseLargeCanvas(text.width, text.height);
  const canvas = {width: text.width, height: text.height};
  const block = textlayout.layout(text.text, text, text.width);
  if (!draw.fits(text, block, canvas)) {
    const better = horizontalMotion(text.motion) ? "a marquee or a pan up or down" : "a marquee or a pan left or right";
    throw new Rejection(DOES_NOT_FIT, `a block of ${block.width} x ${block.height} cannot be seen whole on ${canvas.width} x ${canvas.height} with ${text.effect} ${text.motion}; ${text.effect === "static" || text.effect === "slide" ? "a pan or a marquee shows all of it" : `${better} shows all of it`}`);
  }
  const textData = new TextEncoder().encode(text.text);
  const payload = new Uint8Array(TEXT_SETTINGS_SIZE + textData.length + GLYPH_SIZE * block.glyphs.length);
  const font = textlayout.FONTS[text.font];
  payload[0] = font.id;
  payload[1] = textlayout.fontOf(font.id).version;
  payload[2] = draw.EFFECTS.indexOf(text.effect);
  payload[3] = draw.MOTIONS.indexOf(text.motion);
  payload[4] = draw.ALIGNS.indexOf(text.align);
  payload[5] = draw.VALIGNS.indexOf(text.valign);
  payload[6] = draw.DIRECTIONS.indexOf(text.direction);
  payload[7] = text.wrap ? 1 : 0;
  putColour(payload, 8, text.color);
  putColour(payload, 11, text.background);
  putU16(payload, 14, text.speed);
  putU16(payload, 16, text.pause);
  putU16(payload, 18, textData.length);
  putU16(payload, 20, block.glyphs.length);
  putU16(payload, 22, block.width);
  putU16(payload, 24, block.height);
  payload.set(textData, TEXT_SETTINGS_SIZE);
  block.glyphs.forEach((glyph, one) => {
    const at = TEXT_SETTINGS_SIZE + textData.length + GLYPH_SIZE * one;
    putU16(payload, at, glyph.glyph);
    putU16(payload, at + 2, glyph.x);
    putU16(payload, at + 4, glyph.y);
  });
  return wrap("text", text.width, text.height, draw.passMs(text, block, canvas), payload);
}

// The text of a decoded container, as its JSON source has it.
export function textOf(decoded) {
  return {width: decoded.header.width, height: decoded.header.height, text: decoded.text, ...decoded.settings};
}

function horizontalMotion(motion) {
  return motion === "left" || motion === "right";
}
