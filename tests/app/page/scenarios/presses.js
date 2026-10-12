// The operator presses buttons of the show screen, one after the other.

import {controls, rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const step of app.settings.presses) {
    app.press(step.press);
    await app.until(() => app.says(step.until), `on the screen: ${step.until}`, 5000);
    await app.sleep(200);
    seen.push({...state(app), ...controls(app), rows: rows(app), message: app.text("message-text"), buttons: [...app.doc.querySelectorAll("#show button")].map((button) => button.textContent.trim())});
  }
  return seen;
}
