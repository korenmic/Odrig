export const withoutTheApp = true;

export default async function () {
  const d = await import("/upload-destination.js");
  const ready = await import("/ready.js");
  const space = {free: 1000000, external: {present: true, read_only: false, free: 1000000}};
  const catalog = {internal: {state: "ok", generation: 1}, external: {state: "ok", generation: 4, writable: true}};
  const state = {space, catalog, level: {path: "night/deep", id: 60004}, animations: []};
  const seen = {};
  const equal = (name, actual, expected) => { if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`${name}: ${JSON.stringify(actual)}`); seen[name] = true; };
  const refuses = (name, run, pattern) => {
    try { run(); } catch (error) { if (!pattern.test(error.message)) throw error; seen[name] = true; return; }
    throw new Error(`${name}: accepted`);
  };
  let form = d.capture(state, 3);
  equal("default_empty_list", form.storage, "external");
  state.level.path = "elsewhere";
  equal("captured_navigation", d.pathOf(form, "new.odrg"), "night/deep/new.odrg");
  d.synchronize(form, {free: 1000000, external: null});
  equal("absent_fallback", [form.storage, d.pathOf(form, "new.odrg")], ["internal", "new.odrg"]);
  equal("flat_root_explanation", /no matching subfolders/.test(d.reason(form, null)), true);
  d.synchronize(form, space);
  equal("redetection_default", form.storage, "external");
  d.select(form, "internal", space);
  d.synchronize(form, null); d.synchronize(form, space);
  equal("explicit_internal_survives", form.storage, "internal");
  state.level.path = "night/deep";
  equal("next_form_external", d.capture(state, 3).storage, "external");
  form = d.capture(state, 3);
  const fresh = {space, catalog, root: [], items: [], folderValid: true};
  refuses("stale_catalog", () => d.validate(form, {...fresh, catalog: {...catalog, external: {...catalog.external, generation: 5}}}, "new.odrg", 100, 3), /catalog changed/);
  refuses("stale_target", () => d.validate(form, fresh, "new.odrg", 100, 4), /target changed/);
  refuses("missing_folder", () => d.validate(form, {...fresh, folderValid: false}, "new.odrg", 100, 3), /folder changed/);
  refuses("read_only", () => d.validate(form, {...fresh, space: {...space, external: {...space.external, read_only: true}}}, "new.odrg", 100, 3), /read-only/);
  refuses("collision", () => d.validate(form, {...fresh, items: [{file: "night/deep/new.odrg", external: true}]}, "new.odrg", 100, 3), /already exists/);
  for (const name of ["../new.odrg", "new.mp4", "New.odrg", "a".repeat(33)+".odrg"]) refuses(`unsafe_${name}`, () => d.pathOf(form, name), /filename/);
  form = d.capture({...state, level: {path: "", id: null}}, 3);
  equal("namespace_separate", d.validate(form, {...fresh, items: [{file: "new.odrg", external: false}]}, "new.odrg", 100, 3).path, "new.odrg");
  d.select(form, "internal", space);
  equal("full_internal", d.validate(form, {...fresh, space: {free: 100, external: null}}, "new.odrg", 1000, 3).noSpace, 100);
  const bytes = new Uint8Array(24);
  bytes.set([79,68,82,71,1,1,60,0,6,0,0,0,255,255,255,255]);
  const file = new File([bytes], "compressed.odrg");
  const prepared = await ready.prepare(file, {width: 60, height: 6});
  equal("no_inflate_compressed_body", [prepared.previewSafe, [...prepared.bytes]], [false, [...bytes]]);
  let bodyRead = false;
  const wrongCanvas = {name: file.name, size: file.size, slice: (...args) => file.slice(...args), arrayBuffer() {bodyRead=true; throw new Error("body should not be loaded");}};
  try { await ready.prepare(wrongCanvas, {width: 60, height: 60}); throw new Error("accepted wrong canvas"); } catch (error) {
    if (!/canvas/.test(error.message)) throw error;
  }
  equal("mismatch_header_only", bodyRead, false);
  return seen;
}
