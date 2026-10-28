// The bar of the animation playing now, worked as an operator works it: the acts of the
// test press its buttons and others, type into its field and leave it, open a folder or a
// filter, take the app off the screen, and ask the test for its steps; the screen is looked
// at where the test asks.

import {rowOf, shown} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

// What a child of a line of the bar shows: a button's words, `(disabled)` after those of
// one that is, a field's text in brackets, or a line's words.
function shownAs(child) {
  if (child.localName === "button") {
    return `${child.textContent}${child.disabled ? " (disabled)" : ""}`;
  }
  if (child.localName === "input") {
    return `[${child.value}]`;
  }
  return child.textContent;
}

function barOf(app) {
  const place = app.byId("now-bar");
  if (!displayed(place)) {
    return null;
  }
  const box = place.getBoundingClientRect();
  return {
    lines: [...place.querySelectorAll(":scope > .bar-line")].map((line) => [...line.children].filter(displayed).map(shownAs)),
    named: [...place.querySelectorAll("button, input")].filter(displayed).map((one) => one.getAttribute("aria-label")),
    height: box.height,
    previous: place.previousElementSibling.id,
    next: place.nextElementSibling.id,
  };
}

function look(app) {
  const view = app.frame.contentWindow;
  const field = app.doc.getElementById("repeat-count");
  const band = parseFloat(view.getComputedStyle(app.doc.body, "::before").height) || 0;
  const panel = app.byId("now-panel");
  const checked = [...app.doc.querySelectorAll("#animations-list .pick input")].filter((input) => input.checked).map((input) => Number(input.closest(".row").dataset.id));
  const pressed = [...app.doc.querySelectorAll("#filters button[aria-pressed=\"true\"]")].map((button) => button.getAttribute("aria-label").split(",")[0]);
  return {
    bar: barOf(app),
    now: app.text("now"),
    playing: app.text("playing"),
    message: app.text("message-text"),
    question: app.text("confirm-text"),
    level: app.raw("level-title"),
    selecting: app.byId("animations-list").classList.contains("selecting"),
    checked,
    filters: pressed,
    field: field === null ? null : field.value,
    focused: field !== null && app.doc.activeElement === field,
    frozen: panel.classList.contains("frozen"),
    panelBottom: panel.classList.contains("frozen") ? band + panel.getBoundingClientRect().height : band,
    rowTops: Object.fromEntries([...app.doc.querySelectorAll("#animations-list > .row")].map((row) => [row.dataset.id, row.getBoundingClientRect().top])),
    scrolled: view.scrollY,
    stale: panel.classList.contains("stale"),
  };
}

// Presses the button of the bar whose accessible name is this.
function pressBar(app, named) {
  const found = [...app.byId("now-bar").querySelectorAll("button")].filter((button) => displayed(button) && button.getAttribute("aria-label") === named);
  if (found.length !== 1) {
    throw new Error(`${found.length} buttons of the bar are named "${named}"`);
  }
  found[0].click();
}

export default async function (app) {
  await shown(app, app.settings.rows);
  let hidden = false;
  Object.defineProperty(app.doc, "hidden", {configurable: true, get: () => hidden});
  const looks = {};
  for (const act of app.settings.acts) {
    if (act.until !== undefined) {
      await app.until(() => app.says(act.until), act.until, act.ms ?? 8000);
    }
    if (act.untilBar !== undefined) {
      await app.until(() => {
        const bar = barOf(app);
        return bar !== null && bar.named.includes(act.untilBar);
      }, `the bar with ${act.untilBar}`);
    }
    if (act.untilNoBar) {
      await app.until(() => barOf(app) === null, "no bar");
    }
    if (act.press !== undefined) {
      if (act.in !== undefined) app.pressIn(act.in, act.press);
      else app.press(act.press);
    }
    if (act.bar !== undefined) {
      pressBar(app, act.bar);
    }
    if (act.open !== undefined) {
      app.doc.querySelector(`#animations-list > .folder-row[data-path="${act.open}"]`).click();
    }
    if (act.filter !== undefined) {
      [...app.byId(`filter-${act.filter[0]}`).querySelectorAll("button")].find((button) => button.getAttribute("aria-label").split(",")[0] === act.filter[1]).click();
    }
    if (act.focus) {
      app.byId("repeat-count").focus();
    }
    if (act.type !== undefined) {
      app.byId("repeat-count").focus();
      app.fill("repeat-count", act.type);
    }
    if (act.enter) {
      app.byId("repeat-count").dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    }
    if (act.leave) {
      app.byId("repeat-count").blur();
    }
    if (act.row !== undefined) {
      rowOf(app, act.row);
    }
    if (act.hide !== undefined) {
      hidden = act.hide;
      app.doc.dispatchEvent(new Event("visibilitychange"));
    }
    if (act.step) {
      await app.step();
    }
    if (act.wait !== undefined) {
      await app.sleep(act.wait);
    }
    if (act.look !== undefined) {
      looks[act.look] = look(app);
    }
  }
  return looks;
}
