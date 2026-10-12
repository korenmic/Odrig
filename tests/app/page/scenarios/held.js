// The operator holds the slider while somebody else changes the brightness.

import {controls, shown, state} from "../reading.js";

function look(app) {
  return {...controls(app), brightness: state(app).brightness};
}

export default async function (app) {
  await shown(app, app.settings.rows);
  app.slide("level", 200);
  await app.until(() => app.says("Brightness 200"), "the brightness the slider asked for");
  await app.step();
  await app.until(() => app.says("Brightness 10"), "the brightness somebody else set");
  await app.sleep(1300);
  const whileHeld = look(app);
  app.release("level");
  await app.until(() => app.says("Brightness 200"), "the brightness at which the slider was let go");
  const letGo = look(app);
  await app.sleep(1300);
  await app.step();
  await app.until(() => controls(app).slider === 30, "the slider at what somebody else set", 4000);
  return {whileHeld, letGo, later: look(app)};
}
