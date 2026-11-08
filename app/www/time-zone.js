import {crc32} from "./crc32.js";

export const FIRST = 946684800;
export const UNTIL = 4102444800;
const STEP = 21600;
const MAX_TRANSITIONS = 276;
const MAX_OFFSETS = 8;

export class ZoneFailure extends Error {
  constructor(message) { super(message); this.name = "ZoneFailure"; }
}

export function currentZone() {
  const zone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (typeof zone !== "string" || !/^[A-Za-z0-9_+/-]{1,63}$/.test(zone) ||
      zone.startsWith("/") || zone.endsWith("/") || zone.includes("//")) {
    throw new ZoneFailure("The phone's time zone cannot be used by this installation.");
  }
  return zone;
}

export function zoneOffset(zone) {
  let formatter;
  try {
    formatter = new Intl.DateTimeFormat("en-GB", {timeZone: zone, calendar: "gregory", numberingSystem: "latn",
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"});
  } catch {
    throw new ZoneFailure("The phone's time zone is unavailable.");
  }
  return utc => {
    const fields = {};
    for (const part of formatter.formatToParts(new Date(utc * 1000))) {
      if (part.type !== "literal") fields[part.type] = Number(part.value);
    }
    const value = (Date.UTC(fields.year, fields.month - 1, fields.day, fields.hour, fields.minute, fields.second) / 1000) - utc;
    if (!Number.isInteger(value) || Math.abs(value) > 86400) throw new ZoneFailure("The phone's time zone cannot be represented.");
    return value;
  };
}

export function snapshot(zone, offsetAt = zoneOffset(zone)) {
  if (typeof zone !== "string" || !/^[A-Za-z0-9_+/-]{1,63}$/.test(zone) ||
      zone.startsWith("/") || zone.endsWith("/") || zone.includes("//")) {
    throw new ZoneFailure("The phone's time zone cannot be represented.");
  }
  const offsets = [];
  const indexOf = value => {
    if (!Number.isInteger(value) || Math.abs(value) > 86400) throw new ZoneFailure("The phone's time zone cannot be represented.");
    let index = offsets.indexOf(value);
    if (index < 0) {
      if (offsets.length >= MAX_OFFSETS) throw new ZoneFailure("The phone's time zone has too many offset changes.");
      index = offsets.length;
      offsets.push(value);
    }
    return index;
  };
  const transitions = [];
  let at = FIRST;
  let offset = offsetAt(at);
  indexOf(offset);
  while (at < UNTIL - 1) {
    const next = Math.min(at + STEP, UNTIL - 1);
    const after = offsetAt(next);
    if (after !== offset) {
      let low = at;
      let high = next;
      while (high - low > 1) {
        const middle = Math.floor((low + high) / 2);
        if (offsetAt(middle) === offset) low = middle;
        else high = middle;
      }
      if (transitions.length >= MAX_TRANSITIONS) throw new ZoneFailure("The phone's time zone has too many transitions.");
      transitions.push([high, indexOf(after)]);
      offset = after;
    }
    at = next;
  }
  const bytes = new Uint8Array(120 + transitions.length * 5);
  bytes.set(new TextEncoder().encode("ODTZ0001"));
  const view = new DataView(bytes.buffer);
  view.setUint32(8, FIRST, true);
  view.setUint32(12, UNTIL, true);
  bytes[16] = 0;
  bytes[17] = offsets.length;
  view.setUint16(18, transitions.length, true);
  bytes[20] = zone.length;
  offsets.forEach((value, index) => view.setInt32(24 + index * 4, value, true));
  bytes.set(new TextEncoder().encode(zone), 56);
  transitions.forEach(([utc, index], at) => {
    view.setUint32(120 + at * 5, utc, true);
    bytes[124 + at * 5] = index;
  });
  return bytes;
}

let prepared = null;
let pending = null;

export function forgetZone() {
  prepared = null;
  if (pending !== null) {
    const old = pending;
    pending = null;
    old.worker.terminate();
    old.reject(new ZoneFailure("Time-zone preparation was cancelled."));
  }
}

export function prepareZone(zone = currentZone()) {
  if (prepared?.zone === zone) return Promise.resolve(prepared);
  if (pending?.zone === zone) return pending.promise;
  forgetZone();
  let worker;
  try {
    worker = new Worker(new URL("./time-zone-worker.js", import.meta.url), {type: "module"});
  } catch {
    return Promise.reject(new ZoneFailure("The phone could not prepare its time zone. Update Android System WebView and try again."));
  }
  let resolve;
  let reject;
  const promise = new Promise((done, failed) => { resolve = done; reject = failed; });
  const job = {zone, worker, promise, reject};
  pending = job;
  const finish = (result, error) => {
    if (pending !== job) return;
    pending = null;
    worker.terminate();
    if (error !== null) reject(new ZoneFailure(error));
    else { prepared = result; resolve(result); }
  };
  worker.onmessage = event => {
    const value = event.data;
    if (value?.ok !== true || !(value.bytes instanceof Uint8Array) || value.bytes.length < 120 || value.bytes.length > 1500) {
      finish(null, typeof value?.error === "string" ? value.error : "The phone could not prepare its time zone.");
      return;
    }
    const bytes = value.bytes;
    let text = "";
    for (const byte of bytes) text += String.fromCharCode(byte);
    finish({zone, bytes, revision: crc32(bytes), base64: btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")}, null);
  };
  worker.onerror = () => finish(null, "The phone could not prepare its time zone.");
  worker.postMessage({zone});
  return promise;
}
