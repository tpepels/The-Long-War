# AGENTS.md

## Purpose

The Long War is a game first. Keep the repository easy to change while guaranteeing that browser play, simulations, AI/search, and analysis all consume the same game semantics.

Read `ARCHITECTURE.md` before structural work. Its ownership/dependency rules are enforced by `tests/test_architecture_boundaries.py`.

## Non-negotiable architecture

- There is one authoritative game engine for state, legal actions, transitions, scoring, visibility, and card effects.
- `GameRules` is configuration. Rule experiments use explicit `with_overrides(...)`; do not create a second engine or named rules implementation.
- Cards are data. `design_rules` is the only executable card-mechanics schema.
- Never special-case a canonical card id/title in engine, heuristic, or search code. New behavior requires a reusable mechanic/effect primitive.
- Decks are match input. Construction policy belongs in `decks.py`; shipped deck membership belongs only in `decks/index.json`.
- Do not duplicate configurable `GameRules` values in tools, tests, docs, or UI.
- AI/search consumes the game core; it may own search state/evaluation, never alternate game semantics.
- `simulate.py` is the single AI-vs-AI match loop.
- Browser adapters may depend on the core and production play agent, but not on telemetry, counterfactual, solver training, or Balance Lab modules.
- Dependency direction is one-way: content/configuration -> core -> consumers/adapters -> analysis.

Native rule composition lives in `_fast_engine_core.pxi`. Host search layers search on top. Browser builds include the same engine core plus only the production heuristic. Core Python reaches native transitions through `native_engine.py`; research agents use `native_search.py`.

## Browser and multiplayer boundary

Browser UI code is not a rules implementation.

- `web_api.PlaySession` adapts canonical engine state/actions to snapshots.
- `web/browser-engine.mjs` transports those calls through Pyodide.
- `web/play.js` renders snapshots and submits canonical action keys.
- `web/remote-peer.mjs` is transport only.

Remote play is host-authoritative. The host owns `PlaySession(mode="remote")`; the guest receives only its viewer-specific snapshot and sends action/mulligan requests back. Never trust guest state, duplicate rules in JavaScript, or expose the opponent's hidden snapshot to simplify networking.

The UI setup choices `remote-host` and `remote-join` are product states, not engine modes. The underlying application session mode is `remote`.

A signaling/rendezvous service or TURN relay may be added later, but it remains transport infrastructure unless a separate architectural decision explicitly moves game authority server-side.

## Browser static integrity

Cheap browser failures must be caught before deployment.

`tools/check_web_static.py` checks:

- JavaScript/module syntax;
- local HTML assets and module imports;
- `play.js` literal DOM ids;
- built `data/*.json` references;
- runtime/Pyodide references and wheel manifest.

`make browser-parity` runs these checks before and after the Pages build, then verifies browser/native behavior.

When adding or renaming a generated browser file, update producer and consumer together and add a focused contract regression.

## Command surface

Make is a small human-facing lifecycle surface. Do not add a target for a parameter combination, solver variant, experiment name, or convenience alias.

Supported targets:

```bash
make install
make native-build
make browser-build
make verify
make verify-algorithms
make test
make test-fast
make test-integration
make simulate
make balance
make experiments
make full-lab
make pages
make browser-parity
```

Variations use arguments:

```bash
make simulate SIMULATE_ARGS="..."
make balance BALANCE_PRESET=deep BALANCE_ARGS="..."
make experiments EXPERIMENT_ARGS="..."
make full-lab FULL_LAB_ARGS="..."
```

`make experiments` is the supported search-strength entry point. `make full-lab` is a distinct lifecycle operation for the complete resumable evidence/publication pipeline.

## Development rules

- Refresh current `main` before substantial writes and preserve unrelated changes.
- Work directly on `main` unless isolation is genuinely necessary.
- Change rules once in the canonical engine/configuration and verify every consumer.
- Add regressions at the semantic or contract boundary that changed.
- Prefer deleting obsolete paths over compatibility wrappers.
- Never introduce a second card/deck fixture merely to support an experiment.
- Experiment-only card variants use copied/in-memory overrides; never edit canonical card data just to run an ablation.
- Never add another runner when an existing orchestrator can accept a command/argument.
- Rebuild native extensions after changing `.pyx` or `.pxi`.
- Use small deterministic tests for plumbing; large simulations are evidence, not correctness tests.
- Generated reports, policies, builds, logs, toolchains, and stage markers live under `artifacts/` or `dist/`.
- The only versioned generated Balance Lab snapshots are `artifacts/lab-report.json` and `artifacts/balance-health.json`.
- Never commit native/wasm binaries.
- When a lifecycle command, ownership boundary, browser mode, or build contract changes, update the static maintainer docs too.

## Verification expectations

Typical verification:

- rules/native engine: focused test + `make native-build && make verify`;
- browser/session/UI/network transport: `make verify`;
- search/solver: `make native-build && make verify-algorithms`;
- print/rulebook pipeline: `make pages`;
- analysis/reporting plumbing: focused tests first; do not run expensive evidence automatically.

GitHub Actions remain deployment-only. The Pages workflow may run compile/static integrity checks required for a safe deploy, but no pytest suites, simulations, balance runs, MCCFR training, or research experiments belong there.

## AI/search

- Canonical ISMCTS defaults live in `DEFAULT_ISMCTS_*` constants in `agents/ismcts_agent.py`.
- Runners consume shared search defaults unless a publication workflow deliberately pins and records an explicit budget.
- Do not reintroduce optimizer sweeps/tournament configuration machinery without a concrete design need.
- The supported search-parameter evidence workflow is `make experiments EXPERIMENT_ARGS="ismcts-tournament ..."`: one-factor screening, independent-seed finalist round-robin, then independent baseline confirmation under equal wall-clock budgets.
- Alpha-beta is an occasional equal-wall-clock sanity check after parameter selection, not the optimizer opponent.
- Progressive widening remains experimental unless the shared baseline enables it.
- Tree reuse is valid only while belief/search context remains valid.
- Mirrored comparisons preserve candidate-specific RNG seeds across seat swaps.
- Do not promote a search configuration from tiny or historical samples.

Offline and online MCCFR are research/evidence tools unless explicitly promoted. The browser production AI is a separate product choice.

## Balance Lab discipline

Keep evidence types distinct:

- ISMCTS self-play: strategic progression/pacing;
- heuristic paired replacement: broad screening;
- online MCCFR: targeted confirmation;
- offline MCCFR: learned-policy evidence with visible fallback coverage;
- ISMCTS vs alpha-beta: solver/search-strength sanity check.

`make full-lab` is resumable. Stage reuse is keyed to current game fingerprint plus stage configuration; unrelated reporting/tooling edits must not retrain expensive policies. `--force` is the deliberate regeneration switch.

Do not change global rules or canonical card data merely to simplify an experimental diagnosis. Use explicit experiment overrides with provenance.

## Repository discipline

Do not solve architecture problems by adding more architecture. Prefer fewer permanent entry points, fewer named modes, and configuration passed through existing boundaries.

Historical reports and old generated artifacts are not current evidence. Verify fingerprints when current evidence matters.
