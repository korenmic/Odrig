// A file the app made, saved on the phone or the computer as it is written: in a browser a
// download of the bytes, in the app through its shell's plugin `Save`, which writes them to a
// file of its own and then lets the operator choose the place and the name in the system's
// dialog. Bytes are kept in pieces, never as one copy of the whole file in the page.

import {shell} from "./target.js";

// The most bytes one call of the shell carries, and how many bytes a browser keeps as
// pieces before it folds them into the one Blob it keeps.
const PIECE = 48 * 1024;
const FOLD = 1024 * 1024;

// Bytes as base64, the alphabet of RFC 4648, section 4, with padding.
export function base64Of(bytes) {
  let text = "";
  for (let at = 0; at < bytes.length; at += 0x8000) {
    text += String.fromCharCode(...bytes.subarray(at, at + 0x8000));
  }
  return btoa(text);
}

class Download {
  constructor(name, type) {
    this.name = name;
    this.type = type;
    this.kept = new Blob([], {type});
    this.pieces = [];
    this.waiting = 0;
  }

  async write(bytes) {
    this.pieces.push(bytes.slice());
    this.waiting += bytes.length;
    if (this.waiting >= FOLD) {
      this.kept = new Blob([this.kept, ...this.pieces], {type: this.type});
      this.pieces = [];
      this.waiting = 0;
    }
  }

  async finish() {
    const whole = new Blob([this.kept, ...this.pieces], {type: this.type});
    this.pieces = [];
    const url = URL.createObjectURL(whole);
    const link = document.createElement("a");
    link.href = url;
    link.download = this.name;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    return {saved: true, name: this.name, bytes: whole.size};
  }

  abandon() {
    this.pieces = [];
    this.kept = null;
  }
}

class Shelled {
  constructor(bridge, name) {
    this.bridge = bridge;
    this.name = name;
    this.bytes = 0;
  }

  async write(bytes) {
    for (let at = 0; at < bytes.length; at += PIECE) {
      await this.bridge.nativePromise("Save", "append", {data: base64Of(bytes.subarray(at, at + PIECE))});
    }
    this.bytes += bytes.length;
  }

  async finish() {
    const result = await this.bridge.nativePromise("Save", "finish", {});
    const saved = result !== null && typeof result === "object" && result.saved === true;
    return {saved, name: saved && typeof result.name === "string" ? result.name : this.name, bytes: this.bytes};
  }

  abandon() {
    // The shell drops the file it holds; it does so too when the next one begins, and when it
    // starts, should this call not reach it.
    this.bridge.nativePromise("Save", "abandon", {}).catch(() => {});
  }
}

// Begins a file of this name and media type. Gives a sink with `write(bytes)`, `finish()`,
// which saves the file and gives `{saved, name, bytes}`, `saved` false when the operator
// closed the dialog without choosing a place, and `abandon()`, which drops what was written.
export async function begin(name, type = "application/octet-stream") {
  const bridge = shell();
  if (bridge === null) return new Download(name, type);
  await bridge.nativePromise("Save", "begin", {name, type});
  return new Shelled(bridge, name);
}
