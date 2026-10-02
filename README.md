# The Long War

The Long War is a two-player card game with one canonical rules engine shared by browser play, simulations, AI/search, and analysis.

This README is the developer entry point. Player-facing rules live in `rules/rulebook.md`; architecture and repository ownership rules live in `ARCHITECTURE.md` and `AGENTS.md`.

## Development setup

The complete workflow uses Python 3.14, Node.js, a C compiler, `make`, and Typst 0.15.1. Native Python development supports Python 3.11+, but the browser/Pyodide and Pages workflow currently target Python 3.14.

The first browser build downloads a pinned Pyodide/Emscripten toolchain. Later builds reuse local artifacts.

```bash
python -m venv .venv
source .venv/bin/activate
make install
make native-build
make verify
```

Rebuild the native extension after every `.pyx` or `.pxi` change.

## Supported command surface

Make is intentionally small. Parameter combinations belong in arguments, not new targets.

| Command | Purpose |
| --- | --- |
| `make install` | Install the editable package and development dependencies |
| `make native-build` | Rebuild the host Cython extension |
| `make browser-build` | Rebuild the browser/Pyodide runtime only |
| `make verify` | Canonical data validation, fast tests, browser static integrity, Pages build, and browser/native parity |
| `make verify-algorithms` | Search/solver correctness against the current canonical engine |
| `make test` | Full pytest suite |
| `make test-fast` | Fast non-algorithm, non-integration tests |
| `make test-integration` | Multi-game/report pipeline tests |
| `make simulate` | Configurable AI-vs-AI simulation |
| `make balance` | Canonical Balance Lab quick/deep/exhaustive pipeline |
| `make experiments` | Supported search-strength experiment entry point |
| `make full-lab` | Resumable complete Balance Lab publication workflow |
| `make browser-parity` | Browser build plus exact browser/native session parity |
| `make pages` | Build the static site and Typst rulebook PDF |

Common overrides:

```bash
make simulate SIMULATE_ARGS="--games 10 --seed 1701 --agent-a heuristic --agent-b heuristic"
make balance BALANCE_PRESET=deep BALANCE_ARGS="--agent ismcts --games 24 --jobs 8 --publish-lab"
make experiments EXPERIMENT_ARGS="--games 8"
make full-lab FULL_LAB_ARGS="--force"
```

## What to edit

| Change | Primary source | Normal verification |
| --- | --- | --- |
| Configurable match rule | `src/longwar/rules.py` | focused regression; rebuild native code if affected |
| Engine transition/effect primitive | `src/longwar/_fast_engine_*.pxi` under `_fast_engine_core.pxi` | `make native-build && make verify` |
| Card data/mechanics | `cards/cards.json` | `make verify` |
| Shipped deck membership | `decks/*.json`, catalogued by `decks/index.json` | `make verify` |
| Browser session adapter | `src/longwar/web_api.py` | `make verify` |
| Browser UI | `web/play.html`, `web/play.js`, `web/play.css` | `make verify` |
| Remote peer transport | `web/remote-peer.mjs` | `make verify` |
| Search/evaluation | search `.pxi`, agent adapters, heuristic core | `make native-build && make verify-algorithms` |
| Rulebook prose | `rules/rulebook.md` | `make pages` |
| Balance/reporting | analysis modules and tools | focused tests first; expensive evidence only when needed |

Add regressions at the semantic or contract boundary that changed. Do not duplicate a rule in several consumers just to make tests pass.

## Canonical engine

The canonical native engine composition is:

```text
src/longwar/_fast_engine_core.pxi
```

It owns packed state, legal actions, transitions, scoring, visibility, card effects, and information-state encoding. `GameRules` is configuration. `game/engine.py` is the Python-facing facade and reaches native rule execution through `native_engine.py`.

Search layers on top through `native_search.py`. The compiled extension layout is an implementation detail, not a second rules engine.

Cards and decks are inputs:

- `cards/cards.json` is the canonical card pool.
- `design_rules` is the only executable card-mechanics schema.
- `decks.py` owns construction validation.
- `decks/index.json` is the single catalogue of shipped/canonical deck profiles.

Configurable numeric rule values are deliberately not copied into developer docs. `GameRules.standard()` is the source of truth and generated rule/reference surfaces derive from it.

See `ARCHITECTURE.md` for the enforced dependency map.

## Browser architecture

The static web game uses the same canonical Cython engine through Pyodide.

The browser runtime intentionally contains only the game core, heuristic evaluation, Tactical AI, canonical ISMCTS, and `web_api.PlaySession`. Analysis, telemetry, counterfactual, solver training, MCCFR research, and Balance Lab code are excluded.

`web/browser-engine.mjs` is the JSON/Pyodide bridge. `web/play.js` renders snapshots and submits canonical action keys; it does not predict engine results.

### Play modes

The browser exposes:

- **Tactical AI** - fast local one-ply heuristic opponent;
- **Canonical AI** - the production ISMCTS opponent with canonical search defaults, including next-Battle rollout planning;
- **hot-seat** - two players sharing one browser;
- **remote host / remote join** - two browsers on different machines.

Remote play is host-authoritative:

1. Player 1 owns `PlaySession(mode="remote")`.
2. Player 2 receives only its viewer-specific snapshot.
3. Player 2 sends mulligan choices and canonical action keys back.
4. The host applies all transitions and returns a new redacted snapshot.

`web/remote-peer.mjs` is transport only. It contains no card, legality, or transition logic.

The current static deployment uses WebRTC with a manual invite-token/response-token handshake and STUN. There is no rendezvous service or TURN relay yet. A future short room code or relay therefore belongs to signaling/transport, not to the game engine.

## Browser verification

`make browser-parity` performs:

1. authored browser JS/module syntax checks;
2. HTML/module/DOM-id reference checks;
3. a Pages build;
4. built data/runtime/asset reference checks;
5. browser-engine contract generation;
6. browser/native session-trace parity.

The static checker can also be run directly:

```bash
python tools/check_web_static.py
python tools/check_web_static.py --dist dist
```

It catches missing generated data files, missing modules, malformed JavaScript, stale DOM ids, and broken runtime-manifest references.

For visual changes:

```bash
python tools/check_card_layout.py --require-browser
python tools/check_game_layout.py --require-browser
python tools/check_play_start.py --require-browser --viewport 1280x720
python tools/check_play_start.py --require-browser --viewport 1440x900 --reduced-motion
python tools/check_play_start.py --require-browser --remote-invite
```

Browser/Pyodide build logs live under `artifacts/browser/`; browser-parity output lives under `artifacts/logs/browser-parity.log`.

## Pages and printable rulebook

`tools/build_pages.py` builds the static site into `dist/`.

The printable rulebook is independent of browser pagination:

```text
rules/rulebook.md
  -> rule-token rendering from GameRules.standard()
  -> Markdown-to-Typst conversion
  -> dist/rulebook.typ
  -> Typst compile
  -> dist/rulebook.pdf
```

`tools/build_rulebook_pdf.py` owns and verifies that pipeline. `make pages` builds both the static site and PDF.

GitHub Pages is deployment-only infrastructure. The workflow performs compile/static build-integrity checks and publishes `dist/`; it does not run simulations, balance analysis, pytest research suites, or solver training.

## Balance Lab

`tools/run_experiments.py` is the main experiment orchestrator. `make balance` uses it for canonical quick/deep/exhaustive evidence.

`make full-lab` is the complete resumable publication workflow. It composes validation, Narrative/Command in-memory ablations, canonical deep ISMCTS balance/progression, broad heuristic paired screening, targeted online MCCFR, solver-strength evidence, six offline MCCFR policies/evaluations, MCCFR verification/suite assembly, and final Lab/Pages builds.

Completed stages are recorded under `artifacts/full-lab/stages/`. Reuse is keyed to the current **game fingerprint plus stage configuration**. The experiment fingerprint remains provenance, but unrelated presentation/tooling changes do not force expensive retraining. Use `--force` only for deliberate regeneration.

Keep evidence types distinct:

1. ISMCTS self-play - strategic progression/pacing.
2. Heuristic paired counterfactual - broad card screening.
3. Online MCCFR - targeted confirmation.
4. Offline MCCFR - learned-policy evidence with visible fallback coverage.
5. ISMCTS vs alpha-beta - search-strength sanity check.

They are not one balance score.

## Generated files and repository discipline

Generated material belongs under `artifacts/` or `dist/`.

- `dist/` is disposable Pages output.
- Browser toolchains, runtime builds, logs, raw reports, policies, and full-Lab stage markers are generated.
- The curated versioned Lab snapshots are `artifacts/lab-report.json` and `artifacts/balance-health.json`.
- Native/wasm binaries are never committed.
- Historical reports under `reports/` are context, not current evidence.

Work directly on `main` unless isolation is genuinely useful. Preserve unrelated changes and refresh current `main` before substantial writes.
