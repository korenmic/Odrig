// The zip writer of the app, alone: an archive of a folder and of files given in pieces,
// what it measures beforehand, and what it refuses.

export const withoutTheApp = true;

function base64Of(bytes) {
  let text = "";
  for (let at = 0; at < bytes.length; at += 0x8000) text += String.fromCharCode(...bytes.subarray(at, at + 0x8000));
  return btoa(text);
}

function bytesOf(text) {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let at = 0; at < raw.length; at += 1) bytes[at] = raw.charCodeAt(at);
  return bytes;
}

async function refused(work) {
  try {
    await work();
  } catch (error) {
    return error.message;
  }
  return null;
}

export default async function (app) {
  const zip = await import("/zip-writer.js");
  const written = [];
  const sink = {write: async (bytes) => { written.push(bytes.slice()); }};
  const writer = new zip.ZipWriter(sink, new Date(2026, 10, 8, 17, 30, 42));
  const seen = {entries: []};
  await writer.directory("empty");
  for (const file of app.settings.files) {
    const bytes = bytesOf(file.data);
    const pieces = [];
    for (let at = 0; at < bytes.length; at += file.piece) pieces.push(bytes.subarray(at, at + file.piece));
    seen.entries.push(await writer.file(file.name, pieces));
  }
  seen.refusals = [];
  for (const name of ["../up.odrg", "/top.odrg", "a//b.odrg", "a\\b.odrg", "a/./b.odrg", "", app.settings.files[0].name]) {
    seen.refusals.push(await refused(() => writer.file(name, [new Uint8Array(1)])));
  }
  seen.size = await writer.finish();
  seen.afterFinish = await refused(() => writer.file("late.odrg", [new Uint8Array(1)]));
  const whole = new Uint8Array(written.reduce((sum, part) => sum + part.length, 0));
  let at = 0;
  for (const part of written) {
    whole.set(part, at);
    at += part.length;
  }
  seen.archive = base64Of(whole);
  seen.measured = zip.measure([{name: "empty/", size: null}, ...app.settings.files.map((file) => ({name: file.name, size: bytesOf(file.data).length}))]);
  seen.fits = [zip.fits([{name: "a", size: zip.MOST_BYTES - 100}]), zip.fits([{name: "a", size: 1000}]),
    zip.fits(Array.from({length: zip.MOST_ENTRIES}, (_, number) => ({name: `${number}/`, size: null}))),
    zip.fits(Array.from({length: zip.MOST_ENTRIES + 1}, (_, number) => ({name: `${number}/`, size: null})))];
  // An archive of as many entries as needs no zip64 takes no more.
  const many = new zip.ZipWriter({write: async () => {}});
  for (let number = 0; number < zip.MOST_ENTRIES; number += 1) await many.directory(`${number}`);
  seen.tooMany = await refused(() => many.directory("one-more"));
  seen.mostEntries = zip.MOST_ENTRIES;
  return seen;
}
