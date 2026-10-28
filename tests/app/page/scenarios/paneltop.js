// The top row of the panel of what plays: the power icon, which switches the LEDs, and the
// button that collapses the panel to that row and expands it again; and what Animations no
// longer has.

import {shown} from "../reading.js";
import {behind} from "./look.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

function box(element) {
  const rect = element.getBoundingClientRect();
  return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
}

// A button of the top row: its state, its words for a screen reader, where it stands, its
// roundness, and the colour of its icon over what lies behind it; null when the page has
// none.
function button(app, id) {
  const view = app.frame.contentWindow;
  const element = app.doc.getElementById(id);
  if (element === null) {
    return null;
  }
  const style = view.getComputedStyle(element);
  return {
    pressed: element.getAttribute("aria-pressed"),
    expanded: element.getAttribute("aria-expanded"),
    label: element.getAttribute("aria-label"),
    ...box(element),
    radius: parseFloat(style.borderTopLeftRadius),
    icon: view.getComputedStyle(element.querySelector("svg path")).stroke,
    behind: behind(view, element),
  };
}

function look(app) {
  const view = app.frame.contentWindow;
  const panel = app.byId("now-panel");
  const style = view.getComputedStyle(panel);
  const at = panel.getBoundingClientRect();
  const nav = app.doc.querySelector("nav");
  const first = app.doc.querySelector("#animations-list > .row");
  const outside = (element) => element.closest("#now-bar, #row-menu, nav") === null;
  let kept = null;
  try {
    kept = view.localStorage.getItem("odrig.panel");
  } catch (error) {
    kept = "unreadable";
  }
  return {
    power: button(app, "power-toggle"),
    collapse: button(app, "now-collapse"),
    mark: app.doc.getElementById("now-collapse-mark")?.getAttribute("d") ?? null,
    collapsed: panel.classList.contains("collapsed"),
    parts: [...panel.children].filter(displayed).map((part) => part.id || part.className),
    row: panel.querySelector(".now-top") === null ? null : box(panel.querySelector(".now-top")),
    inner: {left: at.left + parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft), right: at.right - parseFloat(style.borderRightWidth) - parseFloat(style.paddingRight)},
    height: at.height,
    frozen: panel.classList.contains("frozen"),
    padding: app.doc.documentElement.style.scrollPaddingTop,
    band: parseFloat(view.getComputedStyle(app.doc.body, "::before").height) || 0,
    nav: displayed(nav) ? nav.getBoundingClientRect().height : 0,
    view: view.innerHeight,
    firstRow: first === null ? null : first.getBoundingClientRect().top,
    kept,
    bar: [...app.byId("now-bar").querySelectorAll("button")].filter(displayed).map((element) => element.textContent.trim()),
    // Every other control on the screen, a checkbox by its label.
    others: [...app.doc.querySelectorAll("button, input, select, label.button")]
      .filter((element) => displayed(element) && element.id !== "power-toggle" && element.id !== "now-collapse")
      .map((element) => ({what: element.id || element.getAttribute("aria-label") || element.textContent.trim(), ...box(element.type === "checkbox" ? element.closest("label") : element)})),
    gone: {
      selectMode: app.doc.getElementById("select-mode") !== null,
      addAnimation: app.doc.getElementById("add-animation") !== null,
      playing: displayed(app.byId("playing")),
      words: app.raw("playing"),
      onOff: ["on", "off"].filter((id) => displayed(app.byId(id))),
      buttons: [...app.doc.querySelectorAll("button")].filter((element) => displayed(element) && outside(element)).map((element) => element.textContent.trim()),
    },
  };
}

// Each act of the settings in turn: a press of a button of the top row, which must be on
// the screen; a look at once after it; a reload of the app; a step of the test; a wait for
// the power icon's state; or a pause.
export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = {};
  for (const act of app.settings.acts) {
    if (act.press !== undefined) {
      const element = app.byId(act.press);
      if (!displayed(element)) {
        throw new Error(`${act.press} is not on the screen`);
      }
      element.click();
    }
    if (act.reload) {
      await app.reload();
      await shown(app, app.settings.rows);
    }
    if (act.step) {
      await app.step();
    }
    if (act.pressed !== undefined) {
      await app.until(() => app.byId("power-toggle").getAttribute("aria-pressed") === act.pressed, `the power icon with aria-pressed ${act.pressed}`);
    }
    if (act.wait !== undefined) {
      await app.sleep(act.wait);
    }
    if (act.look !== undefined) {
      seen[act.look] = look(app);
    }
  }
  return seen;
}
