import {shown} from '../reading.js';

export default async function(app) {
  await shown(app, 0);
  await app.until(() => app.raw('level-title') === 'clocks' &&
    app.text('inventory-state')?.includes('Clocks folder unavailable'), 'unavailable Clocks explanation');
  const notice = app.text('inventory-state');
  const restartDisabled = app.byId('play-all').disabled;
  app.press('Target');
  const target = app.shown();
  app.press('Settings');
  await app.until(() => !app.byId('clocks').disabled, 'mode recovery available');
  app.byId('clocks').value = 'off';
  app.byId('clocks').dispatchEvent(new Event('change', {bubbles: true}));
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.status?.clockMode === 'off' && client.state.level.path === '', 'confirmed exit from Only');
  return {notice, restartDisabled, target, mode: client.state.status.clockMode, level: client.state.level.path};
}
