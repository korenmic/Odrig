export async function unlockMapping(app) {
  await app.until(() => !app.byId('mapping-lock').disabled, 'mapping lock ready');
  if (app.byId('mapping-lock').getAttribute('aria-pressed') === 'true') {
    app.byId('mapping-lock').click();
    await app.until(() => app.byId('mapping-lock-dialog').open, 'unlock confirmation');
    app.byId('mapping-lock-yes').click();
  }
  const mapping = await app.frame.contentWindow.eval('import("/screens/mapping.js")');
  await app.until(() => mapping.canEdit(), 'confirmed mapping unlock');
}
