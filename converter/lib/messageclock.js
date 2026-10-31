// Bounded message-clock payloads and deterministic procedural pixels.
import {SINE} from "./fonttables.js";
import * as strictjson from "./strictjson.js";
import {Rejection, BAD_SETTINGS, BAD_TEXT, TRUNCATED, PAYLOAD_SIZE, TRAILING_BYTES, LOOP_MISMATCH} from "./errors.js";

export const MASK_BYTES = 900;
export const GLYPH_BYTES = 3968;
const TOP = ["version", "type", "width", "height", "widget", "tab", "messages", "glyphs"];
const CAPTION = ["text", "flags", "mask"];
const bad = (why) => { throw new Rejection(BAD_SETTINGS, why); };
const u16 = (p, a) => p[a] | p[a + 1] << 8;
const u32 = (p, a) => (p[a] | p[a + 1] << 8 | p[a + 2] << 16 | p[a + 3] << 24) >>> 0;
const hex = (p) => Array.from(p, (b) => b.toString(16).padStart(2, "0")).join("");
function unhex(text, count) {
  if (typeof text !== "string" || text.length !== count * 2 || !/^[0-9a-f]+$/.test(text)) bad("invalid mask bytes");
  return Uint8Array.from(text.match(/../g), (b) => parseInt(b, 16));
}
export function load(top) {
  strictjson.members(top, TOP);
  if (Number(strictjson.integer(top.get("width"), 60, 60, "width")) !== 60 ||
      Number(strictjson.integer(top.get("height"), 60, 60, "height")) !== 60) bad("message-clock canvas");
  const tab = Number(strictjson.integer(top.get("tab"), 1, 7, "tab"));
  const rows = top.get("messages");
  if (!Array.isArray(rows) || rows.length < 1 || rows.length > 24) bad("caption count");
  const messages = rows.map((row) => {
    strictjson.members(row, CAPTION);
    const text = row.get("text");
    if (typeof text !== "string") bad("caption text");
    if ([...text].some((c) => c.codePointAt(0) >= 0xd800 && c.codePointAt(0) <= 0xdfff)) throw new Rejection(BAD_TEXT, "caption surrogate");
    const flags = Number(strictjson.integer(row.get("flags"), 0, 31, "flags"));
    return {text, flags, mask: unhex(row.get("mask"), MASK_BYTES), duration: flags & 1 ? 2000 : 6100};
  });
  return {widget: "message-clock", width: 60, height: 60, tab, messages,
    loopMs: messages.reduce((n, m) => n + m.duration, 0), glyphs: unhex(top.get("glyphs"), GLYPH_BYTES)};
}
export function source(settings) {
  return {version: 1, type: "widget", width: 60, height: 60, widget: "message-clock", tab: settings.tab,
    messages: settings.messages.map((m) => ({text: m.text, flags: m.flags, mask: hex(m.mask)})), glyphs: hex(settings.glyphs)};
}
export function encode(settings) {
  const texts = settings.messages.map((m) => new TextEncoder().encode(m.text));
  const count = texts.length;
  const textSize = texts.reduce((n, p) => n + p.length, 0);
  const masks = 24 + count * 12 + textSize, glyphs = masks + count * MASK_BYTES;
  const p = new Uint8Array(glyphs + GLYPH_BYTES), v = new DataView(p.buffer);
  p.set([6, 1, settings.tab, count]);
  v.setUint32(4, settings.loopMs, true); v.setUint16(8, textSize, true);
  v.setUint32(12, masks, true); v.setUint32(16, glyphs, true); v.setUint32(20, p.length, true);
  let offset = 0;
  settings.messages.forEach((m, i) => {
    const at = 24 + i * 12;
    v.setUint32(at, m.flags & 1 ? 2000 : 6100, true); p[at + 4] = m.flags;
    v.setUint16(at + 6, offset, true); v.setUint16(at + 8, texts[i].length, true);
    p.set(texts[i], 24 + count * 12 + offset); offset += texts[i].length;
    p.set(m.mask, masks + i * MASK_BYTES);
  });
  p.set(settings.glyphs, glyphs);
  decode(p, {width: 60, height: 60, payloadSize: p.length, loopMs: settings.loopMs});
  return p;
}
export function decode(p, header) {
  const take = (at, n) => {
    if (at + n > p.length) throw new Rejection(TRUNCATED, "message-clock ended early");
    return p.subarray(at, at + n);
  };
  if (header.width !== 60 || header.height !== 60) bad("message-clock canvas");
  take(0, 24);
  const tab = p[2], count = p[3], loopMs = u32(p, 4), textSize = u16(p, 8);
  if (p[0] !== 6 || p[1] !== 1 || tab < 1 || tab > 7 || count < 1 || count > 24 || u16(p, 10) || textSize < 1 || textSize > 4096) bad("message-clock header");
  const masks = 24 + count * 12 + textSize, glyphs = masks + count * MASK_BYTES, total = glyphs + GLYPH_BYTES;
  if (u32(p, 12) !== masks || u32(p, 16) !== glyphs) bad("message-clock offsets");
  if (u32(p, 20) !== total || header.payloadSize !== total || total > 32768) throw new Rejection(PAYLOAD_SIZE, "message-clock size");
  let offset = 0, elapsed = 0, stops = 0, freezes = 0;
  const messages = [];
  for (let i = 0; i < count; ++i) {
    const at = 24 + 12 * i; take(at, 12);
    const duration = u32(p, at), flags = p[at + 4], size = u16(p, at + 8);
    if (p[at + 5] || u16(p, at + 10) || flags & ~31 || (flags & 3) === 3 ||
        (flags & 3) && tab !== 5 || (flags & 4) && tab !== 1 || (flags & 24) && tab !== 6 ||
        size < 1 || size > 256 || u16(p, at + 6) !== offset || duration !== (flags & 1 ? 2000 : 6100)) bad("message-clock caption");
    if ((flags & 4) && ++stops > 1 || (flags & 8) && ++freezes > 1) bad("duplicate stop");
    messages.push({duration, flags, offset, size}); offset += size; elapsed += duration;
  }
  if (offset !== textSize) bad("message-clock text lengths");
  messages.forEach((m, i) => {
    let text;
    try { text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(take(24 + count * 12 + m.offset, m.size)); }
    catch (error) { if (error instanceof Rejection) throw error; throw new Rejection(BAD_TEXT, "caption UTF-8"); }
    if (/[\x00-\x1f\x7f-\x9f]/.test(text)) throw new Rejection(BAD_TEXT, "caption control");
    delete m.offset; delete m.size; m.text = text; m.mask = take(masks + i * MASK_BYTES, MASK_BYTES);
  });
  const atlas = take(glyphs, GLYPH_BYTES);
  if (p.length > total) throw new Rejection(TRAILING_BYTES, "bytes follow message-clock");
  if (loopMs !== elapsed || header.loopMs !== loopMs) throw new Rejection(LOOP_MISMATCH, "message-clock loop");
  return {widget: "message-clock", width: 60, height: 60, tab, loopMs, seconds: loopMs / 1000, messages, glyphs: atlas};
}

function random(x) { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; return x >>> 0; }
function motion(t, stop) {
  if (stop < 0 || t < stop) return t;
  const u = Math.min(t - stop, 3500);
  return stop + u - Math.floor(u ** 3 / 12250000) + Math.floor(u ** 4 / 85750000000);
}
function cosine(t) {
  const angle = Math.floor(t * 67108864 / 4000) + 16777216;
  const i = Math.floor(angle / 65536) % 1024, part = angle % 65536;
  return SINE[i] + Math.floor((SINE[(i + 1) % 1024] - SINE[i]) * part / 65536);
}
const square = (t) => Math.floor((60 * 16384 + 53 * cosine(t)) / 32768);
const alpha = (p, index) => index & 1 ? (p[index >> 1] & 15) * 17 : (p[index >> 1] >> 4) * 17;
function glyph(atlas, glyph, x, rowQ) {
  if (x < 0 || x >= 8) return 0;
  const y = Math.floor(rowQ / 256), f = rowQ - y * 256;
  const one = (row) => row < 0 || row >= 16 ? 0 : alpha(atlas, glyph * 128 + row * 8 + x);
  return Math.floor((one(y) * (256 - f) + one(y + 1) * f) / 256);
}
export function draw(settings, seed, elapsed, picture) {
  const t = elapsed % settings.loopMs, rows = settings.messages;
  let at = 0, chosen = 0, stop = -1, freeze = -1;
  for (let i = 0; i < rows.length; ++i) {
    if (rows[i].flags & 4) stop = at;
    if (rows[i].flags & 8) freeze = at;
    if (t >= at) chosen = i;
    at += rows[i].duration;
  }
  const m = motion(t, stop);
  let r = random(seed >>> 0 || 1), start = r % 86400;
  const digits = [Math.floor(start / 36000), Math.floor(start / 3600) % 10, Math.floor(start / 600) % 6,
    Math.floor(start / 60) % 10, Math.floor(start / 10) % 6, start % 10];
  const from = digits.slice(), rolls = Array(6).fill(-10000);
  const roll = (i, direction, when) => { from[i] = digits[i]; digits[i] = (digits[i] + direction + 10) % 10; rolls[i] = when; };
  for (let when = 2000; when <= m; when += 2000) {
    let boost = false, mark = 0;
    for (const row of rows) { if (when >= mark && when < mark + row.duration) boost = Boolean(row.flags & 16); mark += row.duration; }
    roll(5, 1, when); if (digits[5] === 0) roll(4, 1, when);
    r = random(r); const minute = r * 100 < (boost ? 48 : 14) * 4294967296;
    r = random(r); const hour = r * 1000 < (boost ? 250 : 45) * 4294967296;
    if (minute) { r = random(r); const d = r < 2147483648 ? -1 : 1; roll(3, d, when); if (digits[3] === (d > 0 ? 0 : 9)) roll(2, d, when); }
    if (hour) { r = random(r); const d = r < 2147483648 ? -1 : 1; roll(1, d, when); if (digits[1] === (d > 0 ? 0 : 9)) roll(0, d, when); }
  }
  const centre = square(freeze >= 0 && t >= freeze ? motion(freeze, stop) : m);
  const row = rows[chosen], phase = t - rows.slice(0, chosen).reduce((sum, item) => sum + item.duration, 0);
  const numerator = row.flags & 1 ? 1 : phase < 600 ? phase : phase < 5600 ? 1 : 6100 - phase;
  const denominator = row.flags & 1 ? 1 : phase < 600 ? 600 : phase < 5600 ? 1 : 500;
  const origins = [2, 9, 23, 30, 43, 50, 16, 36];
  picture.fill(0);
  for (let y = 0; y < 60; ++y) for (let x = 0; x < 60; ++x) {
    let value = 0, blue = false;
    if (y < 30) {
      value = Math.floor(alpha(row.mask, y * 60 + x) * numerator / denominator);
      const wave = t % 9000;
      blue = wave < 1500 && value >= 8 && Math.abs(x * 150000 - (135 * wave - 22500) * 60) < 630000;
      if (value < 4) value = 0;
    } else if (y >= 34 && y < 50) {
      for (let slot = 0; slot < 8; ++slot) {
        const xx = x - origins[slot];
        let a;
        if (slot >= 6) a = glyph(settings.glyphs, 60 + slot - 6, xx, (y - 34) * 256);
        else {
          const age = m - rolls[slot], q = (y - 34) * 256;
          if (age < 500 && !(stop >= 0 && t >= stop + 3500)) {
            const shift = Math.floor(4096 * age * age * (1500 - 2 * age) / 125000000);
            a = glyph(settings.glyphs, slot * 10 + from[slot], xx, q + shift) + glyph(settings.glyphs, slot * 10 + digits[slot], xx, q + shift - 4096);
          } else a = glyph(settings.glyphs, slot * 10 + digits[slot], xx, q);
        }
        value = Math.min(255, value + a - Math.floor(value * a / 255));
      }
    } else if (y >= 57 && Math.abs(x - centre) <= 1) value = 255;
    const p = 3 * ((59 - y) * 60 + x);
    picture[p] = blue ? Math.floor(value * 90 / 255) : value;
    picture[p + 1] = blue ? Math.floor(value * 205 / 255) : value;
    picture[p + 2] = value;
  }
  return picture;
}
