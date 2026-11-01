import {shown} from '../reading.js';
import {unlockMapping} from '../mapping-lock.js';
import {photoCanvas} from './photo-analysis.js';

const locked = app => app.byId('mapping-lock').getAttribute('aria-pressed') === 'true';
const ask = async app => {
  await app.until(() => !app.byId('mapping-lock').disabled, 'lock toggle ready');
  app.byId('mapping-lock').click();
  await app.until(() => app.byId('mapping-lock-dialog').open, 'lock confirmation');
};

async function givePhoto(app, pins) {
  const canvas = photoCanvas(app, {pins});
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  const view = app.frame.contentWindow;
  const transfer = new view.DataTransfer();
  transfer.items.add(new view.File([blob], 'wall.png', {type: blob.type}));
  app.byId('photo').files = transfer.files;
  app.byId('photo').dispatchEvent(new view.Event('change', {bubbles: true}));
  await app.until(() => !app.byId('photo-result').hidden && app.doc.querySelectorAll('#photo-words li').length > 0, 'locked photo analysis', 15000);
}

export default async function(app) {
  await shown(app, 2);
  app.press('Settings');
  await app.until(() => app.doc.querySelectorAll('#mapping-pins > .map-pin').length === 20 && !app.byId('mapping-lock').disabled, 'mapping ready');
  const mapping = await app.frame.contentWindow.eval('import("/screens/mapping.js")');
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const seen = {};
  if (app.settings.mode === 'disconnect') {
    await unlockMapping(app);
    let lost = false;
    client.watch(state => { if (state.link === 'no-answer') lost = true; });
    await app.step();
    await app.until(() => lost && client.state.link === 'answers', 'reconnected target');
    return {locked: locked(app), canEdit: mapping.canEdit()};
  }
  if (app.settings.mode === 'queued') {
    await unlockMapping(app);
    await app.step();
    await app.step();
    const before = client.state.statusCount;
    app.doc.querySelector('#mapping-pins .handle').dispatchEvent(new app.frame.contentWindow.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
    await app.until(() => mapping.saving(), 'mapping queued behind status');
    app.press('Animations');
    await app.step();
    await app.until(() => !mapping.saving() && client.state.statusCount > before, 'cancelled queued edit');
    await app.sleep(200);
    return {locked: locked(app), link: client.state.link};
  }
  if (app.settings.mode === 'photo') {
    await givePhoto(app, [...mapping.mapping().pins]);
    seen.analysisVisible = !app.byId('photo-result').hidden;
    seen.applyDisabled = app.byId('photo-apply').disabled;
    app.byId('photo-apply').dispatchEvent(new app.frame.contentWindow.MouseEvent('click', {bubbles: true}));
    await app.step();
    await unlockMapping(app);
    await app.until(() => !app.byId('photo-apply').disabled, 'unlocked photo apply');
    app.byId('photo-apply').click();
    await app.until(() => app.says('Saved from the photo') && mapping.canEdit(), 'photo saved');
    await ask(app);
    app.byId('mapping-lock-yes').click();
    seen.otherDisabled = app.byId('photo-other').disabled;
    app.byId('photo-other').dispatchEvent(new app.frame.contentWindow.MouseEvent('click', {bubbles: true}));
    await app.sleep(150);
    return {...seen, locked: locked(app)};
  }
  if (app.settings.mode === 'target') {
    await ask(app);
    app.press('Target');
    app.fill('address', app.settings.other);
    app.press('Use');
    await app.until(() => app.shown() === 'animations', 'other target');
    app.byId('mapping-lock-yes').click();
    app.press('Settings');
    await app.until(() => mapping.mapping()?.pins[0] === app.settings.first, 'other mapping');
    return {locked: locked(app), promptClosed: !app.byId('mapping-lock-dialog').open,
      handlesDisabled: [...app.doc.querySelectorAll('#mapping-pins .handle')].every(handle => handle.disabled)};
  }
  await ask(app);
  seen.question = app.text('mapping-lock-question');
  const box = app.byId('mapping-lock-dialog').getBoundingClientRect();
  seen.dialogFits = box.left >= 0 && box.right <= app.doc.documentElement.clientWidth;
  seen.cancelFocused = app.doc.activeElement === app.byId('mapping-lock-no');
  app.byId('mapping-lock-no').click();
  seen.cancelKeepsLocked = locked(app);
  await ask(app);
  app.doc.dispatchEvent(new app.frame.contentWindow.KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));
  seen.escapeKeepsLocked = locked(app) && !app.byId('mapping-lock-dialog').open;
  await unlockMapping(app);
  const handle = app.doc.querySelector('#mapping-pins .handle');
  handle.dispatchEvent(new app.frame.contentWindow.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
  await app.until(() => app.says('Saved: GPIO 1 drives snake 2') && mapping.canEdit(), 'unlocked key saved');
  seen.unlockedSave = true;
  await ask(app);
  app.byId('mapping-lock-no').click();
  seen.cancelKeepsUnlocked = !locked(app);
  await ask(app);
  app.byId('mapping-lock-yes').click();
  seen.relocked = locked(app) && !mapping.canEdit();
  await unlockMapping(app);
  app.press('Animations');
  await app.until(() => app.shown() === 'animations', 'leave Settings');
  app.press('Settings');
  await app.until(() => app.shown() === 'settings', 'return to locked Settings');
  seen.exitRelocked = locked(app);
  await unlockMapping(app);
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: true});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  seen.hiddenRelocked = locked(app);
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: false});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  return seen;
}
