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
  UNKNOWN_WIDGET,
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
export const TYPES = {frames: 1, text: 2, widget: 3};
export const TYPE_NAMES = {1: "frames", 2: "text", 3: "widget"};
export const TYPE_VERSIONS = {1: 1, 2: 1, 3: 1};
// The most bytes a payload of each type may have; frames have no limit of their own.
export const LARGEST_PAYLOAD = {1: 0xffffffff, 2: 3612, 3: 20};
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

// The widget payload, version 1: 20 bytes of settings of a clock.
export const WIDGET_SIZE = 20;

// The members of the JSON source of a clock, in the order in which it is written.
export const WIDGET_MEMBERS = ["version", "type", "width", "height", "widget", "seconds", "face", "hands", "rim", "background", "speed_min", "speed_max"];

// Reads a container of a widget given as bytes: `{header, settings}`, in the order in which
// the core checks it: the canvas, the payload's length, the widget, the other settings in
// the order of their offsets, the end and the loop.
export function decodeWidget(data, header = readHeader(data)) {
  refuseLargeCanvas(header.width, header.height);
  if (header.payloadSize !== WIDGET_SIZE) {
    throw new Rejection(PAYLOAD_SIZE, `the header gives the payload ${header.payloadSize} bytes, not ${WIDGET_SIZE}`);
  }
  const read = cursor(payloadOf(data));
  const fixed = read.take(WIDGET_SIZE, "the settings of the widget");
  if (fixed[0] < 1 || fixed[0] > draw.WIDGETS.length) {
    throw new Rejection(UNKNOWN_WIDGET, `widget ${fixed[0]} is none this player has`);
  }
  if (fixed[1] !== 0) throw badSettings("the reserved byte is not 0");
  const seconds = u16(fixed, 2);
  if (seconds < 1 || seconds > draw.LONGEST_CLOCK) throw badSettings(`a loop of ${seconds} seconds is not 1 to ${draw.LONGEST_CLOCK}`);
  const speedMin = u16(fixed, 16);
  const speedMax = u16(fixed, 18);
  if (speedMin < 1 || speedMin > draw.FASTEST_CLOCK) throw badSettings(`the least speed is ${speedMin}, not 1 to ${draw.FASTEST_CLOCK}`);
  if (speedMax < speedMin || speedMax > draw.FASTEST_CLOCK) throw badSettings(`the greatest speed is ${speedMax}, not ${speedMin} to ${draw.FASTEST_CLOCK}`);
  if (read.left() !== 0) {
    throw new Rejection(TRAILING_BYTES, `${read.left()} bytes follow the settings`);
  }
  checkLoop(header, 1000 * seconds);
  const settings = {
    widget: draw.WIDGETS[fixed[0] - 1], seconds, face: colour(fixed, 4), hands: colour(fixed, 7), rim: colour(fixed, 10),
    background: colour(fixed, 13), speedMin, speedMax,
  };
  return {header, settings};
}

// A clock as the JSON source has it: `{width, height, widget, seconds, face, hands, rim,
// background, speedMin, speedMax}`.
export function loadsWidget(top) {
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

// The canonical JSON source of a clock.
export function dumpsWidget(widget) {
  const source = {
    version: SOURCE_VERSION, type: "widget", width: widget.width, height: widget.height, widget: widget.widget,
    seconds: widget.seconds, face: widget.face, hands: widget.hands, rim: widget.rim, background: widget.background,
    speed_min: widget.speedMin, speed_max: widget.speedMax,
  };
  return new TextEncoder().encode(`${JSON.stringify(source, null, 2)}\n`);
}

// A container of a clock, its loop `seconds` long.
export function encodeWidget(widget) {
  refuseLargeCanvas(widget.width, widget.height);
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

// The clock of a decoded container, as its JSON source has it.
export function widgetOf(decoded) {
  return {width: decoded.header.width, height: decoded.header.height, ...decoded.settings};
}
