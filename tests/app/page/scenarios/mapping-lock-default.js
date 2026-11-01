import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 2);
  app.press('Settings');
  await app.until(() => app.doc.querySelectorAll('#mapping-pins > .map-pin').length === 20, 'mapping rows');
  const mapping = await app.frame.contentWindow.eval('import("/screens/mapping.js")');
  const handles = [...app.doc.querySelectorAll('#mapping-pins .handle')];
  const seen = {handlesDisabled: handles.every(handle => handle.disabled),
    defaultsDisabled: app.byId('mapping-defaults').disabled};
  seen.photoAccepted = mapping.saveFromPhoto([...mapping.mapping().pins].reverse());
  if (seen.photoAccepted) await app.until(() => app.says('Saved from the photo'), 'unprotected photo write');
  const handle = handles[0];
  handle.dispatchEvent(new app.frame.contentWindow.KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
  handle.dispatchEvent(new app.frame.contentWindow.PointerEvent('pointerdown',
    {pointerId: 8, pointerType: 'touch', isPrimary: true, button: 0, bubbles: true}));
  app.byId('mapping-defaults').click();
  await app.sleep(150);
  seen.lifted = app.doc.querySelector('#mapping-pins > .lifted') !== null;
  return seen;
}
