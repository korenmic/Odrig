export const withoutTheApp = true;

export default async function(app) {
  let failStatus = false;
  const sent = [];
  let file = {id: 1, file: 'one.odrg', bytes: 100, external: false, ignored: false};
  let board = 'board-a';
  let generation = 1;
  let revision = 11;
  let keyRevision = 101;
  let failPage = false;
  const files = () => app.settings.change === 'partial' ? [file,
    {id: 2, file: 'two.odrg', bytes: 100, external: false, ignored: false}] : [file];
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      if (app.settings.permanent) await app.sleep(20);
      const line = request.line;
      sent.push(line);
      let answer;
      if (line === 'status') {
        if (failStatus) {
          failStatus = false;
          return {status: 500, body: ''};
        }
        answer = {ok: true, on: true, brightness: 40, playing: 'all', animation: file.id,
          file: file.file, fps: 50, error: null};
      } else if (line.startsWith('list')) {
        const from = Number(line.split(' ').at(-1)) || 0;
        if (from > 0 && failPage) { if (!app.settings.permanent) failPage = false; return {status: 500, body: ''}; }
        answer = {ok: true, items: files().slice(from, from + 1), next: from + 1 < files().length ? from + 1 : null};
      } else if (line.startsWith('order')) answer = {ok: true, ids: files().map(item => item.id), revision: 77, next: null};
      else if (line.startsWith('catalog page')) {
        answer = {ok: true, generation, text: line.split(' ')[3] === '0' ?
          files().map(item => `${generation === 1 ? 'aabbccdd' : 'eeeeff00'} ${item.bytes} 60 60 1000 frames ${item.file}\n`).join('') : '', next: null};
      } else if (line === 'catalog') answer = {ok: true,
        internal: {state: 'ok', generation, entries: files().length, uncataloged: 0},
        external: {state: 'absent'}, rebuild: null,
        ...(app.settings.change === 'legacy' ? {} : {inventory: {board, internal: revision, external: 22,
          internal_keys: keyRevision, external_keys: 202, authoritative: true}})};
      else if (line === 'space') answer = {ok: true, free: 1000, total: 2000};
      else answer = {ok: true};
      return {status: 200, body: JSON.stringify(answer)};
    },
  };
  const client = await import('/client.js');
  client.showing('animations');
  client.keptKeysReady();
  client.begin();
  await app.until(() => client.state.animations?.length === files().length && client.state.order !== null &&
    client.state.keys.internal !== null, 'complete initial inventory');
  const arrays = client.state.animations;
  const order = client.state.order;
  const keys = client.state.keys.internal;
  const version = client.state.listVersion;
  const count = prefix => sent.filter(line => line === prefix || line.startsWith(prefix + ' ')).length;
  const before = {list: count('list'), pages: count('catalog page')};
  let lostKeys = false;
  client.watch(state => { if (state.keys.internal === null) lostKeys = true; });
  failStatus = true;
  await app.until(() => client.state.link === 'no-answer', 'one failed status');
  const stale = {listRetained: client.state.animations === arrays,
    marked: client.state.inventoryFresh === false};
  let guard = null;
  if (app.settings.guard) {
    client.play(1);
    await app.sleep(30);
    guard = {sent: count('play'), stillDisconnected: client.state.link === 'no-answer'};
  }
  await app.until(() => client.state.link === 'answers' && client.state.statusFresh, 'reconnected');
  await app.sleep(500);
  const reconnect = {sameList: client.state.animations === arrays, sameOrder: client.state.order === order,
    sameKeys: client.state.keys.internal === keys, lostKeys, version: client.state.listVersion === version,
    lists: count('list') - before.list, pages: count('catalog page') - before.pages};
  if (app.settings.change === 'legacy') {
    return {stale, reconnect, fresh: client.state.inventoryFresh, retained: client.state.animations === arrays};
  }
  if (app.settings.change) {
    const previousTarget = client.targetVersion();
    if (app.settings.change === 'board') {
      board = 'board-b';
      file = {...file, id: 9, file: 'other.odrg'};
    } else {
      file = {...file, bytes: 101};
      generation += 1;
      revision += 1;
      keyRevision += 1;
    }
    failPage = app.settings.change === 'partial';
    let partial = null;
    if (app.settings.change === 'partial') {
      client.watch(state => {
        if (state.link === 'no-answer' && partial === null) {
          partial = {retained: state.animations === arrays, bytes: state.animations[0].bytes};
        }
      });
    }
    const beforeChange = count('list');
    client.refreshContent();
    if (app.settings.change === 'partial') await app.until(() => partial !== null, 'failed later page');
    if (app.settings.permanent) {
      await app.sleep(2100);
      return {partial, lists: count('list') - beforeChange, retained: client.state.animations === arrays};
    }
    await app.until(() => client.state.inventoryFresh && client.state.animations?.[0].file === file.file &&
      client.state.animations?.[0].bytes === file.bytes && client.state.keys.internal !== null &&
      client.state.keys.internal !== keys, 'validated actual change');
    return {partial, newList: client.state.animations !== arrays, newKeys: client.state.keys.internal !== keys,
      bytes: client.state.animations[0].bytes, file: client.state.animations[0].file,
      newTarget: client.targetVersion() !== previousTarget, rows: client.state.animations.length};
  }
  if (app.settings.poll) {
    const listed = count('list');
    await app.sleep(11000);
    return {stale, reconnect, periodic: {lists: count('list') - listed,
      sameList: client.state.animations === arrays, sameKeys: client.state.keys.internal === keys}};
  }
  const listed = count('list');
  client.refreshContent();
  await app.until(() => count('list') > listed, 'explicit list validation');
  await app.sleep(300);
  return {stale, reconnect, ...(guard === null ? {} : {guard}), explicit: {sameList: client.state.animations === arrays,
    sameOrder: client.state.order === order, sameKeys: client.state.keys.internal === keys,
    version: client.state.listVersion === version}};
}
