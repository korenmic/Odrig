import assert from "node:assert/strict";
import test from "node:test";
import * as message from "../lib/messageclock.js";
import {draw, odrgx} from "../lib/index.js";

function settings(flags = [0], tab = 1) {
  const masks = flags.map(() => {
    const mask = new Uint8Array(900); mask[(15 * 60 + 5) >> 1] = 15; return mask;
  });
  return {width: 60, height: 60, widget: "message-clock", tab,
    messages: flags.map((f, i) => ({text: i ? "אפס" : "hello", flags: f, duration: f & 1 ? 2000 : 6100, mask: masks[i]})),
    loopMs: flags.reduce((n, f) => n + (f & 1 ? 2000 : 6100), 0), glyphs: new Uint8Array(3968)};
}
function pixels(s, t, seed = 1) { return draw.drawClock(s, seed, t, {width: 60, height: 60}, new Uint8Array(10800)); }
function pixel(p, x, y) { return [...p.subarray(3 * ((59 - y) * 60 + x), 3 * ((59 - y) * 60 + x) + 3)]; }
const rejected = (fn, reason) => assert.throws(fn, (error) => error.reason === reason);

test("message-clock source, binary and canonical source round trip", () => {
  const input = settings([1, 2, 0], 5);
  const loaded = odrgx.loadsSource(new TextEncoder().encode(JSON.stringify(message.source(input))));
  const data = odrgx.encodeSource(loaded);
  const read = odrgx.decodeWidget(data);
  assert.equal(read.settings.loopMs, 14200);
  assert.equal(read.settings.messages[1].text, "אפס");
  const again = odrgx.loadsSource(odrgx.dumpsWidget(odrgx.widgetOf(read)));
  assert.deepEqual(odrgx.encodeSource(again), data);
});

test("message-clock fade, sweep and bottom square use physical black background", () => {
  const s = settings();
  assert.deepEqual(pixel(pixels(s, 0), 5, 15), [0, 0, 0]);
  assert.deepEqual(pixel(pixels(s, 300), 5, 15), [44, 102, 127]);
  assert.deepEqual(pixel(pixels(s, 600), 5, 15), [255, 255, 255]);
  assert.deepEqual(pixel(pixels(s, 5650), 5, 15), [229, 229, 229]);
  assert.deepEqual(pixel(pixels(s, 0), 56, 59), [255, 255, 255]);
  assert.deepEqual(pixel(pixels(s, 0), 0, 0), [0, 0, 0]);
  assert.deepEqual(pixels(s, 100), pixels(s, 6200));
});

test("countdown and stopped motion remain steadily illuminated", () => {
  const countdown = settings([1], 5);
  assert.deepEqual(pixel(pixels(countdown, 0), 5, 15), [255, 255, 255]);
  assert.deepEqual(pixel(pixels(countdown, 1999), 5, 15), [255, 255, 255]);
  for (const [flags, tab] of [[[4], 1], [[8], 6]]) {
    const s = settings(flags, tab);
    for (let i = 0; i < s.glyphs.length; ++i) s.glyphs[i] = (i * 37) & 255;
    const a = pixels(s, 4000), b = pixels(s, 5000);
    assert.deepEqual(a.subarray(0, 540), b.subarray(0, 540));
    assert.equal(a.subarray(0, 540).filter((v) => v === 255).length, 27);
    if (flags[0] === 4) {
      const frozen = a.subarray(1800, 4680);
      assert.ok(frozen.some((v) => v !== 0));
      assert.deepEqual(frozen, b.subarray(1800, 4680));
      assert.deepEqual(frozen, pixels(s, 3500).subarray(1800, 4680));
    } else assert.notDeepEqual(a.subarray(1800, 4680), b.subarray(1800, 4680));
  }
});

test("message-clock seeking and loop restart have no mutable renderer state", () => {
  const s = settings([16, 0, 8], 6);
  for (let i = 0; i < s.glyphs.length; ++i) s.glyphs[i] = (i * 37) & 255;
  const expected = pixels(s, 12499, 0xdeadbeef);
  for (const t of [18000, 0, 2200, 6100]) pixels(s, t, 9);
  assert.deepEqual(pixels(s, 12499, 0xdeadbeef), expected);
  assert.deepEqual(pixels(s, 12499 + s.loopMs, 0xdeadbeef), expected);
  assert.notDeepEqual(pixels(s, 12499, 1), pixels(s, 12499, 2));
});

test("message-clock strict payload bounds and caption UTF-8", () => {
  const data = odrgx.encodeWidget(settings());
  for (const [at, value, reason] of [[21, 2, "bad-settings"], [22, 0, "bad-settings"],
    [30, 1, "bad-settings"], [32, 0, "bad-settings"], [48, 32, "bad-settings"],
    [49, 1, "bad-settings"], [56, 255, "bad-text"]]) {
    const changed = data.slice(); changed[at] = value;
    rejected(() => odrgx.decodeWidget(changed), reason);
  }
  for (const length of [20, 23, 43, 45, 55, 56, data.length - 1]) {
    rejected(() => odrgx.decodeWidget(data.subarray(0, length)), "truncated");
  }
  const trailing = new Uint8Array(data.length + 1); trailing.set(data);
  rejected(() => odrgx.decodeWidget(trailing), "trailing-bytes");
  const loop = data.slice(); loop[12] ^= 1;
  rejected(() => odrgx.decodeWidget(loop), "loop-mismatch");
});
