// The two storage lines of the show screen as they follow what the target reports: for
// each pattern of `untils`, after a step of the test from the second one on, the lines
// once both together match it, written as `<internal line> | <external line>`.

import {shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const [at, wanted] of app.settings.untils.entries()) {
    if (at > 0) {
      await app.step();
    }
    const pattern = new RegExp(wanted);
    await app.until(() => pattern.test(`${app.text("show-space")} | ${app.text("show-external-space")}`), `the storage lines: ${wanted}`, app.settings.ms ?? 8000);
    const now = state(app);
    seen.push({internal: now.internalLine, external: now.externalLine});
  }
  return {seen};
}
