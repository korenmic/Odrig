export const withoutTheApp = true;

export default async function(app) {
  const zones = await import('/time-zone.js');
  const {crc32} = await import('/crc32.js');
  if (app.settings.action === 'errors') {
    const results = [];
    const day = 86400;
    const cases = [
      () => zones.snapshot('bad:name', () => 0),
      () => zones.snapshot('Test/Offsets', utc => Math.floor((utc - zones.FIRST) / day) % 9 * 60),
      () => zones.snapshot('Test/Transitions', utc => Math.floor((utc - zones.FIRST) / day) % 2 * 3600),
      () => zones.snapshot('Test/Range', () => 86401),
    ];
    for (const run of cases) {
      try { run(); results.push({name: 'accepted'}); }
      catch (error) { results.push({name: error.name, message: error.message}); }
    }
    return results;
  }
  let bytes;
  let ticks = 0;
  if (app.settings.action === 'maximum') {
    bytes = zones.snapshot('Test/Maximum', utc => Math.min(276, Math.floor((utc - zones.FIRST) / 86400)) % 2 * 3600);
  } else if (app.settings.action === 'worker') {
    const timer = setInterval(() => { ticks += 1; }, 0);
    try { bytes = (await zones.prepareZone(app.settings.zone)).bytes; }
    finally { clearInterval(timer); }
  } else bytes = zones.snapshot(app.settings.zone);
  let raw = '';
  for (const byte of bytes) raw += String.fromCharCode(byte);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const count = view.getUint16(18, true);
  const samples = [zones.FIRST, zones.UNTIL - 1];
  for (let at = 0; at < count; at += 1) {
    const utc = view.getUint32(120 + at * 5, true);
    samples.push(utc - 1, utc);
  }
  const offset = app.settings.action === 'maximum' ? null : zones.zoneOffset(app.settings.zone);
  return {base64: btoa(raw), revision: crc32(bytes), ticks,
    checks: offset === null ? [] : samples.map(utc => ({utc, offset: offset(utc)}))};
}
