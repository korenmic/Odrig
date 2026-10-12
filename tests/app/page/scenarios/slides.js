// The operator moves the brightness slider through values and lets it go.

import {controls, shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  for (const value of app.settings.values) {
    app.slide("level", value);
    await app.sleep(app.settings.every);
  }
  app.release("level");
  const soon = [];
  for (const ms of app.settings.looks) {
    await app.sleep(ms);
    soon.push({...controls(app), brightness: state(app).brightness});
  }
  return soon;
}
