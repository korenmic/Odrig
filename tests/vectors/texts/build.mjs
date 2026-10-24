// Builds the vectors of texts of this folder with the converter's library. Run from the
// repository root: node tests/vectors/texts/build.mjs
//
// valid/ holds containers of texts with their JSON sources: X.odrgx and X.json. invalid/
// holds containers that every reader refuses, each named by its reason and what is wrong.

import {mkdirSync, readdirSync, rmSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const {odrgx} = await import(new URL("../../../converter/lib/index.js", import.meta.url).href);

function text(more) {
  return {
    width: 60, height: 60, text: "Hello", font: "small", color: 0xffd040, background: 0x000010, align: "center",
    valign: "middle", direction: "auto", wrap: false, effect: "static", motion: "left", speed: 20, pause: 2000, ...more,
  };
}

// The texts of valid/, by name.
export const TEXTS = {
  "english.static": text({}),
  "hebrew.marquee": text({text: "שלום עולם", font: "medium", effect: "marquee", speed: 30, color: 0x40c0ff}),
  "mixed.pan": text({text: "שלום world 2026!", font: "large", effect: "pan", motion: "left", pause: 500, speed: 25}),
  "multiline.wrap": text({text: "one two three four five six seven", wrap: true, align: "left", valign: "top"}),
  "finals.slide": text({text: "ךםןףץ ק", effect: "slide", motion: "right", pause: 700, speed: 40}),
  "tall.up": text({text: "a\nb\nc\nd\ne\nf\ng\nh", font: "medium", effect: "marquee", motion: "up", speed: 15}),
  "rtl.down": text({text: "(מחיר: 3.14)", direction: "rtl", effect: "pan", motion: "down", pause: 300, align: "right"}),
};

function changed(data, at, ...bytes) {
  const made = Uint8Array.from(data);
  made.set(bytes, at);
  return made;
}

function u16(value) {
  return [value & 0xff, (value >>> 8) & 0xff];
}

function u32(value) {
  return [...u16(value & 0xffff), ...u16(Math.floor(value / 65536))];
}

// Every vector, by its place in the folder.
export function vectors() {
  const made = new Map();
  for (const [name, one] of Object.entries(TEXTS)) {
    made.set(`valid/${name}.odrgx`, odrgx.encodeText(one));
    made.set(`valid/${name}.json`, odrgx.dumpsText(one));
  }
  const good = odrgx.encodeText(text({text: "Hi you"}));
  const p = odrgx.HEADER_SIZE;
  const decoded = odrgx.decodeText(good);
  const textBytes = new TextEncoder().encode(decoded.text).length;
  const glyphs = p + odrgx.TEXT_SETTINGS_SIZE + textBytes;
  made.set("invalid/canvas-too-large.odrgx", changed(good, 8, ...u16(200), ...u16(200)));
  made.set("invalid/truncated.settings.odrgx", good.subarray(0, p + 10));
  made.set("invalid/unknown-font.id.odrgx", changed(good, p, 9));
  made.set("invalid/unknown-font.version.odrgx", changed(good, p + 1, 2));
  made.set("invalid/bad-settings.effect.odrgx", changed(good, p + 2, 7));
  made.set("invalid/bad-settings.wrap.odrgx", changed(good, p + 7, 2));
  made.set("invalid/bad-settings.speed.odrgx", changed(good, p + 14, ...u16(0)));
  made.set("invalid/bad-settings.static-pause.odrgx", changed(good, p + 16, ...u16(19)));
  made.set("invalid/bad-text.length.odrgx", changed(good, p + 18, ...u16(0)));
  made.set("invalid/bad-settings.glyphs.odrgx", changed(good, p + 20, ...u16(513)));
  made.set("invalid/bad-settings.block.odrgx", changed(good, p + 24, ...u16(0)));
  made.set("invalid/bad-settings.reserved.odrgx", changed(good, p + 26, 1));
  made.set("invalid/payload-size.settings.odrgx", changed(good, 16, ...u32(good.length - p + 1)));
  made.set("invalid/payload-size.header.odrgx", changed(good, 16, ...u32(4000)));
  made.set("invalid/does-not-fit.odrgx", changed(good, p + 22, ...u16(61)));
  made.set("invalid/bad-text.utf8.odrgx", changed(good, p + odrgx.TEXT_SETTINGS_SIZE, 0xff));
  made.set("invalid/bad-glyph.index.odrgx", changed(good, glyphs, ...u16(999)));
  made.set("invalid/bad-glyph.outside.odrgx", changed(good, glyphs + 2, ...u16(decoded.block.width)));
  made.set("invalid/truncated.glyphs.odrgx", good.subarray(0, good.length - 2));
  made.set("invalid/trailing-bytes.odrgx", Uint8Array.of(...good, 0));
  made.set("invalid/loop-mismatch.odrgx", changed(good, 12, ...u32(decoded.header.loopMs + 1)));
  return made;
}

function main() {
  for (const folder of ["valid", "invalid"]) {
    rmSync(join(HERE, folder), {recursive: true, force: true});
    mkdirSync(join(HERE, folder));
  }
  for (const [name, data] of vectors()) {
    writeFileSync(join(HERE, name), data);
  }
  for (const folder of ["valid", "invalid"]) {
    console.log(`${folder}: ${readdirSync(join(HERE, folder)).length} files`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
