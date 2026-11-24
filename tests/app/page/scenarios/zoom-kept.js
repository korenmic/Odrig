// The brightness zoom's pair kept in a storage, worked without the app: a storage that
// throws, none, one that holds nothing, malformed pairs and good ones; and the pins moved, the
// words and the line of a value outside the zoom.

export const withoutTheApp = true;

function holding(text) {
  return {getItem: () => text, setItem: () => {}};
}

export default async function () {
  const zoom = await import("/zoom.js");
  const throwing = {getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); }};
  const written = {};
  const writable = {getItem: (key) => written[key] ?? null, setItem: (key, value) => { written[key] = value; }};
  const narrow = {start: 2, end: 12};
  zoom.save(writable, narrow);
  let threw = false;
  try {
    zoom.save(throwing, narrow);
  } catch (_) {
    threw = true;
  }
  return {
    none: zoom.load(null),
    throwing: zoom.load(throwing),
    threw,
    empty: zoom.load(holding(null)),
    malformed: ["2", "2 12 3", "12 2", "5 5", "0 256", "a b", " 2 12", "-1 12"].map((text) => zoom.load(holding(text))),
    good: zoom.load(holding("2 12")),
    full: zoom.load(holding("0 255")),
    written,
    readBack: zoom.load(writable),
    words: zoom.words(narrow),
    outside: [zoom.outside(40, narrow), zoom.outside(1, narrow), zoom.outside(5, narrow), zoom.outside(null, narrow)],
    moved: [zoom.moved(narrow, "start", 200), zoom.moved(narrow, "end", 0), zoom.moved(zoom.FULL, "end", 300), zoom.moved(narrow, "start", -4)],
  };
}
