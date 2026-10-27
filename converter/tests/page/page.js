// What the library is asked to do in a page, and the page that asks it.
//
// `work` uses nothing but the library and the language, so the test runs the very same
// calls in Node.js and compares. In a page this file loads the library as a module, runs
// `work`, and posts what came out, or the error it met, to the server it was loaded from.

const FITS = ["fill", "fit", "stretch"];
const CANVASES = [[60, 6], [60, 60], [7, 5]];
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

// Bytes as base64 text.
export function base64(bytes) {
  let text = "";
  for (let at = 0; at < bytes.length; at += 3) {
    const left = bytes.length - at;
    const three = (bytes[at] << 16) | ((left > 1 ? bytes[at + 1] : 0) << 8) | (left > 2 ? bytes[at + 2] : 0);
    text += LETTERS[three >> 18] + LETTERS[(three >> 12) & 63] + (left > 1 ? LETTERS[(three >> 6) & 63] : "=") + (left > 2 ? LETTERS[three & 63] : "=");
  }
  return text;
}

// Three source pictures filled by a fixed rule: one wider than high with every pixel
// opaque, one higher than wide with alphas of every value, and one of a single row.
export function sourcePictures() {
  const picture = (width, height, rule) => {
    const rgba = new Uint8Array(4 * width * height);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        rgba.set(rule(x, y), 4 * (y * width + x));
      }
    }
    return {width, height, rgba};
  };
  return [
    picture(96, 54, (x, y) => [(x * 5 + y * 3) & 255, (x * x + 7 * y) & 255, (x ^ (y * 9)) & 255, 255]),
    picture(31, 77, (x, y) => [(x * 8) & 255, (y * 3) & 255, (x * y) & 255, (x * 11 + y * 5) & 255]),
    picture(40, 1, (x) => [x * 6, 255 - x * 6, (x * 37) & 255, x % 5 === 0 ? 0 : 255]),
  ];
}

// Everything the test compares: the two files of an animation, what they decode to, and
// source pictures imported and fitted with each fit, each as base64 text.
export async function work(library, sourceBytes) {
  const {fit, jsonframes, odrg, timeline} = library;
  const animation = jsonframes.loads(sourceBytes);
  const compressed = odrg.encode(animation);
  const uncompressed = odrg.encode(animation, {compressed: false});
  const decodedTo = (file) => {
    const decoded = odrg.decode(file);
    return base64(jsonframes.dumps({width: decoded.width, height: decoded.height, frames: decoded.records}));
  };
  const pictures = sourcePictures();
  const imported = {};
  const placed = {};
  for (const name of FITS) {
    const frames = pictures.map((picture, i) => ({...picture, delayMs: 20 * (i + 2)}));
    const result = await timeline.importFrames({kind: "gif", frames}, {width: 60, height: 6}, {fit: name});
    imported[name] = base64(jsonframes.dumps(result));
    placed[name] = [];
    for (const picture of pictures) {
      for (const [w, h] of CANVASES) {
        placed[name].push(base64(fit.place(picture, w, h, name)));
      }
    }
  }
  const timed = pictures.map((picture, i) => ({...picture, time: [1001 * i, 30]}));
  const video = await timeline.importFrames({kind: "video", frames: timed}, {width: 60, height: 60}, {fit: "fill", startMs: 20});
  const {odrgx, thumbnail} = library;
  const sourceOf = (source) => odrgx.encodeSource(odrgx.loadsSource(new TextEncoder().encode(JSON.stringify(source))));
  const text = sourceOf({version: 1, type: "text", width: 60, height: 60, text: "Hello \u05e9\u05dc\u05d5\u05dd", font: "small", color: 16764992,
    background: 16, align: "center", valign: "middle", direction: "auto", wrap: false, effect: "marquee", motion: "left", speed: 40, pause_ms: 700});
  const clock = sourceOf({version: 1, type: "widget", width: 60, height: 60, widget: "analog", seconds: 30, face: 16051408, hands: 2105376,
    rim: 13934615, background: 0, speed_min: 60, speed_max: 600});
  const previewed = [compressed, uncompressed, odrg.encode(video), text, clock];
  return {
    compressed: base64(compressed),
    uncompressed: base64(uncompressed),
    decoded: [decodedTo(compressed), decodedTo(uncompressed)],
    imported,
    placed,
    video: base64(jsonframes.dumps(video)),
    reasons: Object.keys(library.errors).filter((name) => name === name.toUpperCase()).length,
    previews: previewed.map((file) => `${thumbnail.keyOf(file)} ${base64(thumbnail.make(file))}`),
  };
}

async function inPage() {
  const state = document.getElementById("state");
  let answer;
  try {
    const library = await import("/lib/index.js");
    const response = await fetch("/hello.json");
    if (!response.ok) {
      throw new Error(`the source was not served: ${response.status}`);
    }
    const sourceBytes = new Uint8Array(await response.arrayBuffer());
    answer = {results: await work(library, sourceBytes), agent: navigator.userAgent};
  } catch (error) {
    answer = {error: `${error instanceof Error ? `${error.name}: ${error.message}` : String(error)}`};
  }
  state.textContent = answer.error === undefined ? "The library ran." : `The library failed: ${answer.error}`;
  await fetch("/result", {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(answer)});
}

if (typeof document !== "undefined") {
  inPage();
}
