// The operator removes empty folders with Remove folder in the menu of a folder's row: the
// menu's actions and notes for each folder, then each act in turn, a folder found not empty,
// the question with Cancel, Escape and Remove, and what the app says afterwards.

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

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  await app.until(() => settings.folders.every((path) => rowOf(app, path) !== null), "the folders' rows", 10000);
  await app.until(() => settings.folders.every((path) => !rowOf(app, path).querySelector(".more").disabled), "the folders' menus", 10000);
  // New folder is offered at the root once the app knows whether the board may write the card.
  await app.until(() => !app.byId("new-folder").hidden, "the card's state", 10000);
  const seen = {menus: {}, acts: []};
  for (const path of settings.folders) {
    seen.menus[path] = menuOf(app, path);
    escape(app);
  }
  for (const act of settings.acts) {
    const done = {path: act.path};
    await app.until(() => rowOf(app, act.path) !== null && !rowOf(app, act.path).querySelector(".more").disabled, "the folder's menu", 10000);
    menuOf(app, act.path);
    choose(app, "Remove folder");
    const dialog = app.byId("folder-remove-dialog");
    await app.until(() => !dialog.hidden || !app.byId("message").hidden, "the question or a message", 10000);
    if (!dialog.hidden) {
      done.question = app.text("folder-remove-text");
      if (act.answer === "cancel") app.pressIn("#folder-remove-dialog", "Cancel");
      else if (act.answer === "escape") escape(app);
      else app.pressIn("#folder-remove-dialog", "Remove");
      done.closed = dialog.hidden;
    }
    if (act.answer === "cancel" || act.answer === "escape") {
      seen.acts.push(done);
      continue;
    }
    await app.until(() => !app.byId("message").hidden, "what the app says", 20000);
    done.message = app.text("message-text");
    app.press("OK");
    if (act.gone !== undefined) {
      await app.until(() => (rowOf(app, act.path) === null) === act.gone, "the list read again", 10000);
    }
    done.rows = [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => row.dataset.path);
    seen.acts.push(done);
  }
  return seen;
}
