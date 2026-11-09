// The operator renames and moves folders of the board's own storage: the menu of each folder's
// row, then each act in turn: `Rename…` with the name typed, `Move to…` of one folder with the
// destinations the chooser offers and why some are disabled, and a folder selected and moved
// with `Move to…` of the selection; and what the app says after each.

import {choose, shown} from "../reading.js";

function rowOf(app, path) {
  return app.doc.querySelector(`#animations-list > .folder-row[data-path="${path}"]`);
}

function menuOf(app, path) {
  rowOf(app, path).querySelector(".more").click();
  const menu = app.byId("row-menu");
  if (menu.hidden) throw new Error(`the menu of folder ${path} did not open`);
  return [...menu.children].map((item) => (item.localName === "button" ? `${item.textContent}${item.disabled ? " (disabled)" : ""}` : item.textContent));
}

function escape(app) {
  app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
}

function choices(app) {
  return [...app.byId("move-folder").options].map((option) => `${option.textContent}${option.disabled ? " (disabled)" : ""}`);
}

async function said(app) {
  await app.until(() => !app.byId("message").hidden, "what the app says", 20000);
  const text = app.text("message-text");
  app.press("OK");
  return text;
}

async function ready(app, path) {
  await app.until(() => rowOf(app, path) !== null && !rowOf(app, path).querySelector(".more").disabled, `the menu of ${path}`, 10000);
}

export default async function (app) {
  const settings = app.settings;
  const view = app.frame.contentWindow;
  await shown(app, settings.rows);
  await app.until(() => settings.folders.every((path) => rowOf(app, path) !== null), "the folders' rows", 10000);
  for (const path of settings.folders) await ready(app, path);
  const seen = {menus: {}, acts: []};
  for (const path of settings.folders) {
    seen.menus[path] = menuOf(app, path);
    escape(app);
  }
  for (const act of settings.acts) {
    const done = {act: act.kind, path: act.path};
    await ready(app, act.path);
    if (act.kind === "rename") {
      menuOf(app, act.path);
      choose(app, "Rename…");
      await app.until(() => !app.byId("folder-dialog").hidden, "the rename dialog");
      done.title = app.text("folder-dialog-title");
      done.where = app.text("folder-where");
      done.field = app.byId("folder-name").value;
      for (const name of act.names) {
        app.fill("folder-name", name);
        done[`path ${name}`] = app.text("folder-path");
        app.pressIn("#folder-dialog", "Rename");
        if (!app.byId("folder-dialog").hidden) done[`problem ${name}`] = app.text("folder-problem");
      }
      if (!app.byId("folder-dialog").hidden) app.pressIn("#folder-dialog", "Cancel");
      else done.message = await said(app);
    } else if (act.kind === "move") {
      menuOf(app, act.path);
      choose(app, "Move to…");
      const folder = app.byId("move-folder");
      await app.until(() => folder.options.length > 1, "the destinations", 10000);
      done.storages = [...app.byId("move-storage").options].map((option) => `${option.value}${option.disabled ? " (disabled)" : ""}`);
      done.choices = choices(app);
      folder.value = act.to;
      folder.dispatchEvent(new view.Event("change", {bubbles: true}));
      const go = app.byId("move-go");
      await app.until(() => !go.disabled, "the move's preview", 10000);
      done.preview = app.text("move-preview");
      go.click();
      done.message = await said(app);
    } else if (act.kind === "selected") {
      menuOf(app, act.path);
      choose(app, "Select");
      await app.until(() => /selected/.test(app.raw("selection-summary")), "the selection");
      app.press("Move to…");
      const storage = app.byId("move-storage");
      await app.until(() => app.byId("move-folder").options.length > 0, "the destinations", 10000);
      storage.value = "internal";
      storage.dispatchEvent(new view.Event("change", {bubbles: true}));
      const folder = app.byId("move-folder");
      await app.until(() => [...folder.options].some((option) => option.value === act.to), "the internal folders", 10000);
      folder.value = act.to;
      folder.dispatchEvent(new view.Event("change", {bubbles: true}));
      const go = app.byId("move-go");
      await app.until(() => !go.disabled, "the move's preview", 10000);
      done.preview = app.text("move-preview");
      go.click();
      done.message = await said(app);
    }
    if (act.gone !== undefined) {
      await app.until(() => (rowOf(app, act.path) === null) === act.gone, "the list read again", 10000);
    }
    done.rows = [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => row.dataset.path);
    seen.acts.push(done);
  }
  return seen;
}
