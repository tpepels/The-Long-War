# AGENTS.md

## Goal

Keep one obvious implementation path and local verification path for rules, cards, algorithms and balance analysis. Fix problems with regressions; prefer removing dead paths to restoring migration wrappers. Read README.md for the supported command surface.

## Canonical architecture

- `_fast_search.pyx` owns rules, transitions, visibility and information encoding. `game/engine.py` is a dataclass/action adapter.
- `GameRules` in `rules.py` owns configuration, profile names and profile lookup. Select profiles in tools; do not duplicate their switches.
- `cards/cards.json` is canonical; experiment fixtures live under `cards/experiments/` and `decks/experiments/`. `cards.py` validates both files and in-memory input. New effect names require schema and native support.
- Browser play uses the same Cython package compiled to WebAssembly through Pyodide. `web/browser-engine.mjs` is transport only; `web_api.PlaySession` owns session/privacy/pacing adaptation. Never add JavaScript rules or AI policy.
- `_heuristic_core.pxi` owns shared evaluation separately from rules. Search algorithms consume engine/evaluator interfaces without rule-specific branches.
- `_alpha_beta_core.pxi`, `_ismcts_core.pxi`, `_mccfr_core.pxi` own native algorithms. Python alpha-beta and generic MCCFR traversal are maintained correctness references, not alternate rules engines.
- Belief construction and observation-conditioned deck priors live in `belief.py`, outside search.
- `known_hidden_hand` is canonical knowledge. `ObservationEvent` is a presentation/history log, not another knowledge source.

## Supported workflow

Use Python 3.14 for browser builds, Node.js, a native compiler and make. Activate `.venv` after `make install`.

```bash
make native-build       # required after every .pyx/.pxi change
make verify-cards       # all shipped schemas/decks/native loading
make verify             # data + fast tests + browser/native parity
make verify-algorithms  # learning/correctness + fixed-seed search validation
make test-integration   # simulation/report integration
make balance-quick      # small canonical playability/health check
make balance-deep       # opt-in release-sized balance pipeline
```

`make browser-parity` builds/caches the wasm wheel and compares native/wasm rules plus complete browser session traces. `tools/build_browser_runtime.py` pins runtime/build-tool versions and isolates cross compilation under `artifacts/`. Rebuild automatically when package sources change. Do not commit wasm/native binaries or downloaded toolchains.

Add regressions at the changed semantic boundary. Use small deterministic smoke runs to validate plumbing; do not run massive experiments to substitute for a correctness test. Keep exact larger benchmark commands in README and report exact local commands/results. Do not spend GitHub Actions budget for issue #20.

## ISMCTS

- Serious default: 100,000 iterations; explicit smoke overrides are supported.
- Historical c=0.3 results in issue #20 predate correctness fixes and must be remeasured.
- Progressive widening is experimental, disabled by default, with configurable coefficient and fixed alpha=0.5. Do not make it canonical without strength evidence.
- Battle-boundary rollouts use the shared next-Battle evaluator.
- Reuse is permitted only under a valid belief/search context. New hidden information invalidates accumulated statistics. Keep inherited/new visits and discarded nodes distinguishable.
- Root selection uses lifetime visits within a valid context. Default arena cap is four times iteration budget; at capacity search rolls out and resets on reroot as needed. Keep allocation growth bounded.

## Analysis ownership

- `simulate.py` and `telemetry.py`: games, per-game seed/outcome provenance, observations and decision metrics.
- `balance.py`: static diagnostics from machine rules.
- `health.py` and `playability.py`: observational uncertainty/flags and card flow.
- `counterfactual.py` and `targeted_counterfactual.py`: paired causal replacement/factorial analysis and stronger follow-up using identical broad contexts.
- `tools/run_experiments.py`: supported orchestration, validation, canonical balance and search benchmarks.
- `cardflow.py`: experimental Force/Command scheduling/reporting, exposed through the runner's `run` subcommand.
- Lab/Pages builders aggregate or render; they do not reimplement analysis or card semantics.

Keep policy-specific causal estimates separate from conditional-win correlations. Bootstrap mirrored deals as pairs. Do not give statistically certain labels to single/constant tiny samples. Save seeds, effective settings, source/card/deck fingerprints and per-game outcomes. Different configurations must not silently overwrite each other. Fingerprints include native `.pxi` files and analysis entry points; stale reports/policies require regeneration.

## Repository and concurrency

Refresh origin/main, recent commits and open PRs before substantial writes. Preserve unrelated user edits/commits. PR #18 is separate unless merged or explicitly reconciled; do not absorb its game-design changes.

`reports/` contains useful historical analyses. Canonical and experimental card/deck fixtures remain separate. Generated reports, policies, contracts, logs and toolchains belong under `artifacts/`; Pages output is `dist/`. Both are ignored. Do not add a new parallel experiment runner or compatibility wrapper when an existing interface can be fixed.
