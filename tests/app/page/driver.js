// Runs one scenario against the app, which is in a frame of this page, and posts what
// the scenario found. A scenario works the app the way an operator does.

const asked = new URLSearchParams(location.search);
const KEY = "odrig.target";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function loaded(frame) {
  return new Promise((resolve) => frame.addEventListener("load", resolve, {once: true}));
}

function displayed(element) {
  return element.getClientRects().length > 0;
}

function tools(frame) {
  const app = {
    settings: JSON.parse(asked.get("settings")),
    frame,
    sleep,
    get doc() {
      return frame.contentDocument;
    },
    byId(id) {
      const found = app.doc.getElementById(id);
      if (found === null) {
        throw new Error(`the page has no element ${id}`);
      }
      return found;
    },
    // The text of an element, or null while it is not on the screen.
    text(id) {
      const element = app.byId(id);
      return displayed(element) ? element.textContent.trim() : null;
    },
    // The text of an element, on the screen or not.
    raw(id) {
      return app.byId(id).textContent.trim();
    },
    // Everything that is on the screen, as text.
    screen() {
      return app.doc.body.innerText;
    },
    // Whether the screen says something that a pattern describes, its words taken with
    // one space between them.
    says(pattern) {
      return new RegExp(pattern).test(app.screen().replace(/\s+/g, " "));
    },
    // The id of the screen that is shown.
    shown() {
      return [...app.doc.querySelectorAll("main > section")].filter(displayed).map((section) => section.id).join(" ");
    },
    // Presses the button that has these words.
    press(words) {
      const found = [...app.doc.querySelectorAll("button")].filter((button) => displayed(button) && button.textContent.trim() === words);
      if (found.length !== 1) {
        throw new Error(`${found.length} buttons on the screen say "${words}"`);
      }
      found[0].click();
    },
    // Writes a text into a field, as typing does.
    fill(id, text) {
      const field = app.byId(id);
      field.value = text;
      field.dispatchEvent(new Event("input", {bubbles: true}));
    },
    // Waits until a check gives something, and gives that.
    async until(check, what, ms = 8000) {
      const end = performance.now() + ms;
      for (;;) {
        const found = check();
        if (found) {
          return found;
        }
        if (performance.now() > end) {
          throw new Error(`after ${ms} ms still not: ${what}`);
        }
        await sleep(25);
      }
    },
    // Loads the app again, as closing and opening it does.
    async reload() {
      const again = loaded(frame);
      frame.contentWindow.location.reload();
      await again;
    },
    // Asks the test for its next step and waits until it is done.
    async step() {
      await fetch("/step", {method: "POST", body: ""});
    },
    // What the app keeps as its address, or null.
    kept() {
      return localStorage.getItem(KEY);
    },
  };
  return app;
}

async function main() {
  if (asked.has("address")) {
    localStorage.setItem(KEY, asked.get("address"));
  } else {
    localStorage.removeItem(KEY);
  }
  const scenario = await import(`./scenarios/${asked.get("scenario")}.js`);
  const frame = document.createElement("iframe");
  frame.width = asked.get("width");
  frame.height = asked.get("height");
  let result;
  try {
    if (scenario.withoutTheApp !== true) {
      const first = loaded(frame);
      frame.src = "/index.html";
      document.body.append(frame);
      await first;
    }
    result = {ok: true, seen: await scenario.default(tools(frame))};
  } catch (error) {
    const screen = frame.contentDocument === null ? "" : frame.contentDocument.body.innerText;
    result = {ok: false, error: String(error !== null && error.stack !== undefined ? error.stack : error), screen};
  }
  await fetch("/result", {method: "POST", body: JSON.stringify(result)});
}

main();
