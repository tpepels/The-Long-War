# AGENTS.md

## Purpose

The Long War is a game first. Keep the **physical game**, **print presentation**, **runtime engine/webgame**, and **AI/balance research** as distinct workstreams.

Read `WORKSTREAMS.md` before choosing a branch or PR scope. Read `ARCHITECTURE.md` before structural software work. Runtime ownership/dependency rules are enforced by `tests/test_architecture_boundaries.py`.

The physical card/rule design may temporarily lead the runtime implementation. When it does, do not force engine changes into the same PR and do not duplicate missing engine behavior in JavaScript. Treat the webgame as experimental until the linked engine-sync work is complete.

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
- Use the workstream branch prefixes in `WORKSTREAMS.md` for substantive work; keep PRs single-purpose.
- Physical cards/rules are authored independently of runtime implementation. Do not require an engine change merely to merge a physical playtest change.
- When implementing authored mechanics in software, change runtime semantics once in the canonical engine/configuration and verify every executable consumer.
- Add regressions only for durable semantic or contract boundaries. Tests must not freeze temporary card balance, prose, naming, deck composition, or visual design.
- If an intentional design change makes a design assertion obsolete, update or delete that assertion instead of preserving the old design to keep tests green.
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

Read `TESTING.md` before adding or tightening tests. During active design, tests are guardrails rather than a second ruleset.

Typical verification:

- rules/native engine: focused semantic tests when implementing runtime behavior;
- browser/session/UI/network transport: focused behavior/static checks;
- search/solver: `make native-build && make verify-algorithms`;
- print/rulebook pipeline: `make pages`;
- evolving card/rulebook/layout expectations: advisory `pytest -m design`;
- analysis/reporting plumbing: focused tests first; do not run expensive evidence automatically.

`make test-fast` excludes `design` assertions. GitHub Pages must never be blocked by pytest, balance, simulation, algorithm, or browser-layout diagnostics; it blocks only on source/static integrity and the ability to build deployable artifacts. The Code checks workflow has a small blocking sanity job and a separate advisory diagnostics job.

## AI/search

- Canonical ISMCTS defaults live in `DEFAULT_ISMCTS_*` constants in `agents/ismcts_agent.py`.
- Search-strength evidence produced before the playtest-overhaul engine is historical only. The old coarse screen found high UCT exploration harmful, belief count 4 promising, and rollout depth 12 promising, but none of those directions may be promoted for the rewritten game until the migrated engine is verified and the equal-time screen is rerun.
- Runners consume shared search defaults unless a publication workflow deliberately pins and records an explicit budget.
- Do not reintroduce optimizer sweeps/tournament configuration machinery without a concrete design need.
- The supported search-parameter evidence workflow is `make experiments EXPERIMENT=ismcts-tournament EXPERIMENT_ARGS="..."`: the default `coarse` design screens a broad one-factor set with widely spaced values on representative decks with multiple mirrored deals per deck - "coarse" refers to parameter spacing, not tiny evidence samples. `--design refine --refine-profiles ...` combines/refines only nominated directions on broader evidence, and `--design full` retains the legacy exhaustive interaction/finalist/confirmation machinery. All strength comparisons use equal wall-clock budgets.
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

The persistent-board playtest deliberately removed automatic lost-Front Retreat. Legacy printed clauses phrased as "instead of Retreating" must not be silently reinterpreted as direct drive-offs. Explicit card-effect Retreats remain live; redesign of the affected legacy cards is deferred until fresh post-overhaul evidence.

## Repository discipline

Do not solve architecture problems by adding more architecture. Prefer fewer permanent entry points, fewer named modes, and configuration passed through existing boundaries.

New branches should use `game/`, `print/`, `web/`, `engine/`, `ai/`, `balance/`, `research/`, or `docs/`. Do not create new generic `fix-*`, `cleanup/*`, or agent-named branches.

Historical reports and old generated artifacts are not current evidence. Verify fingerprints when current evidence matters.
