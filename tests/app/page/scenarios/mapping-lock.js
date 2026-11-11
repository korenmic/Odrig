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

const LOCK_KEY = 'odrig.mappingLock';

// Settings opened, and the mapping editor's module of the page as it is loaded now.
async function settings(app) {
  await app.until(() => app.shown() !== '', 'a screen');
  app.press('Settings');
  await app.until(() => app.shown() === 'settings', 'Settings');
  return app.frame.contentWindow.eval('import("/screens/mapping.js")');
}

// Moves snake 1's pin one place down with the arrow key, and waits until the target has
// the new assignment.
async function edit(app, mapping, after) {
  await app.until(() => mapping.canEdit() && mapping.mapping() !== null, `edits after ${after}`);
  const before = mapping.mapping().pins[0];
  app.doc.querySelector('#mapping-pins .handle').dispatchEvent(new app.frame.contentWindow.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
  await app.until(() => !mapping.saving() && mapping.mapping().pins[0] !== before && mapping.canEdit(), `a save after ${after}`);
  return true;
}

async function kept(app) {
  await shown(app, 2);
  let mapping = await settings(app);
  await app.until(() => app.doc.querySelectorAll('#mapping-pins > .map-pin').length === 20, 'mapping ready');
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const seen = {};
  await unlockMapping(app);
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: true});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: false});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  seen.afterHide = !locked(app) && await edit(app, mapping, 'the page was hidden');
  app.press('Animations');
  await app.until(() => app.shown() === 'animations', 'leave Settings');
  app.press('Settings');
  await app.until(() => app.shown() === 'settings', 'back in Settings');
  seen.afterLeave = !locked(app) && await edit(app, mapping, 'Settings was left');
  client.begin();
  seen.afterBegin = !locked(app) && await edit(app, mapping, 'a new start of the link');
  await app.reload();
  mapping = await settings(app);
  seen.afterReload = !locked(app) && await edit(app, mapping, 'a reload');
  await ask(app);
  app.byId('mapping-lock-yes').click();
  seen.locked = locked(app) && !mapping.canEdit();
  await app.reload();
  mapping = await settings(app);
  await app.until(() => mapping.mapping() !== null, 'the mapping read after the reload');
  seen.lockKept = locked(app) && !mapping.canEdit();
  return seen;
}

async function noBoard(app) {
  await settings(app);
  const seen = {};
  seen.enabled = await app.until(() => !app.byId('mapping-lock').disabled, 'the lock without a board', 4000).then(() => true, () => false);
  if (!seen.enabled) return seen;
  await ask(app);
  app.byId('mapping-lock-no').click();
  seen.cancelKeepsLocked = locked(app);
  await ask(app);
  app.byId('mapping-lock-yes').click();
  seen.unlocked = !locked(app);
  seen.waits = app.raw('mapping-lock-state') === 'Mapping edits are unlocked. Edits wait until the installation answers.';
  seen.stored = app.frame.contentWindow.localStorage.getItem(LOCK_KEY) === 'unlocked';
  return seen;
}

async function refused(app) {
  await shown(app, 2);
  await settings(app);
  const view = app.frame.contentWindow;
  const original = view.Storage.prototype.setItem;
  view.Storage.prototype.setItem = function (key, value) {
    if (key === LOCK_KEY) throw new view.DOMException('the store is full', 'QuotaExceededError');
    return original.call(this, key, value);
  };
  await unlockMapping(app);
  const seen = {unlocked: !locked(app)};
  seen.said = app.raw('mapping-lock-state').endsWith('This choice could not be kept on this phone; it holds until the app is closed.');
  await app.reload();
  const mapping = await settings(app);
  await app.until(() => mapping.mapping() !== null, 'the mapping read after the reload');
  seen.lockedAfterReload = locked(app);
  return seen;
}

async function unknown(app) {
  await shown(app, 2);
  app.frame.contentWindow.localStorage.setItem(LOCK_KEY, 'maybe');
  await app.reload();
  const mapping = await settings(app);
  await app.until(() => mapping.mapping() !== null && !app.byId('mapping-lock').disabled, 'the mapping read after the reload');
  return {locked: locked(app), canEdit: mapping.canEdit()};
}

export default async function(app) {
  if (app.settings.mode === 'kept') return kept(app);
  if (app.settings.mode === 'noboard') return noBoard(app);
  if (app.settings.mode === 'refused') return refused(app);
  if (app.settings.mode === 'unknown') return unknown(app);
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
  await app.until(() => app.shown() === 'settings', 'return to Settings');
  seen.exitKept = !locked(app);
  await unlockMapping(app);
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: true});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  seen.hiddenKept = !locked(app);
  Object.defineProperty(app.doc, 'hidden', {configurable: true, value: false});
  app.doc.dispatchEvent(new app.frame.contentWindow.Event('visibilitychange'));
  return seen;
}
