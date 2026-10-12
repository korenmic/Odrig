// An input file read whole and an output file written whole.

import fs from "node:fs";

import {errors} from "../lib/index.js";

// The words of the operating system for a failure, as it writes them on macOS and Linux.
const WORDS = {
  ENOENT: "No such file or directory",
  EISDIR: "Is a directory",
  ENOTDIR: "Not a directory",
  EACCES: "Permission denied",
  EEXIST: "File exists",
  ENOTEMPTY: "Directory not empty",
};

// Whether an error is a failure of the file system, and not a mistake of the program.
export function isSystemError(error) {
  return error instanceof Error && typeof error.code === "string" && typeof error.syscall === "string";
}

// Why the file system refused: its words for the failure, or the code of the failure when
// it is none of the common ones.
export function why(error) {
  return Object.prototype.hasOwnProperty.call(WORDS, error.code) ? WORDS[error.code] : error.code;
}

// The bytes of the file. A file that is absent or unreadable is rejected as `missing`.
export function read(path, missing = errors.NOT_FOUND) {
  try {
    return fs.readFileSync(path);
  } catch (error) {
    if (!isSystemError(error)) {
      throw error;
    }
    throw new errors.Rejection(missing, `${path}: ${why(error)}`);
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
    throw new errors.Rejection(errors.CANNOT_WRITE, `${path}: ${why(error)}`);
  }
}
