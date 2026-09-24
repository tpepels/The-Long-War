# AGENTS.md

## Goal

The Long War is a game first. Keep the codebase easy to change while guaranteeing
that browser play, simulations, and AI all use the same game semantics.

Read `ARCHITECTURE.md` before structural work. Its dependency rules are enforced
by `tests/test_architecture_boundaries.py`.

## Non-negotiable architecture

- There is one authoritative game engine for rules, legal actions, transitions,
  scoring, visibility, and card effects.
- `GameRules` is configuration. Prefer tunable constants and
  `with_overrides(...)` for experiments; do not create another rules engine or
  another named mode for a parameter combination.
- Cards are data. Ordinary new cards should not require algorithm or UI changes.
- Never special-case a card id/title in engine, heuristic, or search code. If a
  card needs new behavior, add a reusable capability/effect primitive to the
  card schema and canonical engine so all consumers see it.
- Decks are match input, separate from rules. Reference/archetype decks are not
  engine constants and must not leak into core code.
- AI/search consumes the engine. It never reimplements rules or branches on
  individual `GameRules` fields.
- Browser code adapts the game core and the chosen play agent. It must not depend
  on analysis, telemetry, training, counterfactual, or solver-research modules.
- Simulation is the single AI-vs-AI match loop. Analysis consumes simulations;
  it does not create alternate game loops.
- Dependency direction is one-way: content -> core -> consumers -> analysis.
  Nothing points back toward analysis or a particular experiment.

The current native extension still physically bundles engine and search cores.
Treat that as cleanup debt, not as permission to couple their semantics.

## Command surface

Make is deliberately small. Do not add a target for a parameter combination,
solver variant, experiment name, or convenience alias.

Supported lifecycle commands:

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
make pages
make browser-parity
```

Variations use arguments:

```bash
make simulate SIMULATE_ARGS="..."
make balance BALANCE_PRESET=deep BALANCE_ARGS="..."
make experiments EXPERIMENT=ismcts-match EXPERIMENT_ARGS="..."
```

`make experiments` defaults to the canonical search suite and keeps the machine
awake with `systemd-inhibit`. The runner, not Make, owns experiment defaults.

## Development rules

- Change rules once in the canonical engine/configuration and verify every
  consumer against them.
- Add regressions at the semantic boundary that changed.
- Prefer deleting obsolete paths over compatibility wrappers.
- Never introduce a second card/deck fixture merely to support an experiment.
- Never add a new runner when an existing runner can accept another argument.
- Generated reports, policies, build products, logs and toolchains live under
  `artifacts/`; Pages output lives under `dist/`.
- Do not commit native/wasm binaries or generated artifacts.
- Rebuild native extensions after changing `.pyx` or `.pxi`.
- Use small deterministic tests to validate plumbing; large simulations are
  evidence, not correctness tests.

## AI/search

- Serious ISMCTS default: 100,000 iterations.
- Current provisional exploration constant: 0.3.
- Progressive widening remains experimental and off by default.
- Tree reuse is valid only while the belief/search context remains valid.
- Mirrored strength comparisons preserve candidate-specific RNG seeds across
  seat swaps.
- Equal wall-clock comparisons are the relevant cross-algorithm evidence.
- Do not promote an AI configuration to production from tiny or historical
  samples.

Search implementations may have their own trees, beliefs, evaluators and
performance code, but all legal actions and transitions come from the engine.

## Repository discipline

Work directly on `main` unless isolation is genuinely necessary. Preserve
unrelated user changes. Before substantial writes, refresh current `main` and
open PR state.

Do not solve architecture problems by adding more architecture. Prefer fewer
entry points, fewer permanent modes, and configuration passed through existing
boundaries.
