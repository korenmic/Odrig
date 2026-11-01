export const withoutTheApp = true;

export default async function(app) {
  const destination = await import('/upload-destination.js');
  const external = {present: true, read_only: false, free: 1000000, total: 2000000};
  const catalog = {internal: {state: 'ok', generation: 1, entries: 0, uncataloged: 0},
    external: {state: 'ok', generation: 2, entries: 1, writable: true}};
  const space = {free: 1000000, total: 2000000,
    external: app.settings.present ? external : null};
  const state = {status: {clockMode: app.settings.rootDraft ? 'off' : 'only'},
    level: app.settings.rootDraft ? {path: '', id: null} : {path: 'clocks', id: 60007}, space, catalog};
  const form = destination.capture(state, 3);
  if (app.settings.internal) destination.select(form, 'internal', space);
  destination.synchronize(form, space);
  if (app.settings.rootDraft) destination.synchronize(form, space, true);
  if (app.settings.release) destination.synchronize(form, space, false);
  let allowed = false;
  let error = null;
  try {
    destination.validate(form, {space, catalog, root: [], items: [], folderValid: true}, 'ready.odrg', 100, 3);
    allowed = true;
  } catch (caught) { error = caught.message; }
  return {storage: form.storage, label: destination.label(form, 'ready.odrg'), allowed, error,
    reason: destination.reason(form, space)};
}
