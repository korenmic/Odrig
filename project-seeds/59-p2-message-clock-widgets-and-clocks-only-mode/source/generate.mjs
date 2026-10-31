// Compiles retained message sequences into bounded widget sources using authored fonts.
import fs from "node:fs";
import path from "node:path";
import {createHash} from "node:crypto";
import {pathToFileURL} from "node:url";
import {fontOf, glyphIndex, visualLines} from "../../../converter/lib/textlayout.js";
import * as messageclock from "../../../converter/lib/messageclock.js";

export const REFERENCE = new URL("../references/led_grid_simulator_v7_tabs_v4_no_blink.html", import.meta.url);
export const REFERENCE_SHA256 = "a84cec0bd28b5d608b0d36b4a6ceb32a48d310329639fd2453643d70416b358e";
export const NAMES = ["consciousness", "symmetry", "temperature", "the-time", "countdown", "the-clock", "mistakes"];
export const TEXT_SCALE = {x: 0.8, y: 8 / 9, pitch: 9, width: 58};
export const DIGIT_SCALE = {x: 0.6, y: 2 / 3};
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

// This pinned reference has a data-only array with single-quoted strings and four keys.
// Parse it as JSON; none of the supplied script is executed.
export function extract(bytes) {
  if (sha256(bytes) !== REFERENCE_SHA256) throw new Error("reference checksum differs");
  const html = new TextDecoder("utf-8", {fatal: true}).decode(bytes);
  const match = html.match(/const sequences=(\[[\s\S]*?\n\]);/);
  if (!match) throw new Error("reference sequence array missing");
  const json = match[1].replace(/'([^'\\]*)'/g, (_all, text) => JSON.stringify(text))
    .replace(/\b(name|lines|text|zero):/g, '"$1":').replace(/,\s*([\]}])/g, "$1");
  const sequences = JSON.parse(json);
  if (sequences.length !== 7 || sequences.some((entry) => typeof entry.name !== "string" || !Array.isArray(entry.lines))) {
    throw new Error("reference sequence shape differs");
  }
  const marker = (pattern) => {
    const found = html.match(pattern);
    if (!found) throw new Error("reference motion marker missing");
    return found[1];
  };
  const stop = marker(/if\(text==='([^']+)'\)stopAt=elapsed/);
  const freeze = marker(/if\(text==='([^']+)'\)pendulumFrozenX=lastPendulumX/);
  const boost = marker(/minuteRandom=Math\.random\(\) < \(sequences\[section\]\.lines\[index\]==='([^']+)'/);
  const countdown = marker(/name\.includes\('([^']+)'\)&&index<=10/);
  const zero = marker(/lc\.fillText\('([^']+)',30,split\?6:18\)/);
  return {zero, sequences: sequences.map((entry, tab) => ({
    tab: tab + 1, title: entry.name, file: `v7-${NAMES[tab]}.odrgx`,
    messages: entry.lines.map((line, index) => {
      const text = typeof line === "string" ? line : line.text;
      if (typeof text !== "string" || typeof line === "object" && line.zero !== true) throw new Error("reference caption shape differs");
      const flags = (entry.name.includes(countdown) && index <= 10 ? 1 : 0) |
        (typeof line === "object" && line.zero ? 2 : 0) |
        (text === stop ? 4 : 0) | (text === freeze ? 8 : 0) | (text === boost ? 16 : 0);
      return {text, flags, duration: flags & 1 ? 2000 : 6100};
    }),
  }))};
}

function rectangle(pixels, width, height, x, y, sx, sy) {
  for (let row = Math.max(0, Math.floor(y)); row < Math.min(height, Math.ceil(y + sy)); row += 1) {
    for (let column = Math.max(0, Math.floor(x)); column < Math.min(width, Math.ceil(x + sx)); column += 1) {
      const area = Math.max(0, Math.min(column + 1, x + sx) - Math.max(column, x)) *
        Math.max(0, Math.min(row + 1, y + sy) - Math.max(row, y));
      pixels[row * width + column] += area;
    }
  }
}

function glyph(pixels, width, height, font, code, left, top, sx, sy) {
  const index = glyphIndex(font.table, code);
  if (index < 0) throw new Error(`unsupported authored glyph ${code}`);
  for (let row = 0; row < font.rows; row += 1) {
    const bits = font.table.rows[index * font.rows + row];
    for (let column = 0; column < font.table.widths[index]; column += 1) {
      if (bits & (0x80 >> column)) rectangle(pixels, width, height,
        left + column * sx, top + row * sy, sx, sy);
    }
  }
}

function pack(pixels) {
  const bytes = new Uint8Array(pixels.length / 2);
  for (let index = 0; index < pixels.length; index += 1) {
    const value = Math.round(15 * Math.max(0, Math.min(1, pixels[index])));
    bytes[index >> 1] |= value << (index & 1 ? 0 : 4);
  }
  return bytes;
}

function text(pixels, caption, center) {
  const font = fontOf(1);
  const lines = visualLines(caption, {font: "small", wrap: true, direction: "rtl"}, Math.floor(TEXT_SCALE.width / TEXT_SCALE.x));
  if (lines.length > 2) throw new Error("caption exceeds the two-line source layout");
  lines.forEach((codes, line) => {
    const advance = (code) => font.table.widths[glyphIndex(font.table, code)] + 1;
    const width = codes.reduce((sum, code) => sum + advance(code), 0) - (codes.length ? 1 : 0);
    let x = (60 - width * TEXT_SCALE.x) / 2;
    const y = center + (line - (lines.length - 1) / 2) * TEXT_SCALE.pitch - font.rows * TEXT_SCALE.y / 2;
    for (const code of codes) {
      if (code !== 32) glyph(pixels, 60, 30, font, code, x, y, TEXT_SCALE.x, TEXT_SCALE.y);
      x += advance(code) * TEXT_SCALE.x;
    }
  });
}

export function captionMask(caption, zero) {
  const pixels = new Float64Array(60 * 30);
  if (caption.flags & 2) {
    text(pixels, zero, 6);
    text(pixels, caption.text, 19);
  } else text(pixels, caption.text, 15);
  return pack(pixels);
}

export function digitAtlas() {
  const font = fontOf(3);
  const sx = font.scale * DIGIT_SCALE.x, sy = font.scale * DIGIT_SCALE.y;
  const origins = [2, 9, 23, 30, 43, 50, 16, 36];
  const slots = [0, 1, 3, 4, 6, 7, 2, 5];
  const bytes = new Uint8Array(messageclock.GLYPH_BYTES);
  let at = 0;
  origins.forEach((origin, position) => {
    const center = (60 - 6.9 * 8) / 2 + (slots[position] + 0.5) * 6.9;
    for (let digit = 0; digit < (position < 6 ? 10 : 1); digit += 1) {
      const code = position < 6 ? 48 + digit : 58;
      const index = glyphIndex(font.table, code);
      const width = font.table.widths[index] * sx;
      const pixels = new Float64Array(8 * 16);
      glyph(pixels, 8, 16, font, code, center - origin - width / 2, (16 - font.rows * sy) / 2, sx, sy);
      bytes.set(pack(pixels), at);
      at += 64;
    }
  });
  if (at !== bytes.length) throw new Error("digit atlas size differs");
  return bytes;
}

export function compile(bytes = fs.readFileSync(REFERENCE)) {
  const reference = extract(bytes);
  const glyphs = digitAtlas();
  return reference.sequences.map((sequence) => {
    const messages = sequence.messages.map((caption) => ({...caption, mask: captionMask(caption, reference.zero)}));
    const settings = {widget: "message-clock", width: 60, height: 60, tab: sequence.tab,
      messages, glyphs, loopMs: messages.reduce((sum, caption) => sum + caption.duration, 0)};
    messageclock.encode(settings);
    return {...sequence, settings, source: messageclock.source(settings)};
  });
}

export function manifest(items) {
  return {version: 1, reference: "project-seeds/59-p2-message-clock-widgets-and-clocks-only-mode/references/led_grid_simulator_v7_tabs_v4_no_blink.html", referenceSha256: REFERENCE_SHA256,
    font: {source: "fonts/small.txt", sha256: sha256(fs.readFileSync(new URL("../../../fonts/small.txt", import.meta.url))),
      text: {name: "small", ...TEXT_SCALE}, digits: {name: "large", ...DIGIT_SCALE}},
    adaptation: "Existing authored fonts replace Arial/monospace; area-sampled alpha4 masks, fixed 9px text spacing, no unlit-dot or browser background decorations.",
    files: items.map((item) => ({file: item.file, title: item.title, tab: item.tab, loopMs: item.settings.loopMs,
      payloadBytes: messageclock.encode(item.settings).length,
      captions: item.messages.map((caption) => ({text: caption.text, flags: caption.flags, duration: caption.duration}))}))};
}

function main(argv) {
  if (argv.length !== 1) throw new Error("usage: node generate.mjs OUTPUT_FOLDER");
  const items = compile();
  fs.mkdirSync(argv[0], {recursive: true});
  for (const item of items) {
    fs.writeFileSync(path.join(argv[0], item.file.replace(/\.odrgx$/, ".json")), JSON.stringify(item.source, null, 2) + "\n", "utf8");
    process.stdout.write(`${item.file} ${item.messages.length} captions ${item.settings.loopMs} ms\n`);
  }
  fs.writeFileSync(path.join(argv[0], "manifest.json"), JSON.stringify(manifest(items), null, 2) + "\n", "utf8");
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main(process.argv.slice(2));
