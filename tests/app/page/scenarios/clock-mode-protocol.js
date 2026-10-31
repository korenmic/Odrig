export const withoutTheApp = true;

export default async function(app) {
  let answer;
  const sent = [];
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      sent.push(request.line);
      return {status: 200, body: JSON.stringify(answer)};
    },
  };
  const commands = await import('/commands.js');
  const results = [];
  for (const entry of app.settings.replies) {
    answer = entry.reply;
    try { results.push(await commands[entry.command](...(entry.args ?? []))); }
    catch (error) { results.push({error: error.kind || error.code || error.name}); }
  }
  return {results, sent};
}
