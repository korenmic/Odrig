// The operator downloads an animation from its row's menu, or selects files and folders of
// a level and presses Download selected, which saves one zip of one storage, and may press
// Stop or choose another target while it runs. The bytes the app hands to the browser as a
// download are what the scenario gives the test.

import {choose, menuOf, rowOf, shown, startSelection} from "../reading.js";

// Every file the app saves from now on: its name and the Blob it made.
function capture(app) {
  const view = app.frame.contentWindow;
  const saved = [];
  const blobs = new Map();
  const create = view.URL.createObjectURL.bind(view.URL);
  view.URL.createObjectURL = (blob) => {
    const url = create(blob);
    blobs.set(url, blob);
    return url;
  };
  view.HTMLAnchorElement.prototype.click = function () {
    saved.push({name: this.download, blob: blobs.get(this.href)});
  };
  return saved;
}

async function base64Of(blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let text = "";
  for (let at = 0; at < bytes.length; at += 0x8000) text += String.fromCharCode(...bytes.subarray(at, at + 0x8000));
  return btoa(text);
}

async function enter(app, path) {
  const button = await app.until(() => app.doc.querySelector(`button[aria-label="Open folder ${path}"]`), `the folder row ${path}`, 10000);
  button.click();
  await app.until(() => app.text("level-title") === path, `the folder ${path}`, 10000);
}

function folderPick(app, path) {
  const row = app.doc.querySelector(`#animations-list > .folder-row[data-path="${path}"]`);
  if (row === null) throw new Error(`no row of the folder ${path}`);
  return row.querySelector(".pick input");
}

async function saved(app, files, count) {
  await app.until(() => files.length >= count && !app.byId("message").hidden, "the file saved and the message", 30000);
  return {message: app.text("message-text"), files: await Promise.all(files.map(async (file) => ({name: file.name, data: await base64Of(file.blob)})))};
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  const files = capture(app);
  const seen = {};
  // The sizes of the animations, which the board knows once it has read them after its start.
  await app.until(() => [...app.doc.querySelectorAll("#animations-list > .row")].every((row) => row.dataset.fault !== "" ||
    !row.querySelector(".meta").textContent.includes("size not read yet")), "the sizes of the animations", 15000);
  for (const path of settings.enter ?? []) await enter(app, path);
  if (settings.rowsThere !== undefined) {
    await app.until(() => app.doc.querySelectorAll("#animations-list > .row").length === settings.rowsThere, "the level's rows", 10000);
  }
  if (settings.one !== undefined) {
    seen.menu = menuOf(app, settings.one);
    choose(app, "Download");
    if (settings.hide) {
      // The app is taken off the screen after the first piece, and comes back.
      await app.until(() => /^Read [1-9]/.test(app.raw("download-progress")), "the first piece read", 10000);
      let hidden = true;
      Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
      app.doc.dispatchEvent(new Event("visibilitychange"));
      await app.sleep(1500);
      seen.whileHidden = app.raw("download-progress");
      hidden = false;
      app.doc.dispatchEvent(new Event("visibilitychange"));
    }
    Object.assign(seen, await saved(app, files, 1));
    return seen;
  }
  // The selection: a row's Select, then the files and folders asked for, or all the files.
  await app.until(() => startSelection(app) !== null, "a row that offers Select", 10000);
  for (const input of app.doc.querySelectorAll("#animations-list .row .pick input")) if (input.checked) input.click();
  if (settings.selectAll) app.press("Select all");
  for (const id of settings.files ?? []) rowOf(app, id).querySelector(".pick input").click();
  for (const path of settings.folders ?? []) folderPick(app, path).click();
  await app.until(() => /selected/.test(app.raw("selection-summary")), "the selection summary");
  seen.summary = app.text("selection-summary");
  seen.deleteDisabled = app.byId("delete-selected").disabled;
  seen.deleteTitle = app.byId("delete-selected").title;
  seen.moveDisabled = app.byId("move-selected").disabled;
  seen.downloadDisabled = app.byId("download-selected").disabled;
  app.press("Download selected");
  await app.until(() => !app.byId("download-dialog").hidden, "the download dialog");
  seen.choice = app.text("download-choice") === null ? null : [...app.byId("download-storage").options].map((option) => option.textContent);
  if (settings.storage !== undefined) {
    const storage = app.byId("download-storage");
    storage.value = settings.storage;
    storage.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
  }
  seen.source = app.text("download-source");
  seen.what = app.text("download-what");
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const target = await app.frame.contentWindow.eval('import("/target.js")');
  app.press("Save the backup");
  if (settings.stopAt !== undefined || settings.other !== undefined) {
    // Stop, or another target, while the file of this place is read.
    const at = settings.stopAt ?? settings.switchAt;
    await app.until(() => app.raw("download-progress").startsWith(`File ${at} of`), `file ${at} under way`, 20000);
    await app.sleep(settings.afterMs ?? 0);
    if (settings.stopAt !== undefined) {
      app.tap("download-stop");
    } else {
      target.setAddress(settings.other);
      client.begin();
      await app.until(() => app.byId("download-dialog").hidden, "the end of the run", 20000);
      await app.sleep(500);
      seen.files = files.map((file) => file.name);
      seen.message = app.byId("message").hidden ? null : app.text("message-text");
      return seen;
    }
  }
  Object.assign(seen, await saved(app, files, 1));
  seen.dialogHidden = app.byId("download-dialog").hidden;
  return seen;
}
