// The answers of the Python package that the tests compare with, kept in
// converter/tests/expected/: what the converter before this one, the Python package,
// answered to every request of the tests, recorded once while both existed. Each request,
// a question to that package or a command line of its tool or of a generator, is kept
// under a key made of what it asks: the request and its input, with the temporary folders
// and the repository written as names and the parts of the paths below them joined by `/`
// on every system, the files of those folders as they were before it, and every other file
// its command line names, of a folder of the repository only the files git tracks. With it are kept its answer and the files
// it made, wrote and removed. A run of more than 64 hexadecimal digits in an answer is kept
// as a digest, the first 16 digits of its SHA-256 and its number of bytes, except in the
// answers of `deflate`, which the tests go on to read. A file larger than 16 KB that a
// request wrote is a file of its own in expected/files/, compressed and named by its
// SHA-256.
//
// No test starts Python: a request gives the stored answer and writes the stored files.

import {spawnSync} from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import {fileURLToPath} from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const EXPECTED = path.join(ROOT, "converter", "tests", "expected");
export const EXPECTED_FILES = path.join(EXPECTED, "files");

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

// A path that starts with a name, up to a space, a quote or a colon.
const NAMED_PATH = /<(?:tmp\d+|root)>[^\s"':]*/g;

// A text with the parts of each path that starts with a name joined by `/`, as the answers
// were stored, whatever the system joins them by.
function slashed(text) {
  return path.sep === "/" ? text : text.replace(NAMED_PATH, (found) => found.split(path.sep).join("/"));
}

// A value with each temporary folder written as <tmpN> and the repository as <root>.
function named(value, folders) {
  return mapStrings(value, (text) => {
    let made = text;
    folders.forEach((folder, i) => {
      made = made.split(folder).join(`<tmp${i}>`);
    });
    return slashed(made.split(ROOT).join("<root>"));
  });
}

// A run of a text that may be a path: up to a space, a quote or a colon.
const PATH_RUN = /[^\s"':]+/g;

// The words of command lines that may name a path, as the stored answers write them and
// as the request gave them, the longest first.
function givenWords(commands, folders) {
  const words = new Map();
  for (const {argv} of commands) {
    for (const word of argv) {
      if (word !== "" && !word.startsWith("-") && !words.has(named(word, folders))) {
        words.set(named(word, folders), word);
      }
    }
  }
  return [...words].sort(([a], [b]) => b.length - a.length);
}

// A text of the stored answers as the tool writes it on this system: a path that begins
// with a word of the command lines begins with that word as it was given, and the rest of
// that path, and every other path that starts with a name, has its parts joined as the
// system joins them.
function spelled(text, words) {
  if (path.sep === "/") {
    return text;
  }
  return text.replace(PATH_RUN, (run) => {
    for (const [stored, given] of words) {
      if (run.startsWith(stored) && /^(?:$|[/.])/.test(run.slice(stored.length))) {
        return given + run.slice(stored.length).split("/").join(path.sep);
      }
    }
    return /^<(?:tmp\d+|root)>/.test(run) ? run.split("/").join(path.sep) : run;
  });
}

// A value of the stored answers with the names put back, its paths as `spelled` gives them.
function unnamed(value, folders, words = []) {
  return mapStrings(value, (text) => {
    let made = spelled(text, words).split("<root>").join(ROOT);
    folders.forEach((folder, i) => {
      made = made.split(`<tmp${i}>`).join(folder);
    });
    return made;
  });
}

// The SHA-256 of a file's content, with the temporary folders and the repository in it
// written as names, or "unreadable" for a file that may not be read: refused with EACCES on
// macOS and Linux, and with EPERM on Windows.
function contentOf(file, folders) {
  try {
    return sha256(Buffer.from(named(fs.readFileSync(file).toString("latin1"), folders), "latin1"));
  } catch (error) {
    if (error.code === "EACCES" || error.code === "EPERM") {
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
      // In the order of their names, which is the order macOS and Linux give them in.
      for (const entry of entries.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))) {
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

let trackedPaths;

// The files git tracks in the repository and the folders above them, as paths from the
// repository with `/` between the parts, or null where git does not list them.
function tracked() {
  if (trackedPaths === undefined) {
    const listed = spawnSync("git", ["ls-files", "-z"], {cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 28});
    trackedPaths = null;
    if (listed.status === 0 && listed.stdout !== "") {
      trackedPaths = new Set();
      for (const file of listed.stdout.split("\0").filter((name) => name !== "")) {
        const parts = file.split("/");
        parts.forEach((unused, i) => trackedPaths.add(parts.slice(0, i + 1).join("/")));
      }
    }
  }
  return trackedPaths;
}

// Whether a file or a folder counts in what a folder holds: inside the repository only
// what git tracks does, so that what one computer has beside the tracked files, such as a
// .DS_Store of macOS, does not change a key.
function counts(target) {
  const inside = path.relative(ROOT, target);
  if (inside === "" || inside.startsWith("..") || path.isAbsolute(inside) || tracked() === null) {
    return true;
  }
  return tracked().has(inside.split(path.sep).join("/"));
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
    if (counts(path.join(target, entry))) {
      parts.push([entry, holding(path.join(target, entry))]);
    }
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
      if (folders.some((folder) => target === folder || target.startsWith(`${folder}${path.sep}`))) {
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

// The digits of the SHA-256 a digest keeps.
const DIGEST_DIGITS = 16;

function digestOf(bytes) {
  return {digest: sha256(bytes).slice(0, DIGEST_DIGITS), bytes: bytes.length};
}

// Whether a stored value is the digest of a long run of hexadecimal digits.
export function isDigest(value) {
  return value !== null && typeof value === "object" && typeof value.digest === "string" && typeof value.bytes === "number";
}

// The number of bytes of a run of hexadecimal digits of an answer, kept whole or as a
// digest.
export function storedLength(stored) {
  return isDigest(stored) ? stored.bytes : stored.length / 2;
}

// Bytes, or their hexadecimal digits, in the form a stored value has: the digits, or the
// digest where the stored value is one.
export function asStored(ours, stored) {
  const digits = typeof ours === "string" ? ours : Buffer.from(ours).toString("hex");
  return isDigest(stored) ? digestOf(Buffer.from(digits, "hex")) : digits;
}

// A value the tests made, in the form of a stored answer: each run of hexadecimal digits
// where the stored answer has a digest, as a digest, and everything else as it is.
export function inStoredForm(ours, stored) {
  if (isDigest(stored)) {
    return typeof ours === "string" ? asStored(ours, stored) : ours;
  }
  if (Array.isArray(ours) && Array.isArray(stored)) {
    return ours.map((inner, i) => inStoredForm(inner, stored[i]));
  }
  if (ours !== null && stored !== null && typeof ours === "object" && typeof stored === "object" && !Array.isArray(ours) && !Array.isArray(stored)) {
    return Object.fromEntries(Object.entries(ours).map(([name, inner]) => [name, inStoredForm(inner, stored[name])]));
  }
  return ours;
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

// The stored answer of one request, which writes the files the request wrote. `ask` is
// what the request asks, as JSON; `commands` are the command lines it runs, `{cwd, argv}`.
export function answered(kind, ask, commands) {
  const folders = temporaryFolders([ask, commands.map(({cwd, argv}) => [cwd, argv])]);
  const key = sha256(JSON.stringify([kind, named(ask, folders), snapshot(folders), outside(commands, folders)]));
  const stored = expected(kind)[key];
  if (stored === undefined) {
    throw new Error(`no stored answer of the kind ${kind} for this request: what it asks has changed since the answers were stored`);
  }
  apply(stored, folders);
  return unnamed(stored.answer, folders, givenWords(commands, folders));
}
