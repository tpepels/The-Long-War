import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import { BrowserSession, initializeBrowserEngine } from "../web/browser-engine.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const runtimePath = path.join(root, "artifacts/browser/runtime");
const manifest = JSON.parse(fs.readFileSync(path.join(runtimePath, "longwar-runtime.json"), "utf8"));
const { loadPyodide } = await import(pathToFileURL(path.join(runtimePath, "pyodide.mjs")).href);
const pyodide = await loadPyodide({ indexURL: runtimePath + path.sep });
await initializeBrowserEngine({
  pyodide,
  wheelBytes: new Uint8Array(fs.readFileSync(path.join(runtimePath, manifest.wheel))),
});

const cards = JSON.parse(fs.readFileSync(path.join(root, "cards/cards.json"), "utf8"));
const deck = JSON.parse(fs.readFileSync(path.join(root, "decks/reference.json"), "utf8"));
const contractIndex = process.argv.indexOf("--contract");
const contractPath = contractIndex < 0
  ? path.join(root, "artifacts/browser-engine-contract.json")
  : process.argv[contractIndex + 1];
assert(contractPath, "--contract requires a path");
const contract = JSON.parse(fs.readFileSync(contractPath, "utf8"));

// Use the same projection/replay helper on both architectures. All rule work
// below executes in the wasm build of longwar._fast_search.
pyodide.FS.mkdirTree("/tools");
pyodide.FS.writeFile("/tools/build_browser_contract.py", fs.readFileSync(path.join(root, "tools/build_browser_contract.py")));
pyodide.runPython("import sys; sys.path.insert(0, '/tools')");
const checkerModule = pyodide.pyimport("build_browser_contract");
const scenarios = checkerModule.check_engine_contract_json(JSON.stringify(cards), JSON.stringify(contract));
checkerModule.destroy();
let snapshots = 0;
for (const trace of contract.sessions) {
  const session = new BrowserSession(cards, deck, trace.mode, trace.seed);
  try {
    for (const [index, step] of trace.steps.entries()) {
      assert.deepStrictEqual(session[step.method](...step.args), step.snapshot,
        `${trace.mode} seed ${trace.seed}, step ${index} (${step.method})`);
      snapshots += 1;
    }
  } finally {
    session.destroy();
  }
}
console.log(`PASS: canonical wasm/native parity: ${scenarios} engine scenarios, ${snapshots} session snapshots (${contract.game_fingerprint})`);
