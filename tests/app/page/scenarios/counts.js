// The two storage lines of the show screen as they follow what the target reports: for
// each entry of `untils`, after a step of the test from the second one on, the lines
// once both together match its pattern, written as `<internal line> | <external line>`,
// and whether they are dimmed. An entry is the pattern, or `{lines, dimmed}` with the
// pattern and whether the screen must be dimmed, as it is while the target does not
// answer.

import {shown, state} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = [];
  for (const [at, wanted] of app.settings.untils.entries()) {
    if (at > 0) {
      await app.step();
    }
    const asked = typeof wanted === "string" ? {lines: wanted} : wanted;
    const pattern = new RegExp(asked.lines);
    const fits = () => pattern.test(`${app.text("show-space")} | ${app.text("show-external-space")}`) && (asked.dimmed === undefined || state(app).dimmed === asked.dimmed);
    await app.until(fits, `the storage lines: ${asked.lines}${asked.dimmed === undefined ? "" : asked.dimmed ? ", dimmed" : ", not dimmed"}`, app.settings.ms ?? 8000);
    const now = state(app);
    seen.push({internal: now.internalLine, external: now.externalLine, dimmed: now.dimmed});
  }
  return {seen};
}
