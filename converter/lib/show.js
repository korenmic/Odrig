// The show file of docs/show.md: the items that can be played and what plays at power-on.

import {
  BAD_JSON,
  BAD_TYPE,
  BAD_VERSION,
  DUPLICATE_ID,
  MISSING_MEMBER,
  NESTED_CYCLE,
  Rejection,
  SHOW_MALFORMED,
  UNDEFINED_ID,
} from "./errors.js";
import * as strictjson from "./strictjson.js";

export const VERSION = 1;
export const LARGEST_ID = 65535;
export const LONGEST_TURN = 65535;
export const FILE_NAME = /^[a-z0-9._-]{1,32}$/;
export const ENDING = ".odrg";

const MEMBERS = ["version", "brightness", "items"];
const OPTIONAL = ["start"];
const ANIMATION_MEMBERS = ["id", "file"];
const CYCLE_MEMBERS = ["id", "cycle", "seconds"];

// Reads a show file given as bytes: its format first, then its ids.
//
// The result is `{brightness, items, start}`. An item is `{id, file, cycle, seconds}`: an
// animation has a `file` and null for the other two, a cycle has `cycle`, the ids it names
// in order, and `seconds`, and null for `file`. `start` is null when the file has none.
export function loads(bytes) {
  let show;
  try {
    show = read(bytes);
  } catch (error) {
    if (!(error instanceof Rejection)) {
      throw error;
    }
    throw new Rejection(SHOW_MALFORMED, `${error.reason}: ${error.detail}`);
  }
  checkIds(show);
  return show;
}

// The different file names the show uses, in the order of their first use.
export function files(show) {
  const names = [];
  for (const item of show.items) {
    if (item.file !== null && !names.includes(item.file)) {
      names.push(item.file);
    }
  }
  return names;
}

function malformed(detail) {
  return new Rejection(SHOW_MALFORMED, detail);
}

function read(bytes) {
  const top = strictjson.loads(bytes);
  if (!(top instanceof Map)) {
    throw new Rejection(BAD_JSON, "the top level is not an object");
  }
  if (!top.has("version")) {
    throw new Rejection(MISSING_MEMBER, 'the file has no member "version"');
  }
  const version = strictjson.integer(top.get("version"), null, null, "version");
  if (version !== VERSION) {
    throw new Rejection(BAD_VERSION, `version is ${version}, not ${VERSION}`);
  }
  strictjson.members(top, MEMBERS, OPTIONAL);
  const brightness = strictjson.integer(top.get("brightness"), 0, 255, "brightness");
  const listed = strictjson.array(top.get("items"), "items");
  if (listed.length === 0) {
    throw malformed("items is empty");
  }
  const items = listed.map((entry, position) => itemOf(entry, `entry ${position + 1} of items`));
  const start = top.has("start") ? strictjson.integer(top.get("start"), null, null, "start") : null;
  return {brightness, items, start};
}

function itemOf(entry, what) {
  if (!(entry instanceof Map)) {
    throw new Rejection(BAD_TYPE, `${what} is not an object`);
  }
  if (entry.has("file")) {
    strictjson.members(entry, ANIMATION_MEMBERS, [], what);
  } else {
    strictjson.members(entry, CYCLE_MEMBERS, [], what);
  }
  const number = strictjson.integer(entry.get("id"), 1, LARGEST_ID, `id of ${what}`);
  if (entry.has("file")) {
    const name = entry.get("file");
    if (typeof name !== "string") {
      throw new Rejection(BAD_TYPE, `file of item ${number} is not a string`);
    }
    if (!FILE_NAME.test(name) || !name.endsWith(ENDING)) {
      throw malformed(`file of item ${number} is not 1 to 32 characters from a-z, 0-9, -, _ and . ending in ${ENDING}`);
    }
    return {id: number, file: name, cycle: null, seconds: null};
  }
  const cycle = strictjson.array(entry.get("cycle"), `cycle of item ${number}`);
  if (cycle.length === 0) {
    throw malformed(`cycle of item ${number} is empty`);
  }
  for (const named of cycle) {
    strictjson.integer(named, null, null, `an entry of the cycle of item ${number}`);
  }
  const seconds = strictjson.integer(entry.get("seconds"), 1, LONGEST_TURN, `seconds of item ${number}`);
  return {id: number, file: null, cycle: cycle.slice(), seconds};
}

// Repeated ids first, then ids that no item has, then cycles that name a cycle.
function checkIds(show) {
  const kinds = new Map();
  for (const item of show.items) {
    if (kinds.has(item.id)) {
      throw new Rejection(DUPLICATE_ID, `two items have the id ${item.id}`);
    }
    kinds.set(item.id, item.cycle !== null ? "cycle" : "animation");
  }
  for (const item of show.items) {
    for (const named of item.cycle === null ? [] : item.cycle) {
      if (!kinds.has(named)) {
        throw new Rejection(UNDEFINED_ID, `the cycle of item ${item.id} names the id ${named}, which no item has`);
      }
    }
  }
  if (show.start !== null && !kinds.has(show.start)) {
    throw new Rejection(UNDEFINED_ID, `start names the id ${show.start}, which no item has`);
  }
  for (const item of show.items) {
    for (const named of item.cycle === null ? [] : item.cycle) {
      if (kinds.get(named) === "cycle") {
        throw new Rejection(NESTED_CYCLE, `the cycle of item ${item.id} names item ${named}, which is a cycle`);
      }
    }
  }
}
