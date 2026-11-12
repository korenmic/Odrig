// Every text of the app's table of messages, asked for without the app.

export const withoutTheApp = true;

export default async function (app) {
  const messages = await import("/messages.js");
  const refusals = {};
  // A fourth member asks for the words of a target that plays the clocks of both storages.
  for (const [code, line, reason, both] of app.settings.refusals) {
    refusals[`${code} | ${line} | ${reason}${both ? " | both" : ""}`] = messages.ofRefusal({code, line}, reason, both === true);
  }
  const failures = {};
  for (const [kind, detail] of app.settings.failures) {
    failures[kind] = messages.ofFailure({kind, detail});
  }
  const conversions = {};
  for (const [reason, detail] of app.settings.conversions || []) {
    conversions[reason] = messages.ofConversion({reason, detail});
  }
  return {notForTheApp: messages.NOT_FOR_THE_APP, refusals, failures, conversions, silence: [0, 1, 2, 75].map((seconds) => messages.ofSilence(seconds))};
}
