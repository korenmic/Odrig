import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 1);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.level.path === 'clocks' && client.state.statusFresh &&
    client.state.animations?.length === 1 && client.state.catalog?.external.state === 'ok' &&
    client.state.keys.external !== null, 'native Clocks list with its keys', 15000);
  const animations = client.state.animations;
  const files = animations.map(row => row.file);
  const keyed = keys => JSON.stringify([keys?.generation, keys?.entries, [...(keys?.byName ?? [])]]);
  const keys = keyed(client.state.keys.external);
  const version = client.state.listVersion;
  const row = app.doc.querySelector('#animations-list > .row');
  const paths = [];
  client.watch(state => paths.push(state.level.path));
  await app.step();
  await app.until(() => client.state.link === 'no-answer', 'one dropped native status');
  const stale = {retained: client.state.animations === animations,
    disabled: app.byId('play-all').disabled, marked: app.byId('animations-list').classList.contains('stale')};
  await app.until(() => client.state.statusFresh && client.state.link === 'answers' &&
    client.state.listVersion > version && client.state.keys.external !== null, 'validated Only reconnect', 10000);
  await app.sleep(350);
  return {stale, paths, sameFiles: JSON.stringify(client.state.animations.map(one => one.file)) === JSON.stringify(files),
    sameKeys: keyed(client.state.keys.external) === keys,
    sameRow: app.doc.querySelector('#animations-list > .row') === row,
    level: client.state.level.path, mode: client.state.status.clockMode};
}
