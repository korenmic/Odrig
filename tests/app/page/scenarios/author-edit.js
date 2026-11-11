// The operator edits an installed text or clock from its row's menu: the form opens on
// Upload with what the installation holds, takes a change, and Save puts it in place; or
// another controller changed the animation meanwhile; or the clock is made from a picture,
// and a message says so in place of the form. And the menus of some rows.

import {choose, menuOf, rows, shown, spaceKnown, storage} from "../reading.js";

function set(app, id, value) {
  const field = app.byId(id);
  field.value = String(value);
  field.dispatchEvent(new Event("input", {bubbles: true}));
  field.dispatchEvent(new Event("change", {bubbles: true}));
}

// The fields of the form that tell what it holds.
function form(app) {
  return {title: app.text("author-title"), words: app.byId("text-words").value, seconds: app.byId("clock-seconds").value, button: app.byId("author-upload").textContent};
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  const seen = {menus: {}};
  for (const id of settings.menus || []) {
    seen.menus[id] = menuOf(app, id);
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape"}));
  }
  if (settings.edit === undefined) {
    return seen;
  }
  menuOf(app, settings.edit);
  choose(app, "Edit");
  if (settings.refused === true) {
    await app.until(() => app.text("message-text") !== null, "a message in place of the form", 10000);
    seen.message = app.text("message-text");
    seen.formShown = !app.byId("author").hidden;
    app.press("OK");
    return seen;
  }
  await app.until(() => app.shown() === "upload" && app.byId("author-upload").textContent === "Save" && !app.byId("author-upload").disabled, "the form of the animation", 10000);
  seen.opened = form(app);
  for (const [id, value] of settings.fields || []) {
    set(app, id, value);
  }
  seen.says = app.text("author-says");
  if (settings.changedElsewhere === true) {
    await app.step();
  }
  if (settings.beginAgain === true) {
    // The target is asked again from the start: its status answers, and the root's names
    // are still being read when Save is pressed.
    await app.step();
    const client = await app.frame.contentWindow.eval('import("/client.js")');
    client.begin();
    await app.until(() => client.state.link === "answers" && client.state.status !== null && !app.byId("author-upload").disabled,
      "the target answering again with the form ready", 10000);
    seen.namesWhileSaving = client.state.rootNames;
  }
  app.press("Save");
  // Every text of the line, and for each Checking text whether Cancel is shown with it.
  seen.sending = [];
  seen.cancelShown = [];
  await app.until(() => {
    const now = app.text("author-uploading");
    if (now !== null && seen.sending[seen.sending.length - 1] !== now) {
      seen.sending.push(now);
      if (now.startsWith("Checking")) {
        seen.cancelShown.push(app.text("author-cancel") !== null);
      }
    }
    return app.text("message-text") !== null;
  }, "a message after saving", 20000);
  seen.message = app.text("message-text");
  seen.lineHidden = app.text("author-uploading") === null;
  seen.after = form(app);
  app.press("OK");
  if (settings.beginAgain === true) {
    return seen;
  }
  app.press("Animations");
  await app.until(() => app.shown() === "animations" && spaceKnown(app) && rows(app).length === settings.rows, "Animations", 10000);
  seen.rows = storage(app).rows;
  return seen;
}
