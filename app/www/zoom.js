// The brightness zoom: the range the brightness slider moves through, between two pins, kept
// in the storage of the phone. It changes no brightness and sends nothing.

export const KEY = "odrig.brightness-zoom";
export const FULL = Object.freeze({start: 0, end: 255});

// The kept pair, or the full range when the storage cannot be read or holds no usable pair:
// two whole numbers, the first below the second, up to 255.
export function load(storage) {
  try {
    const text = storage?.getItem(KEY);
    const match = typeof text === "string" ? /^(\d{1,3}) (\d{1,3})$/.exec(text) : null;
    if (match === null) return {...FULL};
    const start = Number(match[1]);
    const end = Number(match[2]);
    return start < end && end <= 255 ? {start, end} : {...FULL};
  } catch (_) {
    return {...FULL};
  }
}

// Keeps the pair. A storage that cannot be written is let be: the zoom holds for this run.
export function save(storage, range) {
  try {
    storage?.setItem(KEY, `${range.start} ${range.end}`);
  } catch (_) {
    // Nothing is said.
  }
}

// The pair with one pin moved to a value: inside 0 to 255, and at least 1 from the other pin.
export function moved(range, which, to) {
  const value = Math.round(Number(to));
  if (which === "start") return {start: Math.max(0, Math.min(value, range.end - 1)), end: range.end};
  return {start: range.start, end: Math.min(255, Math.max(value, range.start + 1))};
}

// Where a value stands from the zoom: "below", "above", or null inside it or for no value.
export function place(value, range) {
  if (typeof value !== "number") return null;
  return value < range.start ? "below" : value > range.end ? "above" : null;
}

export function words(range) {
  return `Zoom ${range.start} to ${range.end}`;
}

// The line of a value outside the zoom, or null.
export function outside(value, range) {
  const where = place(value, range);
  return where === null ? null : `${value} is ${where} the zoom ${range.start} to ${range.end}.`;
}
