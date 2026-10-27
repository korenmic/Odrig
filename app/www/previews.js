// The previews of the animations: the default preview catalog that comes with the app,
// `thumbnails/`, which maps the key of an animation's file to its GIF; the phone's own
// catalog of previews, those this phone made of what it uploaded, kept in the web view's
// IndexedDB; and the square of a row or of the panel of what plays, which shows the preview
// of a key or stays empty.

import {previewMaker} from "./convert.js";
import {crc32} from "./crc32.js";
import defaults from "./thumbnails/catalog.js";

const DATABASE = "odrig-previews";
const STORE = "previews";

// The phone's own previews by key, each as the address of its GIF in this run; the open
// database, or null when the web view keeps none; and who is told when one is added.
const own = new Map();
let database = null;
const watchers = new Set();

// Whether the default catalog holds a key.
export function inDefaults(key) {
  return Object.prototype.hasOwnProperty.call(defaults, key);
}

// The source of the preview of a key: the GIF of the default catalog beside the app, else the
// phone's own, or null when neither has one.
export function sourceOf(key) {
  if (key === null) {
    return null;
  }
  if (inDefaults(key)) {
    return `thumbnails/${defaults[key].gif}`;
  }
  return own.has(key) ? own.get(key) : null;
}

// Calls a function whenever the phone's own catalog gains a preview.
export function watch(watcher) {
  watchers.add(watcher);
}

function told() {
  for (const watcher of watchers) {
    watcher();
  }
}

// A request of IndexedDB as a promise.
function done(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function opened(factory) {
  const request = factory.open(DATABASE, 1);
  request.onupgradeneeded = () => request.result.createObjectStore(STORE);
  return done(request);
}

// Opens the phone's own catalog and takes its previews, after dropping each one whose key the
// default catalog has. A web view without IndexedDB, or one that refuses it, keeps the
// previews of this run alone, and nothing is said.
export async function start(factory = typeof indexedDB === "undefined" ? null : indexedDB) {
  database = null;
  if (factory === null) {
    return;
  }
  try {
    const found = await opened(factory);
    const writing = found.transaction(STORE, "readwrite").objectStore(STORE);
    const keys = await done(writing.getAllKeys());
    const gifs = await done(writing.getAll());
    keys.forEach((key, at) => {
      if (inDefaults(key)) {
        writing.delete(key);
      } else if (!own.has(key)) {
        own.set(key, URL.createObjectURL(gifs[at]));
      }
    });
    database = found;
    told();
  } catch {
    database = null;
  }
}

// Makes the preview of bytes this phone uploaded, a step at a time between the app's other
// work, and keeps it by their key, in the phone's own catalog and for this run. A key that
// either catalog has, and bytes that make no preview, are left as they are, and nothing is
// said.
export function makeOwn(bytes) {
  const key = `${crc32(bytes)}-${bytes.length}`;
  if (inDefaults(key) || own.has(key)) {
    return;
  }
  let making;
  try {
    making = previewMaker(bytes);
  } catch {
    return;
  }
  const step = () => {
    try {
      if (!making.step()) {
        setTimeout(step, 0);
        return;
      }
    } catch {
      return;
    }
    const gif = new Blob([making.preview], {type: "image/gif"});
    own.set(key, URL.createObjectURL(gif));
    told();
    if (database !== null) {
      try {
        database.transaction(STORE, "readwrite").objectStore(STORE).put(gif, key);
      } catch {
        // The preview stays for this run.
      }
    }
  };
  setTimeout(step, 0);
}

// Shows a preview in a square, or nothing: the image is made, changed or taken out only when
// its source differs, so that a square that shows a preview keeps it while it is redrawn.
export function show(square, source) {
  const image = square.querySelector("img");
  if (source === null) {
    if (image !== null) {
      image.remove();
    }
    return;
  }
  if (image !== null && image.getAttribute("src") === source) {
    return;
  }
  const made = image === null ? square.ownerDocument.createElement("img") : image;
  made.alt = "";
  made.draggable = false;
  made.decoding = "async";
  made.setAttribute("src", source);
  if (image === null) {
    square.append(made);
  }
}
