export const withoutTheApp = true;

export default async function(app) {
  const sent = [];
  let missing = app.settings.case === 'initial';
  let remapped = false;
  let mode = 'only';
  let hold = null;
  let release = null;
  let held = false;
  const rootId = () => remapped ? 60017 : 60007;
  const childId = () => remapped ? 60018 : 60008;
  const rows = folder => folder === null ? (missing ? [] : [
    {id: rootId(), playlist: 'clocks', files: 1, external: true}]) :
    folder === rootId() && !missing ? [
      {id: 60003, file: 'clocks/c.odrg', bytes: 100, external: true},
      {id: childId(), playlist: 'clocks/message', files: 1, external: true}] :
    folder === childId() && !missing ? [
      {id: 60006, file: 'clocks/message/m.odrg', bytes: 100, external: true}] : null;
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      const line = request.line;
      sent.push(line);
      if (hold !== null && line.startsWith('list in')) {
        const waiting = hold;
        hold = null;
        held = true;
        await waiting;
      }
      let answer;
      if (line === 'status') answer = {ok: true, on: true, brightness: 40,
        playing: missing ? null : rootId(), animation: null, fps: 50, error: null,
        ...(mode === 'unknown' ? {} : {clocks: mode !== 'off', clock_mode: mode,
          clock_only: mode === 'only' ? {folder: app.settings.case === 'initial' ? null : rootId(),
            state: missing ? 'no-clocks' : 'playing'} : null})};
      else if (line.startsWith('list')) {
        const match = /^list in (\d+)/.exec(line);
        const items = rows(match === null ? null : Number(match[1]));
        answer = items === null ? {ok: false, error: 'unknown-id'} : {ok: true, items, next: null};
      } else if (line === 'catalog') answer = {ok: true, internal: {state: 'none', uncataloged: 0},
        external: {state: missing ? 'absent' : 'none'}, rebuild: null};
      else if (line === 'space') answer = {ok: true, free: 1000, total: 2000};
      else answer = {ok: false, error: 'unknown-command'};
      return {status: 200, body: JSON.stringify(answer)};
    },
  };
  const client = await import('/client.js');
  client.showing('animations');
  client.keptKeysReady();
  client.begin();
  await app.until(() => client.state.status?.clockMode === 'only', 'confirmed Only');
  const paths = [];
  client.watch(state => paths.push(state.level.path));
  if (app.settings.case === 'initial') {
    await app.sleep(1200);
    return {paths, level: client.state.level, fresh: (client.state.animations !== null && !client.state.onlyUnavailable),
      rootRequests: sent.filter(line => line === 'list' || line.startsWith('list ' ) && !line.startsWith('list in')).length};
  }
  await app.until(() => client.state.level.path === 'clocks' && (client.state.animations !== null && !client.state.onlyUnavailable), 'initial Clocks list');
  if (app.settings.case === 'target') {
    hold = new Promise(resolve => { release = resolve; });
    client.refreshContent();
    await app.until(() => held, 'old folder request held');
    mode = 'off';
    client.begin();
    paths.length = 0;
    release();
    await app.until(() => client.state.status?.clockMode === 'off' && (client.state.animations !== null && !client.state.onlyUnavailable), 'new target confirmed');
    return {paths, level: client.state.level, mode: client.state.status.clockMode};
  }
  if (['child', 'remap'].includes(app.settings.case)) {
    client.enter({playlist: 'clocks/message', id: childId()});
    await app.until(() => client.state.level.path === 'clocks/message' && (client.state.animations !== null && !client.state.onlyUnavailable), 'child list');
    paths.length = 0;
    if (app.settings.case === 'child') {
      const count = client.state.statusCount;
      await app.until(() => client.state.statusCount >= count + 2, 'repeated Only');
      return {paths, level: client.state.level};
    }
    remapped = true;
    client.refreshContent();
    await app.until(() => client.state.level.id === childId() && (client.state.animations !== null && !client.state.onlyUnavailable), 'remapped descendant');
    return {paths, level: client.state.level};
  }
  missing = true;
  client.refreshContent();
  await app.sleep(1800);
  const absent = {paths: [...paths], level: client.state.level,
    unavailable: client.state.onlyUnavailable, fresh: (client.state.animations !== null && !client.state.onlyUnavailable)};
  if (app.settings.restart) {
    const played = sent.filter(line => line.startsWith('play ')).length;
    client.playAll();
    await app.sleep(50);
    return {sent: sent.filter(line => line.startsWith('play ')).length - played};
  }
  if (app.settings.case === 'unknown') {
    mode = 'unknown';
    const count = client.state.statusCount;
    await app.until(() => client.state.statusCount > count && client.state.status.clockMode === null, 'unknown policy');
    return {...absent, afterUnknown: client.state.level};
  }
  if (!app.settings.restore) return absent;
  missing = false;
  remapped = true;
  client.refreshContent();
  await app.until(() => client.state.level.path === 'clocks' && client.state.level.id === rootId() &&
    (client.state.animations !== null && !client.state.onlyUnavailable), 'Clocks returns');
  return {...absent, restored: client.state.level};
}
