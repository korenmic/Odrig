import {shown} from "../reading.js";

export default async function(app) {
  await shown(app, 1);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  app.press('Settings');
  await app.until(() => !app.byId('clocks').disabled, 'mode recovery available');
  const before = {reason: app.raw('clocks-state'),
    messageDisabled: app.byId('clock-message').disabled, modeDisabled: app.byId('clocks').disabled};
  app.byId('clocks').value = 'off';
  app.byId('clocks').dispatchEvent(new Event('change', {bubbles: true}));
  await app.until(() => client.state.status.clockMode === 'off', 'explicit mode recovery');
  return {before, after: {mode: client.state.status.clockMode, error: client.state.status.clockError}};
}
