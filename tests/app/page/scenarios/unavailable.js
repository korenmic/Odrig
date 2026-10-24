// The show screen's rows when some animations are unavailable: whether each is marked as
// such, whether its Play can be pressed, its words and how it is drawn.

import {shown} from "../reading.js";

export default async function (app) {
  await shown(app, app.settings.rows);
  await app.until(() => app.doc.querySelectorAll("#animations > .unavailable").length === app.settings.unavailable, `${app.settings.unavailable} unavailable rows`, 8000);
  return [...app.doc.querySelectorAll("#animations > *")].map((row) => ({
    id: Number(row.dataset.id),
    unavailable: row.classList.contains("unavailable"),
    disabled: row.querySelector("button").disabled,
    text: row.innerText.replace(/\s+/g, " ").trim(),
    opacity: Number(app.doc.defaultView.getComputedStyle(row).opacity),
  }));
}
