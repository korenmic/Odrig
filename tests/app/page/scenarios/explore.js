// The operator makes a folder of the card at the root, selects an internal animation and
// moves it into that folder, the destination shown before it is sent. `ends` is what the
// message at the move's end says, `Moved 1 of 1` unless the settings name another. With
// `settle`, the message and the paths of the moves the phone keeps are read again that many
// milliseconds after the end.

import {rowOf, shown, startSelection} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  const view = app.frame.contentWindow;
  await shown(app, settings.rows);
  const seen = {};
  if (settings.selectAll) {
    for (const path of ["night", "night/deep"]) {
      const button = await app.until(() => app.doc.querySelector(`button[aria-label="Open folder ${path}"]`), "the folder row");
      button.click();
      await app.until(() => app.text("level-title") === path, "the explored folder");
    }
    await app.until(() => app.doc.querySelector('#animations-list .row[data-external="true"]') !== null, "the card's row");
    startSelection(app);
    app.press("Select all");
    await app.until(() => /selected/.test(app.raw("selection-summary")), "the selection summary");
    seen.summary = app.text("selection-summary");
    seen.deleteDisabled = app.byId("delete-selected").disabled;
    seen.moveDisabled = app.byId("move-selected").disabled;
    return seen;
  }
  const newFolder = app.byId("new-folder");
  await app.until(() => !newFolder.hidden && !newFolder.disabled, "the New folder button");
  app.press("New folder");
  await app.until(() => !app.byId("folder-dialog").hidden, "the folder dialog");
  seen.where = app.text("folder-where");
  app.fill("folder-name", settings.folder);
  app.press("Make it");
  await app.until(() => app.says("Made the folder"), "the folder made", 10000);
  seen.made = app.text("message-text");
  await app.until(() => app.doc.querySelector(`button[aria-label="Open folder ${settings.folder}"]`) !== null, "the empty folder's row", 10000);
  startSelection(app);
  for (const input of app.doc.querySelectorAll("#animations-list .row .pick input")) {
    if (input.checked) input.click();
  }
  rowOf(app, settings.id).querySelector(".pick input").click();
  await app.until(() => /1 selected/.test(app.raw("selection-summary")), "the selection summary");
  seen.summary = app.text("selection-summary");
  app.press("Move to\u2026");
  const folder = app.byId("move-folder");
  await app.until(() => [...folder.options].some((option) => option.value === settings.folder), "the card's folders", 10000);
  folder.value = settings.folder;
  folder.dispatchEvent(new view.Event("change", {bubbles: true}));
  const go = app.byId("move-go");
  await app.until(() => !go.disabled, "the move's preview", 10000);
  seen.preview = app.text("move-preview");
  seen.go = go.textContent.trim();
  go.click();
  await app.until(() => app.says(settings.ends ?? "Moved 1 of 1"), "the move's end", 30000);
  seen.message = app.text("message-text");
  if (settings.settle !== undefined) {
    await new Promise((resolve) => setTimeout(resolve, settings.settle));
    seen.settled = app.text("message-text");
    seen.kept = Object.values(JSON.parse(view.localStorage.getItem("odrig.moves") || "{}")).flat().map((job) => job.source.path);
  }
  return seen;
}
