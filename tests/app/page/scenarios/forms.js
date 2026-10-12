// What the app makes of each text an operator may write as an address.

export const withoutTheApp = true;

export default async function (app) {
  const target = await import("/target.js");
  const kept = {};
  for (const text of app.settings.texts) {
    try {
      kept[text] = target.parse(text);
    } catch (error) {
      kept[text] = `refused: ${error.kind}`;
    }
  }
  return {board: target.BOARD, first: target.address(), kept};
}
