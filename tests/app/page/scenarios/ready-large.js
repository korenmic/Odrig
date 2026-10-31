export const withoutTheApp = true;

export default async function (app) {
  const {prepare} = await import("/ready.js");
  const response = await fetch(`/m/${app.settings.file}`);
  if (!response.ok) throw new Error("large animation fixture could not be read");
  const blob = await response.blob();
  const file = new File([blob], app.settings.file);
  const prefixReads = [];
  let encodedReads = 0;
  const selected = {name: file.name, size: file.size,
    slice(first, last) { prefixReads.push([first, last]); return file.slice(first, last); },
    arrayBuffer() { encodedReads += 1; return file.arrayBuffer(); }};
  const prepared = await prepare(selected, {width: 60, height: 60});
  const hash = await crypto.subtle.digest("SHA-256", prepared.bytes);
  return {bytes: prepared.bytes.length, sha256: [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, "0")).join(""),
    prefixReads, encodedReads, previewSafe: prepared.previewSafe, frames: prepared.header.frameCount,
    materializedFrames: "animation" in prepared || "frames" in prepared};
}
