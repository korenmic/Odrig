// The mapping file of docs/mapping.md: the canvas size and the legs of one physical build.
//
// A file is a row-leg file or a column-leg file. A strip is one straight run of LEDs of a
// leg: a row of the canvas in a row-leg file, a column in a column-leg file.

import {BAD_JSON, BAD_VERSION, MAPPING_MALFORMED, MISSING_MEMBER, Rejection} from "./errors.js";
import * as strictjson from "./strictjson.js";

export const VERSION = 1;
export const LONGEST_STRIP = 65535;
export const LARGEST_CANVAS = 65534;

export const ROWS = "rows";
export const COLUMNS = "columns";

// The names of one kind of file. `length` is the top-level member that gives the number of
// LEDs in every strip. `strips` is the member of a leg that lists its strips, and `strip`
// is what one of them is called. `ends` are the two values of `first_led`: the end of a
// strip where x or y is 1, then the other end.
const NAMES = {
  [ROWS]: {length: "width", strips: "rows", strip: "row", ends: ["left", "right"]},
  [COLUMNS]: {length: "height", strips: "columns", strip: "column", ends: ["bottom", "top"]},
};

// The number of LEDs in every strip of a mapping.
export function stripLength(mapping) {
  return mapping.kind === ROWS ? mapping.width : mapping.height;
}

// The number of LEDs of a leg of a mapping.
export function ledCount(mapping, leg) {
  return stripLength(mapping) * leg.strips.length;
}

function malformed(detail) {
  return new Rejection(MAPPING_MALFORMED, detail);
}

// Reads a mapping file given as bytes. Every broken rule is `mapping-malformed`.
//
// The result is `{kind, width, height, legs}`: `kind` is ROWS or COLUMNS, and each leg is
// `{leg, pin, firstLed, strips}`, with the y of each row or the x of each column in chain
// order.
export function loads(bytes) {
  try {
    return read(bytes);
  } catch (error) {
    if (!(error instanceof Rejection) || error.reason === MAPPING_MALFORMED) {
      throw error;
    }
    throw malformed(`${error.reason}: ${error.detail}`);
  }
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
  if (top.has("width") && top.has("height")) {
    throw malformed('the file has both "width" and "height"');
  }
  if (!top.has("width") && !top.has("height")) {
    throw malformed('the file has neither "width" nor "height"');
  }
  const kind = top.has("width") ? ROWS : COLUMNS;
  const names = NAMES[kind];
  strictjson.members(top, ["version", names.length, "legs"]);
  const length = strictjson.integer(top.get(names.length), 1, LONGEST_STRIP, names.length);
  const listed = strictjson.array(top.get("legs"), "legs");
  if (listed.length === 0) {
    throw malformed("legs is empty");
  }

  const legs = [];
  const numbers = new Set();
  const pins = new Set();
  for (let place = 1; place <= listed.length; place += 1) {
    const entry = listed[place - 1];
    const what = `entry ${place} of legs`;
    strictjson.members(entry, ["leg", "pin", "first_led", names.strips], [], what);
    const number = strictjson.integer(entry.get("leg"), 1, 255, `leg of ${what}`);
    if (numbers.has(number)) {
      throw malformed(`two legs have the number ${number}`);
    }
    numbers.add(number);
    const pin = strictjson.integer(entry.get("pin"), 0, 255, `pin of leg ${number}`);
    if (pins.has(pin)) {
      throw malformed(`two legs have the pin ${pin}`);
    }
    pins.add(pin);
    const firstLed = entry.get("first_led");
    if (typeof firstLed !== "string" || !names.ends.includes(firstLed)) {
      throw malformed(`first_led of leg ${number} is not "${names.ends[0]}" or "${names.ends[1]}"`);
    }
    const strips = strictjson.array(entry.get(names.strips), `${names.strips} of leg ${number}`);
    if (strips.length === 0) {
      throw malformed(`${names.strips} of leg ${number} is empty`);
    }
    for (const strip of strips) {
      strictjson.integer(strip, null, null, `a ${names.strip} of leg ${number}`);
    }
    legs.push({leg: number, pin, firstLed, strips: strips.slice()});
  }

  let total = 0;
  for (const leg of legs) {
    total += leg.strips.length;
  }
  const seen = new Set();
  for (const leg of legs) {
    for (const strip of leg.strips) {
      if (strip < 1 || strip > total) {
        throw malformed(`${names.strip} ${strip} of leg ${leg.leg} is not from 1 to ${total}, the number of ${names.strips}`);
      }
      if (seen.has(strip)) {
        throw malformed(`${names.strip} ${strip} is listed twice`);
      }
      seen.add(strip);
    }
  }
  const width = kind === ROWS ? length : total;
  const height = kind === ROWS ? total : length;
  if (width * height > LARGEST_CANVAS) {
    throw malformed(`the canvas of ${width} x ${height} has ${width * height} pixels, above ${LARGEST_CANVAS}`);
  }
  return {kind, width, height, legs};
}
