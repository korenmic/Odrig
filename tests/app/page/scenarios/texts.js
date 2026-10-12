// Every text of the app's table of messages, asked for without the app.

export const withoutTheApp = true;

export default async function (app) {
  const messages = await import("/messages.js");
  const refusals = {};
  for (const [code, line, reason] of app.settings.refusals) {
    refusals[`${code} | ${line} | ${reason}`] = messages.ofRefusal({code, line}, reason);
  }
  const failures = {};
  for (const [kind, detail] of app.settings.failures) {
    failures[kind] = messages.ofFailure({kind, detail});
  }
  return {notForTheApp: messages.NOT_FOR_THE_APP, refusals, failures, silence: [0, 1, 2, 75].map((seconds) => messages.ofSilence(seconds))};
}
