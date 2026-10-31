// Settings' panel Clocks: what its boxes show, a tap on each, what the panel says, and the
// panel's look. The settings give the acts in their order: `tap` a box and look at once,
// `step` the test, `wait` some milliseconds, `untilSaid` the line of the panel says something
// new, `until` the boxes are so, `look` and `measure`.
import {shown} from "../reading.js";
import {measure} from "./look.js";

const BOXES = ["clocks", "clock-message"];

function look(app) {
  const label = (id) => app.doc.querySelector(`label[for="${id}"]`);
  return {
    hidden: app.byId("clocks-panel").getClientRects().length === 0,
    kind: app.byId("clocks").tagName,
    mode: app.byId("clocks").value,
    options: [...app.byId("clocks").querySelectorAll("option")].map((option) => ({value: option.value, text: option.textContent, disabled: option.disabled})),
    title: app.doc.querySelector("#clocks-panel h2").textContent,
    after: app.byId("clocks-panel").previousElementSibling.querySelector("input").id,
    labels: BOXES.map((id) => label(id).querySelector(".title").textContent),
    smalls: BOXES.map((id) => label(id).querySelector(".small").textContent),
    checked: BOXES.map((id) => id === "clocks" && app.byId(id).tagName === "SELECT" ? app.byId(id).value !== "off" : app.byId(id).checked),
    disabled: BOXES.map((id) => app.byId(id).disabled),
    said: app.text("clocks-said"),
    role: app.byId("clocks-said").getAttribute("role"),
  };
}

export default async function (app) {
  await shown(app, app.settings.rows);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  // The first status has come with Animations; one more makes sure the panel drew from it.
  await app.sleep(1200);
  const seen = {first: look(app)};
  for (const act of app.settings.acts) {
    if (act.tap !== undefined) {
      // A tap clears the line of the panel at once, and its answer says something.
      if (act.tap === "clocks" && app.byId(act.tap).tagName === "SELECT") {
        const field = app.byId(act.tap);
        field.value = field.value === "off" ? "between" : "off";
        field.dispatchEvent(new Event("change", {bubbles: true}));
      } else app.byId(act.tap).click();
      seen[act.look] = look(app);
      await app.until(() => app.text("clocks-said") !== null && BOXES.every((id) => !app.byId(id).disabled), `the tap on ${act.tap} answered`, 15000);
      seen[act.answered] = look(app);
    }
    if (act.step) await app.step();
    if (act.wait !== undefined) await app.sleep(act.wait);
    if (act.until !== undefined) {
      await app.until(() => JSON.stringify(look(app).checked) === JSON.stringify(act.until.checked) &&
        (act.until.disabled === undefined || JSON.stringify(look(app).disabled) === JSON.stringify(act.until.disabled)), `the boxes ${JSON.stringify(act.until)}`, 8000);
    }
    if (act.look !== undefined && act.tap === undefined) seen[act.look] = look(app);
    if (act.measure !== undefined) seen[act.measure] = measure(app);
  }
  return seen;
}
