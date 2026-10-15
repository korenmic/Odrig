// An input file read whole and an output file written whole.

import fs from "node:fs";
import nodePath from "node:path";

import {errors} from "../lib/index.js";

// The words of the operating system for a failure, as it writes them on macOS and Linux.
const WORDS = {
  ENOENT: "No such file or directory",
  EISDIR: "Is a directory",
  ENOTDIR: "Not a directory",
  EACCES: "Permission denied",
  EEXIST: "File exists",
  ENOTEMPTY: "Directory not empty",
  EPERM: "Operation not permitted",
};

// Whether an error is a failure of the file system, and not a mistake of the program.
export function isSystemError(error) {
  return error instanceof Error && typeof error.code === "string" && typeof error.syscall === "string";
}

// Why the file system refused: its words for the failure, or the code of the failure when
// it is none of the common ones.
export function why(error, path = error.path) {
  const code = process.platform === "win32" ? asElsewhere(error.code, path) : error.code;
  return Object.prototype.hasOwnProperty.call(WORDS, code) ? WORDS[code] : code;
}

// The code macOS and Linux give for a failure that Windows names otherwise. There a folder
// that is read or written over is refused as if for want of permission, and a path below a
// file as if nothing were there. The words are to be the same on every system, so the path
// is looked at: a folder is a folder, and a path below a file is below a file. What else
// Windows refuses for want of permission it names EPERM, where macOS and Linux give EACCES.
function asElsewhere(code, path) {
  if (typeof path === "string" && (code === "EPERM" || code === "EACCES") && isFolder(path)) {
    return "EISDIR";
  }
  if (typeof path === "string" && code === "ENOENT" && belowAFile(path)) {
    return "ENOTDIR";
  }
  return code === "EPERM" ? "EACCES" : code;
}

function isFolder(path) {
  try {
    return fs.statSync(path).isDirectory();
  } catch {
    return false;
  }
}

// Whether something above the path is there and is not a folder.
function belowAFile(path) {
  let above = nodePath.dirname(nodePath.resolve(path));
  for (;;) {
    try {
      return !fs.statSync(above).isDirectory();
    } catch {
      const next = nodePath.dirname(above);
      if (next === above) {
        return false;
      }
      above = next;
    }
  }
}

// The bytes of the file. A file that is absent or unreadable is rejected as `missing`.
export function read(path, missing = errors.NOT_FOUND) {
  try {
    return fs.readFileSync(path);
  } catch (error) {
    if (!isSystemError(error)) {
      throw error;
    }
    throw new errors.Rejection(missing, `${path}: ${why(error, path)}`);
  }
}

// Writes the file through `<path>.part`, which takes the file's place once complete.
//
// An existing file is replaced. When writing fails, no `.part` file is left and an
// existing file is as it was.
export function write(path, bytes) {
  const part = `${path}.part`;
  try {
    fs.writeFileSync(part, bytes);
    fs.renameSync(part, path);
  } catch (error) {
    if (!isSystemError(error)) {
      throw error;
    }
    try {
      fs.unlinkSync(part);
    } catch (second) {
      if (!isSystemError(second)) {
        throw second;
      }
    }
    throw new errors.Rejection(errors.CANNOT_WRITE, `${path}: ${why(error, path)}`);
  }
}
