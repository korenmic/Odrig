import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 0);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  if (app.settings.catalogState) {
    await app.until(() => client.state.catalog?.external.state === app.settings.catalogState,
      'uncertain catalog heard');
    return {notice: app.text('only-boundary'), restartDisabled: app.byId('play-all').disabled,
      level: client.state.level};
  }
  await app.until(() => app.raw('level-title') === 'clocks' &&
    app.text('only-boundary')?.includes('Clocks folder unavailable'), 'unavailable Clocks explanation');
  const notice = app.text('only-boundary');
  const restartDisabled = app.byId('play-all').disabled;
  app.press('Target');
  const target = app.shown();
  app.press('Settings');
  await app.until(() => !app.byId('clocks').disabled, 'mode recovery available');
  app.byId('clocks').value = 'off';
  app.byId('clocks').dispatchEvent(new Event('change', {bubbles: true}));
  await app.until(() => client.state.status?.clockMode === 'off' && client.state.level.path === '', 'confirmed exit from Only');
  return {notice, restartDisabled, target, mode: client.state.status.clockMode, level: client.state.level.path};
}
