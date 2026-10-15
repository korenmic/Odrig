// The operator opens the storage screen, and may remove an animation: presses its
// `Remove`, reads the question, and answers it.

import {shown, storage} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  app.press("Storage");
  await app.until(() => app.shown() === "storage", "the storage screen");
  await app.until(() => app.text("space") !== "-" && storage(app).rows.length === app.settings.rows, `the space and ${app.settings.rows} rows`);
  const seen = {before: storage(app), buttons: [...app.doc.querySelectorAll("nav button")].map((button) => button.textContent.trim())};
  if (app.settings.remove !== undefined) {
    app.pressIn(`#installed > [data-id="${app.settings.remove}"]`, "Remove");
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
