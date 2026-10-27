// The replies to `limits` as commands.js checks them, and the lines of the current limits
// it sends, through the native bridge as the APK sends them.
export const withoutTheApp = true;
export default async function(app) {
  const sent = [];
  let answer;
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      sent.push(request.line);
      return {status: 200, body: JSON.stringify(answer)};
    },
  };
  const commands = await import("/commands.js");
  const found = [];
  for (const [from, reply] of app.settings.replies) {
    answer = reply;
    try {
      found.push(await commands.limits(from));
    } catch (error) {
      found.push({error: error.kind || error.code});
    }
  }
  answer = {ok: true};
  await commands.limitsWall(2000);
  await commands.limitsSnake(3, 0);
  return {found, sent};
}
