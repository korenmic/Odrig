import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 2);
  app.press('Settings');
  await app.until(() => app.doc.querySelectorAll('#mapping-pins > .map-pin').length === 20, 'mapping rows');
  const commands = await app.frame.contentWindow.eval('import("/commands.js")');
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  return {checkbox: app.doc.getElementById('mapping-cross') !== null, api: typeof commands.mappingCross === 'function',
    clientApi: typeof client.mappingCross === 'function'};
}
