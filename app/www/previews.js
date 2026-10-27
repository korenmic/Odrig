// The previews of the animations: the default preview catalog that comes with the app,
// `thumbnails/`, which maps the key of an animation's file to its GIF and to the names it
// was given, so that a name and a size find a key too; the phone's own catalog of previews,
// those this phone made of what it uploaded, kept in the web view's IndexedDB, beside the
// keys the catalogs of each target gave, kept for the next start; and the square of a row or
// of the panel of what plays, which shows the preview of a key or stays empty.

import {previewMaker} from "./convert.js";
import {crc32} from "./crc32.js";
import defaults from "./thumbnails/catalog.js";

const DATABASE = "odrig-previews";
const VERSION = 2;
const STORE = "previews";
const KEYS = "keys";

// The phone's own previews by key, each as the address of its GIF in this run; the open
// database, or null when the web view keeps none; and who is told when one is added.
const own = new Map();
let database = null;
const watchers = new Set();
// The keys the catalogs gave, by the target's address and the storage, `${address}
// ${storage}`, each `{generation, entries, byName}`; in the store `keys` each is kept as
// `{generation, entries, names}`, `names` the pairs of `byName`.
const kept = new Map();

// The keys of the default catalog by each of the names it gives them.
const named = new Map();
for (const [key, entry] of Object.entries(defaults)) {
  for (const name of entry.names) {
    if (!named.has(name)) {
      named.set(name, []);
    }
    named.get(name).push(key);
  }
}

// Whether the default catalog holds a key.
export function inDefaults(key) {
  return Object.prototype.hasOwnProperty.call(defaults, key);
}

// The key of the default catalog that a file's name and size find, for a row whose key is
// not known: the one key of that size that the catalog gives the name, or, for a file of the
// card whose path the catalog does not name, its own name. Null when none or more than one
// is found.
export function keyByName(file, bytes) {
  if (typeof file !== "string" || typeof bytes !== "number") {
    return null;
  }
  const own = file.slice(file.lastIndexOf("/") + 1);
  const keys = named.get(file) ?? (file.includes("/") ? named.get(own) : undefined) ?? [];
  const sized = keys.filter((key) => key.endsWith(`-${bytes}`));
  return sized.length === 1 ? sized[0] : null;
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

// Opens the database at its version, with each of its stores that it does not hold yet. An
// open that another connection of an older version blocks is given up; when it succeeds later,
// it is closed.
function opened(factory) {
  const request = factory.open(DATABASE, VERSION);
  request.onupgradeneeded = () => {
    for (const name of [STORE, KEYS]) {
      if (!request.result.objectStoreNames.contains(name)) {
        request.result.createObjectStore(name);
      }
    }
  };
  return new Promise((resolve, reject) => {
    let ended = false;
    request.onsuccess = () => {
      if (ended) {
        request.result.close();
      } else {
        ended = true;
        resolve(request.result);
      }
    };
    request.onerror = () => {
      ended = true;
      reject(request.error);
    };
    request.onblocked = () => {
      if (!ended) {
        ended = true;
        reject(new Error("blocked"));
      }
    };
  });
}

function keptName(address, storage) {
  return `${address} ${storage}`;
}

// A record of the store `keys` as the keys it holds, or null for one of another shape.
function keysOf(record) {
  if (record === null || typeof record !== "object" || !Number.isInteger(record.generation) || !Number.isInteger(record.entries) || !Array.isArray(record.names)) {
    return null;
  }
  if (!record.names.every((pair) => Array.isArray(pair) && pair.length === 2 && typeof pair[0] === "string" && typeof pair[1] === "string")) {
    return null;
  }
  return {generation: record.generation, entries: record.entries, byName: new Map(record.names)};
}

function writeKeys(write) {
  if (database === null) {
    return;
  }
  try {
    write(database.transaction(KEYS, "readwrite").objectStore(KEYS));
  } catch {
    // The keys stay for this run.
  }
}

// Where the client keeps the keys of the catalogs between two starts of the app.
export const keeper = {
  kept(address, storage) {
    return kept.get(keptName(address, storage)) ?? null;
  },
  keep(address, storage, keys) {
    const name = keptName(address, storage);
    kept.set(name, {generation: keys.generation, entries: keys.entries, byName: new Map(keys.byName)});
    writeKeys((store) => store.put({generation: keys.generation, entries: keys.entries, names: [...keys.byName]}, name));
  },
  forget(address, storage) {
    const name = keptName(address, storage);
    kept.delete(name);
    writeKeys((store) => store.delete(name));
  },
};

// Opens the phone's own catalog and takes its previews, after dropping each one whose key the
// default catalog has, and the keys kept at an earlier start; keys kept in this run before
// it ends stay, and are written then. A web view without IndexedDB, or one that refuses it,
// keeps the previews and the keys of this run alone, and nothing is said.
export async function start(factory = typeof indexedDB === "undefined" ? null : indexedDB) {
  database = null;
  if (factory === null) {
    return;
  }
  try {
    const found = await opened(factory);
    found.onversionchange = () => {
      found.close();
      if (database === found) {
        database = null;
      }
    };
    const writing = found.transaction([STORE, KEYS], "readwrite");
    const previews = writing.objectStore(STORE);
    const keys = await done(previews.getAllKeys());
    const gifs = await done(previews.getAll());
    keys.forEach((key, at) => {
      if (inDefaults(key)) {
        previews.delete(key);
      } else if (!own.has(key)) {
        own.set(key, URL.createObjectURL(gifs[at]));
      }
    });
    const ours = new Set(kept.keys());
    const store = writing.objectStore(KEYS);
    const names = await done(store.getAllKeys());
    const records = await done(store.getAll());
    names.forEach((name, at) => {
      const found = keysOf(records[at]);
      if (typeof name === "string" && found !== null && !ours.has(name)) {
        kept.set(name, found);
      }
    });
    for (const name of ours) {
      const keys = kept.get(name);
      store.put({generation: keys.generation, entries: keys.entries, names: [...keys.byName]}, name);
    }
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
