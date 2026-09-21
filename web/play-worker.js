import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs";

let pyodide = null;
let initialized = false;

async function boot() {
  if (initialized) return;
  pyodide = await loadPyodide();

  const [bundleResponse, cardsResponse, deckResponse] = await Promise.all([
    fetch("data/python-bundle.json", { cache: "no-store" }),
    fetch("data/cards.json", { cache: "no-store" }),
    fetch("data/reference-deck.json", { cache: "no-store" }),
  ]);
  if (!bundleResponse.ok || !cardsResponse.ok || !deckResponse.ok) {
    throw new Error("Could not load the game engine bundle.");
  }

  const bundle = await bundleResponse.json();
  const cardsText = await cardsResponse.text();
  const deckText = await deckResponse.text();

  pyodide.FS.mkdirTree("/game");
  for (const [relativePath, source] of Object.entries(bundle)) {
    const fullPath = "/game/" + relativePath;
    const directory = fullPath.slice(0, fullPath.lastIndexOf("/"));
    pyodide.FS.mkdirTree(directory);
    pyodide.FS.writeFile(fullPath, source);
  }

  pyodide.globals.set("CARD_DATA_JSON", cardsText);
  pyodide.globals.set("DECK_JSON", deckText);
  await pyodide.runPythonAsync(
    'import sys\nsys.path.insert(0, "/game")\nfrom longwar.web_api import PlaySession\nsession = None'
  );
  initialized = true;
}

async function handle(message) {
  await boot();

  if (message.type === "new_game") {
    pyodide.globals.set("MODE_JS", String(message.mode));
    pyodide.globals.set("SEED_JS", Number(message.seed));
    const result = await pyodide.runPythonAsync(
      'session = PlaySession(CARD_DATA_JSON, DECK_JSON, str(MODE_JS), int(SEED_JS))\nsession.snapshot_json(None if str(MODE_JS) == "hotseat" else 0)'
    );
    return JSON.parse(result);
  }

  if (message.type === "view") {
    pyodide.globals.set("VIEWER_JS", message.viewer == null ? -1 : Number(message.viewer));
    const result = await pyodide.runPythonAsync(
      'session.snapshot_json(None if int(VIEWER_JS) < 0 else int(VIEWER_JS))'
    );
    return JSON.parse(result);
  }

  if (message.type === "act") {
    pyodide.globals.set("KEY_JS", String(message.key));
    pyodide.globals.set("VIEWER_JS", Number(message.viewer));
    const result = await pyodide.runPythonAsync(
      'session.act_json(str(KEY_JS), int(VIEWER_JS))'
    );
    return JSON.parse(result);
  }

  throw new Error("Unknown worker request: " + message.type);
}

self.addEventListener("message", async (event) => {
  const { id, ...message } = event.data;
  try {
    const result = await handle(message);
    self.postMessage({ id, ok: true, result });
  } catch (error) {
    self.postMessage({
      id,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

boot()
  .then(() => self.postMessage({ type: "ready" }))
  .catch((error) => self.postMessage({
    type: "boot_error",
    error: error instanceof Error ? error.message : String(error),
  }));
