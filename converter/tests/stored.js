// The answers of the Python package that the tests compare with, kept in
// converter/tests/expected/. Each request a test makes, a request of reference.py or a
// command line of the Python tool, is kept under a key made of what it asks: the request
// and its input, with the temporary folders and the repository written as names, the
// files of those folders as they were before it, and every other file its command line
// names. With it are kept its answer, in which a long run of hexadecimal digits is kept as
// a digest, and the files it wrote and removed.
//
// ODRIG_EXPECTED says what a request does: `stored` gives the stored answer and writes
// the stored files, without Python; `verify` asks Python, checks that its answer and its
// files are the stored ones, and gives its whole answer; `record` asks Python and keeps
// what it answered in the folder ODRIG_EXPECTED_RECORDS, from which
// tests/converter/make_expected.py writes the stored files. Without it a request of a
// kind of STORED_KINDS is `stored`, and any other `verify`.

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import {fileURLToPath} from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const EXPECTED = path.join(ROOT, "converter", "tests", "expected");
export const EXPECTED_FILES = path.join(EXPECTED, "files");

// The kinds whose stored answers the tests take without asking Python.
export const STORED_KINDS = new Set([]);
// The kinds whose answers are kept whole: the tests go on to work with them.
export const KEPT_WHOLE = new Set(["deflate"]);

// The longest run of hexadecimal digits an answer keeps as it is. A longer one is kept as
// a digest: the first DIGEST_DIGITS digits of its SHA-256, and its number of bytes.
export const LONGEST_HEX = 64;
export const DIGEST_DIGITS = 16;
// The largest file kept within its answer; a larger one is a file of EXPECTED_FILES.
export const LARGEST_INLINE = 16384;

// A temporary folder of the tests, by either name the system's folder of temporary files
// has, the longer first.
const TEMPORARY = new RegExp(
  `(?:${[...new Set([fs.realpathSync(os.tmpdir()), os.tmpdir()])]
    .sort((a, b) => b.length - a.length)
    .map((folder) => folder.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|")})[\\\\/]odrig-converter-[A-Za-z0-9]+`,
  "g",
);

export function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

export function mode(kind) {
  const given = process.env.ODRIG_EXPECTED;
  if (given === "stored" || given === "verify" || given === "record") {
    return given;
  }
  return STORED_KINDS.has(kind) ? "stored" : "verify";
}

// The temporary folders a value names, in the order they first appear.
function temporaryFolders(value, found = []) {
  if (typeof value === "string") {
    for (const match of value.matchAll(TEMPORARY)) {
      if (!found.includes(match[0])) {
        found.push(match[0]);
      }
    }
  } else if (Array.isArray(value)) {
    value.forEach((inner) => temporaryFolders(inner, found));
  } else if (value !== null && typeof value === "object") {
    Object.values(value).forEach((inner) => temporaryFolders(inner, found));
  }
  return found;
}

function mapStrings(value, change) {
  if (typeof value === "string") {
    return change(value);
  }
  if (Array.isArray(value)) {
    return value.map((inner) => mapStrings(inner, change));
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([name, inner]) => [name, mapStrings(inner, change)]));
  }
  return value;
}

// A value with each temporary folder written as <tmpN> and the repository as <root>.
function named(value, folders) {
  return mapStrings(value, (text) => {
    let made = text;
    folders.forEach((folder, i) => {
      made = made.split(folder).join(`<tmp${i}>`);
    });
    return made.split(ROOT).join("<root>");
  });
}

// A value of the stored answers with the names put back.
function unnamed(value, folders) {
  return mapStrings(value, (text) => {
    let made = text.split("<root>").join(ROOT);
    folders.forEach((folder, i) => {
      made = made.split(`<tmp${i}>`).join(folder);
    });
    return made;
  });
}

// The SHA-256 of a file's content, with the temporary folders and the repository in it
// written as names, or "unreadable" for a file that may not be read.
function contentOf(file, folders) {
  try {
    return sha256(Buffer.from(named(fs.readFileSync(file).toString("latin1"), folders), "latin1"));
  } catch (error) {
    if (error.code === "EACCES") {
      return "unreadable";
    }
    throw error;
  }
}

// Every file and folder under the temporary folders: their content's SHA-256, "unreadable"
// or "folder".
function snapshot(folders) {
  const found = {};
  folders.forEach((folder, i) => {
    const walk = (inner) => {
      let entries;
      try {
        entries = fs.readdirSync(path.join(folder, inner), {withFileTypes: true});
      } catch {
        return;
      }
      for (const entry of entries) {
        const name = inner === "" ? entry.name : `${inner}/${entry.name}`;
        if (entry.isDirectory()) {
          found[`<tmp${i}>/${name}`] = "folder";
          walk(name);
        } else if (entry.isFile()) {
          found[`<tmp${i}>/${name}`] = contentOf(path.join(folder, name), folders);
        }
      }
    };
    walk("");
  });
  return found;
}

// What a file or a folder outside the temporary folders holds, for the key.
function holding(target) {
  let status;
  try {
    status = fs.statSync(target);
  } catch {
    return null;
  }
  if (status.isFile()) {
    return contentOf(target, []);
  }
  if (!status.isDirectory()) {
    return "other";
  }
  const parts = [];
  for (const entry of fs.readdirSync(target).sort()) {
    parts.push([entry, holding(path.join(target, entry))]);
  }
  return sha256(JSON.stringify(parts));
}

// The files outside the temporary folders that the words of command lines name, relative
// to the folders they run in.
function outside(commands, folders) {
  const found = [];
  for (const {cwd, argv} of commands) {
    for (const word of argv) {
      if (word === "" || word.startsWith("-")) {
        continue;
      }
      const target = path.resolve(cwd, word);
      if (folders.some((folder) => target === folder || target.startsWith(`${folder}/`))) {
        continue;
      }
      const held = holding(target);
      if (held !== null) {
        found.push([named(word, folders), held]);
      }
    }
  }
  return found;
}

function digestOf(bytes) {
  return {digest: sha256(bytes).slice(0, DIGEST_DIGITS), bytes: bytes.length};
}

function compact(value) {
  if (typeof value === "string" && value.length > LONGEST_HEX && value.length % 2 === 0 && /^[0-9a-f]+$/.test(value)) {
    return digestOf(Buffer.from(value, "hex"));
  }
  if (Array.isArray(value)) {
    return value.map(compact);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([name, inner]) => [name, compact(inner)]));
  }
  return value;
}

// Whether a stored value is the digest of a long run of hexadecimal digits.
export function isDigest(value) {
  return value !== null && typeof value === "object" && typeof value.digest === "string" && typeof value.bytes === "number";
}

// Bytes, or their hexadecimal digits, in the form a stored value has: the digits, or the
// digest where the stored value is one.
export function asStored(ours, stored) {
  const digits = typeof ours === "string" ? ours : Buffer.from(ours).toString("hex");
  return isDigest(stored) ? digestOf(Buffer.from(digits, "hex")) : digits;
}

const stores = {};

// The stored answers of a kind, by their keys.
export function expected(kind) {
  if (!(kind in stores)) {
    const plain = path.join(EXPECTED, `${kind}.json`);
    const packed = `${plain}.gz`;
    if (fs.existsSync(plain)) {
      stores[kind] = JSON.parse(fs.readFileSync(plain, "utf8"));
    } else if (fs.existsSync(packed)) {
      stores[kind] = JSON.parse(zlib.gunzipSync(fs.readFileSync(packed)).toString("utf8"));
    } else {
      stores[kind] = {};
    }
  }
  return stores[kind];
}

function storedFile(stored) {
  if ("base64" in stored) {
    return Buffer.from(stored.base64, "base64");
  }
  return zlib.gunzipSync(fs.readFileSync(path.join(EXPECTED_FILES, `${stored.file}.gz`)));
}

function keptFile(bytes, records) {
  if (bytes.length <= LARGEST_INLINE) {
    return {base64: Buffer.from(bytes).toString("base64")};
  }
  const digest = sha256(bytes);
  if (records !== null) {
    fs.mkdirSync(path.join(records, "files"), {recursive: true});
    fs.writeFileSync(path.join(records, "files", digest), bytes);
  }
  return {file: digest};
}

// What a request did to the temporary folders: the folders it made, the files it wrote,
// and what it removed.
function effects(before, after, folders, records) {
  const made = [];
  const written = {};
  const removed = [];
  for (const [name, held] of Object.entries(after).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
    if (before[name] === held) {
      continue;
    }
    if (held === "folder") {
      made.push(name);
    } else {
      written[name] = keptFile(fs.readFileSync(unnamed(name, folders)), records);
    }
  }
  for (const name of Object.keys(before).sort()) {
    if (!(name in after)) {
      removed.push(name);
    }
  }
  return {made, written, removed};
}

function apply(entry, folders) {
  for (const name of [...entry.removed].reverse()) {
    fs.rmSync(unnamed(name, folders), {recursive: true, force: true});
  }
  for (const name of entry.made) {
    fs.mkdirSync(unnamed(name, folders), {recursive: true});
  }
  for (const [name, stored] of Object.entries(entry.written)) {
    const target = unnamed(name, folders);
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, storedFile(stored));
  }
}

function sameStored(entry, stored) {
  return JSON.stringify(entry) === JSON.stringify(stored);
}

// Answers one request. `ask` is what the request asks, as JSON; `commands` are the command
// lines it runs, `{cwd, argv}`; `python` asks Python and gives its answer.
export function answered(kind, ask, commands, python) {
  const folders = temporaryFolders([ask, commands.map(({cwd, argv}) => [cwd, argv])]);
  const before = snapshot(folders);
  const key = sha256(JSON.stringify([kind, named(ask, folders), before, outside(commands, folders)]));
  const how = mode(kind);
  if (how === "stored") {
    const stored = expected(kind)[key];
    if (stored === undefined) {
      throw new Error(`no stored answer of the kind ${kind} for this request: what it asks has changed since the answers were stored`);
    }
    apply(stored, folders);
    return unnamed(stored.answer, folders);
  }
  const answer = python();
  const records = how === "record" ? process.env.ODRIG_EXPECTED_RECORDS : null;
  const kept = named(answer, folders);
  const entry = {answer: KEPT_WHOLE.has(kind) ? kept : compact(kept), ...effects(before, snapshot(folders), folders, records)};
  if (how === "record") {
    fs.mkdirSync(records, {recursive: true});
    fs.appendFileSync(path.join(records, `${process.pid}.jsonl`), `${JSON.stringify({kind, key, entry})}\n`);
  } else {
    const stored = expected(kind)[key];
    if (stored === undefined) {
      throw new Error(`no stored answer of the kind ${kind} for this request`);
    }
    if (!sameStored(entry, stored)) {
      throw new Error(`the stored answer of the kind ${kind} differs from what Python answers: ${key}`);
    }
  }
  return answer;
}
