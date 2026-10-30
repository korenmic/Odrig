// The previews this phone makes of what it uploads: an animation made on Upload, or a text
// made in its form, uploaded and then shown in its row, again after the app is loaded anew;
// the phone's catalog at the start, its copy of a key of the default catalog dropped; a
// preview that cannot be made; a web view without IndexedDB; and a start that a later one
// overtakes.

// The app's own modules, through a module script in its frame.
async function modules(app) {
  const script = app.doc.createElement("script");
  script.type = "module";
  script.textContent = 'import * as previews from "./previews.js"; import * as client from "./client.js"; window.ownModules = {previews, client};';
  app.doc.head.append(script);
  await app.until(() => app.frame.contentWindow.ownModules, "the app's modules");
  return app.frame.contentWindow.ownModules;
}

function squareOf(app, file) {
  const row = [...app.doc.querySelectorAll("#animations-list > .row")].find((one) => one.dataset.file === file);
  const image = row === undefined ? null : row.querySelector(".thumb img");
  return {row: row !== undefined, src: image === null ? null : image.getAttribute("src"), loaded: image !== null && image.complete && image.naturalWidth > 0};
}

async function ready(app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
}

// The keys the phone's own catalog holds in IndexedDB, at the version the database has.
async function storedKeys(app) {
  const view = app.frame.contentWindow;
  return new Promise((resolve, reject) => {
    const request = view.indexedDB.open("odrig-previews");
    request.onupgradeneeded = () => request.result.createObjectStore("previews");
    request.onsuccess = () => {
      const keys = request.result.transaction("previews").objectStore("previews").getAllKeys();
      keys.onsuccess = () => {
        request.result.close();
        resolve(keys.result.map(String).sort());
      };
      keys.onerror = () => reject(keys.error);
    };
    request.onerror = () => reject(request.error);
  });
}

// The names of the keys of the catalogs kept in IndexedDB, at the version the database has.
async function keptNames(app) {
  const view = app.frame.contentWindow;
  return new Promise((resolve, reject) => {
    const request = view.indexedDB.open("odrig-previews");
    request.onsuccess = () => {
      const names = request.result.transaction("keys").objectStore("keys").getAllKeys();
      names.onsuccess = () => {
        request.result.close();
        resolve(names.result.map(String).sort());
      };
      names.onerror = () => reject(names.error);
    };
    request.onerror = () => reject(request.error);
  });
}

// IndexedDB of the app's frame, whose opens wait until `let()` is called.
function held(view) {
  const waiting = [];
  return {
    open(name, version) {
      const request = {};
      waiting.push(() => {
        const real = view.indexedDB.open(name, version);
        real.onupgradeneeded = () => {
          request.result = real.result;
          if (request.onupgradeneeded) request.onupgradeneeded();
        };
        real.onsuccess = () => {
          request.result = real.result;
          if (request.onsuccess) request.onsuccess();
        };
        real.onerror = () => {
          request.error = real.error;
          if (request.onerror) request.onerror();
        };
        real.onblocked = () => {
          if (request.onblocked) request.onblocked();
        };
      });
      return request;
    },
    let() {
      for (const open of waiting.splice(0)) open();
    },
  };
}

async function storeKeys(app, keys) {
  const view = app.frame.contentWindow;
  await new Promise((resolve, reject) => {
    const request = view.indexedDB.open("odrig-previews");
    request.onupgradeneeded = () => request.result.createObjectStore("previews");
    request.onsuccess = () => {
      const writing = request.result.transaction("previews", "readwrite");
      for (const key of keys) {
        writing.objectStore("previews").put(new view.Blob([new Uint8Array([71, 73, 70])], {type: "image/gif"}), key);
      }
      writing.oncomplete = () => {
        request.result.close();
        resolve();
      };
      writing.onerror = () => reject(writing.error);
    };
    request.onerror = () => reject(request.error);
  });
}

async function uploadMedia(app, file) {
  app.press("Upload");
  await app.until(() => app.shown() === "upload" && app.text("upload-space") !== "-", "Upload with the space");
  const blob = await (await fetch(`/m/${file}`)).blob();
  const view = app.frame.contentWindow;
  const handed = new view.DataTransfer();
  handed.items.add(new view.File([blob], file, {type: blob.type}));
  const field = app.byId("media");
  field.files = handed.files;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
  await app.until(() => app.text("media-name") !== null, "the name of the file");
  app.press("Make the animation");
  await app.until(() => app.text("made-facts") !== null, "the animation", 30000);
  app.press("Upload to the installation");
  await app.until(() => app.text("message-text") !== null, "a message after the upload", 30000);
  const said = app.text("message-text");
  app.press("OK");
  app.press("Animations");
  return said;
}

async function uploadText(app, words) {
  app.press("Upload");
  await app.until(() => app.shown() === "upload" && app.text("upload-space") !== "-", "Upload with the space");
  app.press("Make a text");
  await app.until(() => app.text("author-says") !== null, "the form of a text");
  const field = app.byId("text-words");
  field.value = words;
  field.dispatchEvent(new Event("input", {bubbles: true}));
  field.dispatchEvent(new Event("change", {bubbles: true}));
  app.press("Upload to the installation");
  await app.until(() => app.text("message-text") !== null, "a message after the upload", 20000);
  const said = app.text("message-text");
  app.press("OK");
  app.press("Animations");
  return said;
}

export default async function (app) {
  const settings = app.settings;
  await ready(app);
  const seen = {};
  if (settings.mode === "generated") {
    const {previews} = await modules(app);
    previews.makeOwn(new Uint8Array(settings.bytes));
    await app.until(() => previews.sourceOf(settings.key) !== null, "the generated widget preview", 15000);
    const source = previews.sourceOf(settings.key);
    const image = new app.frame.contentWindow.Image();
    image.src = source;
    await image.decode();
    seen.size = [image.naturalWidth, image.naturalHeight];
    const bytes = new Uint8Array(await (await app.frame.contentWindow.fetch(source)).arrayBuffer());
    seen.signature = Array.from(bytes.subarray(0, 6));
    seen.message = app.text("message-text");
    return seen;
  }
  if (settings.mode === "start") {
    await storeKeys(app, [settings.defaultKey, "0badcafe-12"]);
    await app.reload();
    await ready(app);
    const {previews} = await modules(app);
    await app.sleep(1000);
    seen.stored = await storedKeys(app);
    seen.defaultSource = previews.sourceOf(settings.defaultKey);
    seen.ownSource = previews.sourceOf("0badcafe-12");
    return seen;
  }
  if (settings.mode === "overtaken") {
    // A start that a later one overtakes, here one without IndexedDB, leaves the database it
    // opens: the keys kept afterwards are written nowhere.
    const {previews} = await modules(app);
    await app.sleep(1000);
    const slow = held(app.frame.contentWindow);
    const overtaken = previews.start(slow);
    await previews.start(null);
    slow.let();
    await overtaken;
    previews.keeper.keep("overtaken", "internal", {generation: 1, entries: 1, byName: new Map([["a.odrg", "00000000-1"]])});
    await app.sleep(500);
    seen.kept = await keptNames(app);
    return seen;
  }
  if (settings.mode === "refused") {
    const {previews} = await modules(app);
    previews.makeOwn(new Uint8Array([79, 68, 82, 71, 9, 9, 9]));
    await app.sleep(1500);
    seen.source = previews.sourceOf(settings.refusedKey);
    seen.stored = await storedKeys(app);
    seen.message = app.text("message-text");
    return seen;
  }
  if (settings.mode === "no-database") {
    const {previews} = await modules(app);
    await previews.start(null);
  }
  seen.message = settings.text === undefined ? await uploadMedia(app, settings.file) : await uploadText(app, settings.text);
  const file = settings.name;
  await app.until(() => {
    const square = squareOf(app, file);
    return square.src !== null && square.src.startsWith("blob:") && square.loaded;
  }, "the row's own preview", 30000);
  seen.uploaded = squareOf(app, file);
  seen.stored = await storedKeys(app);
  await app.reload();
  await ready(app);
  if (settings.mode === "no-database") {
    await app.until(() => squareOf(app, file).row, "the row after the reload", 15000);
    await app.sleep(4000);
  } else {
    await app.until(() => {
      const square = squareOf(app, file);
      return square.src !== null && square.src.startsWith("blob:") && square.loaded;
    }, "the row's own preview after a reload", 30000);
  }
  seen.reloaded = squareOf(app, file);
  return seen;
}
