// The layout of a text: its characters checked, put in order by the bidirectional algorithm,
// broken into lines, and placed as glyphs of a font in a block, as docs/format.md has it.
// The player draws the block it is given; it lays out nothing itself.

import * as bidi from "./bidi.js";
import {Rejection, UNSUPPORTED_CHARACTER} from "./errors.js";
import {FONT_TABLES} from "./fonttables.js";

export const LONGEST_TEXT = 512;
export const MOST_GLYPHS = 512;
const LINE_FEED = 0x0a;
const SPACE = 0x20;

// The fonts a text may name: each draws with a table of glyphs, at a scale.
export const FONTS = {
  small: {id: 1, table: 1, scale: 1},
  medium: {id: 2, table: 2, scale: 1},
  large: {id: 3, table: 1, scale: 2},
};
export const FONT_NAMES = {1: "small", 2: "medium", 3: "large"};

// A font by its id: its table, its scale, its version, the rows of a glyph's cell and the
// distance between lines, both before the scale, or null for an id that is no font.
export function fontOf(id) {
  const name = FONT_NAMES[id];
  if (name === undefined) return null;
  const {table, scale} = FONTS[name];
  const glyphs = FONT_TABLES[table];
  const rows = glyphs.ascent + glyphs.descent;
  return {id, name, table: glyphs, scale, version: glyphs.version, rows, pitch: rows + 1};
}

// The place of a character in a font's table, or -1 when the font has no glyph for it.
export function glyphIndex(table, code) {
  let low = 0;
  let high = table.codes.length - 1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (table.codes[middle] === code) return middle;
    if (table.codes[middle] < code) low = middle + 1;
    else high = middle - 1;
  }
  return -1;
}

// The characters of a text that no font has, each once, in the order in which they come:
// `{character, code}`. A line feed is no glyph but begins a paragraph.
export function unsupported(text) {
  const found = [];
  const table = FONT_TABLES[1];
  for (const character of text) {
    const code = character.codePointAt(0);
    if (code !== LINE_FEED && glyphIndex(table, code) === -1 && !found.some((one) => one.code === code)) {
      found.push({character, code});
    }
  }
  return found;
}

// U+XXXX of a code point.
export function codePoint(code) {
  return `U+${code.toString(16).toUpperCase().padStart(4, "0")}`;
}

// Refuses a text with a character that no font has, naming every such character.
export function checkCharacters(text) {
  const missing = unsupported(text);
  if (missing.length !== 0) {
    const named = missing.map(({character, code}) => `${JSON.stringify(character)} (${codePoint(code)})`).join(", ");
    throw new Rejection(UNSUPPORTED_CHARACTER, `the text holds characters no font has: ${named}`);
  }
}

// The columns a character takes before the next, its spacing included, at the scale.
function advance(font, code) {
  return (font.table.widths[glyphIndex(font.table, code)] + 1) * font.scale;
}

// The width of a row of characters: their advances less the spacing after the last.
function widthOf(font, codes) {
  if (codes.length === 0) return 0;
  return codes.reduce((sum, code) => sum + advance(font, code), 0) - font.scale;
}

// A paragraph's characters without the spaces at their end.
function trimmed(codes) {
  let end = codes.length;
  while (end > 0 && codes[end - 1] === SPACE) end -= 1;
  return end;
}

// The lines of a paragraph, each as the range of its characters `[start, end)`, with the
// spaces at its end left out. With wrapping, a line is no wider than `room`: it breaks after
// spaces, and a word wider than `room` between its characters.
function breakLines(font, codes, wrap, room) {
  if (!wrap) return [[0, trimmed(codes)]];
  const lines = [];
  let start = 0;
  do {
    let end = start;
    // Where the line may end: after the last run of spaces that follows a character of it.
    let lastBreak = -1;
    let seen = false;
    while (end < codes.length) {
      if (codes[end] === SPACE) {
        end += 1;
        if (seen) lastBreak = end;
        continue;
      }
      if (seen && widthOf(font, codes.slice(start, end + 1)) > room) break;
      seen = true;
      end += 1;
    }
    if (end >= codes.length) {
      lines.push([start, start + trimmed(codes.slice(start))]);
      break;
    }
    const cut = lastBreak > start ? lastBreak : end;
    lines.push([start, start + trimmed(codes.slice(start, cut))]);
    start = cut;
  } while (start < codes.length);
  return lines;
}

// The lines of a text as they are shown: for each, the code points of its characters from
// left to right, a bracket in a right-to-left run as its mirror. `settings` gives `font`,
// `wrap` and `direction`; `room` is the width of the canvas, within which wrapped lines
// stay.
export function visualLines(text, settings, room) {
  checkCharacters(text);
  const font = fontOf(FONTS[settings.font].id);
  const paragraphs = text.split("\n").map((part) => Array.from(part, (character) => character.codePointAt(0)));
  const lines = [];
  for (const codes of paragraphs) {
    const level = bidi.paragraphLevel(codes, settings.direction);
    const resolved = bidi.levels(codes, level);
    for (const [start, end] of breakLines(font, codes, settings.wrap, room)) {
      const lineCodes = codes.slice(start, end);
      const order = bidi.visualOrder(lineCodes, resolved.slice(start, end), level);
      lines.push(order.map((at) => {
        const code = lineCodes[at];
        return resolved[start + at] % 2 === 1 && code in bidi.MIRRORED ? bidi.MIRRORED[code] : code;
      }));
    }
  }
  return lines;
}

// The layout of a text: `{glyphs, width, height, lines}`. A glyph is `{glyph, x, y}`: its
// place in the font's table and the top left corner of its cell in the block, y growing
// downwards. `settings` gives `font`, `wrap`, `direction` and `align`; `room` is the width of
// the canvas, within which wrapped lines stay.
export function layout(text, settings, room) {
  const font = fontOf(FONTS[settings.font].id);
  const placedLines = visualLines(text, settings, room);
  const widths = placedLines.map((codes) => widthOf(font, codes));
  const width = Math.max(1, ...widths);
  const glyphs = [];
  placedLines.forEach((codes, line) => {
    const free = width - widths[line];
    let x = settings.align === "center" ? Math.floor(free / 2) : settings.align === "right" ? free : 0;
    const y = line * font.pitch * font.scale;
    for (const code of codes) {
      if (code !== SPACE) glyphs.push({glyph: glyphIndex(font.table, code), x, y});
      x += advance(font, code);
    }
  });
  const height = placedLines.length * font.pitch * font.scale - font.scale;
  return {glyphs, width, height, lines: placedLines.length};
}
