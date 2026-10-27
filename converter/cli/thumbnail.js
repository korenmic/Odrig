// The subcommand `thumbnail`: the preview of one file, or the previews of files added to the
// preview catalog of a folder.
//
// A preview catalog is a folder of GIF files, each named by the key of the animation it
// shows, and `catalog.js`, the mapping from each key to its GIF and to the names the
// animation was given. The mapping is read and written as text, in one fixed shape: the
// line `export default {`, one line for each key in the order of its bytes, and `};`.

import fs from "node:fs";
import path from "node:path";

import {errors, thumbnail as previews} from "../lib/index.js";
import * as files from "./files.js";

export const CATALOG = "catalog.js";
const HEAD = "export default {";
const TAIL = "};";
const ENTRY = /^  ("[0-9a-f]{8}-[0-9]+"): (\{"gif": "[0-9a-f]{8}-[0-9]+\.gif", "names": \[.*\]\}),$/;

// The bytes of a text, to order texts by them.
function bytesOf(text) {
  return new TextEncoder().encode(text);
}

function byBytes(a, b) {
  const left = bytesOf(a);
  const right = bytesOf(b);
  for (let at = 0; at < Math.min(left.length, right.length); at += 1) {
    if (left[at] !== right[at]) {
      return left[at] - right[at];
    }
  }
  return left.length - right.length;
}

// A text as a JSON string with every character above `~` written as `\u` and four
// hexadecimal digits, so that it is plain ASCII.
export function ascii(text) {
  return JSON.stringify(text).replace(/[\u007f-￿]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

// The mapping of a `catalog.js`: for each key its GIF's name and its names. A text of
// another shape is a fault of the folder, not a rejected input: it is thrown as an error.
export function parseCatalog(text, where = CATALOG) {
  const lines = text.split("\n");
  if (lines.length < 3 || lines[0] !== HEAD || lines[lines.length - 2] !== TAIL || lines[lines.length - 1] !== "") {
    throw new Error(`${where} is not a preview catalog: it does not begin with "${HEAD}" and end with "${TAIL}"`);
  }
  const mapping = new Map();
  lines.slice(1, -2).forEach((line, place) => {
    const found = ENTRY.exec(line);
    const value = found === null ? null : JSON.parse(found[2]);
    const key = found === null ? null : JSON.parse(found[1]);
    if (found === null || value.gif !== `${key}.gif` || !value.names.every((name) => typeof name === "string") || mapping.has(key)) {
      throw new Error(`${where}: line ${place + 2} is not an entry of a preview catalog`);
    }
    mapping.set(key, {gif: value.gif, names: new Set(value.names)});
  });
  return mapping;
}

// The text of a `catalog.js` for a mapping: the keys and each key's names in the order of
// their bytes.
export function formatCatalog(mapping) {
  const lines = [HEAD];
  for (const key of [...mapping.keys()].sort(byBytes)) {
    const {gif, names} = mapping.get(key);
    const listed = [...names].sort(byBytes).map(ascii).join(", ");
    lines.push(`  ${ascii(key)}: {"gif": ${ascii(gif)}, "names": [${listed}]},`);
  }
  lines.push(TAIL, "");
  return lines.join("\n");
}

// The name of a file in the mapping: its path from the card's folder, its parts joined by
// `/`, when it is inside that folder; otherwise its own name.
export function nameOf(file, card) {
  if (card !== null) {
    const inside = path.relative(path.resolve(card), path.resolve(file));
    if (inside !== "" && !inside.startsWith("..") && !path.isAbsolute(inside)) {
      return inside.split(path.sep).join("/");
    }
  }
  return path.basename(file);
}

function oneSpaced(text) {
  return text.split(/\s+/).filter((word) => word !== "").join(" ");
}

// Adds the previews of the files to the preview catalog of a folder, and writes the mapping
// anew. A file that is refused is passed over, with one line on standard error.
function intoCatalog(values, streams) {
  const folder = values.catalog;
  try {
    fs.mkdirSync(folder, {recursive: true});
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    throw new errors.Rejection(errors.CANNOT_WRITE, `${folder}: ${files.why(error, folder)}`);
  }
  const where = path.join(folder, CATALOG);
  const mapping = fs.existsSync(where) ? parseCatalog(fs.readFileSync(where, "utf8"), where) : new Map();
  for (const file of values.files) {
    try {
      const data = files.read(file);
      const key = previews.keyOf(data);
      let entry = mapping.get(key);
      const gif = path.join(folder, `${key}.gif`);
      if (entry === undefined || !fs.existsSync(gif)) {
        files.write(gif, previews.make(data));
        entry = entry === undefined ? {gif: `${key}.gif`, names: new Set()} : entry;
        mapping.set(key, entry);
      }
      entry.names.add(nameOf(file, values.card));
    } catch (error) {
      if (!(error instanceof errors.Rejection) || error.reason === errors.CANNOT_WRITE) {
        throw error;
      }
      streams.err.write(`passed over: ${file}: ${error.reason}: ${oneSpaced(error.detail)}\n`);
    }
  }
  files.write(where, bytesOf(formatCatalog(mapping)));
}

export function thumbnail(values, streams) {
  if (values.catalog !== null) {
    intoCatalog(values, streams);
    return;
  }
  const file = values.files[0];
  const data = files.read(file);
  files.write(values.out, errors.naming(file, () => previews.make(data)));
}
