import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 1);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.level.path === 'clocks' && client.state.inventoryFresh &&
    client.state.catalog?.inventory?.authoritative && client.state.keys.external !== null,
    'authoritative native Clocks snapshot', 15000);
  const animations = client.state.animations;
  const keys = client.state.keys.external;
  const version = client.state.listVersion;
  const row = app.doc.querySelector('#animations-list > .row');
  const paths = [];
  client.watch(state => paths.push(state.level.path));
  await app.step();
  await app.until(() => client.state.link === 'no-answer', 'one dropped native status');
  const stale = {retained: client.state.animations === animations,
    disabled: app.byId('play-all').disabled, marked: !client.state.inventoryFresh};
  await app.until(() => client.state.statusFresh && client.state.inventoryFresh &&
    client.state.link === 'answers', 'validated Only reconnect', 10000);
  await app.sleep(350);
  return {stale, paths, sameList: client.state.animations === animations,
    sameKeys: client.state.keys.external === keys, sameVersion: client.state.listVersion === version,
    sameRow: app.doc.querySelector('#animations-list > .row') === row,
    level: client.state.level.path, mode: client.state.status.clockMode};
}
