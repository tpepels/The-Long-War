# The Long War

A head-to-head card game about building legends across a physical battlefield.

The core grammar is:

**Subject → Link → Name**

Example: **The Fifty Men → Followed → Namar**

## Repository roles

- `cards/cards.json` — canonical card database: visible text plus machine-readable rules.
- `decks/` — reproducible test and reference decks.
- `rules/rulebook.md` — canonical printable rules.
- `src/longwar/game/` — deterministic rules engine.
- `src/longwar/agents/` — random, heuristic, and MCCFR policy agents.
- `src/longwar/mccfr.py` — external-sampling Monte Carlo CFR trainer and information abstraction.
- `src/longwar/telemetry.py` — game, card, pass, and Legend telemetry.
- `src/longwar/health.py` — confidence-aware balance flags and health analysis.
- `src/longwar/balance.py` — static balance diagnostics.
- `src/longwar/simulate.py` — repeated game simulation.
- `web/` — static source for the printable GitHub Pages site and Balance Lab.
- `tools/` — CLI entry points.
- `.github/workflows/` — CI, balance diagnostics, and Pages deployment.

The printed cards, engine, search algorithms, and balance tooling consume the same canonical card database.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

python tools/balance_report.py
python tools/simulate.py --games 1000 --agent-a heuristic --agent-b heuristic
python tools/analyze_telemetry.py
python tools/train_mccfr.py --iterations 50 --depth 3
python tools/build_pages.py
```

## Testing

Install the development dependencies once:

```bash
make install
```

Then use the test tiers independently:

```bash
make test-fast         # deterministic unit/rules tests
make test-algorithm    # MCCFR learning/correctness tests
make test-integration  # multi-game simulation and telemetry tests
make test              # everything
make check             # everything plus reports and Pages build
```

The MCCFR algorithm suite contains a controlled final-Battle state in which **Pass** is provably the winning action while several alternative plays remain legal. Training from that fixed state must drive regret matching above 90% probability for Pass. A second test verifies deterministic reproducibility from the same seed.

For an executable MCCFR end-to-end smoke test:

```bash
make mccfr-smoke
```

This trains a small policy artifact and immediately uses it in complete matches against the heuristic agent.

GitHub CI runs the fast, algorithm, and integration suites as separate named steps on every push and pull request.


## MCCFR

The repository implements **depth-limited external-sampling Monte Carlo Counterfactual Regret Minimization**.

For every sampled root deal:

1. chance is sampled by shuffling both decks and drawing the private opening hands;
2. training traverses once for each player;
3. at the traverser's information sets, every legal action is expanded and counterfactual regrets are updated;
4. at the opponent's information sets, one action is sampled from regret matching;
5. sampled-path opponent strategies are accumulated into the exported average policy;
6. at the configured depth frontier, the public-information heuristic state evaluator supplies a bounded continuation value.

The information set contains public battlefield/discard information, the acting player's own hand and remaining-deck multiset, public hand/deck counts, and only information the player is allowed to know about Schemes. It never contains opponent hand identities or deck order.

### Explicit approximations

The current solver is intentionally transparent about two approximations:

- **Depth-limited solving.** It converges toward the truncated game induced by the frontier evaluator, not yet the exact full match.
- **State abstraction / imperfect recall.** The information key describes the currently observable state rather than preserving the entire action-observation history.

The exported policy records these limitations in its metadata. The next solver work should measure information-set coverage, raise depth/iteration budgets, and eventually compare against a perfect-recall history abstraction on smaller subgames.

Train:

```bash
python tools/train_mccfr.py \
  --iterations 50 \
  --depth 3 \
  --output artifacts/mccfr-policy.json
```

Evaluate the learned table with heuristic fallback for unseen information sets:

```bash
python tools/simulate.py \
  --games 100 \
  --agent-a mccfr \
  --policy-a artifacts/mccfr-policy.json \
  --agent-b heuristic
```

## Heuristic agent

The heuristic player performs one-ply lookahead across every legal action. Its evaluation uses Front control, Strength margins, Victory markers, public hand-size advantage, completed Legends, own-hand completion potential, and pass/card-conservation value. It never evaluates the identities of cards in the opponent's hand.

The same public-information evaluator is used only at MCCFR depth frontiers.

## Telemetry and Balance Lab

Simulations record card playability, immediate board swing, pass behavior, completed Legends, conditional outcomes, and decision statistics. The health analyzer adds Wilson 95% intervals, minimum-evidence thresholds, within-type z-scores, and diagnostic flags.

GitHub Pages publishes:

- printable cards;
- printable rulebook;
- the Balance Lab generated from fresh heuristic self-play.

## Balance pipeline

The automated stack is now:

1. static Subject–Link–Name combinatorial analysis;
2. deterministic full-match engine;
3. heuristic self-play;
4. extended telemetry;
5. confidence-aware health analysis;
6. **depth-limited external-sampling MCCFR**;
7. MCCFR-policy evaluation against the heuristic baseline.

Planned next layers:

8. double-oracle deck/meta search;
9. counterfactual card replacement experiments;
10. marginal/Shapley interaction analysis.

Static outliers, conditional win rates, heuristic values, and shallow MCCFR policies are diagnostics, not automatic balance verdicts.
