// The app is taken off the screen of the phone and comes back.

import {shown} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  let hidden = true;
  Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
  app.doc.dispatchEvent(new Event("visibilitychange"));
  await app.sleep(400);
  await app.step();
  await app.sleep(3000);
  await app.step();
  hidden = false;
  app.doc.dispatchEvent(new Event("visibilitychange"));
  await app.sleep(400);
  await app.step();
  return {};
}
