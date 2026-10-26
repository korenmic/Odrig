// The operator presses buttons of Animations, or plays a row, one after the other.

import {badges, controls, playRow, rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const step of app.settings.presses) {
    if (step.row !== undefined) {
      playRow(app, step.row);
    } else {
      app.press(step.press);
    }
    await app.until(() => app.says(step.until), `on the screen: ${step.until}`, 5000);
    await app.sleep(200);
    seen.push({...state(app), ...controls(app), rows: rows(app), badges: badges(app), message: app.text("message-text"), buttons: [...app.doc.querySelectorAll("#animations button")].filter((button) => button.getClientRects().length > 0).map((button) => button.getAttribute("aria-label") || button.textContent.trim())});
  }
  return seen;
}
