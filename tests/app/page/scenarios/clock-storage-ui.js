// Settings' panel Clocks with the dropdown of the preferred storage: where it stands, its
// words and its options, a choice and what the panel says of it. The settings give the acts in
// their order: `storage` chooses a value and looks at once as `pending`, `step` the test,
// `wait` some milliseconds, `until` the dropdown is so, `target` another address, `look`.
import {shown} from "../reading.js";

function look(app) {
  const storage = app.byId("clock-storage");
  const label = app.doc.querySelector('label[for="clock-storage"]');
  return {
    value: storage.value,
    disabled: storage.disabled,
    options: [...storage.querySelectorAll("option")].map((option) => ({value: option.value, text: option.textContent})),
    label: label.querySelector(".title").textContent,
    explanation: label.querySelector(".small").textContent,
    support: app.text("clock-storage-support"),
    said: app.raw("clocks-said"),
    description: app.raw("clocks-description"),
    reason: app.raw("clocks-state"),
    modeDisabled: app.byId("clocks").disabled,
    // The ids of the panel's controls in their order on the page.
    order: [...app.byId("clocks-panel").querySelectorAll("select, input")].map((control) => control.id),
  };
}

function matches(seen, until) {
  return Object.entries(until).every(([key, value]) => key === "said" ? seen.said.includes(value) : seen[key] === value);
}

export default async function (app) {
  await shown(app, app.settings.rows ?? 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings" && !app.byId("clocks").disabled, "Settings with the clocks' controls");
  const seen = {first: look(app)};
  for (const act of app.settings.acts ?? []) {
    if (act.storage !== undefined) {
      const select = app.byId("clock-storage");
      select.value = act.storage;
      select.dispatchEvent(new app.frame.contentWindow.Event("change", {bubbles: true}));
      seen.pending = look(app);
    }
    if (act.step) await app.step();
    if (act.wait !== undefined) await app.sleep(act.wait);
    if (act.target !== undefined) {
      app.press("Target");
      app.fill("address", act.target);
      app.press("Connect over Wi-Fi");
      app.press("Settings");
    }
    if (act.until !== undefined) await app.until(() => matches(look(app), act.until), JSON.stringify(act.until), 15000);
    if (act.look !== undefined) seen[act.look] = look(app);
  }
  return seen;
}
