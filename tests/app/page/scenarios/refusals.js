// The operator presses buttons that the target refuses, and reads the messages.

import {playRow, rows, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const step of app.settings.presses) {
    if (step.step === true) {
      await app.step();
    }
    if (step.dismiss === true) {
      app.press("OK");
      seen.push({message: app.text("message-text")});
      continue;
    }
    if (step.row !== undefined) {
      playRow(app, step.row);
    } else {
      app.press(step.press);
    }
    await app.until(() => app.text("message-text") !== null && app.text("message-text") !== step.not, "a message", 7000);
    await app.sleep(step.wait === undefined ? 300 : step.wait);
    seen.push({message: app.text("message-text"), ...state(app), rows: rows(app), shown: app.shown()});
  }
  return seen;
}
