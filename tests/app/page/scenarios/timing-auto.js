export default async function(app) {
  await app.until(() => app.raw('link') === 'Answers', 'connected target');
  const {send} = await import('/target.js');
  const deadline = performance.now() + 12000;
  let clock;
  do {
    clock = await send('time');
    if (clock.valid) break;
    await app.sleep(200);
  } while (performance.now() < deadline);
  return {clock, connected: app.raw('link')};
}
