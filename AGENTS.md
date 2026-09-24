# AGENTS.md

## Goal

Keep The Long War easy to change at the surface and rigorous underneath. Rule changes, card additions, algorithm work, and balance experiments should each have one obvious implementation path and one obvious local verification path.

## Canonical architecture

- The Cython engine is the single source of truth for game rules and state transitions.
- `GameRules` owns rule/profile configuration. Search algorithms must not duplicate rule switches or rule logic.
- `cards/cards.json` is the canonical card database. Experimental card sets live under `cards/experiments/`.
- Browser compatibility may adapt the canonical engine, but must not create a second rules implementation.
- Belief construction stays outside search algorithms.
- The shared heuristic/evaluator remains separate from engine rules and is reused by search where appropriate.
- Native algorithms currently include alpha-beta, ISMCTS, and MCCFR. Preserve independent algorithm implementations, but share common engine/evaluation contracts rather than duplicating infrastructure.

## ISMCTS baseline

Treat these as measured baselines, not assumptions:

- Serious decisions use 100,000 iterations.
- UCT exploration near `0.3-0.5` is materially stronger than the old `sqrt(2)` default in current tests.
- `c=0.3`, cold tree, no progressive widening reproduced 43-21 vs alpha-beta over 64 games.
- Persistent tree reuse is implemented and currently looks promising, but has a measurable runtime/memory cost.
- Progressive widening is optional and experimental. Its coefficient is configurable; alpha is currently 0.5. Do not make it canonical without evidence.
- Battle-boundary rollouts stop at the Battle transition and use the canonical next-Battle evaluator.

## Balance and experiment tooling

The current tooling is powerful but spread across several entry points. Prefer consolidation over adding more scripts.

Important pieces include:

- `src/longwar/simulate.py`
- `src/longwar/telemetry.py`
- `src/longwar/balance.py`
- `src/longwar/health.py`
- `src/longwar/counterfactual.py`
- `src/longwar/targeted_counterfactual.py`
- `tools/run_experiments.py`
- `tools/cardflow_experiment.py`
- `tools/simulate.py`
- MCCFR benchmark/verification tools

Aim for a small public command surface that can answer:

1. Is the engine/ruleset valid?
2. Is a card/rule change structurally valid?
3. Did browser/native behavior remain compatible?
4. Did search algorithms remain correct?
5. What changed in playability/balance?
6. Is a result statistically meaningful or just noise?

Do not create another parallel experiment runner when an existing runner can be extended or simplified.

## Card and rule changes

A card addition/change should be easy to verify locally without understanding the entire analysis stack. The preferred flow should validate schema/IDs, deck legality, engine loading, affected rule semantics, browser/native parity where relevant, and a fast targeted simulation or balance smoke test.

A rule change should be made in the canonical rule/profile layer and engine only. Algorithms should observe the changed engine contract, not gain rule-specific branches. Add focused regression tests at the rule boundary and only add algorithm tests when the algorithm contract itself changes.

## Repository maintenance

- Prefer fewer, stronger modules and commands over wrappers that only forward arguments.
- Remove dead/obsolete experiment code when replacing it.
- Keep experimental outputs under `artifacts/`; do not commit bulky generated results unless intentionally retained as fixtures.
- Keep README/Makefile/AGENTS instructions aligned with the actual supported workflow.
- Preserve reproducible seeds and configuration metadata in benchmark artifacts.
- Keep benchmark configurations separated so one experiment cannot silently overwrite another.

## Local verification

Do not rely on GitHub Actions for routine development. The Actions budget is constrained. Run local checks and report exact commands/results.

After any `.pyx` or `.pxi` change:

```bash
git pull
make native-build
```

Core local checks should stay simple. Prefer consolidating toward one fast command for ordinary changes and one deeper command for algorithm/balance changes.

Current useful commands include:

```bash
make test-fast
make test-integration
make browser-parity
make ismcts-validate
python tools/run_experiments.py validate
```

## Working style

Before writing, refresh current `main`, recent commits, and open PRs. There may be concurrent agents. Avoid overwriting unrelated work, especially open PR #18 unless that work has already been merged or explicitly superseded.

For large cleanup/refactor work:

1. inspect first;
2. identify duplicated responsibilities and brittle paths;
3. preserve behavior with tests;
4. consolidate;
5. run local validation;
6. document the resulting simple workflow.

The desired end state is a small, obvious developer surface with enough depth underneath to support serious search, simulation, and balance analysis.
