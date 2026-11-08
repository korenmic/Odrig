import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 1);
  app.press('Upload');
  app.press('Make a text');
  const words = app.byId('text-words');
  words.value = 'Clock';
  words.dispatchEvent(new app.frame.contentWindow.Event('input', {bubbles: true}));
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => app.text('author-says') !== null && client.state.rootNames !== null &&
    app.byId('author-preview').dataset.ms !== undefined, 'text preview and collision names');
  const seen = {disabled: app.byId('author-upload').disabled,
    preview: !app.byId('author-preview').hidden,
    reason: app.doc.getElementById('author-boundary')?.textContent ?? null};
  if (app.settings.release) {
    await app.step();
    await app.until(() => client.state.status?.clockMode === 'off' && !app.byId('author-upload').disabled,
      'normal authoring restored after confirmed Off');
    seen.released = true;
  }
  return seen;
}
