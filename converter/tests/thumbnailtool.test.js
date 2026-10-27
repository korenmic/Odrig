import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {thumbnail} from "../lib/index.js";
import {ROOT, runJs, temporary} from "./support.js";

const ANIMATIONS = path.join(ROOT, "test-animations");
const LINES = path.join(ANIMATIONS, "lines-test.odrg");
const RAINBOW = path.join(ANIMATIONS, "rainbow-lines-01.odrg");
const BROKEN = path.join(ROOT, "tests", "vectors", "invalid", "bad-magic.odrg");

function bytes(file) {
  return new Uint8Array(fs.readFileSync(file));
}

function keyOf(file) {
  return thumbnail.keyOf(bytes(file));
}

function line(key, names) {
  return `  "${key}": {"gif": "${key}.gif", "names": [${names.map((name) => `"${name}"`).join(", ")}]},`;
}

function catalog(...lines) {
  return ["export default {", ...lines, "};", ""].join("\n");
}

function copy(file, to) {
  fs.mkdirSync(path.dirname(to), {recursive: true});
  fs.copyFileSync(file, to);
  return to;
}

test("--out writes the preview of one file and nothing else", (t) => {
  const folder = temporary(t);
  const out = path.join(folder, "lines.gif");
  assert.deepEqual(runJs(["thumbnail", LINES, "--out", out]), {status: 0, out: "", err: ""});
  assert.deepEqual(bytes(out), thumbnail.make(bytes(LINES)));
  assert.deepEqual(fs.readdirSync(folder), ["lines.gif"]);
});

test("--out with a refused file ends with 1 and its reason, and writes nothing", (t) => {
  const folder = temporary(t);
  const out = path.join(folder, "broken.gif");
  const done = runJs(["thumbnail", BROKEN, "--out", out]);
  assert.equal(done.status, 1);
  assert.equal(done.out, "");
  assert.match(done.err, /^error: bad-magic: .*bad-magic\.odrg: the file starts with 4f 44 52 48, not 4f 44 52 47\n$/);
  assert.deepEqual(fs.readdirSync(folder), []);
  const missing = runJs(["thumbnail", path.join(folder, "none.odrg"), "--out", out]);
  assert.equal(missing.status, 1);
  assert.match(missing.err, /^error: not-found: /);
});

test("--catalog makes the folder and writes a GIF and a line for each key, in the order of the keys' bytes", (t) => {
  const folder = path.join(temporary(t), "made", "thumbnails");
  assert.deepEqual(runJs(["thumbnail", RAINBOW, LINES, "--catalog", folder]), {status: 0, out: "", err: ""});
  const keys = [keyOf(LINES), keyOf(RAINBOW)].sort();
  const names = {[keyOf(LINES)]: "lines-test.odrg", [keyOf(RAINBOW)]: "rainbow-lines-01.odrg"};
  assert.equal(fs.readFileSync(path.join(folder, "catalog.js"), "utf8"), catalog(...keys.map((key) => line(key, [names[key]]))));
  assert.deepEqual(fs.readdirSync(folder).sort(), ["catalog.js", ...keys.map((key) => `${key}.gif`)].sort());
  assert.deepEqual(bytes(path.join(folder, `${keyOf(LINES)}.gif`)), thumbnail.make(bytes(LINES)));
});

test("a key the catalog holds keeps its GIF and gains the name, the names in the order of their bytes", (t) => {
  const work = temporary(t);
  const folder = path.join(work, "thumbnails");
  assert.equal(runJs(["thumbnail", LINES, "--catalog", folder]).status, 0);
  const gif = path.join(folder, `${keyOf(LINES)}.gif`);
  fs.writeFileSync(gif, "kept");
  const upper = copy(LINES, path.join(work, "B.odrg"));
  const lower = copy(LINES, path.join(work, "a.odrg"));
  assert.deepEqual(runJs(["thumbnail", lower, upper, LINES, "--catalog", folder]), {status: 0, out: "", err: ""});
  assert.equal(fs.readFileSync(gif, "utf8"), "kept");
  assert.equal(fs.readFileSync(path.join(folder, "catalog.js"), "utf8"), catalog(line(keyOf(LINES), ["B.odrg", "a.odrg", "lines-test.odrg"])));
  // A GIF that is gone is made again.
  fs.rmSync(gif);
  assert.equal(runJs(["thumbnail", LINES, "--catalog", folder]).status, 0);
  assert.deepEqual(bytes(gif), thumbnail.make(bytes(LINES)));
});

test("a name outside printable ASCII is written with \\u, and one with a quote as JSON writes it", (t) => {
  const work = temporary(t);
  const folder = path.join(work, "thumbnails");
  const accented = copy(LINES, path.join(work, "été ש.odrg"));
  const quoted = copy(LINES, path.join(work, 'a"b.odrg'));
  assert.equal(runJs(["thumbnail", accented, quoted, "--catalog", folder]).status, 0);
  const text = fs.readFileSync(path.join(folder, "catalog.js"), "utf8");
  assert.equal(text, catalog(`  "${keyOf(LINES)}": {"gif": "${keyOf(LINES)}.gif", "names": ["a\\"b.odrg", "\\u00e9t\\u00e9 \\u05e9.odrg"]},`));
  assert.ok([...text].every((character) => character.charCodeAt(0) < 128));
});

test("a file inside the folder --card names is named by its path from it, any other by its own name", (t) => {
  const work = temporary(t);
  const card = path.join(work, "card", "odrig");
  const deep = copy(LINES, path.join(card, "night", "deep", "comet.odrg"));
  const loose = copy(RAINBOW, path.join(card, "loose.odrg"));
  const outside = copy(BROKEN.replace("bad-magic.odrg", "bad-magic.odrg"), path.join(work, "elsewhere", "x.odrg"));
  fs.copyFileSync(path.join(ANIMATIONS, "rainbow-lines-02.odrg"), outside);
  const folder = path.join(work, "thumbnails");
  const done = runJs(["thumbnail", deep, loose, outside, "--catalog", folder, "--card", path.relative(ROOT, card)]);
  assert.deepEqual(done, {status: 0, out: "", err: ""});
  const text = fs.readFileSync(path.join(folder, "catalog.js"), "utf8");
  assert.ok(text.includes(`"names": ["night/deep/comet.odrg"]`), text);
  assert.ok(text.includes(`"names": ["loose.odrg"]`), text);
  assert.ok(text.includes(`"names": ["x.odrg"]`), text);
  assert.ok(!text.includes(work) && !text.includes("card/"), text);
});

test("a refused file is passed over with its line, and the run ends with 0", (t) => {
  const work = temporary(t);
  const folder = path.join(work, "thumbnails");
  const missing = path.join(work, "none.odrg");
  const done = runJs(["thumbnail", BROKEN, LINES, missing, "--catalog", folder]);
  assert.equal(done.status, 0);
  assert.equal(done.out, "");
  const lines = done.err.split("\n");
  assert.equal(lines.length, 3);
  assert.equal(lines[0], `passed over: ${BROKEN}: bad-magic: the file starts with 4f 44 52 48, not 4f 44 52 47`);
  assert.match(lines[1], new RegExp(`^passed over: ${missing.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}: not-found: `));
  assert.equal(lines[2], "");
  assert.equal(fs.readFileSync(path.join(folder, "catalog.js"), "utf8"), catalog(line(keyOf(LINES), ["lines-test.odrg"])));
});

test("a catalog.js of another shape is a fault of the folder: status 70", (t) => {
  const folder = path.join(temporary(t), "thumbnails");
  fs.mkdirSync(folder);
  for (const text of ["export default {};\n", catalog('  "1a2b3c4d-1": {"gif": "other.gif", "names": []},'), "nothing\n"]) {
    fs.writeFileSync(path.join(folder, "catalog.js"), text);
    const done = runJs(["thumbnail", LINES, "--catalog", folder]);
    assert.equal(done.status, 70, text);
    assert.match(done.err, /preview catalog/);
  }
});

test("the command line wants one of the two forms", () => {
  for (const argv of [["thumbnail", LINES], ["thumbnail", LINES, "--out", "a.gif", "--catalog", "x"], ["thumbnail", LINES, RAINBOW, "--out", "a.gif"],
    ["thumbnail", LINES, "--out", "a.gif", "--card", "x"], ["thumbnail", "--catalog", "x"], ["thumbnail", LINES, "--catalog"], ["thumbnail", LINES, "--bogus", "--catalog", "x"]]) {
    const done = runJs(argv);
    assert.equal(done.status, 2, argv.join(" "));
    assert.equal(done.out, "");
    assert.match(done.err, /^usage: node converter\/odrig\.js thumbnail /, argv.join(" "));
  }
});

test("an option given twice takes its last value", (t) => {
  const work = temporary(t);
  const first = path.join(work, "first");
  const second = path.join(work, "second");
  assert.equal(runJs(["thumbnail", LINES, "--catalog", first, "--catalog", second]).status, 0);
  assert.equal(fs.existsSync(first), false);
  assert.ok(fs.existsSync(path.join(second, "catalog.js")));
});
