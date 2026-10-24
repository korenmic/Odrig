import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import {bidi, draw, errors, odrgx, pack, textlayout} from "../lib/index.js";
import {ROOT, runJs, temporary, utf8} from "./support.js";

// A text with every setting at a plain value, and some of them changed.
function textOf(more = {}) {
  return {
    width: 60, height: 60, text: "Hello", font: "small", color: 0xffffff, background: 0, align: "center", valign: "middle",
    direction: "auto", wrap: false, effect: "static", motion: "left", speed: 20, pause: 3000, ...more,
  };
}

function sourceOf(more = {}) {
  const text = textOf(more);
  return {
    version: 1, type: "text", width: text.width, height: text.height, text: text.text, font: text.font, color: text.color,
    background: text.background, align: text.align, valign: text.valign, direction: text.direction, wrap: text.wrap,
    effect: text.effect, motion: text.motion, speed: text.speed, pause_ms: text.pause,
  };
}

function reasonOf(action) {
  try {
    action();
  } catch (error) {
    if (error instanceof errors.Rejection) return error.reason;
    throw error;
  }
  return null;
}

// The lines of a text as they are shown, each a string of its characters from left to right.
function shown(text, more = {}, room = 60) {
  return textlayout.visualLines(text, {font: "small", wrap: false, direction: "auto", align: "left", ...more}, room).map((codes) => String.fromCodePoint(...codes));
}

test("the bidirectional algorithm puts mixed text in the order it is read", async (t) => {
  await t.test("English and Hebrew alone", () => {
    assert.deepEqual(shown("Hello world"), ["Hello world"]);
    assert.deepEqual(shown("שלום עולם"), ["םלוע םולש"]);
  });

  await t.test("a paragraph takes the direction of its first strong letter", () => {
    assert.deepEqual(shown("שלום world"), ["world םולש"]);
    assert.deepEqual(shown("I love תל אביב very much"), ["I love ביבא לת very much"]);
    assert.deepEqual(shown("123 שלום"), ["םולש 123"]);
    assert.deepEqual(shown("123 abc"), ["123 abc"]);
  });

  await t.test("numbers keep their order in right-to-left text, with their separators and terminators", () => {
    assert.deepEqual(shown("מחיר 120 שקל"), ["לקש 120 ריחמ"]);
    assert.deepEqual(shown("מחיר: 3.14"), ["3.14 :ריחמ"]);
    assert.deepEqual(shown("שנת 2026!"), ["!2026 תנש"]);
    assert.deepEqual(shown("הנחה 10%"), ["10% החנה"]);
    assert.deepEqual(shown("1+2=3 בדיוק"), ["קוידב 3=1+2"]);
    assert.deepEqual(shown("טל: 03-1234567"), ["03-1234567 :לט"]);
  });

  await t.test("brackets are mirrored in a right-to-left run, never in a left-to-right one", () => {
    assert.deepEqual(shown("(שלום)"), ["(םולש)"]);
    assert.deepEqual(shown("a (b) c"), ["a (b) c"]);
    assert.deepEqual(shown("שלום [עולם]"), ["[םלוע] םולש"]);
    assert.deepEqual(shown("x < y"), ["x < y"]);
  });

  await t.test("a direction that is forced", () => {
    assert.deepEqual(shown("abc def", {direction: "rtl"}), ["abc def"]);
    assert.deepEqual(shown("abc שלום", {direction: "rtl"}), ["םולש abc"]);
    assert.deepEqual(shown("שלום abc", {direction: "ltr"}), ["םולש abc"]);
  });

  await t.test("every line feed begins a paragraph with a direction of its own", () => {
    assert.deepEqual(shown("שלום world\nhello עולם"), ["world םולש", "hello םלוע"]);
    assert.deepEqual(shown("a\n\nb"), ["a", "", "b"]);
  });

  await t.test("the classes of the characters", () => {
    assert.equal(bidi.classOf("a".codePointAt(0)), bidi.L);
    assert.equal(bidi.classOf("ך".codePointAt(0)), bidi.R);
    assert.equal(bidi.classOf("7".codePointAt(0)), bidi.EN);
    assert.deepEqual(["+", "-"].map((one) => bidi.classOf(one.codePointAt(0))), [bidi.ES, bidi.ES]);
    assert.deepEqual(["#", "$", "%"].map((one) => bidi.classOf(one.codePointAt(0))), [bidi.ET, bidi.ET, bidi.ET]);
    assert.deepEqual([",", ".", "/", ":"].map((one) => bidi.classOf(one.codePointAt(0))), [bidi.CS, bidi.CS, bidi.CS, bidi.CS]);
    assert.equal(bidi.classOf(0x20), bidi.WS);
    assert.equal(bidi.classOf("!".codePointAt(0)), bidi.ON);
  });
});

test("wrapping breaks a paragraph at spaces, and a word too wide between its characters", () => {
  assert.deepEqual(shown("one two three four", {wrap: true}, 40), ["one two", "three", "four"]);
  assert.deepEqual(shown("abcdefghijklmnop", {wrap: true}, 30), ["abcde", "fghijk", "lmnop"]);
  assert.deepEqual(shown("  lead", {wrap: true}, 30), ["  lead"]);
  assert.deepEqual(shown("שלום לכם חברים", {wrap: true}, 45), ["םכל םולש", "םירבח"]);
  assert.deepEqual(shown("שלום לכם חברים", {wrap: true}, 30), ["םולש", "םכל", "םירבח"]);
  const made = textlayout.layout("one two three four five six", {font: "small", wrap: true, direction: "auto", align: "left"}, 40);
  assert.ok(made.width <= 40);
  assert.equal(made.lines, 4);
});

test("the layout places glyphs of the font in a block", async (t) => {
  await t.test("a line: advances of width and one column, the block as wide as the widest line", () => {
    const made = textlayout.layout("Hi!", {font: "small", wrap: false, direction: "auto", align: "left"}, 60);
    const table = textlayout.fontOf(1).table;
    const index = (character) => textlayout.glyphIndex(table, character.codePointAt(0));
    assert.deepEqual(made.glyphs, [{glyph: index("H"), x: 0, y: 0}, {glyph: index("i"), x: 6, y: 0}, {glyph: index("!"), x: 8, y: 0}]);
    assert.deepEqual([made.width, made.height, made.lines], [9, 9, 1]);
  });

  await t.test("lines a pitch apart, aligned in the block", () => {
    const made = textlayout.layout("a\nbbb", {font: "small", wrap: false, direction: "auto", align: "right"}, 60);
    assert.deepEqual(made.glyphs.map((glyph) => [glyph.x, glyph.y]), [[12, 0], [0, 10], [6, 10], [12, 10]]);
    assert.deepEqual([made.width, made.height], [17, 19]);
    const centred = textlayout.layout("a\nbbb", {font: "small", wrap: false, direction: "auto", align: "center"}, 60);
    assert.equal(centred.glyphs[0].x, 6);
  });

  await t.test("the large font is the small one twice as big, and the medium one has its own glyphs", () => {
    const large = textlayout.layout("a\nb", {font: "large", wrap: false, direction: "auto", align: "left"}, 60);
    assert.deepEqual([large.width, large.height, large.glyphs[1].y], [10, 38, 20]);
    const medium = textlayout.layout("a", {font: "medium", wrap: false, direction: "auto", align: "left"}, 60);
    assert.deepEqual([medium.width, medium.height], [6, 13]);
  });

  await t.test("the final forms have glyphs of their own", () => {
    const table = textlayout.fontOf(1).table;
    const made = textlayout.layout("ךםןףץ", {font: "small", wrap: false, direction: "auto", align: "left"}, 60);
    assert.deepEqual(made.glyphs.map((glyph) => table.codes[glyph.glyph]).sort(), [0x5da, 0x5dd, 0x5df, 0x5e3, 0x5e5]);
  });
});

test("a character no font has is refused by name and code point", () => {
  assert.throws(() => textlayout.layout("café ☃", {font: "small", wrap: false, direction: "auto", align: "left"}, 60), (error) => {
    assert.equal(error.reason, "unsupported-character");
    assert.match(error.detail, /"é" \(U\+00E9\), "☃" \(U\+2603\)$/);
    return true;
  });
  assert.equal(reasonOf(() => textlayout.checkCharacters("שָׁלוֹם")), "unsupported-character");
  assert.deepEqual(textlayout.unsupported("ab\ncd\t"), [{character: "\t", code: 9}]);
});

test("the pass and the place of the block", async (t) => {
  const canvas = {width: 60, height: 60};
  const block = {width: 30, height: 9};
  const wide = {width: 100, height: 9};

  await t.test("static", () => {
    const settings = textOf({effect: "static", pause: 4000});
    assert.equal(draw.passMs(settings, block, canvas), 4000);
    assert.deepEqual(draw.placeAt(settings, block, canvas, 1234), {x: 15, y: 25});
  });

  await t.test("marquee in each motion", () => {
    const left = textOf({effect: "marquee", motion: "left", speed: 20});
    assert.equal(draw.passMs(left, block, canvas), 4500);
    assert.deepEqual([0, 1000, 4499].map((ms) => draw.placeAt(left, block, canvas, ms).x), [60, 40, -29]);
    const right = textOf({effect: "marquee", motion: "right", speed: 7});
    assert.equal(draw.passMs(right, block, canvas), 12858);
    assert.deepEqual([0, 1000].map((ms) => draw.placeAt(right, block, canvas, ms).x), [-30, -23]);
    const up = textOf({effect: "marquee", motion: "up", speed: 30, valign: "top"});
    assert.equal(draw.passMs(up, block, canvas), 2300);
    assert.deepEqual(draw.placeAt(up, block, canvas, 100), {x: 15, y: 57});
    const down = textOf({effect: "marquee", motion: "down", speed: 30});
    assert.deepEqual(draw.placeAt(down, block, canvas, 0), {x: 15, y: -9});
  });

  await t.test("slide: in, the pause where the alignment puts it, out", () => {
    const left = textOf({effect: "slide", motion: "left", speed: 20, pause: 1000});
    assert.equal(draw.passMs(left, block, canvas), 2250 + 1000 + 2250);
    assert.deepEqual([0, 2249, 2250, 3249, 3250, 4250, 5499].map((ms) => draw.placeAt(left, block, canvas, ms).x), [60, 16, 15, 15, 15, -5, -29]);
    const right = textOf({effect: "slide", motion: "right", speed: 20, pause: 0, align: "left"});
    assert.equal(draw.passMs(right, block, canvas), 1500 + 3000);
    assert.deepEqual([0, 1500, 1501].map((ms) => draw.placeAt(right, block, canvas, ms).x), [-30, 0, 0]);
  });

  await t.test("pan: from one end to the other and back, with a pause at each", () => {
    const left = textOf({effect: "pan", motion: "left", speed: 20, pause: 500});
    assert.equal(draw.passMs(left, wide, canvas), 500 + 2000 + 500 + 2000);
    assert.deepEqual([0, 499, 500, 1500, 2500, 2999, 3000, 4000, 4999].map((ms) => draw.placeAt(left, wide, canvas, ms).x), [0, 0, 0, -20, -40, -40, -40, -20, -1]);
    const right = textOf({effect: "pan", motion: "right", speed: 20, pause: 500});
    assert.deepEqual([0, 2500].map((ms) => draw.placeAt(right, wide, canvas, ms).x), [-40, 0]);
    const fitting = textOf({effect: "pan", motion: "left", pause: 0});
    assert.equal(draw.passMs(fitting, block, canvas), 20);
    assert.deepEqual(draw.placeAt(fitting, block, canvas, 5), {x: 15, y: 25});
  });

  await t.test("what fits", () => {
    assert.ok(draw.fits(textOf({effect: "static"}), block, canvas));
    assert.ok(!draw.fits(textOf({effect: "static"}), wide, canvas));
    assert.ok(!draw.fits(textOf({effect: "slide"}), wide, canvas));
    assert.ok(draw.fits(textOf({effect: "marquee", motion: "left"}), wide, canvas));
    assert.ok(!draw.fits(textOf({effect: "marquee", motion: "up"}), wide, canvas));
    assert.ok(draw.fits(textOf({effect: "pan", motion: "right"}), wide, canvas));
    assert.ok(!draw.fits(textOf({effect: "pan", motion: "down"}), wide, canvas));
  });
});

test("a text's container", async (t) => {
  await t.test("encodeText writes the settings, the text, the glyphs and the pass", () => {
    const text = textOf({text: "שלום world", effect: "marquee", speed: 25});
    const data = odrgx.encodeText(text);
    const decoded = odrgx.decodeText(data);
    assert.deepEqual(odrgx.textOf(decoded), text);
    assert.equal(decoded.header.type, odrgx.TYPES.text);
    const block = textlayout.layout(text.text, text, 60);
    assert.deepEqual(decoded.glyphs, block.glyphs);
    assert.deepEqual(decoded.block, {width: block.width, height: block.height});
    assert.equal(decoded.header.loopMs, draw.passMs(text, decoded.block, {width: 60, height: 60}));
    assert.equal(data.length, 20 + 28 + new TextEncoder().encode(text.text).length + 6 * block.glyphs.length);
  });

  await t.test("a block that cannot be seen whole is refused, with the effect that shows it", () => {
    for (const [more, words] of [[{effect: "static", text: "a long line of text"}, /a pan or a marquee/], [{effect: "marquee", motion: "up", text: "a long line of text"}, /a pan left or right/]]) {
      assert.throws(() => odrgx.encodeText(textOf(more)), (error) => error.reason === "does-not-fit" && words.test(error.detail));
    }
    assert.equal(reasonOf(() => odrgx.encodeText(textOf({width: 200, height: 200}))), "canvas-too-large");
  });

  await t.test("the JSON source is read strictly and written canonically", () => {
    const bytes = utf8(JSON.stringify(sourceOf({text: "שלום"})));
    const read = odrgx.loadsSource(bytes);
    assert.equal(read.type, "text");
    assert.deepEqual(read.text, textOf({text: "שלום"}));
    assert.deepEqual(odrgx.loadsSource(odrgx.dumpsText(read.text)), read);
    const refused = (source) => reasonOf(() => odrgx.loadsSource(utf8(JSON.stringify(source))));
    const without = sourceOf();
    delete without.wrap;
    assert.equal(refused(without), "missing-member");
    assert.equal(refused({...sourceOf(), extra: 1}), "unknown-member");
    assert.equal(refused({...sourceOf(), version: 2}), "bad-version");
    assert.equal(refused({...sourceOf(), type: "poem"}), "unknown-type");
    assert.equal(refused({...sourceOf(), wrap: 1}), "bad-type");
    assert.equal(refused({...sourceOf(), font: "huge"}), "out-of-range");
    assert.equal(refused({...sourceOf(), speed: 0}), "out-of-range");
    assert.equal(refused({...sourceOf(), effect: "static", pause_ms: 10}), "out-of-range");
    assert.equal(refused({...sourceOf(), text: ""}), "out-of-range");
    assert.equal(refused({...sourceOf(), text: "x".repeat(513)}), "out-of-range");
    assert.equal(odrgx.loadsSource(utf8(JSON.stringify({version: 1, width: 1, height: 1, frames: [{ms: 1, pixels: [0]}]}))).type, "frames");
  });

  await t.test("UTF-8 as the standard has it", () => {
    for (const good of [[0x61], [0xd7, 0xa9], [0xe2, 0x98, 0x83], [0xf0, 0x9f, 0x98, 0x80]]) assert.ok(odrgx.isUtf8(Uint8Array.from(good)), good);
    for (const bad of [[0x80], [0xc0, 0xaf], [0xe0, 0x80, 0xaf], [0xed, 0xa0, 0x80], [0xf4, 0x90, 0x80, 0x80], [0xd7], [0xff]]) assert.ok(!odrgx.isUtf8(Uint8Array.from(bad)), bad);
  });
});

test("the command line makes, reads and checks a text", async (t) => {
  const folder = temporary(t);
  const source = path.join(folder, "hello.json");
  fs.writeFileSync(source, JSON.stringify(sourceOf({text: "שלום world", effect: "marquee"})));
  const out = path.join(folder, "hello.odrgx");

  await t.test("encode, decode, check", () => {
    assert.equal(runJs(["encode", source, out]).status, 0);
    const back = path.join(folder, "back.json");
    assert.equal(runJs(["decode", out, back]).status, 0);
    assert.deepEqual(JSON.parse(fs.readFileSync(back, "utf8")), sourceOf({text: "שלום world", effect: "marquee"}));
    const checked = runJs(["check", out]);
    assert.equal(checked.status, 0, checked.err);
    assert.match(checked.out, /^format: odrgx\ntype: text\ncanvas: 60x60\nloop_ms: \d+\nfont: small\neffect: marquee left\nblock: \d+x9\nglyphs: 9\ntext_bytes: 14\nfile_bytes: \d+\n$/);
  });

  await t.test("a text is written as an ODRGX container only", () => {
    const refused = runJs(["encode", source, path.join(folder, "hello.odrg")]);
    assert.equal(refused.status, 2);
    assert.match(refused.err, /a text or a widget is written as \.odrgx/);
  });

  await t.test("a character no font has", () => {
    const bad = path.join(folder, "bad.json");
    fs.writeFileSync(bad, JSON.stringify(sourceOf({text: "naïve"})));
    const refused = runJs(["encode", bad, path.join(folder, "bad.odrgx")]);
    assert.equal(refused.status, 1);
    assert.match(refused.err, /^error: unsupported-character: .*bad\.json: the text holds characters no font has: "ï" \(U\+00EF\)\n$/);
  });

  await t.test("pack takes a text's source for its .odrgx file", () => {
    const show = utf8(JSON.stringify({version: 1, brightness: 9, items: [{id: 1, file: "hello.odrgx"}]}));
    const mapping = utf8(JSON.stringify({version: 1, width: 60, legs: [{leg: 1, pin: 1, first_led: "right", rows: Array.from({length: 60}, (_, at) => 60 - at)}]}));
    const files = pack.pack({mapping, show, sources: {"hello.json": fs.readFileSync(source)}});
    assert.equal(odrgx.decodeText(files.get("hello.odrgx")).text, "שלום world");
  });
});

test("the vectors of texts", async (t) => {
  const folder = path.join(ROOT, "tests", "vectors", "texts");
  const builder = await import(pathToFileURL(path.join(folder, "build.mjs")).href);
  const read = (...parts) => new Uint8Array(fs.readFileSync(path.join(folder, ...parts)));

  await t.test("they are what their builder makes", () => {
    const made = builder.vectors();
    const onDisk = ["valid", "invalid"].flatMap((part) => fs.readdirSync(path.join(folder, part)).map((name) => `${part}/${name}`));
    assert.deepEqual(onDisk.sort(), [...made.keys()].sort(), "run node tests/vectors/texts/build.mjs");
    for (const [name, data] of made) assert.deepEqual(read(name), data, name);
  });

  await t.test("a valid one decodes to its source", () => {
    const names = fs.readdirSync(path.join(folder, "valid")).filter((name) => name.endsWith(".odrgx"));
    assert.ok(names.length >= 6);
    for (const name of names) {
      const decoded = odrgx.decode(read("valid", name));
      assert.equal(decoded.type, "text");
      assert.deepEqual(odrgx.loadsSource(read("valid", name.replace(/\.odrgx$/, ".json"))).text, odrgx.textOf(decoded), name);
    }
  });

  await t.test("an invalid one is refused with the reason of its name, and they have every reason of a text", () => {
    const names = fs.readdirSync(path.join(folder, "invalid"));
    for (const name of names) assert.equal(reasonOf(() => odrgx.decode(read("invalid", name))), name.split(".")[0], name);
    const text = fs.readFileSync(path.join(ROOT, "docs", "reasons.md"), "utf8");
    const section = text.split("\n## Texts in ODRGX\n")[1].split("\n## ")[0];
    const listed = new Set([...section.matchAll(/^\| `([a-z0-9-]+)` \|/gm)].map((match) => match[1]));
    assert.deepEqual(new Set(names.map((name) => name.split(".")[0])), listed);
  });
});
