// The operator presses buttons of Animations, or plays a row, one after the other, each
// time until the screen says what the step names and the line of what plays has the words
// it names.

import {badges, controls, playing, playRow, rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const step of app.settings.presses) {
    if (step.row !== undefined) {
      playRow(app, step.row);
    } else if (step.tap !== undefined) {
      app.tap(step.tap);
    } else if (step.pressIn !== undefined) {
      app.pressIn(step.pressIn, step.press);
    } else {
      app.press(step.press);
    }
    await app.until(() => app.says(step.until), `on the screen: ${step.until}`, 5000);
    if (step.line !== undefined) {
      await app.until(() => new RegExp(step.line).test(playing(app)), `the line of what plays: ${step.line}`, 5000);
    }
    await app.sleep(200);
    seen.push({...state(app), ...controls(app), rows: rows(app), badges: badges(app), message: app.text("message-text"), buttons: [...app.doc.querySelectorAll("#animations button")].filter((button) => button.getClientRects().length > 0).map((button) => button.getAttribute("aria-label") || button.textContent.trim())});
  }
  return seen;
}
