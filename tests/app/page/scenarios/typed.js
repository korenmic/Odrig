// The operator types a brightness into the field beside the slider, enters it with Enter
// or Done, leaves the field, moves the slider, and takes the app off the screen, as the
// acts of the test say; the field, the slider, the fact and the line under the slider are
// looked at where the test asks.

import {controls, shown, state} from "../reading.js";

function look(app) {
  const field = app.byId("level-number");
  return {
    ...controls(app),
    brightness: state(app).brightness,
    range: app.text("level-range"),
    focused: app.doc.activeElement === field,
  };
}

export default async function (app) {
  await shown(app, app.settings.rows);
  const field = app.byId("level-number");
  let hidden = false;
  Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
  const looks = {};
  for (const act of app.settings.acts) {
    if (act.focus) {
      field.focus();
    }
    if (act.type !== undefined) {
      field.focus();
      app.fill("level-number", act.type);
    }
    if (act.enter) {
      field.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    }
    if (act.leave) {
      // Leaving a field the operator typed into: its change, then the focus goes.
      field.dispatchEvent(new Event("change", {bubbles: true}));
      field.blur();
    }
    if (act.slide !== undefined) {
      app.slide("level", act.slide);
    }
    if (act.release) {
      app.release("level");
    }
    if (act.hide !== undefined) {
      hidden = act.hide;
      app.doc.dispatchEvent(new Event("visibilitychange"));
    }
    if (act.step) {
      await app.step();
    }
    if (act.until !== undefined) {
      await app.until(() => app.says(act.until), act.until);
    }
    if (act.wait !== undefined) {
      await app.sleep(act.wait);
    }
    if (act.look !== undefined) {
      looks[act.look] = look(app);
    }
  }
  return looks;
}
