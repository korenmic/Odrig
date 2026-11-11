export const withoutTheApp = true;

export default async function(app) {
  const sent = [];
  let active = 0;
  let maximum = 0;
  let release;
  const gate = new Promise(done => { release = done; });
  let held = false;
  let failTime = false;
  let failStatus = false;
  const kind = app.settings.kind;
  const status = {ok: true, on: true, brightness: 128, playing: 'all', animation: 1, fps: 50, error: null, timing: true};
  const clock = {ok: true, valid: false, utc: null, zone: 'UTC', offset: 0, revision: '11111111',
    from: 946684800, until: 4102444800, board: 'board-a', error: null};
  window.Capacitor = {isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      sent.push({address: request.address, line: request.line});
      active += 1;
      maximum = Math.max(active, maximum);
      try {
        if (!held && ((kind === 'queued' && request.line === 'status') ||
            (kind === 'reply' && request.line.includes('time zone')) ||
            (kind === 'cancel' && request.line === 'time'))) {
          held = true;
          await gate;
        }
        if (request.line === 'status' && failStatus) { failStatus = false; throw new Error('status connection lost'); }
        if (request.line === 'time' && failTime) { failTime = false; throw new Error('time reply lost'); }
        const result = request.line === 'status' ? status : request.line === 'time' ? clock :
          request.line === 'list' ? {ok: true, items: [], next: null} :
          request.line.startsWith('guard ') ? {ok: true} : {ok: false, error: 'unknown-command'};
        return {status: 200, body: JSON.stringify(result)};
      } finally { active -= 1; }
    }};
  const target = await import('/target.js');
  const client = await import('/client.js');
  const wire = await import('/commands.js');
  target.setAddress('127.0.0.1:11111');
  client.begin();
  const settled = promise => promise.then(() => 'ok', error => error.code || error.kind || error.message);
  const write = current => client.timingOperation(async send => {
    await send(() => wire.timeZone('board-a', app.settings.zone));
    await send(() => wire.timeSet('board-a', 1800000000, '11111111'));
  }, client.targetVersion(), current);
  if (kind === 'queued') {
    await app.until(() => held, 'status held');
    const job = settled(write());
    target.setAddress('127.0.0.1:11112');
    client.begin();
    release();
    const result = await job;
    await app.until(() => client.state.statusFresh, 'new target status');
    return {result, maximum, mutations: sent.filter(row => row.line.startsWith('guard '))};
  }
  await app.until(() => client.state.statusFresh, 'fresh status');
  const initial = client.state.connectionVersion;
  if (kind === 'reply') {
    const job = settled(write());
    await app.until(() => held, 'zone request held');
    target.setAddress('127.0.0.1:11112');
    client.begin();
    release();
    const result = await job;
    await app.until(() => client.state.statusFresh, 'new target status');
    return {result, maximum, mutations: sent.filter(row => row.line.startsWith('guard '))};
  }
  if (kind === 'cancel') {
    const read = settled(client.timingOperation(send => send(() => wire.timeRead()), client.targetVersion()));
    await app.until(() => held, 'read held');
    let enabled = true;
    const job = settled(write(() => enabled));
    enabled = false;
    release();
    await read;
    const result = await job;
    return {result, maximum, connected: client.state.link, mutations: sent.filter(row => row.line.startsWith('guard '))};
  }
  failTime = true;
  const result = await settled(client.timingOperation(send => send(() => wire.timeRead()), client.targetVersion()));
  await app.until(() => client.state.statusFresh, 'status after time failure');
  await app.sleep(1200);
  const afterTimeFailure = client.state.connectionVersion;
  failStatus = true;
  await app.until(() => !client.state.statusFresh, 'genuine status failure');
  await app.until(() => client.state.statusFresh, 'genuine reconnection');
  return {result, maximum, initial, afterTimeFailure, reconnected: client.state.connectionVersion,
    timeRequests: sent.filter(row => row.line === 'time').length};
}
