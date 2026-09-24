// Transport only: the same Cython engine and Python PlaySession run in native
// tools and in Pyodide. Keep game rules and AI policy out of this adapter.
let runtimePromise = null;
let runtime = null;
let sessionType = null;

export function initializeBrowserEngine(options = {}) {
  if (runtimePromise) return runtimePromise;
  runtimePromise = (async () => {
    let pyodide = options.pyodide;
    let wheel = options.wheelBytes;
    if (!pyodide) {
      const runtimeURL = new URL("./runtime/", import.meta.url);
      const { loadPyodide } = await import(new URL("pyodide.mjs", runtimeURL).href);
      pyodide = await loadPyodide({ indexURL: runtimeURL.href });
      const response = await fetch(new URL("longwar-runtime.json", runtimeURL), { cache: "no-store" });
      if (!response.ok) throw new Error("Could not load the game runtime manifest.");
      const manifest = await response.json();
      const wheelURL = new URL(manifest.wheel, runtimeURL);
      wheelURL.searchParams.set("v", manifest.source_fingerprint);
      const wheelResponse = await fetch(wheelURL);
      if (!wheelResponse.ok) throw new Error("Could not load the game engine.");
      wheel = await wheelResponse.arrayBuffer();
    }
    if (wheel) {
      const sitePackages = pyodide.runPython("import site; site.getsitepackages()[0]");
      pyodide.unpackArchive(wheel, "zip", { extractDir: sitePackages });
      pyodide.runPython("import importlib; importlib.invalidate_caches()");
    }
    runtime = pyodide;
    const module = runtime.pyimport("longwar.web_api");
    sessionType = module.PlaySession.copy();
    module.destroy();
    return runtime;
  })().catch((error) => {
    runtimePromise = null;
    throw error;
  });
  return runtimePromise;
}

export class BrowserSession {
  constructor(cardData, deckPayload, mode = "heuristic", seed = 1) {
    if (!sessionType) throw new Error("The game engine is still loading.");
    this.session = sessionType(JSON.stringify(cardData), JSON.stringify(deckPayload), mode, Number(seed), true);
  }

  snapshot(viewer = null) {
    // JS null is a distinct JsNull object in Pyodide; omit the argument for None.
    return JSON.parse(viewer === null
      ? this.session.snapshot_json()
      : this.session.snapshot_json(viewer));
  }

  view(viewer) {
    return this.snapshot(viewer);
  }

  act(key, viewer) {
    return JSON.parse(this.session.act_json(key, viewer));
  }

  mulligan(indices, viewer) {
    const selection = runtime.toPy(indices);
    try {
      return JSON.parse(this.session.mulligan_json(selection, viewer));
    } finally {
      selection.destroy();
    }
  }

  aiStep() {
    return JSON.parse(this.session.ai_step_json());
  }

  destroy() {
    this.session.destroy();
  }
}
