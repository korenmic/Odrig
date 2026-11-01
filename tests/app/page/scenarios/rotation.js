import {shown} from '../reading.js';

function look(app) {
  const field = app.doc.getElementById('output-rotation');
  return {present: field !== null, value: field?.value, disabled: field?.disabled,
    said: app.doc.getElementById('rotation-state')?.textContent,
    options: field ? [...field.options].map(option => option.value) : []};
}

export default async function(app) {
  await shown(app, app.settings.rows ?? 2);
  app.press('Settings');
  if (!app.doc.getElementById('output-rotation')) return {first: look(app)};
  await app.until(() => !look(app).said.startsWith('Reading'), 'initial rotation read');
  const seen = {first: look(app)};
  for (const act of app.settings.acts ?? []) {
    if (act.choose !== undefined) {
      const field = app.byId('output-rotation');
      field.value = String(act.choose);
      field.dispatchEvent(new app.frame.contentWindow.Event('change', {bubbles: true}));
    }
    if (act.refresh) app.byId('rotation-refresh').click();
    if (act.step) await app.step();
    if (act.wait) await app.sleep(act.wait);
    if (act.screen) app.press(act.screen);
    if (act.reload) { await app.reload(); await shown(app, app.settings.rows ?? 2); app.press('Settings'); }
    if (act.target) {
      app.press('Target'); app.fill('address', act.target); app.press('Use');
      seen.changed = look(app);
      await shown(app, 2); app.press('Settings');
    }
    if (act.until) await app.until(() => {
      const current = look(app);
      return Object.entries(act.until).every(([key, value]) => key === 'text' ?
        current.said.includes(value) : current[key] === value);
    }, JSON.stringify(act.until), 15000);
    if (act.look) seen[act.look] = look(app);
  }
  return seen;
}
