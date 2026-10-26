import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import {fonttables} from "../lib/index.js";
import {ROOT} from "./support.js";

const generator = await import(pathToFileURL(path.join(ROOT, "fonts", "generate.mjs")).href);

// A font's source with one glyph's rows put in the place of what it had.
function withGlyph(text, code, rows) {
  const at = text.indexOf(`glyph U+${code}\n`);
  const end = text.indexOf("\n\n", at);
  return text.slice(0, at) + `glyph U+${code}\n${rows.join("\n")}` + (end === -1 ? "\n" : text.slice(end));
}

const SMALL = fs.readFileSync(path.join(ROOT, "fonts", "small.txt"), "utf8");

test("the tables are what the fonts give", async (t) => {
  const made = generator.generate();

  await t.test("the core's tables", () => {
    assert.equal(fs.readFileSync(generator.CORE_FILE, "utf8"), made.core, "run node fonts/generate.mjs");
  });

  await t.test("the converter's tables", () => {
    assert.equal(fs.readFileSync(generator.CONVERTER_FILE, "utf8"), made.converter, "run node fonts/generate.mjs");
  });
});

test("every font has every character of the repertoire", () => {
  assert.equal(generator.REPERTOIRE.length, 95 + 27);
  for (const table of Object.values(fonttables.FONT_TABLES)) {
    assert.deepEqual(table.codes, generator.REPERTOIRE, table.name);
    assert.equal(table.widths.length, table.codes.length);
    assert.equal(table.rows.length, table.codes.length * (table.ascent + table.descent));
    for (const width of table.widths) {
      assert.ok(width >= 1 && width <= 8, `${table.name}: a glyph ${width} wide`);
    }
  }
  assert.deepEqual(Object.keys(fonttables.FONT_TABLES), ["1", "2"]);
  const small = fonttables.FONT_TABLES[1];
  const medium = fonttables.FONT_TABLES[2];
  assert.deepEqual([small.name, small.ascent, small.descent], ["small", 7, 2]);
  assert.deepEqual([medium.name, medium.ascent, medium.descent], ["medium", 10, 3]);
});

test("no pixel of a glyph lies outside its width, and only the space is dark", () => {
  for (const table of Object.values(fonttables.FONT_TABLES)) {
    const height = table.ascent + table.descent;
    table.codes.forEach((code, index) => {
      const rows = table.rows.slice(index * height, (index + 1) * height);
      const outside = rows.reduce((all, row) => all | (row & (0xff >> table.widths[index])), 0);
      assert.equal(outside, 0, `${table.name} U+${code.toString(16)}`);
      assert.equal(rows.some((row) => row !== 0), code !== 0x20, `${table.name} U+${code.toString(16)}`);
    });
  }
});

test("the final forms and the qof reach below the baseline, and no other Hebrew letter does", () => {
  const below = [0x5da, 0x5df, 0x5e3, 0x5e5, 0x5e7];
  for (const table of Object.values(fonttables.FONT_TABLES)) {
    const height = table.ascent + table.descent;
    for (let code = 0x5d0; code <= 0x5ea; code += 1) {
      const index = table.codes.indexOf(code);
      const rows = table.rows.slice(index * height + table.ascent, (index + 1) * height);
      assert.equal(rows.some((row) => row !== 0), below.includes(code), `${table.name} U+${code.toString(16)}`);
    }
  }
});

test("the sine table is a whole turn in units of 1/16,384", () => {
  const sine = fonttables.SINE;
  assert.equal(sine.length, 1024);
  assert.deepEqual([sine[0], sine[256], sine[512], sine[768]], [0, 16384, 0, -16384]);
  for (let entry = 0; entry < 256; entry += 1) {
    assert.equal(sine[entry], sine[512 - entry]);
    assert.equal(sine[entry] + sine[512 + entry], 0);
  }
});

test("a font that breaks the rules is refused, with its place", async (t) => {
  await t.test("a row of another width", () => {
    const text = withGlyph(SMALL, "0041", [".###.", "#...#", "#...#", "#####", "#...#", "#...", "#...#", ".....", "....."]);
    assert.throws(() => generator.readFont(text, "small.txt"), /small\.txt:\d+: a row of another width/);
  });

  await t.test("too few rows", () => {
    const text = withGlyph(SMALL, "0041", [".###.", "#...#"]);
    assert.throws(() => generator.readFont(text, "small.txt"), /U\+41 has 2 rows, not 9/);
  });

  await t.test("a glyph missing", () => {
    const at = SMALL.indexOf("glyph U+05E7\n");
    const text = SMALL.slice(0, at) + SMALL.slice(SMALL.indexOf("glyph U+05E8\n"));
    assert.throws(() => generator.readFont(text, "small.txt"), /missing: U\+5e7/);
  });

  await t.test("a character outside the rows", () => {
    const text = withGlyph(SMALL, "0041", [".###.", "#...#", "#...#", "#####", "#.x.#", "#...#", "#...#", ".....", "....."]);
    assert.throws(() => generator.readFont(text, "small.txt"), /a line that is no glyph row: #\.x\.#/);
  });
});
