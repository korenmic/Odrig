// The operator enters folders by their rows, of the board's own storage or of the card,
// selects one animation there and moves it to a storage and a folder, the destination shown
// before it is sent; the card's folders the chooser offers are kept.

import {rowOf, shown, startSelection} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  const view = app.frame.contentWindow;
  await shown(app, settings.rows);
  for (const [id, path] of settings.enter) {
    const row = await app.until(() => app.doc.querySelector(`#animations-list > .folder-row[data-id="${id}"]`), `the folder row ${id}`, 10000);
    (row.querySelector(".folder-open") ?? row).click();
    await app.until(() => app.text("level-title") === path, `the folder ${path}`, 10000);
  }
  await app.until(() => app.doc.querySelector(`#animations-list > .row[data-id="${settings.id}"]`) !== null, `the row of ${settings.id}`, 10000);
  startSelection(app);
  for (const input of app.doc.querySelectorAll("#animations-list .row .pick input")) {
    if (input.checked) input.click();
  }
  rowOf(app, settings.id).querySelector(".pick input").click();
  await app.until(() => /1 selected/.test(app.raw("selection-summary")), "the selection summary");
  app.press("Move to…");
  const go = app.byId("move-go");
  const folder = app.byId("move-folder");
  const preview = app.byId("move-preview");
  await app.until(() => preview.children.length > 0, "the move's first preview", 10000);
  const seen = {cardFolders: [...folder.options].map((option) => option.value)};
  const storage = app.byId("move-storage");
  storage.value = settings.storage;
  storage.dispatchEvent(new view.Event("change", {bubbles: true}));
  if (settings.storage === "external") {
    folder.value = settings.folder;
    folder.dispatchEvent(new view.Event("change", {bubbles: true}));
  }
  await app.until(() => preview.children.length > 0 && (settings.skipped || !go.disabled), "the move's preview", 10000);
  seen.preview = app.text("move-preview");
  if (settings.skipped) {
    seen.go = go.textContent.trim();
    return seen;
  }
  go.click();
  await app.until(() => /Moved \d+ of \d+/.test(app.text("message-text") ?? ""), "the move's end", 30000);
  seen.message = app.text("message-text");
  return seen;
}
