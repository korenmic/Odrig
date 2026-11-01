import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 1);
  if (app.settings.reload) {
    await app.reload();
    await shown(app, 1);
  }
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.inventoryFresh && client.state.level.path === 'clocks', 'confirmed Clocks boundary');
  const backHidden = app.byId('level-back').hidden;
  const paths = [];
  client.watch(state => paths.push(state.level.path));
  app.byId('level-back').click();
  return {backHidden, level: client.state.level.path, paths, note: app.text('only-boundary')};
}
