import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {CATALOG, formatCatalog, parseCatalog} from "../cli/thumbnail.js";
import {thumbnail} from "../lib/index.js";
import {ROOT} from "./support.js";

const FOLDER = path.join(ROOT, "thumbnails");
const VECTORS = path.join(ROOT, "tests", "vectors");
// The tracked animations, whose previews the folder holds as `make` gives them.
const TRACKED = ["test-animations", "tests/vectors/valid", "tests/vectors/containers/valid", "tests/vectors/texts/valid", "tests/vectors/widgets/valid"];

const text = fs.readFileSync(path.join(FOLDER, CATALOG), "utf8");
const mapping = parseCatalog(text);

test("the default preview catalog is its mapping and one GIF for each key, and nothing else", () => {
  const files = fs.readdirSync(FOLDER).sort();
  const gifs = files.filter((name) => name !== CATALOG);
  assert.ok(files.includes(CATALOG));
  assert.deepEqual(gifs, [...mapping.keys()].map((key) => `${key}.gif`).sort());
  for (const [key, {gif, names}] of mapping) {
    assert.match(key, /^[0-9a-f]{8}-[1-9][0-9]*$/);
    assert.equal(gif, `${key}.gif`);
    assert.ok(names.size >= 1, key);
    const data = fs.readFileSync(path.join(FOLDER, gif));
    assert.equal(data.subarray(0, 6).toString("latin1"), "GIF89a", gif);
    assert.ok(data.length <= thumbnail.LARGEST, gif);
  }
});

test("its mapping is plain ASCII in its one shape, the keys and names in the order of their bytes", () => {
  assert.ok([...text].every((character) => character.charCodeAt(0) < 128));
  assert.equal(formatCatalog(mapping), text);
});

test("a name is a file's name or its path on a card, never a place of the computer", () => {
  for (const {names} of mapping.values()) {
    for (const name of names) {
      assert.ok(name.length > 0 && name.length <= 100, name);
      assert.ok(!name.startsWith("/") && !name.startsWith(".") && !name.includes("\\") && !name.includes(":"), name);
      assert.ok(!name.split("/").includes(".."), name);
      assert.ok(!/(^|\/)(Users|Volumes|home|My Drive|CloudStorage|scratch|build)(\/|$)/.test(name), name);
      assert.match(name, /\.odrgx?$/i, name);
    }
  }
});

test("the previews of the tracked animations are those the library makes", () => {
  let checked = 0;
  for (const folder of TRACKED) {
    for (const name of fs.readdirSync(path.join(ROOT, folder)).filter((file) => /\.odrgx?$/.test(file))) {
      const data = new Uint8Array(fs.readFileSync(path.join(ROOT, folder, name)));
      const key = thumbnail.keyOf(data);
      assert.ok(mapping.has(key), `${folder}/${name} has no preview`);
      assert.ok(mapping.get(key).names.has(name), `${folder}/${name} is not among the names of ${key}`);
      assert.deepEqual(new Uint8Array(fs.readFileSync(path.join(FOLDER, `${key}.gif`))), thumbnail.make(data), `${folder}/${name}`);
      checked += 1;
    }
  }
  assert.ok(checked >= 50, `${checked} tracked animations`);
  assert.ok(fs.existsSync(VECTORS));
});
