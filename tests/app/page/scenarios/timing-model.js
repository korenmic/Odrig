export const withoutTheApp = true;

export default async function(app) {
  const {makeTiming} = await import('/timing.js');
  const {Refusal} = await import('/commands.js');
  const options = app.settings.options ?? {};
  let now = 1800000000000;
  let monotonic = 0;
  let target = 0;
  let board = 'board-a';
  let phoneRevision = '11111111';
  let phoneZone = 'UTC';
  let fault = null;
  let reads = 0;
  const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; };
  const preparation = deferred();
  const sending = deferred();
  const waiting = deferred();
  let tail = options.holdQueue ? waiting.promise : Promise.resolve();
  const sent = [];
  const records = new Map();
  if (options.auto === false) records.set('odrig.time.auto', 'off');
  if (options.confirmed) records.set('odrig.time.confirmed', JSON.stringify(options.confirmed));
  const store = {getItem: key => records.get(key) ?? null,
    setItem: (key, value) => { if (options.storageFails) throw new Error('storage unavailable'); records.set(key, value); }};
  const boards = new Map();
  const hardware = () => {
    if (!boards.has(board)) boards.set(board, {valid: options.valid === true, utc: now / 1000,
      anchor: monotonic, revision: '11111111', zone: 'UTC'});
    return boards.get(board);
  };
  const watchers = new Set();
  const peer = {
    state: {link: 'checking', statusFresh: false, status: null, connectionVersion: 0},
    targetVersion: () => target,
    watch: fn => { watchers.add(fn); fn(peer.state); },
    timingOperation(action, version, current) {
      const guard = () => { if (version !== target || !current()) throw new Refusal('stale', 'timing'); };
      const result = tail.then(async () => {
        guard();
        return action(async carry => { guard(); const reply = await carry(); guard(); return reply; });
      });
      tail = result.catch(() => {});
      return result;
    },
  };
  const notify = () => { for (const fn of watchers) fn(peer.state); };
  const guardBoard = id => { if (id !== null && id !== board) throw new Refusal('stale', 'physical identity'); };
  const wire = {
    async timeRead(id = null) {
      reads += 1;
      if (fault === 'read') { fault = null; throw new Refusal('storage-error', 'time read'); }
      guardBoard(id);
      const value = hardware();
      return {ok: true, valid: value.valid, utc: value.valid ? value.utc + Math.floor((monotonic - value.anchor) / 1000) : null,
        zone: value.zone, offset: 0, revision: value.revision, from: 946684800, until: 4102444800, board, error: null};
    },
    async scheduleRead(id) {
      guardBoard(id);
      return {ok: true, enabled: true, on: '18:00', off: '06:00', override: null, revision: '01234567',
        power: true, active: hardware().valid, reason: hardware().valid ? null : 'time-unset', saved: true, error: null};
    },
    async timeZone(id) {
      guardBoard(id);
      Object.assign(hardware(), {revision: phoneRevision, zone: phoneZone});
      sent.push({kind: 'zone', board});
    },
    async timeSet(id, utc) {
      guardBoard(id);
      if (fault === 'refused') { fault = null; throw new Refusal('storage-error', 'time set'); }
      Object.assign(hardware(), {valid: true, utc: fault === 'unconfirmed' ? utc - 86400 : utc, anchor: monotonic});
      sent.push({kind: 'time', board, utc});
      if (options.holdSet) await sending.promise;
      if (fault === 'lost') { fault = null; throw new Refusal('unconfirmed', 'reply lost'); }
      fault = null;
    },
  };
  const model = makeTiming({peer, wire, now: () => now, store, visible: () => true,
    zone: () => phoneZone, cancelPreparation: () => {},
    prepare: async () => {
      if (options.holdPreparation) await preparation.promise;
      return {zone: phoneZone, revision: phoneRevision, base64: 'A'.repeat(160)};
    }});
  const out = {};
  const capture = () => JSON.parse(JSON.stringify({state: model.state, sent, reads,
    confirmed: JSON.parse(records.get('odrig.time.confirmed') ?? '[]')}));
  for (const operation of app.settings.operations) {
    if (operation.advance !== undefined) { now += operation.advance; monotonic += Math.max(0, operation.advance); }
    if (operation.board) board = operation.board;
    if (operation.zone) { phoneZone = operation.zone; phoneRevision = operation.revision; }
    if (operation.fault) fault = operation.fault;
    if (operation.lostClock) hardware().valid = false;
    if (operation.connect) {
      if (operation.newTarget) target += 1;
      Object.assign(peer.state, {link: 'answers', statusFresh: true, status: {timing: operation.legacy !== true}});
      peer.state.connectionVersion += 1;
      notify();
    }
    if (operation.poll) notify();
    if (operation.auto !== undefined) model.setAuto(operation.auto);
    let manual;
    if (operation.sync) manual = model.syncNow();
    if (operation.releasePreparation) preparation.resolve();
    if (operation.releaseSet) sending.resolve();
    if (operation.releaseQueue) waiting.resolve();
    if (operation.phase) await app.until(() => model.state.phase === operation.phase, operation.phase);
    if (operation.sentCount) await app.until(() => sent.filter(entry => entry.kind === 'time').length >= operation.sentCount, 'time command sent');
    if (operation.pending) out[operation.pending] = capture();
    if (operation.wait !== false) {
      if (manual) await manual;
      await app.until(() => !model.state.busy, 'timing job settled');
    }
    if (operation.look) out[operation.look] = capture();
  }
  return out;
}
