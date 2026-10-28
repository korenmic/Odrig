// The panel of what plays at the top of Animations, with the room of the phone's bars the
// test gives: whether it stays at the top while the list scrolls under it, at the height
// where a whole row of the list just fits under it and one pixel lower, with the keyboard
// open, and under a row that is lifted to be moved.

import {rowOf, shown} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

function measure(app) {
  const view = app.frame.contentWindow;
  const panel = app.byId("now-panel");
  const box = panel.getBoundingClientRect();
  const nav = app.doc.querySelector("nav");
  const navBox = nav.getBoundingClientRect();
  const style = view.getComputedStyle(panel);
  const under = [...app.doc.querySelectorAll("#animations-list > .row")].filter((row) => {
    const at = row.getBoundingClientRect();
    return at.top >= box.bottom - 0.5 && at.bottom <= (displayed(nav) ? navBox.top : view.innerHeight) + 0.5;
  });
  // What is on top in the middle of the panel's lower edge, just inside it.
  const found = app.doc.elementFromPoint(box.left + box.width / 2, box.bottom - 6);
  return {
    frozen: panel.classList.contains("frozen"),
    position: style.position,
    top: box.top,
    bottom: box.bottom,
    height: box.height,
    background: style.backgroundColor,
    band: parseFloat(view.getComputedStyle(app.doc.body, "::before").height) || 0,
    nav: displayed(nav) ? navBox.height : 0,
    view: view.innerHeight,
    scrolled: view.scrollY,
    rowsUnder: under.length,
    onTop: found !== null && found.closest("#now-panel") !== null,
    padding: app.doc.documentElement.style.scrollPaddingTop,
  };
}

async function resized(app, height) {
  app.frame.height = String(height);
  await app.until(() => app.frame.contentWindow.innerHeight === height, `a view ${height} high`);
  await app.sleep(150);
}

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 5, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

export default async function (app) {
  const room = app.settings.room;
  for (const side of ["top", "right", "bottom", "left"]) {
    app.doc.documentElement.style.setProperty(`--safe-area-inset-${side}`, `${room[side] ?? 0}px`);
  }
  await shown(app, app.settings.rows);
  await app.until(() => app.byId("now-bar").getClientRects().length > 0, "the bar");
  await app.sleep(1200);
  const view = app.frame.contentWindow;
  const seen = {top: measure(app)};
  view.scrollTo(0, 600);
  await app.sleep(150);
  seen.scrolled = measure(app);
  view.scrollTo(0, 0);
  await app.sleep(150);
  const height = view.innerHeight;
  if (app.settings.threshold) {
    // The height at which a row of 80 pixels just fits between the panel and the tabs.
    const top = seen.top;
    const exact = Math.ceil(top.band + top.height + top.nav + 80);
    await resized(app, exact);
    seen.exact = measure(app);
    await resized(app, exact - 1);
    seen.short = measure(app);
    await resized(app, height);
  }
  if (app.settings.keyboard) {
    const field = app.byId("level-number");
    field.focus();
    await app.sleep(100);
    await resized(app, Math.round(height * 2 / 3));
    seen.typing = {...measure(app), typing: app.doc.body.classList.contains("typing")};
    field.blur();
    await resized(app, height);
    seen.afterTyping = measure(app);
  }
  if (app.settings.lift !== undefined) {
    // A row held and dragged up under the panel: its top edge stops under the panel.
    view.scrollTo(0, 600);
    await app.sleep(150);
    const play = rowOf(app, app.settings.lift).querySelector(".play");
    const box = play.getBoundingClientRect();
    const x = box.left + 20;
    const y = box.top + box.height / 2;
    pointer(app, "pointerdown", play, x, y);
    await app.sleep(600);
    const panel = app.byId("now-panel").getBoundingClientRect();
    for (let step = 1; step <= 6; step += 1) {
      pointer(app, "pointermove", app.doc, x, y + (panel.top + 10 - y) * step / 6);
      await app.sleep(30);
    }
    const lifted = app.doc.querySelector("#animations-list > .row.lifted");
    seen.lifted = {found: lifted !== null, top: lifted === null ? null : lifted.getBoundingClientRect().top, panelBottom: app.byId("now-panel").getBoundingClientRect().bottom};
    pointer(app, "pointerup", app.doc, x, panel.top + 10);
    await app.sleep(300);
  }
  return seen;
}
