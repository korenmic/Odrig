import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {createHash} from "node:crypto";
import {odrgx, thumbnail} from "../lib/index.js";
import {compile, REFERENCE, REFERENCE_SHA256} from "../../project-seeds/59-p2-message-clock-widgets-and-clocks-only-mode/source/generate.mjs";

const NAMES = ["consciousness", "symmetry", "temperature", "the-time", "countdown", "the-clock", "mistakes"];
const COUNTS = [6, 4, 6, 6, 20, 4, 9];
const LOOPS = [36600, 24400, 36600, 36600, 76900, 24400, 54900];
const ROOT = new URL("../../collection/card/clocks/message/", import.meta.url);
const html = fs.readFileSync(REFERENCE, "utf8");
const sourceLists = [...html.matchAll(/lines:\[([^\n]+)\]/g)].map((match) =>
  [...match[1].matchAll(/'([^']*)'/g)].map((text) => text[1]));
const ROLES = [[0,0,0,4,0,0], [0,0,0,0], [0,0,0,0,0,0], [0,0,0,0,0,0],
  [...Array(11).fill(1),2,2,2,0,0,0,0,0,0], [0,0,16,8], Array(9).fill(0)];

for (const [index, name] of NAMES.entries()) {
  test(`message widget ${name} keeps one complete source sequence and its delivery companions`, () => {
    const file = new URL(`v7-${name}.odrgx`, ROOT);
    assert.ok(fs.existsSync(file), `missing widget ${file.pathname}`);
    const data = fs.readFileSync(file);
    const {settings} = odrgx.decodeWidget(data);
    assert.equal(settings.widget, "message-clock");
    assert.equal(settings.tab, index + 1);
    assert.equal(settings.messages.length, COUNTS[index]);
    assert.equal(settings.loopMs, LOOPS[index]);
    assert.deepEqual(settings.messages.map((m) => m.text), sourceLists[index]);
    assert.deepEqual(settings.messages.map((m) => m.flags), ROLES[index]);
    assert.deepEqual(settings.messages.map((m) => m.duration), ROLES[index].map((f) => f & 1 ? 2000 : 6100));
    assert.ok(data.length <= 32788);
    assert.ok(settings.glyphs.some((byte) => byte !== 0));
    assert.ok(settings.messages.every((message) => message.mask.some((byte) => byte !== 0)));
    assert.ok(fs.existsSync(new URL(`v7-${name}.gif`, ROOT)));
    assert.ok(fs.existsSync(new URL(`v7-${name}.md`, ROOT)));
    const preview = fs.readFileSync(new URL(`v7-${name}.gif`, ROOT));
    assert.ok(preview.equals(Buffer.from(thumbnail.make(data))));
    assert.deepEqual(preview, fs.readFileSync(new URL(`../../thumbnails/${thumbnail.keyOf(data)}.gif`, import.meta.url)));
  });
}

test("source reference and existing authored font remain pinned; compilation reproduces delivered bytes", () => {
  assert.equal(createHash('sha256').update(fs.readFileSync(REFERENCE)).digest('hex'), REFERENCE_SHA256);
  assert.equal(createHash('sha256').update(fs.readFileSync(new URL('../../fonts/small.txt', import.meta.url))).digest('hex'),
    '62d98242ab92cbf40f894165e2d02eeef377af7a987e0c980c49873a0021470f');
  for (const item of compile()) {
    const data = fs.readFileSync(new URL(item.file, ROOT));
    assert.ok(Buffer.from(odrgx.encodeSource(odrgx.loadsSource(Buffer.from(JSON.stringify(item.source))))).equals(data));
    assert.ok(Buffer.from(odrgx.encodeWidget(item.settings)).equals(data));
  }
});

test("stationary digits fit the reference's twelve-pixel font inside the sixteen-row wheel window", () => {
  const {settings} = odrgx.decodeWidget(fs.readFileSync(new URL('v7-consciousness.odrgx', ROOT)));
  for (let glyph = 0; glyph < 62; glyph++) {
    const rows = [];
    for(let y=0;y<16;y++)if(settings.glyphs.subarray(glyph*64+y*4,glyph*64+(y+1)*4).some(Boolean))rows.push(y);
    assert.ok(rows.at(-1)-rows[0]+1 <= 12, `glyph ${glyph} is too tall`);
    assert.ok(rows[0] > 0 && rows.at(-1) < 15, `glyph ${glyph} touches the wheel edge`);
  }
});
