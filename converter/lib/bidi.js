// The Unicode Bidirectional Algorithm, UAX #9, for the characters a text may hold: the
// printable ASCII characters and the Hebrew letters. With no explicit embedding, isolate or
// mark among them, a paragraph is one run at its own level, and the rules that apply are
// P2 and P3, W4 to W7, N1, N2, I1 and I2, and for each line L1, L2 and L4.

export const L = "L";
export const R = "R";
export const EN = "EN";
export const ES = "ES";
export const ET = "ET";
export const CS = "CS";
export const WS = "WS";
export const ON = "ON";

// The characters that are shown as their mirror in a run of an odd level.
export const MIRRORED = {0x28: 0x29, 0x29: 0x28, 0x3c: 0x3e, 0x3e: 0x3c, 0x5b: 0x5d, 0x5d: 0x5b, 0x7b: 0x7d, 0x7d: 0x7b};

// The bidirectional class of a character of the repertoire.
export function classOf(code) {
  if ((code >= 0x41 && code <= 0x5a) || (code >= 0x61 && code <= 0x7a)) return L;
  if (code >= 0x5d0 && code <= 0x5ea) return R;
  if (code >= 0x30 && code <= 0x39) return EN;
  if (code === 0x2b || code === 0x2d) return ES;
  if (code === 0x23 || code === 0x24 || code === 0x25) return ET;
  if (code === 0x2c || code === 0x2e || code === 0x2f || code === 0x3a) return CS;
  if (code === 0x20) return WS;
  return ON;
}

// The level of a paragraph: 1 for `rtl`, 0 for `ltr`, and for `auto` 1 when its first
// strong character is right-to-left, else 0 (P2, P3).
export function paragraphLevel(codes, direction) {
  if (direction === "rtl") return 1;
  if (direction === "ltr") return 0;
  for (const code of codes) {
    const kind = classOf(code);
    if (kind === L) return 0;
    if (kind === R) return 1;
  }
  return 0;
}

// The resolved levels of the characters of a paragraph at this level.
export function levels(codes, level) {
  const types = codes.map(classOf);
  const sos = level % 2 === 0 ? L : R;
  const count = types.length;
  // W4: a single separator between two European numbers.
  for (let at = 1; at + 1 < count; at += 1) {
    if (types[at - 1] === EN && types[at + 1] === EN && (types[at] === ES || types[at] === CS)) {
      types[at] = EN;
    }
  }
  // W5: terminators next to European numbers.
  for (let at = 0; at < count; at += 1) {
    if (types[at] !== ET) continue;
    let end = at;
    while (end < count && types[end] === ET) end += 1;
    if ((at > 0 && types[at - 1] === EN) || (end < count && types[end] === EN)) {
      for (let one = at; one < end; one += 1) types[one] = EN;
    }
    at = end - 1;
  }
  // W6: the separators and terminators that are left are other neutrals.
  for (let at = 0; at < count; at += 1) {
    if (types[at] === ES || types[at] === ET || types[at] === CS) types[at] = ON;
  }
  // W7: a European number after left-to-right text, or at the start of a left-to-right
  // paragraph, is left-to-right.
  let strong = sos;
  for (let at = 0; at < count; at += 1) {
    if (types[at] === L || types[at] === R) strong = types[at];
    else if (types[at] === EN && strong === L) types[at] = L;
  }
  // N1 and N2: a row of neutrals takes the direction of the text on both its sides when it
  // is the same, a European number counting as right-to-left; otherwise the paragraph's.
  const direction = (kind) => (kind === L ? L : kind === R || kind === EN ? R : null);
  for (let at = 0; at < count; at += 1) {
    if (types[at] !== WS && types[at] !== ON) continue;
    let end = at;
    while (end < count && (types[end] === WS || types[end] === ON)) end += 1;
    const before = at === 0 ? sos : direction(types[at - 1]);
    const after = end === count ? sos : direction(types[end]);
    const taken = before === after ? before : sos;
    for (let one = at; one < end; one += 1) types[one] = taken;
    at = end - 1;
  }
  // I1, I2.
  return types.map((kind) => {
    if (level % 2 === 0) {
      return kind === R ? level + 1 : kind === EN ? level + 2 : level;
    }
    return kind === L || kind === EN ? level + 1 : level;
  });
}

// The order in which the characters of a line are shown, as their places in the line,
// for their levels: white space at the end of the line takes the paragraph's level (L1),
// and from the highest level down to the lowest odd one every run at that level or above
// is reversed (L2).
export function visualOrder(codes, lineLevels, level) {
  const placed = lineLevels.slice();
  for (let at = codes.length - 1; at >= 0 && classOf(codes[at]) === WS; at -= 1) {
    placed[at] = level;
  }
  const order = codes.map((_, at) => at);
  const highest = Math.max(level, ...placed);
  const lowestOdd = Math.min(...placed.filter((one) => one % 2 === 1), highest + 1);
  for (let at = highest; at >= lowestOdd; at -= 1) {
    let start = 0;
    while (start < order.length) {
      if (placed[order[start]] < at) {
        start += 1;
        continue;
      }
      let end = start;
      while (end < order.length && placed[order[end]] >= at) end += 1;
      const run = order.slice(start, end).reverse();
      order.splice(start, run.length, ...run);
      start = end;
    }
  }
  return order;
}
