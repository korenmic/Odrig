// An animation of the card on Animations: its row's badge and its words, the card's
// storage line, its menu, and, when the menu has Delete, its question and what follows.

import {badges, choose, menuOf, rowOf, shown} from "../reading.js";

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  await app.until(() => /^External storage: [0-9]/.test(app.text("show-external-space") || ""), "the card's storage line");
  const seen = {
    badges: badges(app),
    text: rowOf(app, settings.id).innerText.replace(/\s+/g, " ").trim(),
    external: app.text("show-external-space"),
    menu: menuOf(app, settings.id),
  };
  if (seen.menu.includes("Delete")) {
    choose(app, "Delete");
    await app.until(() => app.text("confirm-text") !== null, "the question");
    seen.question = app.text("confirm-text");
    app.press("Remove it");
    await app.until(() => app.text("message-text") !== null, "a message after the removal", 8000);
    seen.message = app.text("message-text");
  }
  return seen;
}
