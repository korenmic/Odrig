// In Clocks only, the operator renames a folder of the board's own storage at the Clocks level,
// or opens `Move to…` of one inside Clocks: what the menu offers, the destinations the chooser
// gives, and what the app says.

import {choose} from "../reading.js";

function rowOf(app, id) {
  return app.doc.querySelector(`#animations-list > .folder-row[data-id="${id}"]`);
}

function menuOf(app, id) {
  rowOf(app, id).querySelector(".more").click();
  return [...app.byId("row-menu").children].map((item) => (item.localName === "button" ? `${item.textContent}${item.disabled ? " (disabled)" : ""}` : item.textContent));
}

export default async function (app) {
  const settings = app.settings;
  const seen = {};
  await app.until(() => !app.byId("level-back").hidden, "the Clocks folder shown", 10000);
  app.byId("level-back").click();
  await app.until(() => app.raw("level-title") === "Clocks" && app.doc.querySelectorAll("#animations-list > .folder-row").length === 2, "the Clocks level", 10000);
  if (settings.enter !== undefined) {
    rowOf(app, settings.enter).querySelector(".folder-open").click();
    await app.until(() => rowOf(app, settings.id) !== null, "the folder inside", 10000);
  }
  await app.until(() => !rowOf(app, settings.id).querySelector(".more").disabled, "the folder's menu", 10000);
  seen.menu = menuOf(app, settings.id);
  if (settings.rename !== undefined) {
    choose(app, "Rename…");
    await app.until(() => !app.byId("folder-dialog").hidden, "the rename dialog");
    app.fill("folder-name", settings.rename);
    app.pressIn("#folder-dialog", "Rename");
  } else {
    choose(app, "Move to…");
    const folder = app.byId("move-folder");
    await app.until(() => folder.options.length > 0 && app.byId("move-state").textContent !== "", "the destinations", 10000);
    await app.until(() => !app.byId("move-go").disabled || [...folder.options].every((option) => option.disabled), "the preview", 10000);
    seen.choices = [...folder.options].map((option) => `${option.textContent}${option.disabled ? " (disabled)" : ""}`);
    app.pressIn("#move-dialog", "Cancel");
    return seen;
  }
  await app.until(() => !app.byId("message").hidden, "what the app says", 20000);
  seen.message = app.text("message-text");
  return seen;
}
