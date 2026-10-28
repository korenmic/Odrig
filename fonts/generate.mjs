// Reads the fonts of this folder and writes the tables the core and the converter draw
// with: core/src/font_tables.cpp and converter/lib/fonttables.js, the fonts and the sine
// table of the clocks. Run from the repository root: node fonts/generate.mjs
// With --check it writes nothing and fails when either file is not what it would write.

import {readFileSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
export const SOURCES = ["small.txt", "medium.txt", "tiny.txt"];
export const CORE_FILE = join(ROOT, "core", "src", "font_tables.cpp");
export const CONVERTER_FILE = join(ROOT, "converter", "lib", "fonttables.js");

// The characters a font of texts has: the printable ASCII characters and the Hebrew
// letters, the final forms among them.
export const REPERTOIRE = [];
for (let code = 0x20; code <= 0x7e; code += 1) REPERTOIRE.push(code);
for (let code = 0x5d0; code <= 0x5ea; code += 1) REPERTOIRE.push(code);

// The characters of a font of digits, for the time of a picture display: the space, the
// ten digits and the colon.
export const DIGITS = [0x20];
for (let code = 0x30; code <= 0x3a; code += 1) DIGITS.push(code);

// The repertoires a font's header may name; a font that names none has REPERTOIRE.
export const REPERTOIRES = {text: REPERTOIRE, digits: DIGITS};

// The entries of the sine table, a whole turn, in units of 1/16,384.
export const SINE_ENTRIES = 1024;
export const SINE_ONE = 16384;
const HEADER = ["name", "id", "version", "ascent", "descent"];
const OPTIONAL = ["repertoire"];
const WIDEST = 8;

// A font of its source text: the header's numbers, and each glyph's code point, width and
// rows, every row a number whose bit 7 is the glyph's leftmost pixel.
export function readFont(text, file) {
  const header = {};
  const glyphs = [];
  let glyph = null;
  const lines = text.split("\n");
  const fail = (at, why) => {
    throw new Error(`${file}:${at + 1}: ${why}`);
  };
  lines.forEach((raw, at) => {
    const line = raw.replace(/\r$/, "");
    if (line === "" || line.startsWith(";")) {
      if (glyph !== null && line === "") glyph = null;
      return;
    }
    const words = line.split(" ");
    if ((HEADER.includes(words[0]) || OPTIONAL.includes(words[0])) && glyphs.length === 0 && glyph === null) {
      if (words.length !== 2 || words[0] in header) fail(at, `a bad header line: ${line}`);
      header[words[0]] = words[0] === "name" || words[0] === "repertoire" ? words[1] : Number(words[1]);
      return;
    }
    if (words[0] === "glyph") {
      const found = /^glyph U\+([0-9A-F]{4})$/.exec(line);
      if (!found) fail(at, `a bad glyph line: ${line}`);
      glyph = {code: parseInt(found[1], 16), width: 0, rows: [], line: at};
      glyphs.push(glyph);
      return;
    }
    if (glyph === null || !/^[#.]+$/.test(line)) fail(at, `a line that is no glyph row: ${line}`);
    if (glyph.rows.length === 0) glyph.width = line.length;
    if (line.length !== glyph.width) fail(at, "a row of another width than the glyph's first");
    let bits = 0;
    for (let column = 0; column < line.length; column += 1) {
      if (line[column] === "#") bits |= 0x80 >> column;
    }
    glyph.rows.push(bits);
  });
  for (const name of HEADER) {
    if (!(name in header)) throw new Error(`${file}: no ${name}`);
  }
  const height = header.ascent + header.descent;
  for (const one of glyphs) {
    if (one.rows.length !== height) fail(one.line, `U+${one.code.toString(16)} has ${one.rows.length} rows, not ${height}`);
    if (one.width < 1 || one.width > WIDEST) fail(one.line, `U+${one.code.toString(16)} is ${one.width} wide`);
  }
  const repertoire = REPERTOIRES[header.repertoire ?? "text"];
  if (repertoire === undefined) throw new Error(`${file}: no repertoire ${header.repertoire}`);
  delete header.repertoire;
  const codes = glyphs.map((one) => one.code);
  if (codes.join() !== repertoire.join()) {
    const missing = repertoire.filter((code) => !codes.includes(code)).map((code) => `U+${code.toString(16)}`);
    throw new Error(`${file}: the glyphs are not the repertoire in order; missing: ${missing.join(" ") || "none"}`);
  }
  return {...header, glyphs};
}

export function sineTable() {
  const table = [];
  for (let entry = 0; entry < SINE_ENTRIES; entry += 1) {
    table.push(Math.round(Math.sin((2 * Math.PI * entry) / SINE_ENTRIES) * SINE_ONE));
  }
  return table;
}

function rowsOf(numbers, perLine, format) {
  const lines = [];
  for (let at = 0; at < numbers.length; at += perLine) {
    lines.push("    " + numbers.slice(at, at + perLine).map(format).join(", ") + ",");
  }
  return lines.join("\n");
}

const hex = (value) => `0x${value.toString(16).padStart(2, "0")}`;
const decimal = (value) => String(value);

function coreText(fonts, sine) {
  const parts = [
    "// The tables of the fonts and the sine table, written by fonts/generate.mjs from the fonts",
    "// of the folder fonts/. Change the fonts and run it again; never this file.",
    "",
    '#include "fonts.h"',
    "",
    "namespace odrig {",
    "",
    "namespace {",
    "",
  ];
  for (const font of fonts) {
    const name = font.name[0].toUpperCase() + font.name.slice(1);
    parts.push(`const uint16_t k${name}Codes[${font.glyphs.length}] = {`);
    parts.push(rowsOf(font.glyphs.map((one) => one.code), 12, decimal));
    parts.push("};", "");
    parts.push(`const uint8_t k${name}Widths[${font.glyphs.length}] = {`);
    parts.push(rowsOf(font.glyphs.map((one) => one.width), 24, decimal));
    parts.push("};", "");
    const rows = font.glyphs.flatMap((one) => one.rows);
    parts.push(`const uint8_t k${name}Rows[${rows.length}] = {`);
    parts.push(rowsOf(rows, font.ascent + font.descent, hex));
    parts.push("};", "");
  }
  parts.push("const FontTable kTables[] = {");
  for (const font of fonts) {
    const name = font.name[0].toUpperCase() + font.name.slice(1);
    parts.push(`    {${font.id}, ${font.version}, ${font.ascent}, ${font.descent}, ${font.glyphs.length}, k${name}Codes, k${name}Widths, k${name}Rows},`);
  }
  parts.push("};", "", "}  // namespace", "");
  parts.push(`const int16_t kSine[${sine.length}] = {`);
  parts.push(rowsOf(sine, 16, decimal));
  parts.push("};", "");
  parts.push("const FontTable *font_table(uint8_t id) {");
  parts.push("    for (const FontTable &table : kTables) {");
  parts.push("        if (table.id == id) {");
  parts.push("            return &table;");
  parts.push("        }");
  parts.push("    }");
  parts.push("    return nullptr;");
  parts.push("}", "", "}  // namespace odrig", "");
  return parts.join("\n");
}

function converterText(fonts, sine) {
  const parts = [
    "// The tables of the fonts and the sine table, written by fonts/generate.mjs from the fonts",
    "// of the folder fonts/. Change the fonts and run it again; never this file.",
    "",
    "export const FONT_TABLES = {",
  ];
  for (const font of fonts) {
    parts.push(`  ${font.id}: {`);
    parts.push(`    name: ${JSON.stringify(font.name)}, id: ${font.id}, version: ${font.version}, ascent: ${font.ascent}, descent: ${font.descent},`);
    parts.push("    codes: [");
    parts.push(rowsOf(font.glyphs.map((one) => one.code), 12, decimal).replace(/^ {4}/gm, "      "));
    parts.push("    ],");
    parts.push("    widths: [");
    parts.push(rowsOf(font.glyphs.map((one) => one.width), 24, decimal).replace(/^ {4}/gm, "      "));
    parts.push("    ],");
    parts.push("    rows: [");
    parts.push(rowsOf(font.glyphs.flatMap((one) => one.rows), font.ascent + font.descent, hex).replace(/^ {4}/gm, "      "));
    parts.push("    ],");
    parts.push("  },");
  }
  parts.push("};", "");
  parts.push("export const SINE = [");
  parts.push(rowsOf(sine, 16, decimal).replace(/^ {4}/gm, "  "));
  parts.push("];", "");
  return parts.join("\n");
}

// The two files, as the fonts of the folder give them.
export function generate(read = (name) => readFileSync(join(HERE, name), "utf8")) {
  const fonts = SOURCES.map((name) => readFont(read(name), name));
  const sine = sineTable();
  return {core: coreText(fonts, sine), converter: converterText(fonts, sine), fonts};
}

function main(argv) {
  const made = generate();
  const files = [[CORE_FILE, made.core], [CONVERTER_FILE, made.converter]];
  if (argv.includes("--check")) {
    const stale = files.filter(([path, text]) => readFileSync(path, "utf8") !== text).map(([path]) => path);
    if (stale.length !== 0) {
      console.error(`not what fonts/ gives: ${stale.join(", ")}`);
      process.exitCode = 1;
    }
    return;
  }
  for (const [path, text] of files) writeFileSync(path, text);
  for (const font of made.fonts) {
    const rows = font.glyphs.length * (font.ascent + font.descent);
    console.log(`${font.name}: ${font.glyphs.length} glyphs, ${rows + font.glyphs.length * 3} bytes of tables`);
  }
  console.log(`sine: ${SINE_ENTRIES} entries, ${SINE_ENTRIES * 2} bytes`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2));
}
