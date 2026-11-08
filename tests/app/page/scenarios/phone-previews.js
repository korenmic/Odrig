// The previews this phone makes of what it uploads: in the row as soon as the upload ended,
// on a storage without a catalog too, kept with the place across a reload, and dropped with
// the place when a complete list no longer names the file.
import {shown} from "../reading.js";
import {pick} from "./batch.js";

// The source of the preview in the square of a row, or null.
function square(app, file) {
  const row = [...app.doc.querySelectorAll("#animations-list > .row")].find((item) => item.dataset.file === file);
  const image = row?.querySelector(".thumb img") ?? null;
  return image === null ? null : image.getAttribute("src");
}

// What the phone keeps in its database: its version, the keys of its previews and its places.
async function stored(app) {
  const view = app.frame.contentWindow;
  return new Promise((resolve) => {
    const request = view.indexedDB.open("odrig-previews");
    request.onsuccess = () => {
      const database = request.result;
      const names = [...database.objectStoreNames];
      const found = {version: database.version, stores: names.sort(), previews: [], uploads: {}};
      if (!names.includes("uploads")) {
        database.close();
        resolve(found);
        return;
      }
      const reading = database.transaction(["previews", "uploads"], "readonly");
      const keys = reading.objectStore("previews").getAllKeys();
      const records = reading.objectStore("uploads").getAllKeys();
      const pairs = reading.objectStore("uploads").getAll();
      reading.oncomplete = () => {
        found.previews = keys.result;
        records.result.forEach((record, at) => {
          found.uploads[record.replace(/^\S+ /, "")] = pairs.result[at];
        });
        database.close();
        resolve(found);
      };
    };
    request.onerror = () => resolve(null);
  });
}

// Makes the database of an older version, with a record in each store it had.
async function older(app, version) {
  const view = app.frame.contentWindow;
  await new Promise((resolve, reject) => {
    const request = view.indexedDB.open("odrig-previews-old-made", 1);
    request.onsuccess = () => {
      request.result.close();
      resolve();
    };
    request.onerror = () => reject(request.error);
  });
  await new Promise((resolve) => {
    const gone = view.indexedDB.deleteDatabase("odrig-previews");
    gone.onsuccess = gone.onerror = gone.onblocked = () => resolve();
  });
  await new Promise((resolve, reject) => {
    const request = view.indexedDB.open("odrig-previews", version);
    request.onupgradeneeded = () => {
      request.result.createObjectStore("previews");
      if (version >= 2) request.result.createObjectStore("keys");
    };
    request.onsuccess = () => {
      const database = request.result;
      const writing = database.transaction(version >= 2 ? ["previews", "keys"] : ["previews"], "readwrite");
      writing.objectStore("previews").put(new view.Blob([new Uint8Array([71, 73, 70])], {type: "image/gif"}), "00000000-1");
      if (version >= 2) writing.objectStore("keys").put({generation: 1, entries: 1, names: [["a.odrg", "00000000-1"]]}, "127.0.0.1:1 internal");
      writing.oncomplete = () => {
        database.close();
        resolve();
      };
      writing.onerror = () => reject(writing.error);
    };
    request.onerror = () => reject(request.error);
  });
}

// Waits until an asynchronous check gives something, at most `ms` milliseconds.
async function eventually(app, check, ms) {
  const end = performance.now() + ms;
  for (;;) {
    const found = await check();
    if (found || performance.now() > end) return found;
    await app.sleep(100);
  }
}

export default async function (app) {
  const settings = app.settings;
  if (settings.older !== undefined) {
    await older(app, settings.older);
    await app.reload();
    await shown(app, settings.rows);
    await eventually(app, async () => (await stored(app))?.version === 3, 8000);
    const found = await stored(app);
    const view = app.frame.contentWindow;
    const kept = await new Promise((resolve) => {
      const request = view.indexedDB.open("odrig-previews");
      request.onsuccess = () => {
        const reading = request.result.transaction(settings.older >= 2 ? ["previews", "keys"] : ["previews"], "readonly");
        const previews = reading.objectStore("previews").getAllKeys();
        const keys = settings.older >= 2 ? reading.objectStore("keys").getAllKeys() : null;
        reading.oncomplete = () => {
          request.result.close();
          resolve({previews: previews.result, keys: keys === null ? [] : keys.result});
        };
      };
    });
    return {version: found.version, stores: found.stores, ...kept};
  }
  await shown(app, settings.rows);
  app.press("Upload");
  await app.until(() => /^Internal storage: Free [0-9]/.test(app.raw("upload-space")), "the storage's capacity");
  await pick(app, "ready-file", [settings.file]);
  await app.until(() => app.text("made-facts") !== null, "the ready-made form");
  await app.until(() => app.text("ready-preview-note") !== null && !app.byId("ready-preview").hidden, "the preview made on this phone", 15000).catch(() => null);
  const seen = {note: app.text("ready-preview-note")};
  app.press("Upload to the installation");
  await app.until(() => app.text("message-text") !== null, "the upload's end", 30000);
  seen.message = app.text("message-text");
  app.byId("message-close").click();
  const name = settings.file.replace(/\.[^.]*$/, "").toLowerCase() + ".odrg";
  app.press("Animations");
  await app.until(() => app.shown() === "animations", "Animations");
  if (!seen.message.startsWith("Uploaded")) {
    await app.sleep(1500);
    seen.square = square(app, name);
    seen.stored = await stored(app);
    return seen;
  }
  await app.until(() => square(app, name) !== null, "the preview in the row", 15000).catch(() => null);
  seen.square = square(app, name);
  seen.stored = await stored(app);
  if (settings.reload) {
    await app.reload();
    await shown(app, settings.rows + 1);
    await app.until(() => square(app, name) !== null, "the preview after the reload", 15000).catch(() => null);
    seen.afterReload = square(app, name);
  }
  if (settings.removedElsewhere) {
    await app.step();
    await eventually(app, async () => Object.values((await stored(app)).uploads).every((pairs) => pairs.length === 0), 30000);
    seen.afterRemoval = (await stored(app)).uploads;
  }
  if (settings.resized) {
    await app.step();
    await app.until(() => {
      const row = [...app.doc.querySelectorAll("#animations-list > .row")].find((item) => item.dataset.file === name);
      return row !== undefined && square(app, name) === null;
    }, "the row of another size without the preview", 30000).catch(() => null);
    seen.afterResize = square(app, name);
  }
  return seen;
}
