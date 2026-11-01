import {shown} from '../reading.js';

export default async function(app) {
  let client = await app.frame.contentWindow.eval('import("/client.js")');
  if (app.settings.case === 'missing') {
    await app.until(() => client.state.status?.clockMode === 'only' && client.state.animations !== null, 'Only with missing folder');
    return {level:client.state.level.path, files:client.state.animations.map(row => row.file)};
  }
  await shown(app, 1);
  if (app.settings.reload) {
    await app.reload();
    await shown(app, 1);
    client = await app.frame.contentWindow.eval('import("/client.js")');
  }
  await app.until(() => client.state.statusFresh && client.state.level.path === 'clocks' &&
    client.state.folders.length === 2, 'Clocks list');
  const paths = [];
  client.watch(state => paths.push(state.level.path));
  const backHidden = app.byId('level-back').hidden;
  const note = app.text('only-boundary');
  const levels = [];
  if (['uncertain','offline'].includes(app.settings.case)) {
    await app.until(() => app.settings.case === 'uncertain' ? client.state.status?.hasClockMode === false :
      client.state.link === 'no-answer', 'uncertain policy');
    client.back();
    return {level:client.state.level.path, only:client.clocksOnly?.() ?? false};
  } else if (app.settings.case === 'child') {
    client.enter(client.state.folders.find(row => row.playlist === 'clocks/child'));
    await app.until(() => client.state.level.path === 'clocks/child' && client.state.animations?.length === 1, 'child list');
    levels.push(client.state.level.path);
    client.back();
    await app.until(() => client.state.level.path === 'clocks' && client.state.animations?.length === 1, 'Clocks list again');
    levels.push(client.state.level.path);
    client.back();
    levels.push(client.state.level.path);
  } else if (app.settings.case === 'release') {
    await client.clockMode('between');
    await app.until(() => client.state.status?.clockMode === 'between', 'confirmed Between');
    client.back();
    return {level: client.state.level.path};
  } else {
    client.back();
    levels.push(client.state.level.path);
    client.enter({id:60009, playlist:'other'});
    levels.push(client.state.level.path);
    client.enter({id:60012, playlist:'clocks-other'});
    levels.push(client.state.level.path);
  }
  return {paths, levels, backHidden, note};
}
