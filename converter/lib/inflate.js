// Raw DEFLATE (RFC 1951), decoded: stored, fixed and dynamic blocks, distances up to
// 32,768.
//
// Each defect of a stream is judged at the point where zlib judges it, so a stream that is
// both wrong and cut short gets the verdict zlib gives: the counts of a dynamic block when
// its 14 bits are read; the code of the code lengths when all its lengths are read; a
// repeat when its extra bits are read; the two codes of a block when all their lengths are
// read, the missing end-of-block code first; a bit pattern that is no code once as many
// bits are read as the longest code has; a length or distance symbol that does not exist
// when it is decoded; a distance beyond the output when its extra bits are read. An input
// that ends before any of these is truncated.

import {BAD_DEFLATE, Rejection, TRUNCATED} from "./errors.js";

const MOST_LENGTH_CODES = 286;
const MOST_DISTANCE_CODES = 30;
const LONGEST_CODE = 15;
const END_OF_BLOCK = 256;

const LENGTH_BASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258];
const LENGTH_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0];
const DISTANCE_BASE = [
  1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289,
  16385, 24577,
];
const DISTANCE_EXTRA = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13];

// The order in which a dynamic block lists the lengths of its code of code lengths.
const CODE_LENGTH_ORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];

function table(symbols) {
  return {count: new Uint16Array(LONGEST_CODE + 1), symbols: new Uint16Array(symbols), longest: 0};
}

// Builds the two tables of a code from the length of each of its `n` symbols, which start
// at `start` of `lengths`; a length of zero means the symbol has no code. Sets `longest` to
// the longest length in use. Gives 0 for a complete code, a number above 0 for a code that
// leaves bit patterns unused, and one below 0 for lengths no code can have.
function construct(lengths, start, n, into) {
  const {count, symbols} = into;
  count.fill(0);
  for (let i = 0; i < n; i += 1) {
    count[lengths[start + i]] += 1;
  }
  into.longest = 0;
  let left = 1;
  for (let length = 1; length <= LONGEST_CODE; length += 1) {
    if (count[length] !== 0) {
      into.longest = length;
    }
    left = left * 2 - count[length];
    if (left < 0) {
      return left;
    }
  }
  const offset = new Uint16Array(LONGEST_CODE + 2);
  for (let length = 1; length < LONGEST_CODE; length += 1) {
    offset[length + 1] = offset[length] + count[length];
  }
  for (let i = 0; i < n; i += 1) {
    const length = lengths[start + i];
    if (length !== 0) {
      symbols[offset[length]] = i;
      offset[length] += 1;
    }
  }
  return left;
}

// Decodes one raw DEFLATE stream that starts at the first byte of `bytes`.
//
// The result is `{data, used}`: the output of the stream and the number of bytes of input
// the stream took. A stream that is not valid is rejected as `bad-deflate`, and an input
// that ends before the last block is complete as `truncated`.
export function inflateRaw(bytes) {
  const size = bytes.length;
  let at = 0;
  let hold = 0;
  let held = 0;
  let out = new Uint8Array(Math.max(1024, 4 * size));
  let produced = 0;

  const bad = (what) => new Rejection(BAD_DEFLATE, what);
  const cut = () => new Rejection(TRUNCATED, "the file ends inside the DEFLATE stream");

  const room = (more) => {
    if (produced + more > out.length) {
      const larger = new Uint8Array(Math.max(2 * out.length, produced + more));
      larger.set(out.subarray(0, produced));
      out = larger;
    }
  };

  // The next `count` bits of the input as a number, the first bit lowest; `count` is at
  // most 16. A byte of input is taken only when a bit of it is needed.
  const bits = (count) => {
    while (held < count) {
      if (at >= size) {
        throw cut();
      }
      hold |= bytes[at] << held;
      at += 1;
      held += 8;
    }
    const value = hold & ((1 << count) - 1);
    hold >>>= count;
    held -= count;
    return value;
  };

  // Decodes one symbol of a code, a bit at a time. A bit pattern that is no code of the set
  // is refused as soon as it is as long as the longest code, and after one bit when the set
  // has no code at all.
  const symbol = (code) => {
    const {count, symbols, longest} = code;
    let pattern = 0;
    let first = 0;
    let index = 0;
    for (let length = 1; ; length += 1) {
      if (held === 0) {
        if (at >= size) {
          throw cut();
        }
        hold = bytes[at];
        at += 1;
        held = 8;
      }
      pattern |= hold & 1;
      hold >>>= 1;
      held -= 1;
      const codes = count[length];
      if (pattern - codes < first) {
        return symbols[index + (pattern - first)];
      }
      if (length >= longest) {
        throw bad("a bit pattern is no code of its block");
      }
      index += codes;
      first = (first + codes) * 2;
      pattern *= 2;
    }
  };

  const lengths = new Uint8Array(MOST_LENGTH_CODES + MOST_DISTANCE_CODES + 2);
  const lengthCode = table(288);
  const distanceCode = table(MOST_DISTANCE_CODES);
  const codeLengthCode = table(19);

  const fixedCodes = () => {
    lengths.fill(8, 0, 144);
    lengths.fill(9, 144, 256);
    lengths.fill(7, 256, 280);
    lengths.fill(8, 280, 288);
    construct(lengths, 0, 288, lengthCode);
    lengths.fill(5, 0, MOST_DISTANCE_CODES);
    construct(lengths, 0, MOST_DISTANCE_CODES, distanceCode);
  };

  const dynamicCodes = () => {
    const counts = bits(14);
    const lengthCodes = (counts & 31) + 257;
    const distanceCodes = ((counts >> 5) & 31) + 1;
    const listed = (counts >> 10) + 4;
    if (lengthCodes > MOST_LENGTH_CODES || distanceCodes > MOST_DISTANCE_CODES) {
      throw bad("a block lists more codes than there are");
    }

    const codeLengths = new Uint8Array(19);
    for (let i = 0; i < listed; i += 1) {
      codeLengths[CODE_LENGTH_ORDER[i]] = bits(3);
    }
    if (construct(codeLengths, 0, 19, codeLengthCode) !== 0 && codeLengthCode.longest !== 0) {
      throw bad("the lengths of the code of code lengths make no code");
    }

    const total = lengthCodes + distanceCodes;
    let have = 0;
    while (have < total) {
      let coded;
      if (codeLengthCode.longest === 0) {
        // A code of code lengths without codes: every length takes one bit and is zero.
        bits(1);
        coded = 0;
      } else {
        coded = symbol(codeLengthCode);
      }
      if (coded < 16) {
        lengths[have] = coded;
        have += 1;
        continue;
      }
      let repeated = 0;
      let times;
      if (coded === 16) {
        times = 3 + bits(2);
        if (have === 0) {
          throw bad("a block repeats a code length before the first one");
        }
        repeated = lengths[have - 1];
      } else if (coded === 17) {
        times = 3 + bits(3);
      } else {
        times = 11 + bits(7);
      }
      if (have + times > total) {
        throw bad("a block repeats a code length beyond its last code");
      }
      lengths.fill(repeated, have, have + times);
      have += times;
    }

    if (lengths[END_OF_BLOCK] === 0) {
      throw bad("a block has no code for its end");
    }
    let left = construct(lengths, 0, lengthCodes, lengthCode);
    if (left < 0 || (left > 0 && lengthCode.longest !== 1)) {
      throw bad("the lengths of the literal and length codes make no code");
    }
    left = construct(lengths, lengthCodes, distanceCodes, distanceCode);
    if (left < 0 || (left > 0 && distanceCode.longest > 1)) {
      throw bad("the lengths of the distance codes make no code");
    }
  };

  const coded = () => {
    for (;;) {
      let found = symbol(lengthCode);
      if (found < END_OF_BLOCK) {
        room(1);
        out[produced] = found;
        produced += 1;
        continue;
      }
      if (found === END_OF_BLOCK) {
        return;
      }
      if (found > 285) {
        throw bad("a length symbol that does not exist");
      }
      found -= 257;
      const length = LENGTH_BASE[found] + bits(LENGTH_EXTRA[found]);
      found = symbol(distanceCode);
      if (found > 29) {
        throw bad("a distance symbol that does not exist");
      }
      const distance = DISTANCE_BASE[found] + bits(DISTANCE_EXTRA[found]);
      if (distance > produced) {
        throw bad("a distance reaches back beyond the start of the output");
      }
      room(length);
      for (let i = 0; i < length; i += 1) {
        out[produced] = out[produced - distance];
        produced += 1;
      }
    }
  };

  // A stored block starts at the next whole byte with its length, twice.
  const stored = () => {
    hold = 0;
    held = 0;
    if (at + 4 > size) {
      throw cut();
    }
    const length = bytes[at] | (bytes[at + 1] << 8);
    const complement = bytes[at + 2] | (bytes[at + 3] << 8);
    at += 4;
    if (length !== (complement ^ 0xffff)) {
      throw bad("the two lengths of a stored block do not agree");
    }
    if (at + length > size) {
      throw cut();
    }
    room(length);
    out.set(bytes.subarray(at, at + length), produced);
    produced += length;
    at += length;
  };

  for (;;) {
    const header = bits(3);
    const kind = header >> 1;
    if (kind === 0) {
      stored();
    } else if (kind === 1) {
      fixedCodes();
      coded();
    } else if (kind === 2) {
      dynamicCodes();
      coded();
    } else {
      throw bad("a block of a kind that does not exist");
    }
    if ((header & 1) === 1) {
      return {data: out.slice(0, produced), used: at};
    }
  }
}

// The same raw DEFLATE stream decoded a part at a time, holding only the 32,768
// bytes the distances reach back into and the output not given yet.
//
// `push(bytes)` gives it input, `end()` says the input has ended, and `pull(limit)` decodes
// until about `limit` bytes of output are ready, the input runs out, or the stream ends, and
// gives that output. `finished` says the last block was read, `used` how many bytes of input
// the stream took, `wanting` that it waits for input, and `held` the bytes of output it holds.
// Its verdicts, reason and detail, are those of `inflateRaw` for the same input; `truncated`
// comes only after the end of the input is told, and the output given before a verdict is a
// prefix of what `inflateRaw` gives.
export function inflateStream() {
  const RING = 1 << 17;
  const MASK = RING - 1;
  const REACH = 32768;
  const MOST_PULL = 65536;
  const NEED = {};
  let input = new Uint8Array(4096);
  let base = 0;
  let filled = 0;
  let at = 0;
  let hold = 0;
  let held = 0;
  let ended = false;
  const ring = new Uint8Array(RING);
  let produced = 0;
  let given = 0;
  let finished = false;
  let last = false;
  let block = null;
  let stored = 0;
  let wanting = false;

  const bad = (what) => new Rejection(BAD_DEFLATE, what);
  const cut = () => new Rejection(TRUNCATED, "the file ends inside the DEFLATE stream");

  const bits = (count) => {
    while (held < count) {
      if (at >= filled) {
        throw NEED;
      }
      hold |= input[at - base] << held;
      at += 1;
      held += 8;
    }
    const value = hold & ((1 << count) - 1);
    hold >>>= count;
    held -= count;
    return value;
  };

  const symbol = (code) => {
    const {count, symbols, longest} = code;
    let pattern = 0;
    let first = 0;
    let index = 0;
    for (let length = 1; ; length += 1) {
      if (held === 0) {
        if (at >= filled) {
          throw NEED;
        }
        hold = input[at - base];
        at += 1;
        held = 8;
      }
      pattern |= hold & 1;
      hold >>>= 1;
      held -= 1;
      const codes = count[length];
      if (pattern - codes < first) {
        return symbols[index + (pattern - first)];
      }
      if (length >= longest) {
        throw bad("a bit pattern is no code of its block");
      }
      index += codes;
      first = (first + codes) * 2;
      pattern *= 2;
    }
  };

  const lengths = new Uint8Array(MOST_LENGTH_CODES + MOST_DISTANCE_CODES + 2);
  const lengthCode = table(288);
  const distanceCode = table(MOST_DISTANCE_CODES);
  const codeLengthCode = table(19);

  const fixedCodes = () => {
    lengths.fill(8, 0, 144);
    lengths.fill(9, 144, 256);
    lengths.fill(7, 256, 280);
    lengths.fill(8, 280, 288);
    construct(lengths, 0, 288, lengthCode);
    lengths.fill(5, 0, MOST_DISTANCE_CODES);
    construct(lengths, 0, MOST_DISTANCE_CODES, distanceCode);
  };

  const dynamicCodes = () => {
    const counts = bits(14);
    const lengthCodes = (counts & 31) + 257;
    const distanceCodes = ((counts >> 5) & 31) + 1;
    const listed = (counts >> 10) + 4;
    if (lengthCodes > MOST_LENGTH_CODES || distanceCodes > MOST_DISTANCE_CODES) {
      throw bad("a block lists more codes than there are");
    }
    const codeLengths = new Uint8Array(19);
    for (let i = 0; i < listed; i += 1) {
      codeLengths[CODE_LENGTH_ORDER[i]] = bits(3);
    }
    if (construct(codeLengths, 0, 19, codeLengthCode) !== 0 && codeLengthCode.longest !== 0) {
      throw bad("the lengths of the code of code lengths make no code");
    }
    const total = lengthCodes + distanceCodes;
    let have = 0;
    while (have < total) {
      let coded;
      if (codeLengthCode.longest === 0) {
        bits(1);
        coded = 0;
      } else {
        coded = symbol(codeLengthCode);
      }
      if (coded < 16) {
        lengths[have] = coded;
        have += 1;
        continue;
      }
      let repeated = 0;
      let times;
      if (coded === 16) {
        times = 3 + bits(2);
        if (have === 0) {
          throw bad("a block repeats a code length before the first one");
        }
        repeated = lengths[have - 1];
      } else if (coded === 17) {
        times = 3 + bits(3);
      } else {
        times = 11 + bits(7);
      }
      if (have + times > total) {
        throw bad("a block repeats a code length beyond its last code");
      }
      lengths.fill(repeated, have, have + times);
      have += times;
    }
    if (lengths[END_OF_BLOCK] === 0) {
      throw bad("a block has no code for its end");
    }
    let left = construct(lengths, 0, lengthCodes, lengthCode);
    if (left < 0 || (left > 0 && lengthCode.longest !== 1)) {
      throw bad("the lengths of the literal and length codes make no code");
    }
    left = construct(lengths, lengthCodes, distanceCodes, distanceCode);
    if (left < 0 || (left > 0 && distanceCode.longest > 1)) {
      throw bad("the lengths of the distance codes make no code");
    }
  };

  // One step of the stream: a block's header and codes, a literal, a length with its
  // distance, the end of a block, or a part of a stored block. Gives false when the input ran
  // out before the step was whole; nothing of the step is kept then, and it is read again
  // when more input has come.
  const unit = () => {
    const saved = [at, hold, held];
    try {
      if (block === null) {
        const header = bits(3);
        const kind = header >> 1;
        if (kind === 0) {
          hold = 0;
          held = 0;
          if (at + 4 > filled) {
            throw NEED;
          }
          const length = input[at - base] | (input[at - base + 1] << 8);
          const complement = input[at - base + 2] | (input[at - base + 3] << 8);
          at += 4;
          if (length !== (complement ^ 0xffff)) {
            throw bad("the two lengths of a stored block do not agree");
          }
          stored = length;
          block = "stored";
        } else if (kind === 1) {
          fixedCodes();
          block = "coded";
        } else if (kind === 2) {
          dynamicCodes();
          block = "coded";
        } else {
          throw bad("a block of a kind that does not exist");
        }
        last = (header & 1) === 1;
        if (block === "stored" && stored === 0) {
          block = null;
          finished = last;
        }
      } else if (block === "stored") {
        const count = Math.min(stored, filled - at, MOST_PULL);
        if (count === 0) {
          throw NEED;
        }
        for (let i = 0; i < count; i += 1) {
          ring[produced & MASK] = input[at - base + i];
          produced += 1;
        }
        at += count;
        stored -= count;
        if (stored === 0) {
          block = null;
          finished = last;
        }
      } else {
        let found = symbol(lengthCode);
        if (found < END_OF_BLOCK) {
          ring[produced & MASK] = found;
          produced += 1;
        } else if (found === END_OF_BLOCK) {
          block = null;
          finished = last;
        } else {
          if (found > 285) {
            throw bad("a length symbol that does not exist");
          }
          found -= 257;
          const length = LENGTH_BASE[found] + bits(LENGTH_EXTRA[found]);
          found = symbol(distanceCode);
          if (found > 29) {
            throw bad("a distance symbol that does not exist");
          }
          const distance = DISTANCE_BASE[found] + bits(DISTANCE_EXTRA[found]);
          if (distance > produced) {
            throw bad("a distance reaches back beyond the start of the output");
          }
          for (let i = 0; i < length; i += 1) {
            ring[produced & MASK] = ring[(produced - distance) & MASK];
            produced += 1;
          }
        }
      }
      return true;
    } catch (error) {
      if (error !== NEED) {
        throw error;
      }
      [at, hold, held] = saved;
      if (ended) {
        throw cut();
      }
      return false;
    }
  };

  return {
    push(bytes) {
      if (ended) {
        throw new Error("the input has ended");
      }
      // The input taken already is dropped, and what is left kept at the start.
      if (at - base > input.length / 2) {
        input.copyWithin(0, at - base, filled - base);
        base = at;
      }
      const need = filled - base + bytes.length;
      if (need > input.length) {
        const larger = new Uint8Array(Math.max(2 * input.length, need));
        larger.set(input.subarray(0, filled - base));
        input = larger;
      }
      input.set(bytes, filled - base);
      filled += bytes.length;
    },
    end() {
      ended = true;
    },
    pull(limit = MOST_PULL) {
      const most = Math.min(limit, MOST_PULL);
      wanting = false;
      while (!finished && produced - given < most) {
        if (!unit()) {
          wanting = true;
          break;
        }
      }
      const count = produced - given;
      const out = new Uint8Array(count);
      for (let i = 0; i < count; i += 1) {
        out[i] = ring[(given + i) & MASK];
      }
      given = produced;
      return out;
    },
    get finished() {
      return finished;
    },
    get wanting() {
      return wanting;
    },
    get used() {
      return at;
    },
    get held() {
      return Math.min(produced, REACH) + (produced - given);
    },
  };
}
