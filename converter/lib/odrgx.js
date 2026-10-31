// ODRGX, the container of docs/format.md: a header of 20 bytes that names what the
// payload is, frames, a text or a widget, and the payload.
//
// The reasons come in the order in which the core meets them reading a file front to
// back: the header, the payload, and last the length the header gives the payload.

import {deflateRaw} from "./deflate.js";
import * as draw from "./draw.js";
import {
  BAD_CONTAINER,
  BAD_GLYPH,
  BAD_JSON,
  BAD_MAGIC,
  BAD_PICTURE,
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
  UNKNOWN_WIDGET,
  ZERO_SIZE,
} from "./errors.js";
import * as jsonframes from "./jsonframes.js";
import * as odrg from "./odrg.js";
import * as strictjson from "./strictjson.js";
import * as messageclock from "./messageclock.js";
import * as textlayout from "./textlayout.js";

export const MAGIC = Uint8Array.of(0x4f, 0x44, 0x52, 0x58);
export const VERSION = 1;
export const HEADER_SIZE = 20;
export const ENDING = ".odrgx";

// The content types this library reads, by name and by number, and the version of each.
export const TYPES = {frames: 1, text: 2, widget: 3};
export const TYPE_NAMES = {1: "frames", 2: "text", 3: "widget"};
export const TYPE_VERSIONS = {1: 1, 2: 1, 3: 1};
// The most bytes a payload of each type may have; frames have no limit of their own.
export const LARGEST_PAYLOAD = {1: 0xffffffff, 2: 3612, 3: 32768};
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

// Reads a container of frames given as bytes, one frame record at a time, as `odrg.reader`
// reads a file: the canvas of the payload's header is compared at once, and after the last
// record the payload's size and the loop are checked. The result is that of `odrg.reader`
// for the payload, with `header`, and `loopMs()` the loop of the container's header.
export function framesReader(data, header = readHeader(data)) {
  const payload = payloadOf(data);
  const inner = odrg.header(payload);
  if (inner.width !== header.width || inner.height !== header.height) {
    throw new Rejection(CANVAS_MISMATCH, `the container's canvas is ${header.width} x ${header.height} and its frames' ${inner.width} x ${inner.height}`);
  }
  const read = odrg.reader(payload);
  let total = 0;
  let ended = false;
  const next = () => {
    const record = read.next();
    if (record !== null) {
      total += record.ms;
      return record;
    }
    if (!ended) {
      ended = true;
      checkPayloadSize(header, data);
      checkLoop(header, total);
    }
    return null;
  };
  return {
    width: read.width,
    height: read.height,
    paletteSize: read.paletteSize,
    frameCount: read.frameCount,
    compressed: read.compressed,
    header,
    next,
    loopMs: () => header.loopMs,
  };
}

// Reads a container of frames given as bytes: its header and the ODRG file of its payload,
// decoded as `odrg.decode` does. The canvas of the payload's header is compared before its
// frame records are read.
export function decodeFrames(data, header = readHeader(data)) {
  const read = framesReader(data, header);
  const records = [];
  const modes = [];
  for (let record = read.next(); record !== null; record = read.next()) {
    records.push({ms: record.ms, picture: record.picture});
    modes.push(record.mode);
  }
  return {width: read.width, height: read.height, paletteSize: read.paletteSize, compressed: read.compressed, records, modes, header};
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
// text as `decodeText` does and for a widget as `decodeWidget` does, each with `type`, the
// type's name.
export function decode(data) {
  const header = readHeader(data);
  const name = TYPE_NAMES[header.type];
  const reader = {frames: decodeFrames, text: decodeText, widget: decodeWidget}[name];
  return {type: name, ...reader(data, header)};
}

// A JSON source, read by its member `type`: `{type: "frames", animation}` for JSON frames,
// which have no `type`, `{type: "text", text}` for a text and `{type: "widget", widget}`
// for a clock.
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
  if (type === "widget") {
    return {type, widget: loadsWidget(top)};
  }
  throw new Rejection(UNKNOWN_TYPE, `type is ${JSON.stringify(type)}, not "text" or "widget"`);
}

// The container of a JSON source as `loadsSource` reads it.
export function encodeSource(source, {compressed = true} = {}) {
  if (source.type === "text") {
    return encodeText(source.text);
  }
  if (source.type === "widget") {
    return encodeWidget(source.widget);
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
    rest() {
      const taken = bytes.subarray(at);
      at = bytes.length;
      return taken;
    },
  };
}

// A reader of UTF-8 as the standard has it, one byte after the other, as the core reads it:
// `feed` is false at the first byte that no UTF-8 text can have there, and `done` is false
// while a character is not complete. No overlong form, no surrogate, nothing above
// U+10FFFF.
export function utf8Reader() {
  let need = 0;
  let low = 0x80;
  let high = 0xbf;
  return {
    feed(byte) {
      if (need !== 0) {
        if (byte < low || byte > high) return false;
        need -= 1;
        [low, high] = [0x80, 0xbf];
        return true;
      }
      [low, high] = [0x80, 0xbf];
      if (byte <= 0x7f) return true;
      if (byte >= 0xc2 && byte <= 0xdf) need = 1;
      else if (byte === 0xe0) [need, low] = [2, 0xa0];
      else if ((byte >= 0xe1 && byte <= 0xec) || byte === 0xee || byte === 0xef) need = 2;
      else if (byte === 0xed) [need, high] = [2, 0x9f];
      else if (byte === 0xf0) [need, low] = [3, 0x90];
      else if (byte >= 0xf1 && byte <= 0xf3) need = 3;
      else if (byte === 0xf4) [need, high] = [3, 0x8f];
      else return false;
      return true;
    },
    done() {
      return need === 0;
    },
  };
}

// Whether bytes are UTF-8 as `utf8Reader` reads it.
export function isUtf8(bytes) {
  const reader = utf8Reader();
  return bytes.every((byte) => reader.feed(byte)) && reader.done();
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
  const textData = new Uint8Array(textBytes);
  const utf8 = utf8Reader();
  for (let at = 0; at < textBytes; at += 1) {
    textData[at] = read.take(1, "the text")[0];
    if (!utf8.feed(textData[at])) throw new Rejection(BAD_TEXT, `the text is not UTF-8 at its byte ${at + 1}`);
  }
  if (!utf8.done()) throw new Rejection(BAD_TEXT, "the text ends inside a character");
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

// The picture of a decoded text or clock `t` milliseconds into its turn, as the player
// draws it, a clock with the seed of its turn: three bytes for each pixel in the pixel
// order of docs/format.md.
export function pictureAt(decoded, t, seed = 1) {
  const {width, height} = decoded.header;
  const picture = new Uint8Array(3 * width * height);
  if ("widget" in decoded.settings) {
    return draw.drawClock(decoded.settings, seed, t, {width, height}, picture);
  }
  const font = textlayout.fontOf(textlayout.FONTS[decoded.settings.font].id);
  return draw.drawText(decoded, font, t % decoded.header.loopMs, picture);
}

// The text of a decoded container, as its JSON source has it.
export function textOf(decoded) {
  return {width: decoded.header.width, height: decoded.header.height, text: decoded.text, ...decoded.settings};
}

function horizontalMotion(motion) {
  return motion === "left" || motion === "right";
}

// The widget payload, version 1: the 20 bytes of settings of a clock, or a picture widget's
// head, its parts and its picture.
export const WIDGET_SIZE = 20;
export const PICTURE_HEAD_SIZE = 12;
export const HAND_SIZE = 10;
export const CAP_SIZE = 6;
export const FIELD_SIZE = 22;
// The duration the converter gives a picture widget's one frame, which no reader uses.
export const PICTURE_MS = 1000;

// The members of the JSON source of a clock, in the order in which it is written.
export const WIDGET_MEMBERS = ["version", "type", "width", "height", "widget", "seconds", "face", "hands", "rim", "background", "speed_min", "speed_max"];
// The members of the JSON source of a picture clock, in the order in which it is written:
// those of both widgets, then a dial's or a display's; and those of its parts.
export const PICTURE_MEMBERS = ["version", "type", "width", "height", "widget", "seconds", "speed_min", "speed_max", "direction", "turns", "palette", "picture"];
export const DIAL_MEMBERS = ["hands", "caps"];
export const DISPLAY_MEMBERS = ["fields"];
export const HAND_MEMBERS = ["unit", "color", "x", "y", "length", "tail", "half", "offset"];
export const CAP_MEMBERS = ["x", "y", "radius", "color"];
export const FIELD_MEMBERS = ["left", "top", "width", "height", "font", "pattern", "digits", "colons", "blink", "offset"];

function signed(byte) {
  return byte >= 128 ? byte - 256 : byte;
}

// Reads a container of a widget given as bytes: `{header, settings}`, in the order in which
// the core checks it: the canvas, the widget, and then for a clock the payload's length,
// the other settings in the order of their offsets, the end and the loop; for a picture
// widget as `decodePictureWidget` says.
export function decodeWidget(data, header = readHeader(data)) {
  refuseLargeCanvas(header.width, header.height);
  const read = cursor(payloadOf(data));
  const widget = read.take(1, "the settings of the widget")[0];
  if (widget === 6) return {header, settings: messageclock.decode(payloadOf(data), header)};
  if (widget < 1 || widget > draw.WIDGETS.length) {
    throw new Rejection(UNKNOWN_WIDGET, `widget ${widget} is none this player has`);
  }
  const name = draw.WIDGETS[widget - 1];
  if (draw.PICTURE_WIDGETS.includes(name)) {
    return decodePictureWidget(name, read, data, header);
  }
  if (header.payloadSize !== WIDGET_SIZE) {
    throw new Rejection(PAYLOAD_SIZE, `the header gives the payload ${header.payloadSize} bytes, not ${WIDGET_SIZE}`);
  }
  const fixed = Uint8Array.of(widget, ...read.take(WIDGET_SIZE - 1, "the settings of the widget"));
  if (fixed[1] !== 0) throw badSettings("the reserved byte is not 0");
  const seconds = u16(fixed, 2);
  if (seconds < 1 || seconds > draw.LONGEST_CLOCK) throw badSettings(`a loop of ${seconds} seconds is not 1 to ${draw.LONGEST_CLOCK}`);
  const speedMin = u16(fixed, 16);
  const speedMax = u16(fixed, 18);
  refuseSpeeds(speedMin, speedMax);
  if (read.left() !== 0) {
    throw new Rejection(TRAILING_BYTES, `${read.left()} bytes follow the settings`);
  }
  checkLoop(header, 1000 * seconds);
  const settings = {
    widget: name, seconds, face: colour(fixed, 4), hands: colour(fixed, 7), rim: colour(fixed, 10), background: colour(fixed, 13), speedMin,
    speedMax,
  };
  return {header, settings};
}

function refuseSpeeds(speedMin, speedMax) {
  if (speedMin < 1 || speedMin > draw.FASTEST_CLOCK) throw badSettings(`the least speed is ${speedMin}, not 1 to ${draw.FASTEST_CLOCK}`);
  if (speedMax < speedMin || speedMax > draw.FASTEST_CLOCK) throw badSettings(`the greatest speed is ${speedMax}, not ${speedMin} to ${draw.FASTEST_CLOCK}`);
}

// The settings of a picture widget, read on from its first byte: its head, each hand and
// cap or each field in the order of their offsets, then its picture's ODRG header, the
// picture's canvas, its one frame and its palette, the parts' colours against the palette,
// the picture's frame record and its end, the payload's length and the loop.
function decodePictureWidget(widget, read, data, header) {
  const {width, height} = header;
  const head = Uint8Array.of(0, ...read.take(PICTURE_HEAD_SIZE - 1, "the head of the widget"));
  if (head[1] !== 0) throw badSettings("the reserved byte is not 0");
  const seconds = u16(head, 2);
  if (seconds < 1 || seconds > draw.LONGEST_CLOCK) throw badSettings(`a loop of ${seconds} seconds is not 1 to ${draw.LONGEST_CLOCK}`);
  const speedMin = u16(head, 4);
  const speedMax = u16(head, 6);
  refuseSpeeds(speedMin, speedMax);
  if (head[8] >= draw.WAYS.length) throw badSettings(`the direction is ${head[8]}, not 0 to ${draw.WAYS.length - 1}`);
  const direction = draw.WAYS[head[8]];
  const turns = head[9];
  if (turns > draw.MOST_TURNS) throw badSettings(`the turns are ${turns} percent, above ${draw.MOST_TURNS}`);
  if (direction !== "random" && turns !== 0) throw badSettings(`a ${direction} widget has turns of ${turns} percent, not 0`);
  const dial = widget === "picture-dial";
  const parts = head[10];
  const caps = head[11];
  if (dial && (parts < 1 || parts > draw.MOST_HANDS || caps > draw.MOST_CAPS)) {
    throw badSettings(`a dial of ${parts} hands and ${caps} caps, not 1 to ${draw.MOST_HANDS} and 0 to ${draw.MOST_CAPS}`);
  }
  if (!dial && (parts < 1 || parts > draw.MOST_FIELDS || caps !== 0)) {
    throw badSettings(`a display of ${parts} fields and ${caps} caps, not 1 to ${draw.MOST_FIELDS} and 0`);
  }
  const settings = {widget, seconds, speedMin, speedMax, direction, turns};
  const colours = [];
  const place = (bytes, at, what) => {
    const x = u16(bytes, at);
    const y = u16(bytes, at + 2);
    if (x > 2 * width || y > 2 * height) throw badSettings(`${what} is at ${x}, ${y} half pixels, outside the canvas`);
    return {x, y};
  };
  if (dial) {
    settings.hands = [];
    for (let one = 1; one <= parts; one += 1) {
      const what = `hand ${one}`;
      const bytes = read.take(HAND_SIZE, what);
      if (bytes[0] >= draw.UNITS.length) throw badSettings(`the unit of ${what} is ${bytes[0]}, not 0 to ${draw.UNITS.length - 1}`);
      colours.push([bytes[1], `the colour of ${what}`]);
      const {x, y} = place(bytes, 2, what);
      if (bytes[6] < 1) throw badSettings(`${what} has no length`);
      if (bytes[8] < 1 || bytes[8] > draw.WIDEST_HAND) throw badSettings(`the half width of ${what} is ${bytes[8]}, not 1 to ${draw.WIDEST_HAND}`);
      const offset = signed(bytes[9]);
      if (Math.abs(offset) > draw.LARGEST_OFFSET) throw badSettings(`the offset of ${what} is ${offset} hours`);
      settings.hands.push({unit: draw.UNITS[bytes[0]], color: bytes[1], x, y, length: bytes[6], tail: bytes[7], half: bytes[8], offset});
    }
    settings.caps = [];
    for (let one = 1; one <= caps; one += 1) {
      const what = `cap ${one}`;
      const bytes = read.take(CAP_SIZE, what);
      const {x, y} = place(bytes, 0, what);
      if (bytes[4] < 1) throw badSettings(`${what} has no radius`);
      colours.push([bytes[5], `the colour of ${what}`]);
      settings.caps.push({x, y, radius: bytes[4], color: bytes[5]});
    }
  } else {
    settings.fields = [];
    for (let one = 1; one <= parts; one += 1) {
      const what = `field ${one}`;
      const bytes = read.take(FIELD_SIZE, what);
      const box = {left: u16(bytes, 0), top: u16(bytes, 2), width: u16(bytes, 4), height: u16(bytes, 6)};
      if (box.width < 1 || box.height < 1 || box.left + box.width > width || box.top + box.height > height) {
        throw badSettings(`the box of ${what} is ${box.width} x ${box.height} at ${box.left}, ${box.top}, not within the canvas`);
      }
      const font = Object.keys(draw.DISPLAY_FONTS).find((name) => draw.DISPLAY_FONTS[name] === bytes[8]);
      if (font === undefined) throw new Rejection(UNKNOWN_FONT, `font ${bytes[8]} of ${what} is none this player has`);
      colours.push([bytes[9], `the colour of the digits of ${what}`], [bytes[10], `the colour of the colons of ${what}`]);
      if (bytes[11] > 1) throw badSettings(`the blink of ${what} is ${bytes[11]}, not 0 or 1`);
      const offset = signed(bytes[12]);
      if (Math.abs(offset) > draw.LARGEST_OFFSET) throw badSettings(`the offset of ${what} is ${offset} hours`);
      if (bytes[13] !== 0) throw badSettings(`the reserved byte of ${what} is not 0`);
      let pattern = "";
      for (let at = 14; at < FIELD_SIZE; at += 1) {
        const byte = bytes[at];
        if (byte === 0) continue;
        if (at > 14 && bytes[at - 1] === 0) throw badSettings(`the pattern of ${what} goes on after a zero byte`);
        if (!draw.PATTERN_CHARACTERS.includes(String.fromCharCode(byte))) throw badSettings(`the pattern of ${what} has the byte ${byte}`);
        pattern += String.fromCharCode(byte);
      }
      if (pattern === "") throw badSettings(`the pattern of ${what} is empty`);
      settings.fields.push({...box, font, pattern, digits: bytes[9], colons: bytes[10], blink: bytes[11] === 1, offset});
    }
  }
  const pictureBytes = read.rest();
  const inner = odrg.header(pictureBytes);
  if (inner.width !== width || inner.height !== height) {
    throw new Rejection(CANVAS_MISMATCH, `the container's canvas is ${width} x ${height} and its picture's ${inner.width} x ${inner.height}`);
  }
  if (inner.frameCount !== 1 || inner.paletteSize < 1 || inner.paletteSize > draw.MOST_COLOURS) {
    throw new Rejection(BAD_PICTURE, `the picture has ${inner.frameCount} frames and ${inner.paletteSize} colours, not 1 and 1 to ${draw.MOST_COLOURS}`);
  }
  for (const [value, what] of colours) {
    if (value >= inner.paletteSize) throw badSettings(`${what} is ${value}; the palette has ${inner.paletteSize} colours`);
  }
  const picture = odrg.reader(pictureBytes);
  const record = picture.next();
  picture.next();
  checkPayloadSize(header, data);
  checkLoop(header, 1000 * seconds);
  settings.palette = [];
  for (let at = 0; at < picture.palette.length; at += 3) settings.palette.push(colour(picture.palette, at));
  settings.picture = record.buffer;
  return {header, settings};
}

// A clock as the JSON source has it: `{width, height, widget, seconds, face, hands, rim,
// background, speedMin, speedMax}`, or a picture clock as `loadsPictureWidget` gives it.
export function loadsWidget(top) {
  if (top instanceof Map && top.get("widget") === "message-clock") return messageclock.load(top);
  if (top instanceof Map && draw.PICTURE_WIDGETS.includes(top.get("widget"))) {
    return loadsPictureWidget(top);
  }
  strictjson.members(top, WIDGET_MEMBERS);
  const width = Number(strictjson.integer(top.get("width"), 1, 65535, "width"));
  const height = Number(strictjson.integer(top.get("height"), 1, 65535, "height"));
  const widget = top.get("widget");
  if (typeof widget !== "string") throw new Rejection(BAD_TYPE, "widget is not a string");
  if (!draw.WIDGETS.includes(widget)) throw new Rejection(OUT_OF_RANGE, `widget is ${JSON.stringify(widget)}, not one of ${draw.WIDGETS.join(", ")}`);
  const seconds = Number(strictjson.integer(top.get("seconds"), 1, draw.LONGEST_CLOCK, "seconds"));
  const colours = {};
  for (const name of ["face", "hands", "rim", "background"]) {
    colours[name] = Number(strictjson.integer(top.get(name), 0, 0xffffff, name));
  }
  const speedMin = Number(strictjson.integer(top.get("speed_min"), 1, draw.FASTEST_CLOCK, "speed_min"));
  const speedMax = Number(strictjson.integer(top.get("speed_max"), speedMin, draw.FASTEST_CLOCK, "speed_max"));
  return {width, height, widget, seconds, ...colours, speedMin, speedMax};
}

// One of a list of names, as a JSON source has it.
function nameOf(value, names, what) {
  if (typeof value !== "string") throw new Rejection(BAD_TYPE, `${what} is not a string`);
  if (!names.includes(value)) throw new Rejection(OUT_OF_RANGE, `${what} is ${JSON.stringify(value)}, not one of ${names.join(", ")}`);
  return value;
}

function wholeOf(value, low, high, what) {
  return Number(strictjson.integer(value, low, high, what));
}

// The palette and the picture of a picture clock's source or of a tile: 1 to 8 colours, no
// two the same, and a row of characters for each row of the canvas, the top row first, each
// character the digit of a palette index. The picture is given back in the pixel order of
// docs/format.md.
export function loadsPicture(palette, rows, width, height, what = "the file") {
  strictjson.array(palette, `the palette of ${what}`);
  if (palette.length < 1 || palette.length > draw.MOST_COLOURS) {
    throw new Rejection(OUT_OF_RANGE, `the palette of ${what} has ${palette.length} colours, not 1 to ${draw.MOST_COLOURS}`);
  }
  const colours = palette.map((value, at) => wholeOf(value, 0, 0xffffff, `colour ${at} of the palette of ${what}`));
  if (new Set(colours).size !== colours.length) throw new Rejection(OUT_OF_RANGE, `the palette of ${what} has a colour twice`);
  strictjson.array(rows, `the picture of ${what}`);
  if (rows.length !== height) throw new Rejection(OUT_OF_RANGE, `the picture of ${what} has ${rows.length} rows, not ${height}`);
  const picture = new Uint8Array(width * height);
  rows.forEach((row, y) => {
    if (typeof row !== "string") throw new Rejection(BAD_TYPE, `row ${y} of the picture of ${what} is not a string`);
    if (row.length !== width) throw new Rejection(OUT_OF_RANGE, `row ${y} of the picture of ${what} has ${row.length} characters, not ${width}`);
    for (let x = 0; x < width; x += 1) {
      const index = row.charCodeAt(x) - 48;
      if (index < 0 || index >= colours.length) {
        throw new Rejection(OUT_OF_RANGE, `pixel ${x} of row ${y} of the picture of ${what} is ${JSON.stringify(row[x])}, not a palette index`);
      }
      picture[(height - 1 - y) * width + x] = index;
    }
  });
  return {palette: colours, picture};
}

// The rows of a picture in the pixel order of docs/format.md, the top row first, as a
// source has them.
export function pictureRows(picture, width, height) {
  const rows = [];
  for (let y = 0; y < height; y += 1) {
    const from = (height - 1 - y) * width;
    rows.push(Array.from(picture.subarray(from, from + width), (index) => String(index)).join(""));
  }
  return rows;
}

// The settings of a picture clock other than the canvas, the widget, the palette and the
// picture, read from an object that has them: the members of `top` named as in a source.
export function loadsPictureSettings(top, widget, width, height, colours, what = "the file") {
  const seconds = wholeOf(top.get("seconds"), 1, draw.LONGEST_CLOCK, "seconds");
  const speedMin = wholeOf(top.get("speed_min"), 1, draw.FASTEST_CLOCK, "speed_min");
  const speedMax = wholeOf(top.get("speed_max"), speedMin, draw.FASTEST_CLOCK, "speed_max");
  const direction = nameOf(top.get("direction"), draw.WAYS, "direction");
  const turns = wholeOf(top.get("turns"), 0, direction === "random" ? draw.MOST_TURNS : 0, "turns");
  const settings = {widget, seconds, speedMin, speedMax, direction, turns};
  const colourOf = (value, name) => wholeOf(value, 0, colours - 1, name);
  const list = (name, least, most) => {
    const items = strictjson.array(top.get(name), name);
    if (items.length < least || items.length > most) throw new Rejection(OUT_OF_RANGE, `${what} has ${items.length} ${name}, not ${least} to ${most}`);
    return items;
  };
  if (widget === "picture-dial") {
    settings.hands = list("hands", 1, draw.MOST_HANDS).map((hand, at) => {
      const name = `hand ${at + 1}`;
      strictjson.members(hand, HAND_MEMBERS, [], name);
      return {
        unit: nameOf(hand.get("unit"), draw.UNITS, `the unit of ${name}`), color: colourOf(hand.get("color"), `the color of ${name}`),
        x: wholeOf(hand.get("x"), 0, 2 * width, `x of ${name}`), y: wholeOf(hand.get("y"), 0, 2 * height, `y of ${name}`),
        length: wholeOf(hand.get("length"), 1, 255, `the length of ${name}`), tail: wholeOf(hand.get("tail"), 0, 255, `the tail of ${name}`),
        half: wholeOf(hand.get("half"), 1, draw.WIDEST_HAND, `the half width of ${name}`),
        offset: wholeOf(hand.get("offset"), -draw.LARGEST_OFFSET, draw.LARGEST_OFFSET, `the offset of ${name}`),
      };
    });
    settings.caps = list("caps", 0, draw.MOST_CAPS).map((cap, at) => {
      const name = `cap ${at + 1}`;
      strictjson.members(cap, CAP_MEMBERS, [], name);
      return {
        x: wholeOf(cap.get("x"), 0, 2 * width, `x of ${name}`), y: wholeOf(cap.get("y"), 0, 2 * height, `y of ${name}`),
        radius: wholeOf(cap.get("radius"), 1, 255, `the radius of ${name}`), color: colourOf(cap.get("color"), `the color of ${name}`),
      };
    });
    return settings;
  }
  settings.fields = list("fields", 1, draw.MOST_FIELDS).map((field, at) => {
    const name = `field ${at + 1}`;
    strictjson.members(field, FIELD_MEMBERS, [], name);
    const left = wholeOf(field.get("left"), 0, width - 1, `the left of ${name}`);
    const top = wholeOf(field.get("top"), 0, height - 1, `the top of ${name}`);
    const wide = wholeOf(field.get("width"), 1, width - left, `the width of ${name}`);
    const high = wholeOf(field.get("height"), 1, height - top, `the height of ${name}`);
    const font = nameOf(field.get("font"), Object.keys(draw.DISPLAY_FONTS), `the font of ${name}`);
    const pattern = field.get("pattern");
    if (typeof pattern !== "string") throw new Rejection(BAD_TYPE, `the pattern of ${name} is not a string`);
    if (pattern.length < 1 || pattern.length > draw.LONGEST_PATTERN || [...pattern].some((character) => !draw.PATTERN_CHARACTERS.includes(character))) {
      throw new Rejection(OUT_OF_RANGE, `the pattern of ${name} is ${JSON.stringify(pattern)}, not 1 to ${draw.LONGEST_PATTERN} of "${draw.PATTERN_CHARACTERS}"`);
    }
    const blink = field.get("blink");
    if (typeof blink !== "boolean") throw new Rejection(BAD_TYPE, `the blink of ${name} is not true or false`);
    return {
      left, top, width: wide, height: high, font, pattern, digits: colourOf(field.get("digits"), `the digits of ${name}`),
      colons: colourOf(field.get("colons"), `the colons of ${name}`), blink,
      offset: wholeOf(field.get("offset"), -draw.LARGEST_OFFSET, draw.LARGEST_OFFSET, `the offset of ${name}`),
    };
  });
  return settings;
}

// A picture clock as its JSON source has it: `{width, height, widget, seconds, speedMin,
// speedMax, direction, turns, palette, picture}` and `hands` and `caps` or `fields`.
export function loadsPictureWidget(top) {
  const widget = top.get("widget");
  strictjson.members(top, [...PICTURE_MEMBERS, ...(widget === "picture-dial" ? DIAL_MEMBERS : DISPLAY_MEMBERS)]);
  const width = wholeOf(top.get("width"), 1, 65535, "width");
  const height = wholeOf(top.get("height"), 1, 65535, "height");
  const {palette, picture} = loadsPicture(top.get("palette"), top.get("picture"), width, height);
  const settings = loadsPictureSettings(top, widget, width, height, palette.length);
  return {width, height, ...settings, palette, picture};
}

// The canonical JSON source of a clock or a picture clock.
export function dumpsWidget(widget) {
  if (widget.widget === "message-clock") return new TextEncoder().encode(`${JSON.stringify(messageclock.source(widget), null, 2)}\n`);
  let source;
  if (draw.PICTURE_WIDGETS.includes(widget.widget)) {
    source = {
      version: SOURCE_VERSION, type: "widget", width: widget.width, height: widget.height, widget: widget.widget, seconds: widget.seconds,
      speed_min: widget.speedMin, speed_max: widget.speedMax, direction: widget.direction, turns: widget.turns, palette: widget.palette,
      picture: pictureRows(widget.picture, widget.width, widget.height),
    };
    if (widget.widget === "picture-dial") {
      source.hands = widget.hands.map((hand) => Object.fromEntries(HAND_MEMBERS.map((name) => [name, hand[name]])));
      source.caps = widget.caps.map((cap) => Object.fromEntries(CAP_MEMBERS.map((name) => [name, cap[name]])));
    } else {
      source.fields = widget.fields.map((field) => Object.fromEntries(FIELD_MEMBERS.map((name) => [name, field[name]])));
    }
  } else {
    source = {
      version: SOURCE_VERSION, type: "widget", width: widget.width, height: widget.height, widget: widget.widget,
      seconds: widget.seconds, face: widget.face, hands: widget.hands, rim: widget.rim, background: widget.background,
      speed_min: widget.speedMin, speed_max: widget.speedMax,
    };
  }
  return new TextEncoder().encode(`${JSON.stringify(source, null, 2)}\n`);
}

// The ODRG file of a picture widget's picture: one frame of palette indices, in the
// palette's own order, compressed.
export function pictureFile(width, height, palette, picture) {
  const colours = new Uint8Array(3 * palette.length);
  palette.forEach((value, at) => putColour(colours, 3 * at, value));
  const record = odrg.bestRecord(new Uint8Array(width * height), picture, width, 1, PICTURE_MS);
  return odrg.container(width, height, colours, [record], deflateRaw);
}

// A container of a clock or a picture clock, its loop `seconds` long.
export function encodeWidget(widget) {
  refuseLargeCanvas(widget.width, widget.height);
  if (widget.widget === "message-clock") return wrap("widget", 60, 60, widget.loopMs, messageclock.encode(widget));
  if (draw.PICTURE_WIDGETS.includes(widget.widget)) {
    return encodePictureWidget(widget);
  }
  const payload = new Uint8Array(WIDGET_SIZE);
  payload[0] = draw.WIDGETS.indexOf(widget.widget) + 1;
  putU16(payload, 2, widget.seconds);
  putColour(payload, 4, widget.face);
  putColour(payload, 7, widget.hands);
  putColour(payload, 10, widget.rim);
  putColour(payload, 13, widget.background);
  putU16(payload, 16, widget.speedMin);
  putU16(payload, 18, widget.speedMax);
  return wrap("widget", widget.width, widget.height, 1000 * widget.seconds, payload);
}

function encodePictureWidget(widget) {
  const dial = widget.widget === "picture-dial";
  const parts = dial ? widget.hands.length : widget.fields.length;
  const caps = dial ? widget.caps.length : 0;
  const head = new Uint8Array(PICTURE_HEAD_SIZE + (dial ? HAND_SIZE * parts + CAP_SIZE * caps : FIELD_SIZE * parts));
  head[0] = draw.WIDGETS.indexOf(widget.widget) + 1;
  putU16(head, 2, widget.seconds);
  putU16(head, 4, widget.speedMin);
  putU16(head, 6, widget.speedMax);
  head[8] = draw.WAYS.indexOf(widget.direction);
  head[9] = widget.turns;
  head[10] = parts;
  head[11] = caps;
  let at = PICTURE_HEAD_SIZE;
  if (dial) {
    for (const hand of widget.hands) {
      head[at] = draw.UNITS.indexOf(hand.unit);
      head[at + 1] = hand.color;
      putU16(head, at + 2, hand.x);
      putU16(head, at + 4, hand.y);
      head[at + 6] = hand.length;
      head[at + 7] = hand.tail;
      head[at + 8] = hand.half;
      head[at + 9] = hand.offset & 0xff;
      at += HAND_SIZE;
    }
    for (const cap of widget.caps) {
      putU16(head, at, cap.x);
      putU16(head, at + 2, cap.y);
      head[at + 4] = cap.radius;
      head[at + 5] = cap.color;
      at += CAP_SIZE;
    }
  } else {
    for (const field of widget.fields) {
      putU16(head, at, field.left);
      putU16(head, at + 2, field.top);
      putU16(head, at + 4, field.width);
      putU16(head, at + 6, field.height);
      head[at + 8] = draw.DISPLAY_FONTS[field.font];
      head[at + 9] = field.digits;
      head[at + 10] = field.colons;
      head[at + 11] = field.blink ? 1 : 0;
      head[at + 12] = field.offset & 0xff;
      [...field.pattern].forEach((character, place) => {
        head[at + 14 + place] = character.charCodeAt(0);
      });
      at += FIELD_SIZE;
    }
  }
  const picture = pictureFile(widget.width, widget.height, widget.palette, widget.picture);
  const payload = new Uint8Array(head.length + picture.length);
  payload.set(head);
  payload.set(picture, head.length);
  return wrap("widget", widget.width, widget.height, 1000 * widget.seconds, payload);
}

// The clock of a decoded container, as its JSON source has it.
export function widgetOf(decoded) {
  return {width: decoded.header.width, height: decoded.header.height, ...decoded.settings};
}
