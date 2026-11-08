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
const VERSION = 3;
const STORE = "previews";
const KEYS = "keys";
const UPLOADS = "uploads";

// The phone's own previews by key, each as the address of its GIF in this run; the open
// database, or null when the web view keeps none; and who is told when one is added.
const own = new Map();
let database = null;
const watchers = new Set();
// The keys the catalogs gave, by the target's address and the storage, `${address}
// ${storage}`, each `{generation, entries, byName}`; in the store `keys` each is kept as
// `{generation, entries, names}`, `names` the pairs of `byName`.
const kept = new Map();
// The starts so far: only the latest keeps the database it opens.
let starts = 0;
// The places this phone uploaded to, by `${address} ${storage}`, each the file names it put
// there with their keys, kept in the store `uploads` as the pairs; and when in this run each
// name was put there.
const places = new Map();
const placedAt = new Map();
// The previews being made, by key, one at a time in the order they were asked for; and the
// GIFs this phone made in this run, kept to be written when an upload of their bytes ends.
const jobs = new Map();
const queue = [];
let making = null;
const gifs = new Map();

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
    for (const name of [STORE, KEYS, UPLOADS]) {
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

function writePlaces(name) {
  if (database === null) {
    return;
  }
  try {
    const store = database.transaction(UPLOADS, "readwrite").objectStore(UPLOADS);
    const named = places.get(name);
    if (named === undefined || named.size === 0) store.delete(name);
    else store.put([...named], name);
  } catch {
    // The places stay for this run.
  }
}

// The folder of a name of a storage: the part before its last `/`, "" for the root.
function folderOf(name) {
  return name.includes("/") ? name.slice(0, name.lastIndexOf("/")) : "";
}

// Where the client keeps the keys of the catalogs between two starts of the app, and the
// places this phone uploaded to.
export const keeper = {
  placed(address, storage, name) {
    return places.get(keptName(address, storage))?.get(name) ?? null;
  },
  place(address, storage, name, key) {
    const record = keptName(address, storage);
    if (!places.has(record)) places.set(record, new Map());
    places.get(record).set(name, key);
    placedAt.set(`${record}\u0000${name}`, performance.now());
    writePlaces(record);
  },
  unplace(address, storage, name) {
    const record = keptName(address, storage);
    if (places.get(record)?.delete(name)) writePlaces(record);
  },
  // A complete list of a folder of a storage, asked from its first part at `began`, drops the
  // places of that folder it does not name that were kept before it was asked.
  unlisted(address, storage, folder, listed, began) {
    const record = keptName(address, storage);
    const named = places.get(record);
    if (named === undefined) return;
    let dropped = false;
    for (const name of [...named.keys()]) {
      if (folderOf(name) === folder && !listed.has(name) && (placedAt.get(`${record}\u0000${name}`) ?? -Infinity) < began) {
        named.delete(name);
        dropped = true;
      }
    }
    if (dropped) writePlaces(record);
  },
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
  starts += 1;
  const mine = starts;
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
    const writing = found.transaction([STORE, KEYS, UPLOADS], "readwrite");
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
    // The places kept at an earlier start, under those of this run.
    const uploads = writing.objectStore(UPLOADS);
    const placeNames = await done(uploads.getAllKeys());
    const placePairs = await done(uploads.getAll());
    placeNames.forEach((record, at) => {
      if (typeof record !== "string" || !Array.isArray(placePairs[at])) return;
      const earlier = new Map(placePairs[at].filter((pair) => Array.isArray(pair) && pair.length === 2 && typeof pair[0] === "string" && typeof pair[1] === "string"));
      for (const [name, key] of places.get(record) ?? []) earlier.set(name, key);
      places.set(record, earlier);
    });
    for (const [record, named] of places) uploads.put([...named], record);
    // The previews made in this run that an upload asked to keep.
    for (const [key, gif] of gifs) {
      if (gif.kept) previews.put(gif.blob, key);
    }
    // A later start replaces this one: the database it opened is left.
    if (mine !== starts) {
      found.close();
      return;
    }
    database = found;
    told();
  } catch {
    if (mine === starts) {
      database = null;
    }
  }
}

function writeGif(key, blob) {
  if (database === null) {
    return;
  }
  try {
    database.transaction(STORE, "readwrite").objectStore(STORE).put(blob, key);
  } catch {
    // The preview stays for this run.
  }
}

// Makes the next preview asked for, a step at a time between the app's other work.
function nextMaking() {
  if (making !== null) return;
  while (queue.length > 0 && queue[0].stopped) queue.shift();
  if (queue.length === 0) return;
  making = queue.shift();
  const job = making;
  const finish = (preview) => {
    making = null;
    jobs.delete(job.key);
    job.bytes = null;
    if (preview !== null) {
      const blob = new Blob([preview], {type: "image/gif"});
      gifs.set(job.key, {blob, kept: job.kept});
      own.set(job.key, URL.createObjectURL(blob));
      if (job.kept) writeGif(job.key, blob);
      told();
    }
    job.settle();
    setTimeout(nextMaking, 0);
  };
  let maker;
  try {
    maker = previewMaker(job.bytes);
  } catch {
    finish(null);
    return;
  }
  const step = () => {
    if (job.stopped) {
      finish(null);
      return;
    }
    try {
      if (!maker.step()) {
        setTimeout(step, 0);
        return;
      }
    } catch {
      finish(null);
      return;
    }
    finish(maker.preview);
  };
  setTimeout(step, 0);
}

// Makes the preview of bytes this phone sends, or is about to: one at a time, in the order
// they were asked for, the preview this run's at once when it is made. A key that either
// catalog has, and bytes that make no preview, are left as they are, and nothing is said.
// Gives a handle: `key`, `done`, a promise that settles when the preview is made or refused,
// and `release()`, which stops a making that no other handle waits for. `keep(handle)` writes
// the preview into the phone's own catalog, now or when it is made.
export function makeOwn(bytes) {
  const key = `${crc32(bytes)}-${bytes.length}`;
  let job = jobs.get(key);
  if (job === undefined) {
    if (inDefaults(key) || own.has(key)) {
      return {key, done: Promise.resolve(), release() {}};
    }
    let settle;
    const done = new Promise((resolve) => {
      settle = resolve;
    });
    job = {key, bytes, waiting: 0, kept: false, stopped: false, done, settle};
    jobs.set(key, job);
    queue.push(job);
    nextMaking();
  }
  job.waiting += 1;
  let released = false;
  return {
    key,
    done: job.done,
    release() {
      if (released) return;
      released = true;
      job.waiting -= 1;
      if (job.waiting === 0 && jobs.get(key) === job) {
        job.stopped = true;
        jobs.delete(key);
        job.settle();
      }
    },
  };
}

// The upload of a handle's bytes ended with success: its preview is written into the phone's
// own catalog, now or when it is made.
export function keep(handle) {
  const job = jobs.get(handle.key);
  if (job !== undefined) {
    job.kept = true;
    return;
  }
  const gif = gifs.get(handle.key);
  if (gif !== undefined && !gif.kept) {
    gif.kept = true;
    writeGif(handle.key, gif.blob);
  }
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
