// The operator reads the list of Animations with the sizes and the menus of its rows, and
// may delete an animation from its menu: chooses Delete, reads the question, and answers
// it.

import {choose, menuOf, shown, spaceKnown, storage} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  await app.until(() => spaceKnown(app) && storage(app).rows.length === app.settings.rows, `the space and ${app.settings.rows} rows`);
  const seen = {before: storage(app), buttons: [...app.doc.querySelectorAll("nav button")].map((button) => button.textContent.trim()), menus: {}};
  for (const row of seen.before.rows) {
    seen.menus[row.id] = menuOf(app, row.id);
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
  }
  seen.menuClosed = app.byId("row-menu").hidden;
  if (app.settings.remove !== undefined) {
    menuOf(app, app.settings.remove);
    choose(app, "Delete");
    await app.until(() => app.text("confirm-text") !== null, "the question");
    seen.question = app.text("confirm-text");
    seen.answers = [...app.doc.querySelectorAll("#confirm button")].map((button) => button.textContent.trim());
    app.press(app.settings.answer);
    await app.until(() => app.text("confirm-text") === null, "the question is gone");
    if (app.settings.until !== undefined) {
      await app.until(() => app.says(app.settings.until), `on the screen: ${app.settings.until}`, 8000);
    }
    // The list and the space that are asked for after an answer have time to come.
    await app.sleep(1500);
    seen.after = storage(app);
    seen.message = app.text("message-text");
  }
  return seen;
}
