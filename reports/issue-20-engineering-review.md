# Issue #20 engineering review

Completed locally on 2026-09-24 for [issue #20](https://github.com/tpepels/The-Long-War/issues/20). The work began from `1c8d7ff`; the user's intervening `03223b3` commit contains the initial implementation and was preserved. Follow-up fixes remain in the working tree. `origin/main` was refreshed and PR #18 remains separate and open. No GitHub Actions runs were requested for this work.

## Problems fixed

### Rules, cards and browser

- Browser play had its own JavaScript rules and heuristic implementation. It now loads the actual Cython package compiled to WebAssembly through pinned Pyodide. The JavaScript adapter only transports session requests and snapshots. Native and browser play share privacy, mulligans and paced AI behavior.
- Card loading accepted malformed/unsupported machine rules, and raw in-memory input bypassed file validation. Both now share required-field, type, ID, effect, trigger and native-limit checks. Profiles resolve through `GameRules`; experiment fixtures require compatible profiles.
- Native buffers had unchecked capacity assumptions. Card identity capacity now accommodates the 96-card counterfactual pool, while deck, zone and action boundaries are checked. Supported limits are 127 identities, 64 cards per player deck and 1024 generated actions.
- Hidden-hand knowledge could be reconstructed from presentation history after canonical knowledge changed. `known_hidden_hand` is now authoritative; history receives deltas for display.
- Full-width observable values were truncated in information encoding. Encoding version 4 preserves battle, Command, operation and temporary-strength values; regressions distinguish states differing by 256 and check the public policy-ID conversion.
- Browser checks found a clipped long title and false overlap warnings on rotated cards. Fonts now fit the fixed title region; overlap checks use layout coordinates before transforms. The layout fixture uses the shared card role renderer.

### Search and learning

- Python alpha-beta cached cutoff bounds as exact values and omitted cleanup state from its cache key. Bound handling and identity now match the search contract.
- ISMCTS could retain estimates across changed belief evidence, evaluator settings or root-player perspective. Context changes now invalidate those statistics. Root samples must share an acting player and information set; controls reject invalid/non-finite values.
- Persistent arenas could grow with game length. They now have a configurable cap (default four times the iteration budget), use rollout leaves at capacity, and clear when an unseen root needs space. Visit/availability counters are 64-bit. Root choice uses lifetime visits within a valid context; telemetry separates inherited/new visits, discarded nodes, capacity cutoffs and reset reasons.
- Belief priors could select a deck incompatible with occupied hidden Scheme/Stratagem zones despite compatible alternatives. Conditioning now includes those constraints before deck construction.
- MCCFR had a broken information-store reference and incorrect external-sampling own-reach weighting. The Python, generic Cython, direct and packed traversal paths now agree on the regression. Unsafe negative indexing in Cython was removed. Kuhn-poker convergence passes.
- Shared heuristic evaluation had lost hidden-Stratagem option value and free-action handling. Both use canonical scoring/transition contracts, without reading the opponent's hidden card identity.

Progressive widening stays experimental and disabled by default. Its supported schedule is `k * sqrt(N + 1)`; alpha remains fixed at 0.5. Serious ISMCTS defaults remain 100,000 iterations, with explicit smaller smoke budgets supported.

### Analysis and provenance

- Triple counterfactual analysis omitted required pair interventions when pair output was disabled. Intervention construction is now independent of output selection.
- Targeted online follow-up regenerated different contexts from the broad sweep. It now preserves the broad required-card set, deterministic ordering, seeds, intervention families and mulligan conditions.
- Standard errors used the wrong variance denominator, and tiny constant samples could produce falsely certain bootstrap intervals. Sample variance and conservative bounded fallback intervals now expose the uncertainty; invalid bootstrap counts are rejected.
- Strength uncertainty treated mirrored games as independent. It now pairs outcomes by deal seed, retains per-game outcomes, and separates seed ranges between decks.
- Static diagnostics read historical annotations instead of machine rules. They now use canonical rule data. Health summaries are shared by Lab and MCCFR report builders.
- Lab aggregation could give stale or experimental evidence a current canonical fingerprint. It now rejects stale/unidentified sources and mismatched card/rule variants.
- Fingerprints missed native includes and experiment inputs. They now include runtime sources, card/deck fixtures and analysis entry points. Artifact directories distinguish sources and effective settings. Validation itself also uses this identity, so repeating it after a code change preserves prior results and succeeds.

## Consolidation and removals

The engine owns transitions and visibility; `GameRules` owns configuration; beliefs and shared evaluation remain outside algorithms. Python alpha-beta and generic MCCFR remain useful correctness references. Browser builds use an isolated source tree under `artifacts/browser/`, keeping host native extensions intact.

- Replaced the roughly 1,200-line duplicate implementation in `web/browser-engine.mjs` with session transport.
- Moved `tools/cardflow_experiment.py` into `src/longwar/cardflow.py`. The existing runner exposes its parser directly through `run`, without a forwarding script.
- Removed `tools/expanded_balance_validation.py`; its release-sized orchestration is covered by `run_experiments.py balance --preset deep`.
- Removed the unused packed MCCFR traversal that called a nonexistent engine API, obsolete serialization wrappers and old binary information-decoder branches.
- Removed duplicated report-summary and layout-fixture role logic.

Historical reports and useful experimental fixtures were retained. Generated contracts, policies, reports, toolchains and logs belong under ignored `artifacts/`; generated Pages output is `dist/`. README and AGENTS describe the resulting ownership and supported controls.

## Daily workflow

Use the activated project virtualenv; Python 3.14, Node.js and a native compiler support the complete browser workflow. The first browser build downloads the pinned cross-compilation toolchain; later builds reuse it.

| Change | Location | Local command |
| --- | --- | --- |
| Rule | `rules.py`, `_fast_search.pyx`, rulebook | `make native-build && make verify` |
| Card/deck | `cards/cards.json`, `decks/*.json` | `make verify-cards && make verify` |
| Algorithm/evaluator | Native algorithm include and its adapter | `make native-build && make verify-algorithms` |
| Quick balance/playability | Canonical inputs | `make balance-quick` |
| Deep release analysis | Canonical inputs | `make balance-deep` |

Add a focused regression for changed behavior. `make test-integration` verifies simulation/report composition. Native-only tooling also supports Python 3.11+; browser compilation requires 3.14. Browser play now has the initial download/startup cost of the Python/WebAssembly runtime.

## Local verification

Commands below ran with `.venv/bin` first on `PATH`. Counts for overlapping verification targets must not be added together.

| Exact command | Result |
| --- | --- |
| `make native-build` | Host extensions rebuilt successfully after native changes |
| `make test-fast` | 279 passed |
| `make test-integration` | 5 passed |
| `make test-algorithm` | 54 passed; 338 tests across the three disjoint tiers |
| `make ismcts-validate` | 65 passed |
| `python tools/run_experiments.py validate` | 137 focused tests passed; fixed-seed Python/Cython parity passed for automatic and paid draw |
| `python tools/run_experiments.py validate-data` | Both shipped 48-card sets and all eight decks validated and loaded into the engine |
| `make browser-parity` | 2 engine scenarios and 107 exact native/WebAssembly session snapshots passed |
| `make verify` | Combined data, fast and browser checks passed; later final tier counts are recorded above |
| `make verify-mccfr mccfr-smoke` | Kuhn: 30,000 iterations, value error 0.000146, exploitability 0.003261; policy training and five-game simulation completed |
| `python tools/check_card_layout.py --require-browser` | All 48 browser and 48 print cards fit, including rotated fixture coverage |
| `python tools/check_game_layout.py --require-browser` | Fits 1920×1080, 1440×900, 1366×768 and 1024×768 |
| `python tools/check_play_start.py --require-browser` | Human action, full-card inspection and delayed visible opponent response passed |
| `python tools/run_experiments.py balance --preset quick --games 2 --seed 1701` | Eight games and static/health/playability artifacts completed |
| `python tools/run_experiments.py balance --preset deep --games 1 --contexts 1 --games-per-context 1 --seed 1701` | 16 matchup games and 96 causal matches across all 48 cards completed |
| `python tools/run_experiments.py strength-bench --games 1 --jobs 2 --iterations 32 --alpha-nodes 64 --exploration 0.3` | Eight mirrored games completed; paired uncertainty and bounded-tree telemetry emitted |
| `git diff --check` | Passed |

Logs are under `artifacts/issue20-*.log`. Smoke outputs retain their own source fingerprints; some precede the final search-context and validation-path adjustments. They verify pipeline operation, not current strength or card balance. The final test tiers, search validation and native/WebAssembly parity cover the completed implementation.

## Questions requiring gameplay evidence

Correctness changes invalidate the historical cold/reused/PW strength comparison. Conservative belief invalidation and arena limits may reduce reuse and alter wall time, memory and strength. PW should remain optional until new full-game measurements justify it. Compare these matched configurations locally:

```bash
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3 --no-tree-reuse
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3
python tools/run_experiments.py strength-bench --games 8 --jobs 8 --iterations 100000 --exploration 0.3 --progressive-widening 1.0
```

Each runs 64 games over the four decks and two orientations. Inspect paired intervals and resource telemetry before selecting a configuration; larger samples may still be necessary.

Card-value evidence remains policy- and context-specific. Conditional wins when played are correlations. The release suite was deliberately not run at full scale; its exact command is:

```bash
python tools/run_experiments.py balance --preset deep --games 2000 --seed 1701 --contexts 3 --games-per-context 4
```

Use stronger targeted online follow-up on selected broad counterfactual artifacts before making card-design decisions. No rule or card-design change was made to improve benchmark outcomes.
