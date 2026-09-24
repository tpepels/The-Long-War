# The Long War

A two-player card game fought across three Fronts. Subjects occupy the line; Bonds and Names build on them; cards left in hand carry into later Battles.

**Subject → Bond → Name**, for example **The Fifty Men → Followed → Namar**.

## Setup and everyday commands

Use Python 3.14 for the complete workflow, including the browser build, plus Node.js, a C compiler, and `make`. Native tools also support Python 3.11+. The first browser build downloads a pinned Pyodide/Emscripten toolchain; subsequent builds reuse local caches.

```bash
python -m venv .venv
source .venv/bin/activate
make install
make verify
```

| Work | Edit | Verify |
| --- | --- | --- |
| Rule change | `src/longwar/rules.py` for configuration; `_fast_search.pyx` for transitions; update `rules/rulebook.md` | `make native-build && make verify` |
| Card addition/change | `cards/cards.json`; update appropriate `decks/*.json` | `make verify-cards` for immediate feedback, then `make verify` |
| Search/evaluation change | Algorithm's native `.pxi`, its Python adapter, or `_heuristic_core.pxi` | `make native-build && make verify-algorithms` |
| Quick balance/playability signal | Canonical cards and decks | `make balance-quick` |
| Release balance evidence | Canonical cards and decks | `make balance-deep` |

Add a focused regression at the changed boundary. `make verify` checks every shipped card/deck, the fast tests, and native/browser parity. `make verify-algorithms` runs learning/correctness tests plus fixed-seed Python/native alpha-beta comparisons and ISMCTS validation. `make test-integration` checks multi-game and report pipelines. `make test` runs every pytest test.

Rebuild after every `.pyx` or `.pxi` edit. Browser builds automatically detect changed package sources. The first browser build is slower; a current build is reused. No GitHub Actions run is needed for local verification.

## One rules engine

The canonical implementation is `src/longwar/_fast_search.pyx`. It owns legal actions, transitions, scoring, visibility, and the information-state encoder. `GameRules` in `rules.py` owns configuration and named profiles (`GameRules.profile_names()` / `from_profile()`). `game/engine.py` adapts Python dataclasses and action objects to this engine; it does not reimplement transitions.

The standard playtest uses 34-card decks and a 10-card opening/refill hand. Command starts at 20, gains 10 between Battles up to 20, and carries forward. At the start of every turn, draw 1 card automatically; then play one card or Pass when Pass is legal. Playing a card spends its printed Command cost. There is no generic Draw action and no standard Cycle action. Draw piles persist between Battles and the discard pile reshuffles only when a draw requires an empty deck. The first Pass gives the opponent exactly one final operation, then the Battle scores; the first passer starts the next Battle. Stratagems are public and active when played, and completing a formation refunds 1 Command. The four shipped deck templates contain 14 Subject-type cards and 6 printed Names. They now carry multiple distinct Heroes; each Hero is Unique, may be played as either a Subject or a Name, and each side may play only one Hero per Battle.

The static browser runs a WebAssembly build of the **same Cython package** through Pyodide. `web/browser-engine.mjs` only transports JSON to `web_api.PlaySession`; rules and AI live in the Python/Cython package. Hot-seat privacy, mulligans, and paced AI turns share the native session implementation.

```bash
make browser-parity   # build/cache wasm, build Pages, compare complete session traces
make pages
python -m http.server 8000 --directory dist
# Open http://localhost:8000/play.html
```

`tools/build_browser_runtime.py` pins Pyodide 314.0.7 and pyodide-build 0.39.1. Cross compilation uses an isolated source directory under `artifacts/browser/`, so it cannot replace host extensions. The runtime, wheel, toolchain environment, contracts and logs are generated artifacts. `dist/` is the generated Pages site. Both directories are ignored by Git.

The play client is a fixed desktop table, verified at 1280×720, 1366×768, 1440×900 and 1920×1080. Click a hand card, then a highlighted destination. Hover or focus lifts a card; click a selected card again, right-click, or press `I` while focused to inspect it. Inspection also works during mulligans. Select a hand card to see its legal plays and Command costs. `Esc` cancels/closes, `P` passes and `F` toggles fullscreen. Rules, piles, the log and New Match live in the game menu. Motion respects the browser's reduced-motion preference.

`web/play.css` owns the scene and card geometry; the client does not load website layout styles. `web/play.js` renders snapshots and routes legal actions. Its card motion compares visible snapshots, without predicting engine results. After UI changes, run:

```bash
make test-fast browser-parity
python tools/check_card_layout.py --require-browser
python tools/check_game_layout.py --require-browser
python tools/check_play_start.py --require-browser --viewport 1280x720
python tools/check_play_start.py --require-browser --viewport 1440x900 --reduced-motion
```

The [issue #21 desktop-client handoff](reports/issue-21-desktop-client.md) records the redesign, visual QA and remaining human-playtesting questions.

## Cards and fixtures

`cards/cards.json` is the canonical card pool. Each card has a stable unique `id`, title, type, classes, uniqueness, display text/rule blocks, and machine-readable `rules`. Preserve IDs when revising cards: decks and policy artifacts refer to them.

`cards.py` validates required fields, nested rule/effect/trigger names, types and native numeric limits. `make verify-cards` also checks printed Command costs against the canonical static cost model in `balance.py`. `GameEngine` applies the same validation to in-memory data, including browser input. Deck validation enforces size, copy limits and known IDs. Hero cards are Unique, so each Hero title is limited to one copy, while multiple different Heroes may share a deck. New effect kinds require explicit schema and native-engine support plus a regression; misspellings fail instead of silently producing vanilla cards.

The packed engine supports up to 127 card identities, 64 cards per player deck, and 1024 generated actions, with checked boundaries. Counterfactual neutral cards are generated in memory and never added to printable canonical data.

- `decks/*.json`: canonical reference and archetype decks.
- `cards/experiments/` and `decks/experiments/`: Force/Command card-flow fixtures, selected with matching named profiles.
- `reports/`: retained historical playtest analyses. They are context, not current balance evidence.
- `artifacts/`: generated local results, manifests, policies and build output.

Static strength diagnostics read machine rules, not the optional historical `balance` annotations. Display tooling renders authored rule blocks; it does not calculate game effects.

## Search contracts and supported experiments

| Responsibility | Implementation |
| --- | --- |
| Engine and information encoding | `_fast_search.pyx` |
| Shared heuristic / Battle-boundary evaluator | `_heuristic_core.pxi`, `heuristics.py` |
| Alpha-beta | `_alpha_beta_core.pxi`; `algorithms/alpha_beta.py` is the maintained Python reference |
| ISMCTS | `_ismcts_core.pxi`, `agents/ismcts_agent.py` |
| MCCFR | `_mccfr_core.pxi`, `_mccfr_accel.pyx`, `mccfr_core.py`; trainer in `mccfr.py` |
| Online MCCFR | `online_mccfr.py` over externally sampled beliefs |
| Hidden-state/deck priors | `belief.py` |

Algorithms consume engine/evaluator contracts without rule-profile branches. Beliefs stay outside traversal. MCCFR uses external sampling with depth-limited heuristic leaves and an imperfect-recall observation abstraction; a policy is not a full-game equilibrium proof. Generic Python/Cython traversal and the Kuhn-poker reference remain independent correctness checks. Replica multiprocessing is experimental because table serialization/merging can dominate runtime.

ISMCTS serious defaults use 100,000 iterations. UCT exploration is configurable; use explicit `--exploration 0.3` to reproduce the issue's comparison configuration. Progressive widening remains **off by default and experimental**: `k * sqrt(N + 1)`, with fixed alpha 0.5. There is no supported alpha knob.

Persistent trees now invalidate when observable belief evidence or search configuration changes. Retained root selection uses lifetime visits only within the valid context; diagnostics separate inherited and newly accumulated visits. Arenas are bounded (default four times the iteration budget); at capacity, search uses rollout leaves and clears on rerooting when needed. `ISMCTSAgent(max_tree_nodes=...)` can set a smaller cap. `--ismcts-no-tree-reuse` on the simulator and `--no-tree-reuse` on the strength benchmark provide cold-tree comparisons. Reuse/PW telemetry is diagnostic, not evidence that either improves strength.

The pre-audit 43–21 cold / 46–18 reused / 39–25 reused-with-PW results are historical. Corrected belief conditioning, reuse and evaluation require new measurements before claiming the same strength or reuse rate.

```bash
python tools/run_experiments.py --help
python tools/run_experiments.py search-bench --iterations 100000 --exploration 0.3
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3 --no-tree-reuse
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3 --progressive-widening 1.0
```

Strength artifacts preserve per-game seeds/outcomes, effective configuration, source fingerprints and paired uncertainty over mirrored deals. Different budgets/seeds/configurations use different artifact directories.

## Balance and analysis

`tools/run_experiments.py` is the main entry point. It composes existing analysis modules; specialized tools remain available for individual stages.

| Question | Command | Meaning |
| --- | --- | --- |
| Are data/decks valid? | `make verify-cards` | Schema, effects, legal decks, native loading |
| Does ordinary play run? | `make balance-quick` | Static report, 8 heuristic games per canonical deck, health and card flow |
| How do experimental draw profiles play? | `python tools/run_experiments.py run --preset quick --dry-run` | Inspect experimental Force/Command runs before spending compute |
| Which search is stronger? | `python tools/run_experiments.py strength-bench ...` | Mirrored ISMCTS/alpha-beta matches |
| What is a card's paired replacement value? | `python tools/counterfactual_balance.py --cards followed --contexts 3 --games-per-context 4 --no-pairs --no-triples` | Policy-specific causal replacement, with uncertainty |
| Does a selected effect survive stronger play? | `python tools/targeted_online_counterfactual.py --broad artifacts/counterfactual-balance.json` | Online MCCFR on the exact broad contexts/interventions |
| Release balance suite | `make balance-deep` | 2000 games per mirror/directed archetype cell, static/health/card flow, full per-card paired sweep |

Quick runs check plumbing and playability, not statistical balance. Deep runs are explicitly opt-in. Override sizes and seeds for development:

```bash
python tools/run_experiments.py balance --preset quick --games 2 --seed 1701
python tools/run_experiments.py balance --preset deep --games 2000 --seed 1701 --contexts 3 --games-per-context 4
python tools/run_experiments.py run --preset deep --variant experiment --deck all --jobs 8 --seed 26092334 --exploration 0.3
```

Outputs live under `artifacts/balance/<preset>/<identity>/`, `artifacts/cardflow/<preset>/<identity>/`, and `artifacts/search-benchmark/`. Each run saves configuration and source/card/deck fingerprints. An explicitly supplied card-flow output directory cannot silently mix different configurations.

`simulate.py` records action/card/pass/decision telemetry. `health.py` adds confidence-aware observational flags; `playability.py` summarizes card flow. `balance.py` handles static combinations. `counterfactual.py` estimates paired replacement and factorial contrasts; `targeted_counterfactual.py` preserves exact broad-sweep contexts for stronger follow-up. Lab builders aggregate these outputs and reject stale evidence.

“Win when played” is an observational correlation. It is not a card-value estimate. Paired replacements use identical focal seats, game/agent seeds and shuffle permutations. Uncertainty is reported explicitly; a singleton or constant tiny sample cannot establish certainty. Even a narrow interval is specific to the tested policy and deck contexts.

Full-pool causal analysis uses per-card sweeps because all cards/Heroes cannot fit in a legal deck. Selected compatible subsets can request pair/triple factorial analysis. Solver training/verification and targeted online analysis remain separate optional expensive stages:

```bash
make verify-mccfr
make mccfr-smoke
python tools/train_mccfr.py --iterations 5000 --depth 3 --workers 1 --output artifacts/mccfr-policy.json
```

Policies and old balance artifacts must be regenerated after fingerprint-changing rule, card, search or evaluation edits. Pages can display saved compatible evidence without rerunning deep analysis.

The [issue #20 engineering review](reports/issue-20-engineering-review.md) records the fixes, removed paths, exact local verification and remaining gameplay-data questions.
