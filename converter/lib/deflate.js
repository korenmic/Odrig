// Raw DEFLATE (RFC 1951), compressed, by the method of zlib at its highest level.
//
// The matches are found with a hash of three bytes and chains of earlier positions, the
// longest one along at most 4,096 positions, and a match is written only when the match at
// the next position is not longer. A block ends after 16,383 symbols and is written in the
// smallest of three forms: stored, with the fixed codes, or with codes made for the block.
// Everything is whole-number arithmetic, so the same input gives the same stream wherever
// this runs.

const MIN_MATCH = 3;
const MAX_MATCH = 258;
// How far back the format lets a distance reach, and how far back a match is looked for.
const REACH = 32768;
const REACH_MASK = REACH - 1;
const FARTHEST = REACH - (MAX_MATCH + MIN_MATCH + 1);
const HASH_SIZE = 32768;
const HASH_MASK = HASH_SIZE - 1;

const LONGEST_CHAIN = 4096;
const GOOD_LENGTH = 32;
const NICE_LENGTH = 258;
const LAZY_LENGTH = 258;
const TOO_FAR = 4096;
const BLOCK_SYMBOLS = 16383;
const LARGEST_STORED = 65535;

const LITERALS = 256;
const END_OF_BLOCK = 256;
const LENGTH_CODES = 29;
const L_CODES = LITERALS + 1 + LENGTH_CODES;
const D_CODES = 30;
const BL_CODES = 19;
const HEAP_SIZE = 2 * L_CODES + 1;
const LONGEST_CODE = 15;
const LONGEST_LENGTH_CODE = 7;
const REPEAT_3_6 = 16;
const ZEROS_3_10 = 17;
const ZEROS_11_138 = 18;

const EXTRA_LENGTH_BITS = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0];
const EXTRA_DISTANCE_BITS = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13];
const EXTRA_CODE_LENGTH_BITS = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 7];
// The order in which a block lists the lengths of its code of code lengths.
const CODE_LENGTH_ORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];

// For a match length minus 3, its length code; for a length code, the first length of it,
// minus 3.
const LENGTH_CODE = new Uint8Array(MAX_MATCH - MIN_MATCH + 1);
const BASE_LENGTH = new Uint16Array(LENGTH_CODES);
// For a distance minus 1 below 256, and for the top bits of a longer one, its distance
// code; for a distance code, the first distance of it, minus 1.
const DISTANCE_CODE = new Uint8Array(512);
const BASE_DISTANCE = new Uint16Array(D_CODES);

{
  let length = 0;
  for (let code = 0; code < LENGTH_CODES - 1; code += 1) {
    BASE_LENGTH[code] = length;
    for (let n = 0; n < 1 << EXTRA_LENGTH_BITS[code]; n += 1) {
      LENGTH_CODE[length] = code;
      length += 1;
    }
  }
  LENGTH_CODE[length - 1] = LENGTH_CODES - 1;
  let distance = 0;
  let code = 0;
  for (; code < 16; code += 1) {
    BASE_DISTANCE[code] = distance;
    for (let n = 0; n < 1 << EXTRA_DISTANCE_BITS[code]; n += 1) {
      DISTANCE_CODE[distance] = code;
      distance += 1;
    }
  }
  distance >>= 7;
  for (; code < D_CODES; code += 1) {
    BASE_DISTANCE[code] = distance << 7;
    for (let n = 0; n < 1 << (EXTRA_DISTANCE_BITS[code] - 7); n += 1) {
      DISTANCE_CODE[256 + distance] = code;
      distance += 1;
    }
  }
}

function distanceCode(distance) {
  return distance < 256 ? DISTANCE_CODE[distance] : DISTANCE_CODE[256 + (distance >> 7)];
}

function reversed(code, length) {
  let result = 0;
  let left = code;
  for (let i = 0; i < length; i += 1) {
    result = (result << 1) | (left & 1);
    left >>= 1;
  }
  return result;
}

// A set of codes: for each symbol how often it appears, the length of its code and the
// code itself, bits reversed, as they are written. The entries after the symbols are the
// inner nodes of the tree the lengths are made with.
function codes(symbols) {
  const size = 2 * symbols + 1;
  return {
    symbols,
    freq: new Int32Array(size),
    length: new Uint8Array(size + 1),
    code: new Uint16Array(size),
    parent: new Uint16Array(size),
    largest: -1,
  };
}

// Gives every symbol with a length its code: the codes of one length count upward in the
// order of the symbols, and each length starts after the codes of the length before.
function assign(set, largest) {
  const counts = new Uint16Array(LONGEST_CODE + 1);
  for (let n = 0; n <= largest; n += 1) {
    counts[set.length[n]] += 1;
  }
  counts[0] = 0;
  const next = new Uint16Array(LONGEST_CODE + 1);
  let code = 0;
  for (let bits = 1; bits <= LONGEST_CODE; bits += 1) {
    code = (code + counts[bits - 1]) << 1;
    next[bits] = code;
  }
  for (let n = 0; n <= largest; n += 1) {
    const length = set.length[n];
    if (length !== 0) {
      set.code[n] = reversed(next[length], length);
      next[length] += 1;
    }
  }
}

const FIXED_LENGTHS = codes(L_CODES + 2);
FIXED_LENGTHS.length.fill(8, 0, 144);
FIXED_LENGTHS.length.fill(9, 144, 256);
FIXED_LENGTHS.length.fill(7, 256, 280);
FIXED_LENGTHS.length.fill(8, 280, 288);
assign(FIXED_LENGTHS, 287);
const FIXED_DISTANCES = codes(D_CODES);
FIXED_DISTANCES.length.fill(5, 0, D_CODES);
assign(FIXED_DISTANCES, D_CODES - 1);

// Compresses bytes into one raw DEFLATE stream, which any decoder of the format reads.
export function deflateRaw(bytes) {
  const size = bytes.length;
  // The input with zeros after it, so that a comparison may run past its end.
  const data = new Uint8Array(size + MAX_MATCH + MIN_MATCH + 1);
  data.set(bytes);

  // ---- the stream, written bit by bit, the first bit of a byte its lowest ----
  let out = new Uint8Array(Math.max(64, size >> 1));
  let written = 0;
  let hold = 0;
  let held = 0;
  const room = (more) => {
    if (written + more > out.length) {
      const larger = new Uint8Array(Math.max(2 * out.length, written + more));
      larger.set(out.subarray(0, written));
      out = larger;
    }
  };
  const send = (value, length) => {
    hold |= value << held;
    held += length;
    if (held >= 8) {
      room(3);
      while (held >= 8) {
        out[written] = hold & 0xff;
        written += 1;
        hold >>>= 8;
        held -= 8;
      }
    }
  };
  const align = () => {
    if (held > 0) {
      room(1);
      out[written] = hold & 0xff;
      written += 1;
    }
    hold = 0;
    held = 0;
  };

  // ---- the symbols of the block that is open: literals, and matches as a length and a
  // distance ----
  const symbolDistance = new Uint16Array(BLOCK_SYMBOLS + 1);
  const symbolValue = new Uint8Array(BLOCK_SYMBOLS + 1);
  let symbolCount = 0;
  const lengths = codes(L_CODES);
  const distances = codes(D_CODES);
  const codeLengths = codes(BL_CODES);
  let bestBits = 0;
  let fixedBits = 0;

  const heap = new Int32Array(HEAP_SIZE);
  const depth = new Uint8Array(HEAP_SIZE);
  let heapLength = 0;
  let heapMax = 0;

  const openBlock = () => {
    lengths.freq.fill(0);
    distances.freq.fill(0);
    codeLengths.freq.fill(0);
    lengths.freq[END_OF_BLOCK] = 1;
    symbolCount = 0;
    bestBits = 0;
    fixedBits = 0;
  };

  const literal = (value) => {
    symbolDistance[symbolCount] = 0;
    symbolValue[symbolCount] = value;
    symbolCount += 1;
    lengths.freq[value] += 1;
    return symbolCount === BLOCK_SYMBOLS;
  };

  // A match of `length` + 3 bytes that lie `distance` bytes back.
  const match = (distance, length) => {
    symbolDistance[symbolCount] = distance;
    symbolValue[symbolCount] = length;
    symbolCount += 1;
    lengths.freq[LENGTH_CODE[length] + LITERALS + 1] += 1;
    distances.freq[distanceCode(distance - 1)] += 1;
    return symbolCount === BLOCK_SYMBOLS;
  };

  // ---- codes made for a block ----
  const smaller = (freq, n, m) => freq[n] < freq[m] || (freq[n] === freq[m] && depth[n] <= depth[m]);

  const sift = (freq, from) => {
    const moved = heap[from];
    let k = from;
    let j = k << 1;
    while (j <= heapLength) {
      if (j < heapLength && smaller(freq, heap[j + 1], heap[j])) {
        j += 1;
      }
      if (smaller(freq, moved, heap[j])) {
        break;
      }
      heap[k] = heap[j];
      k = j;
      j <<= 1;
    }
    heap[k] = moved;
  };

  // Gives every symbol that appears a code length of at most `longest`, the shortest codes
  // to the symbols that appear most, and adds the bits the block takes with these codes to
  // `bestBits`, and with the fixed codes to `fixedBits` when `fixed` is given.
  const build = (set, fixed, extra, extraBase, longest) => {
    const {freq, length, parent, symbols} = set;
    let largest = -1;
    heapLength = 0;
    heapMax = HEAP_SIZE;
    for (let n = 0; n < symbols; n += 1) {
      if (freq[n] !== 0) {
        heapLength += 1;
        heap[heapLength] = n;
        largest = n;
        depth[n] = 0;
      } else {
        length[n] = 0;
      }
    }
    // A code needs two symbols: symbols that do not appear are added until there are two.
    while (heapLength < 2) {
      let added = 0;
      if (largest < 2) {
        largest += 1;
        added = largest;
      }
      heapLength += 1;
      heap[heapLength] = added;
      freq[added] = 1;
      depth[added] = 0;
      bestBits -= 1;
      if (fixed !== null) {
        fixedBits -= fixed.length[added];
      }
    }
    set.largest = largest;

    for (let n = heapLength >> 1; n >= 1; n -= 1) {
      sift(freq, n);
    }
    let node = symbols;
    do {
      const n = heap[1];
      heap[1] = heap[heapLength];
      heapLength -= 1;
      sift(freq, 1);
      const m = heap[1];
      heapMax -= 1;
      heap[heapMax] = n;
      heapMax -= 1;
      heap[heapMax] = m;
      freq[node] = freq[n] + freq[m];
      depth[node] = (depth[n] >= depth[m] ? depth[n] : depth[m]) + 1;
      parent[n] = node;
      parent[m] = node;
      heap[1] = node;
      node += 1;
      sift(freq, 1);
    } while (heapLength >= 2);
    heapMax -= 1;
    heap[heapMax] = heap[1];

    // The lengths, from the root of the tree downward; then the codes that came out too
    // long are made to fit.
    const counts = new Uint16Array(LONGEST_CODE + 1);
    let overflow = 0;
    length[heap[heapMax]] = 0;
    let h = heapMax + 1;
    for (; h < HEAP_SIZE; h += 1) {
      const n = heap[h];
      let bits = length[parent[n]] + 1;
      if (bits > longest) {
        bits = longest;
        overflow += 1;
      }
      length[n] = bits;
      if (n > largest) {
        continue;
      }
      counts[bits] += 1;
      const more = n >= extraBase ? extra[n - extraBase] : 0;
      bestBits += freq[n] * (bits + more);
      if (fixed !== null) {
        fixedBits += freq[n] * (fixed.length[n] + more);
      }
    }
    if (overflow > 0) {
      do {
        let bits = longest - 1;
        while (counts[bits] === 0) {
          bits -= 1;
        }
        counts[bits] -= 1;
        counts[bits + 1] += 2;
        counts[longest] -= 1;
        overflow -= 2;
      } while (overflow > 0);
      for (let bits = longest; bits !== 0; bits -= 1) {
        let n = counts[bits];
        while (n !== 0) {
          h -= 1;
          const m = heap[h];
          if (m > largest) {
            continue;
          }
          if (length[m] !== bits) {
            bestBits += (bits - length[m]) * freq[m];
            length[m] = bits;
          }
          n -= 1;
        }
      }
    }
    assign(set, largest);
  };

  // Goes through the code lengths of a set as they are written: a length by itself, or a
  // repeat of the length before, or a run of zeros. `one(length)` is called for a length,
  // `run(symbol, count)` for a repeat or a run.
  const lengthsOf = (set, largest, one, run) => {
    const {length} = set;
    let before = -1;
    let next = length[0];
    let count = 0;
    let most = next === 0 ? 138 : 7;
    let least = next === 0 ? 3 : 4;
    const guard = length[largest + 1];
    length[largest + 1] = 0xff;
    for (let n = 0; n <= largest; n += 1) {
      const current = next;
      next = length[n + 1];
      count += 1;
      if (count < most && current === next) {
        continue;
      }
      if (count < least) {
        for (let i = 0; i < count; i += 1) {
          one(current);
        }
      } else if (current !== 0) {
        if (current !== before) {
          one(current);
          count -= 1;
        }
        run(REPEAT_3_6, count);
      } else if (count <= 10) {
        run(ZEROS_3_10, count);
      } else {
        run(ZEROS_11_138, count);
      }
      count = 0;
      before = current;
      if (next === 0) {
        most = 138;
        least = 3;
      } else if (current === next) {
        most = 6;
        least = 3;
      } else {
        most = 7;
        least = 4;
      }
    }
    length[largest + 1] = guard;
  };

  const count = (set, largest) => {
    lengthsOf(
      set,
      largest,
      (length) => {
        codeLengths.freq[length] += 1;
      },
      (symbol) => {
        codeLengths.freq[symbol] += 1;
      },
    );
  };

  const sendCode = (set, symbol) => {
    send(set.code[symbol], set.length[symbol]);
  };

  const sendLengths = (set, largest) => {
    lengthsOf(
      set,
      largest,
      (length) => {
        sendCode(codeLengths, length);
      },
      (symbol, times) => {
        sendCode(codeLengths, symbol);
        if (symbol === REPEAT_3_6) {
          send(times - 3, 2);
        } else if (symbol === ZEROS_3_10) {
          send(times - 3, 3);
        } else {
          send(times - 11, 7);
        }
      },
    );
  };

  const sendSymbols = (lengthSet, distanceSet) => {
    for (let i = 0; i < symbolCount; i += 1) {
      const distance = symbolDistance[i];
      const value = symbolValue[i];
      if (distance === 0) {
        sendCode(lengthSet, value);
        continue;
      }
      let code = LENGTH_CODE[value];
      sendCode(lengthSet, code + LITERALS + 1);
      if (EXTRA_LENGTH_BITS[code] !== 0) {
        send(value - BASE_LENGTH[code], EXTRA_LENGTH_BITS[code]);
      }
      const back = distance - 1;
      code = distanceCode(back);
      sendCode(distanceSet, code);
      if (EXTRA_DISTANCE_BITS[code] !== 0) {
        send(back - BASE_DISTANCE[code], EXTRA_DISTANCE_BITS[code]);
      }
    }
    sendCode(lengthSet, END_OF_BLOCK);
  };

  const stored = (from, length, last) => {
    let at = from;
    let left = length;
    do {
      const part = left > LARGEST_STORED ? LARGEST_STORED : left;
      send(last && part === left ? 1 : 0, 3);
      align();
      room(4 + part);
      out[written] = part & 0xff;
      out[written + 1] = part >> 8;
      out[written + 2] = ~part & 0xff;
      out[written + 3] = (~part >> 8) & 0xff;
      out.set(data.subarray(at, at + part), written + 4);
      written += 4 + part;
      at += part;
      left -= part;
    } while (left > 0);
  };

  // Writes the block of the bytes from `from` to `to` in the smallest of its three forms.
  const closeBlock = (from, to, last) => {
    build(lengths, FIXED_LENGTHS, EXTRA_LENGTH_BITS, LITERALS + 1, LONGEST_CODE);
    build(distances, FIXED_DISTANCES, EXTRA_DISTANCE_BITS, 0, LONGEST_CODE);
    count(lengths, lengths.largest);
    count(distances, distances.largest);
    build(codeLengths, null, EXTRA_CODE_LENGTH_BITS, 0, LONGEST_LENGTH_CODE);
    let listed = BL_CODES - 1;
    while (listed >= 3 && codeLengths.length[CODE_LENGTH_ORDER[listed]] === 0) {
      listed -= 1;
    }
    bestBits += 3 * (listed + 1) + 5 + 5 + 4;

    const fixedBytes = (fixedBits + 3 + 7) >> 3;
    let bestBytes = (bestBits + 3 + 7) >> 3;
    if (fixedBytes <= bestBytes) {
      bestBytes = fixedBytes;
    }
    if (to - from + 4 <= bestBytes) {
      stored(from, to - from, last);
    } else if (fixedBytes === bestBytes) {
      send(2 + (last ? 1 : 0), 3);
      sendSymbols(FIXED_LENGTHS, FIXED_DISTANCES);
    } else {
      send(4 + (last ? 1 : 0), 3);
      send(lengths.largest + 1 - 257, 5);
      send(distances.largest + 1 - 1, 5);
      send(listed + 1 - 4, 4);
      for (let rank = 0; rank <= listed; rank += 1) {
        send(codeLengths.length[CODE_LENGTH_ORDER[rank]], 3);
      }
      sendLengths(lengths, lengths.largest);
      sendLengths(distances, distances.largest);
      sendSymbols(lengths, distances);
    }
    openBlock();
    if (last) {
      align();
    }
  };

  // ---- the search for matches ----
  // For each value of the hash the last position that has it, and for each position the
  // one before it with the same value. Position 0 stands for none.
  const head = new Int32Array(HASH_SIZE);
  const previous = new Int32Array(REACH);
  let position = 0;
  let matchStart = 0;
  let matchLength = MIN_MATCH - 1;
  let earlierLength = MIN_MATCH - 1;

  const insert = (at) => {
    const hash = ((data[at] << 10) ^ (data[at + 1] << 5) ^ data[at + 2]) & HASH_MASK;
    const before = head[hash];
    previous[at & REACH_MASK] = before;
    head[hash] = at;
    return before;
  };

  // The longest match at `position` among the earlier positions of its chain, starting at
  // `candidate`: its length, with `matchStart` set when it is longer than the match at the
  // position before.
  const longest = (candidate) => {
    let chain = earlierLength >= GOOD_LENGTH ? LONGEST_CHAIN >> 2 : LONGEST_CHAIN;
    let best = earlierLength;
    const ahead = size - position;
    const nice = NICE_LENGTH > ahead ? ahead : NICE_LENGTH;
    const limit = position > FARTHEST ? position - FARTHEST : 0;
    const end = position + MAX_MATCH;
    let lastButOne = data[position + best - 1];
    let last = data[position + best];
    let at = candidate;
    do {
      if (
        data[at + best] !== last ||
        data[at + best - 1] !== lastButOne ||
        data[at] !== data[position] ||
        data[at + 1] !== data[position + 1]
      ) {
        continue;
      }
      let scan = position + 2;
      let other = at + 2;
      while (scan < end && data[scan] === data[other]) {
        scan += 1;
        other += 1;
      }
      const length = scan - position;
      if (length > best) {
        matchStart = at;
        best = length;
        if (length >= nice) {
          break;
        }
        lastButOne = data[position + best - 1];
        last = data[position + best];
      }
    } while ((at = previous[at & REACH_MASK]) > limit && --chain !== 0);
    return best <= ahead ? best : ahead;
  };

  openBlock();
  let blockStart = 0;
  let pending = false;
  while (position < size) {
    const ahead = size - position;
    const candidate = ahead >= MIN_MATCH ? insert(position) : 0;
    earlierLength = matchLength;
    const earlierStart = matchStart;
    matchLength = MIN_MATCH - 1;
    if (candidate !== 0 && earlierLength < LAZY_LENGTH && position - candidate <= FARTHEST) {
      matchLength = longest(candidate);
      if (matchLength === MIN_MATCH && position - matchStart > TOO_FAR) {
        matchLength = MIN_MATCH - 1;
      }
    }
    if (earlierLength >= MIN_MATCH && matchLength <= earlierLength) {
      // The match at the position before is written; the positions it covers are entered
      // into the chains.
      const lastToInsert = size - MIN_MATCH;
      const full = match(position - 1 - earlierStart, earlierLength - MIN_MATCH);
      for (let left = earlierLength - 2; left !== 0; left -= 1) {
        position += 1;
        if (position <= lastToInsert) {
          insert(position);
        }
      }
      pending = false;
      matchLength = MIN_MATCH - 1;
      position += 1;
      if (full) {
        closeBlock(blockStart, position, false);
        blockStart = position;
      }
    } else if (pending) {
      if (literal(data[position - 1])) {
        closeBlock(blockStart, position, false);
        blockStart = position;
      }
      position += 1;
    } else {
      pending = true;
      position += 1;
    }
  }
  if (pending) {
    literal(data[position - 1]);
  }
  closeBlock(blockStart, position, true);
  return out.slice(0, written);
}
