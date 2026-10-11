// Strict JSON, read from the bytes of a text.
//
// A text is refused when it is not UTF-8, starts with a byte-order mark, is not exactly
// one JSON value, names a member twice in one object, or is nested too deeply. An object
// is a `Map` in the order of the text, an array an `Array`. An integer is a number written
// without a fraction and without an exponent; it is a whole number of `whole.js`. Any
// other number is `NOT_AN_INTEGER`.

import {BAD_JSON, BAD_TYPE, MISSING_MEMBER, OUT_OF_RANGE, Rejection, UNKNOWN_MEMBER} from "./errors.js";

export const LONGEST_INTEGER = 30;
export const DEEPEST = 512;

const HUGE = 10n ** BigInt(LONGEST_INTEGER);
const MARK = 0xfeff;

// A number written with a fraction or an exponent. It passes no integer check.
export const NOT_AN_INTEGER = Symbol("a number with a fraction or an exponent");

const VALUE = 0;
const NAME = 1;
const AFTER = 2;

const SIMPLE_ESCAPES = new Map([
  [0x22, '"'],
  [0x5c, "\\"],
  [0x2f, "/"],
  [0x62, "\b"],
  [0x66, "\f"],
  [0x6e, "\n"],
  [0x72, "\r"],
  [0x74, "\t"],
]);

const WORDS = [
  ["true", true],
  ["false", false],
  ["null", null],
];
const CONSTANTS = ["NaN", "Infinity", "-Infinity"];

function isDigit(code) {
  return code >= 0x30 && code <= 0x39;
}

function hexDigit(code) {
  if (code >= 0x30 && code <= 0x39) {
    return code - 0x30;
  }
  if (code >= 0x61 && code <= 0x66) {
    return code - 0x61 + 10;
  }
  if (code >= 0x41 && code <= 0x46) {
    return code - 0x41 + 10;
  }
  return -1;
}

// The value of a JSON text given as bytes.
export function loads(bytes) {
  if (!(bytes instanceof Uint8Array)) {
    throw new TypeError("a JSON text is given as a Uint8Array");
  }
  let text;
  try {
    text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(bytes);
  } catch (error) {
    throw new Rejection(BAD_JSON, "not UTF-8");
  }
  if (text.charCodeAt(0) === MARK) {
    throw new Rejection(BAD_JSON, "starts with a byte-order mark");
  }
  return value(text);
}

function value(text) {
  const length = text.length;
  let at = 0;

  const fail = (what, position = at) => {
    let line = 1;
    let lineStart = 0;
    for (let i = text.indexOf("\n"); i >= 0 && i < position; i = text.indexOf("\n", i + 1)) {
      line += 1;
      lineStart = i + 1;
    }
    throw new Rejection(BAD_JSON, `line ${line}, column ${position - lineStart + 1}: ${what}`);
  };

  const skip = () => {
    while (at < length) {
      const code = text.charCodeAt(at);
      if (code !== 0x20 && code !== 0x0a && code !== 0x0d && code !== 0x09) {
        break;
      }
      at += 1;
    }
  };

  const string = () => {
    const opened = at;
    at += 1;
    let begin = at;
    let pieces = "";
    for (;;) {
      if (at >= length) {
        fail("the string that begins here does not end", opened);
      }
      const code = text.charCodeAt(at);
      if (code === 0x22) {
        const whole = pieces + text.slice(begin, at);
        at += 1;
        return whole;
      }
      if (code < 0x20) {
        fail("a string holds a control character");
      }
      if (code !== 0x5c) {
        at += 1;
        continue;
      }
      pieces += text.slice(begin, at);
      const escape = at + 1 < length ? text.charCodeAt(at + 1) : -1;
      if (SIMPLE_ESCAPES.has(escape)) {
        pieces += SIMPLE_ESCAPES.get(escape);
        at += 2;
      } else if (escape === 0x75) {
        let unit = 0;
        for (let i = 2; i < 6; i += 1) {
          const digit = at + i < length ? hexDigit(text.charCodeAt(at + i)) : -1;
          if (digit < 0) {
            fail("four hexadecimal digits are expected after \\u");
          }
          unit = unit * 16 + digit;
        }
        pieces += String.fromCharCode(unit);
        at += 6;
      } else {
        fail("a string holds an escape that JSON does not have");
      }
      begin = at;
    }
  };

  const number = () => {
    const start = at;
    const negative = text.charCodeAt(at) === 0x2d;
    if (negative) {
      at += 1;
    }
    const first = at < length ? text.charCodeAt(at) : -1;
    if (!isDigit(first)) {
      fail(negative ? "a digit is expected after the minus sign" : "a value is expected", negative ? at : start);
    }
    let small = 0;
    at += 1;
    if (first !== 0x30) {
      small = first - 0x30;
      while (at < length && isDigit(text.charCodeAt(at))) {
        small = small * 10 + (text.charCodeAt(at) - 0x30);
        at += 1;
      }
    }
    const digits = at - start;
    let integer = true;
    if (at < length && text.charCodeAt(at) === 0x2e) {
      if (!(at + 1 < length && isDigit(text.charCodeAt(at + 1)))) {
        fail("a digit is expected after the point", at + 1);
      }
      integer = false;
      at += 2;
      while (at < length && isDigit(text.charCodeAt(at))) {
        at += 1;
      }
    }
    if (at < length && (text.charCodeAt(at) === 0x65 || text.charCodeAt(at) === 0x45)) {
      let digit = at + 1;
      if (digit < length && (text.charCodeAt(digit) === 0x2b || text.charCodeAt(digit) === 0x2d)) {
        digit += 1;
      }
      if (!(digit < length && isDigit(text.charCodeAt(digit)))) {
        fail("a digit is expected in the exponent", digit);
      }
      integer = false;
      at = digit + 1;
      while (at < length && isDigit(text.charCodeAt(at))) {
        at += 1;
      }
    }
    if (!integer) {
      return NOT_AN_INTEGER;
    }
    if (digits > LONGEST_INTEGER) {
      return negative ? -HUGE : HUGE;
    }
    if (digits <= 15) {
      return negative && small !== 0 ? -small : small;
    }
    const exact = BigInt(text.slice(start, at));
    return exact >= -BigInt(Number.MAX_SAFE_INTEGER) && exact <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(exact) : exact;
  };

  const scalar = () => {
    for (const word of CONSTANTS) {
      if (text.startsWith(word, at)) {
        throw new Rejection(BAD_JSON, `${word} is not a JSON value`);
      }
    }
    const code = text.charCodeAt(at);
    if (code === 0x2d || isDigit(code)) {
      return number();
    }
    for (const [word, meaning] of WORDS) {
      if (text.startsWith(word, at)) {
        at += word.length;
        return meaning;
      }
    }
    return fail("a value is expected");
  };

  const object = (pairs) => {
    const members = new Map();
    for (let i = 0; i < pairs.length; i += 2) {
      if (members.has(pairs[i])) {
        throw new Rejection(BAD_JSON, `member "${pairs[i]}" appears twice in one object`);
      }
      members.set(pairs[i], pairs[i + 1]);
    }
    return members;
  };

  // The arrays and objects that are open, the innermost last. An array is held as its
  // items; an object as its names and values in turn, with the name that waits for its
  // value.
  const open = [];
  const deeper = () => {
    if (open.length >= DEEPEST) {
      throw new Rejection(BAD_JSON, "nested too deeply");
    }
  };

  let state = VALUE;
  let done;
  for (;;) {
    skip();
    const code = at < length ? text.charCodeAt(at) : -1;
    if (state === VALUE) {
      if (code < 0) {
        fail("the text ends where a value is expected");
      }
      state = AFTER;
      if (code === 0x5b) {
        deeper();
        at += 1;
        skip();
        if (at < length && text.charCodeAt(at) === 0x5d) {
          at += 1;
          done = [];
        } else {
          open.push({items: []});
          state = VALUE;
        }
      } else if (code === 0x7b) {
        deeper();
        at += 1;
        skip();
        if (at < length && text.charCodeAt(at) === 0x7d) {
          at += 1;
          done = new Map();
        } else {
          open.push({pairs: [], name: null});
          state = NAME;
        }
      } else if (code === 0x22) {
        done = string();
      } else {
        done = scalar();
      }
    } else if (state === NAME) {
      if (code !== 0x22) {
        fail("a member name in double quotes is expected");
      }
      const name = string();
      skip();
      if (!(at < length && text.charCodeAt(at) === 0x3a)) {
        fail("a colon is expected after a member name");
      }
      at += 1;
      open[open.length - 1].name = name;
      state = VALUE;
    } else if (open.length === 0) {
      if (code >= 0) {
        fail("there is text after the value");
      }
      return done;
    } else {
      const inner = open[open.length - 1];
      if (inner.items !== undefined) {
        inner.items.push(done);
        if (code === 0x2c) {
          at += 1;
          state = VALUE;
        } else if (code === 0x5d) {
          at += 1;
          open.pop();
          done = inner.items;
        } else {
          fail("a comma or the end of the array is expected");
        }
      } else {
        inner.pairs.push(inner.name, done);
        if (code === 0x2c) {
          at += 1;
          state = NAME;
        } else if (code === 0x7d) {
          at += 1;
          open.pop();
          done = object(inner.pairs);
        } else {
          fail("a comma or the end of the object is expected");
        }
      }
    }
  }
}

// Checks that `obj` is an object with every required member and no unlisted one.
export function members(obj, required, optional = [], what = "the file") {
  if (!(obj instanceof Map)) {
    throw new Rejection(BAD_TYPE, `${what} is not an object`);
  }
  for (const name of required) {
    if (!obj.has(name)) {
      throw new Rejection(MISSING_MEMBER, `${what} has no member "${name}"`);
    }
  }
  for (const name of obj.keys()) {
    if (!required.includes(name) && !optional.includes(name)) {
      throw new Rejection(UNKNOWN_MEMBER, `${what} has the unknown member "${name}"`);
    }
  }
}

// Checks that `value` is an integer from `low` to `high` and gives it back. A bound that
// is null is not checked.
export function integer(value, low = null, high = null, what = "a value") {
  if (typeof value !== "number" && typeof value !== "bigint") {
    throw new Rejection(BAD_TYPE, `${what} is not an integer`);
  }
  if (low !== null && value < low) {
    throw new Rejection(OUT_OF_RANGE, `${what} is below ${low}`);
  }
  if (high !== null && value > high) {
    throw new Rejection(OUT_OF_RANGE, `${what} is above ${high}`);
  }
  return value;
}

// Checks that `value` is an array and gives it back.
export function array(value, what = "a value") {
  if (!Array.isArray(value)) {
    throw new Rejection(BAD_TYPE, `${what} is not an array`);
  }
  return value;
}
