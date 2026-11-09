// The operator enters folders by their rows, selects files and folders of the level shown,
// presses Move to…, chooses a storage and a folder, reads the preview, may give a skipped
// name another one, and moves them. With `journal` the app is opened again first with the
// moves an earlier run left kept on the phone, and the scenario waits for their end.

import {rowOf, shown, startSelection} from "../reading.js";

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

function change(app, id, value) {
  const view = app.frame.contentWindow;
  const field = app.byId(id);
  field.value = value;
  field.dispatchEvent(new view.Event("change", {bubbles: true}));
}

export default async function (app) {
  const settings = app.settings;
  if (settings.journal !== undefined) {
    app.frame.contentWindow.localStorage.setItem("odrig.moves", JSON.stringify({[app.kept()]: settings.journal}));
    await app.reload();
    await shown(app, settings.rows);
    await app.until(() => /interrupted move|Not moved, left/.test(app.text("message-text") ?? ""), "the end of the interrupted moves", 30000);
    const seen = {message: app.text("message-text"), sentAfter: []};
    if (settings.watch !== undefined) {
      // The lines the app sends for a while after it has said how the moves ended.
      const view = app.frame.contentWindow;
      const fetched = view.fetch;
      view.fetch = (url, options) => {
        if (typeof options?.body === "string") seen.sentAfter.push(options.body);
        return fetched.call(view, url, options);
      };
      await app.sleep(settings.watch);
      view.fetch = fetched;
    }
    seen.kept = app.frame.contentWindow.localStorage.getItem("odrig.moves");
    return seen;
  }
  await shown(app, settings.rows);
  // The sizes of the animations, which the board knows once it has read them after its start.
  await app.until(() => [...app.doc.querySelectorAll("#animations-list > .row")].every((row) => row.dataset.fault !== "" ||
    !row.querySelector(".meta").textContent.includes("size not read yet")), "the sizes of the animations", 15000);
  for (const path of settings.enter ?? []) await enter(app, path);
  for (const id of settings.files ?? []) {
    await app.until(() => app.doc.querySelector(`#animations-list > .row[data-id="${id}"]`) !== null, `the row of ${id}`, 10000);
  }
  for (const path of settings.folders ?? []) {
    await app.until(() => app.doc.querySelector(`#animations-list > .folder-row[data-path="${path}"]`) !== null, `the row of the folder ${path}`, 10000);
  }
  startSelection(app);
  for (const input of app.doc.querySelectorAll("#animations-list .pick input")) {
    if (input.checked) input.click();
  }
  for (const id of settings.files ?? []) rowOf(app, id).querySelector(".pick input").click();
  for (const path of settings.folders ?? []) folderPick(app, path).click();
  await app.until(() => /selected/.test(app.raw("selection-summary")), "the selection summary");
  // The card can take files once the app knows it is present, writable and its catalog read.
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.space?.external?.present === true && client.state.catalog?.external?.state === "ok", "the card's catalog read", 15000);
  await app.until(() => !app.byId("move-selected").disabled, "Move to… enabled", 10000);
  const seen = {summary: app.text("selection-summary")};
  app.press("Move to…");
  const go = app.byId("move-go");
  const preview = app.byId("move-preview");
  await app.until(() => preview.children.length > 0, "the move's first preview", 15000);
  change(app, "move-storage", settings.storage);
  await app.until(() => [...app.byId("move-folder").options].some((option) => option.value === settings.folder), "the destination's folders", 10000);
  change(app, "move-folder", settings.folder);
  await app.until(() => preview.children.length > 0 && app.byId("move-folder").value === settings.folder && app.byId("move-storage").value === settings.storage &&
    (settings.skipped || settings.rename !== undefined || !go.disabled), "the move's preview", 15000);
  for (const [label, name] of Object.entries(settings.rename ?? {})) {
    const field = app.doc.querySelector(`#move-preview input[aria-label="Another name for ${label}"]`);
    if (field === null) throw new Error(`no field for another name of ${label}`);
    const before = app.text("move-preview");
    field.value = name;
    field.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
    await app.until(() => app.text("move-preview") !== before, "the preview with the other name", 10000);
  }
  if (!settings.skipped) await app.until(() => !go.disabled, "the move's preview to move", 15000);
  seen.options = [...app.byId("move-folder").options].map((option) => option.value);
  seen.preview = [...preview.children].map((item) => item.textContent);
  seen.go = go.textContent.trim();
  if (settings.skipped) return seen;
  go.click();
  await app.until(() => /Moved \d+ of \d+/.test(app.text("message-text") ?? ""), "the move's end", 60000);
  seen.message = app.text("message-text");
  return seen;
}
