export const withoutTheApp = true;
export default async function(app) {
  const sent = [];
  let answer;
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (_plugin, _method, request) => {
      sent.push(request.line);
      return {status:200, body:JSON.stringify(answer)};
    },
  };
  const commands = await import("/commands.js");
  const found = [];
  for (answer of app.settings.replies) {
    try {found.push(await commands.mappingGet());}
    catch (error) {found.push({error:error.kind || error.code});}
  }
  answer = {ok:true};
  await commands.mappingSet(123, [1,2,3]);
  await commands.mappingTest(true);
  await commands.mappingTest(false);
  await commands.mappingTestSnake(9);
  return {found, sent};
}
