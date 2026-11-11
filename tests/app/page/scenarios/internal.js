// The operator walks the folders of the board's own storage on Animations: the root's rows of
// them, a folder entered with its own rows, and a new folder made at the root and inside one.

import {rows, shown} from "../reading.js";

function folderRows(app) {
  return [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => ({
    path: row.dataset.path,
    id: Number(row.dataset.id),
    meta: row.querySelector(".meta").textContent,
  }));
}

async function makeFolder(app, name, storage) {
  const view = app.frame.contentWindow;
  const newFolder = app.byId("new-folder");
  await app.until(() => !newFolder.hidden && !newFolder.disabled, "the New folder button");
  app.press("New folder");
  await app.until(() => !app.byId("folder-dialog").hidden, "the folder dialog");
  const chosen = app.byId("folder-storage");
  const offered = !chosen.hidden;
  if (storage !== null) {
    chosen.value = storage;
    chosen.dispatchEvent(new view.Event("change", {bubbles: true}));
  }
  const where = app.text("folder-where");
  app.fill("folder-name", name);
  app.press("Make it");
  await app.until(() => app.says("Made the folder"), "the folder made", 10000);
  return {offered, where, made: app.text("message-text")};
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  await app.until(() => folderRows(app).length >= settings.folders, "the root's folder rows");
  const seen = {root: {rows: rows(app).map((row) => row.text), folders: folderRows(app)}};
  seen.atRoot = await makeFolder(app, "made", "internal");
  app.press("OK");
  await app.until(() => app.doc.querySelector('button[aria-label="Open folder made"]') !== null, "the new folder's row", 10000);
  app.doc.querySelector(`button[aria-label="Open folder ${settings.enter}"]`).click();
  await app.until(() => app.text("level-title") === settings.enter, "the internal folder", 10000);
  await app.until(() => rows(app).length >= settings.inside, "the internal folder's rows", 10000);
  seen.inside = {rows: rows(app).map((row) => row.text), folders: folderRows(app)};
  seen.inFolder = await makeFolder(app, "inner", null);
  return seen;
}
