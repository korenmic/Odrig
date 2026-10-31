import {shown} from "../reading.js";
import {measure} from "./look.js";

function look(app) {
  return {
    screen: app.shown(), level: app.raw("level-title"),
    mode: app.byId("clocks").value, message: app.byId("clock-message").checked,
    disabled: app.byId("clocks").disabled, said: app.raw("clocks-said"),
    reason: app.raw("clocks-state"), support: app.raw("clocks-support"),
    notice: app.text("message-text"),
    onlyDisabled: app.byId("clocks").querySelector('option[value="only"]').disabled,
    global: {text: app.raw("play-all"), disabled: app.byId("play-all").disabled},
    rows: [...app.doc.querySelectorAll('#animations-list > .row')].map((row) => ({
      id: Number(row.dataset.id), file: row.dataset.file,
      disabled: row.querySelector('.play').disabled, note: row.querySelector('.row-state').textContent,
      ignored: row.classList.contains('ignored'),
    })),
    folders: [...app.doc.querySelectorAll('#animations-list > .folder-row')].map((row) => ({
      id: Number(row.dataset.id), path: row.dataset.path, ignored: row.classList.contains('ignored'),
      note: row.querySelector('.row-state')?.textContent ?? '',
    })),
    menu: [...app.byId('row-menu').querySelectorAll('button')].map((button) => ({text: button.textContent, disabled: button.disabled})),
    menuNotes: [...app.byId('row-menu').querySelectorAll('p')].map((element) => element.textContent),
  };
}

async function settled(app, until) {
  await app.until(() => {
    const now = look(app);
    return Object.entries(until).every(([key, value]) => key === 'ignored' || key === 'included' ?
      [...now.rows, ...now.folders].some((row) => row.id === value && row.ignored === (key === 'ignored') && !row.note.includes('Saving')) :
      key === 'rows' ? now.rows.length === value :
      key === 'said' ? now.said.includes(value) : now[key] === value);
  }, JSON.stringify(until), 15000);
}

export default async function(app) {
  await shown(app, app.settings.rows ?? 2);
  await app.until(() => !app.byId('clocks').disabled, 'confirmed clock status');
  const seen = {first: look(app)};
  for (const act of app.settings.acts ?? []) {
    if (act.screen) app.press(act.screen);
    if (act.mode !== undefined) {
      app.byId('clocks').value = act.mode;
      app.byId('clocks').dispatchEvent(new Event('change', {bubbles: true}));
    }
    if (act.message) app.byId('clock-message').click();
    if (act.pending) seen[act.pending] = look(app);
    if (act.step) await app.step();
    if (act.wait) await app.sleep(act.wait);
    if (act.back) app.byId('level-back').click();
    if (act.enter) app.doc.querySelector(`.folder-row[data-path="${act.enter}"]`).click();
    if (act.menu !== undefined) app.doc.querySelector(`.row[data-id="${act.menu}"] .more`).click();
    if (act.folderMenu) {
      const button = app.doc.querySelector(`.folder-row[data-path="${act.folderMenu}"] .more`);
      if (button === null) throw new Error('folder has no inclusion menu');
      button.click();
    }
    if (act.choose) app.pressIn('#row-menu', act.choose);
    if (act.restart) app.byId('play-all').click();
    if (act.play !== undefined) app.doc.querySelector(`.row[data-id="${act.play}"] .play`).click();
    if (act.escape) app.doc.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    if (act.target) {
      app.press('Target');
      app.fill('address', act.target);
      app.press('Use');
    }
    if (act.reload) await app.reload();
    if (act.until) await settled(app, act.until);
    if (act.look) seen[act.look] = look(app);
    if (act.measure) seen[act.measure] = measure(app);
  }
  return seen;
}
