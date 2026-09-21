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
- `src/longwar/belief.py` — observation-conditioned hidden-state and deck-construction priors.
- `src/longwar/online_mccfr.py` — online information-set re-solving across sampled beliefs.
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

## v0.1 playtest build

The repository now publishes a playable first human-test build:

- **Browser play:** `play.html` runs the canonical Python `GameEngine` in the browser through Pyodide. Modes are hot-seat Human vs Human, Human vs heuristic, and Human vs online MCCFR.
- **Hot-seat privacy:** hands stay hidden between turns until the next player explicitly reveals their hand.
- **Printable kit:** `playtest-kit.html` prints two complete 30-card reference decks.
- **Battlefield/reference:** `playmat.html` is an A4-landscape battlefield with the six Subject positions, Scheme spaces, Battle line, scoring summary, and Victory boxes.
- **Four initial Schemes:** The Lamps Went Dark, The Road Was Cut, The Hidden Oars, and The Witness Lied.

The browser UI does not duplicate game rules in JavaScript. Pages publishes the tested Python package as a source bundle and Pyodide imports that package directly, so `GameEngine.legal_actions()`, `GameEngine.apply()`, scoring, Scheme triggers, and AI play are shared with CI and simulation.

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
make verify-mccfr      # formal Kuhn-poker MCCFR verification
make check             # everything plus reports and Pages build
```

The MCCFR algorithm suite contains two independent correctness checks:

1. a controlled Long War final-Battle state in which **Pass** is provably the winning action while several alternative plays remain legal; training must drive regret matching above 90% probability for Pass;
2. a formal reference benchmark on **Kuhn poker**, using the exact same shared external-sampling traversal as the Long War solver. Kuhn poker has known game value `-1/18`; CI fails if learned value error or exploitability exceeds fixed thresholds.

A second fixed-state test also verifies deterministic reproducibility from the same seed.

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

### Online re-solving and belief sampling

The online agent does not depend on an offline table matching the current private
hand. Before every non-forced decision it:

1. conditions on the acting player's public observation and own private cards;
2. replays retained observation knowledge, including publicly seen cards that
   later returned to a hidden hand;
3. conditions a deck prior on public cards plus guaranteed hidden-card facts;
4. samples a legal opponent deck composition, then a compatible hidden
   hand/deck/Scheme partition;
5. reshuffles the acting player's unknown future deck order;
6. repeats external-sampling MCCFR over those determinizations while merging
   them at the same root information set;
7. selects from the locally solved average root strategy, then discards the
   local regret table.

This gives root policy coverage by construction instead of hoping an offline
table has previously encountered the exact information set.

The default online belief model no longer receives the opponent's true
decklist. It uses a legal card-pool prior derived from deck-construction rules.
A weighted `HypothesisDeckPrior` is also available for an externally supplied
metagame distribution. Incompatible deck hypotheses are eliminated by observed
card counts.

`GameState` now retains epistemic observation events. If a public Name is
returned to a hand, the opponent remembers that guaranteed hidden card until
public play or another observable transition invalidates the certainty. These
facts are part of the information-set hash and are enforced in every sampled
determinization.

Face-down actions are updated conservatively from public information only: the
knowledge tracker never consults the simulator's actual hidden identity to
decide what the opponent should know. Tests compare states with different true
hidden partitions to enforce this non-leakage property.

Run an online benchmark with:

```bash
python tools/simulate.py \
  --games 20 \
  --agent-a online_mccfr \
  --agent-b heuristic \
  --online-iterations 8 \
  --online-depth 2
```

Evaluate the learned offline table with heuristic fallback for unseen information sets:

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

## Counterfactual card value

The balance pipeline includes paired causal replacement experiments. Each
canonical card is compared with a generated neutral same-type baseline while
keeping the game seed, focal seat, agent seeds, and shuffle index permutation
identical.

Experimental baselines are never added to the printable card set:

- Subject: vanilla 4 Strength;
- Link: vanilla +3 Strength while complete;
- Name: vanilla 2 Strength;
- Plot: universally playable no-op Plot.

For card `c`, the reported causal effect is:

```text
ΔWP(c) = win(base deck) - win(deck with one c replaced)
```

Pair interactions use the second-order factorial contrast:

```text
I(a,b) = f(ab) - f(a0) - f(0b) + f(00)
```

Subject–Link–Name triples use the corresponding third-order factorial
contrast. Confidence intervals are paired percentile-bootstrap intervals over
per-game contrasts, so common random numbers reduce noise rather than comparing
two unrelated win-rate samples.

Run locally:

```bash
python tools/counterfactual_balance.py \
  --contexts 3 \
  --games-per-context 4
```

The current causal estimates are policy-specific: the automated full sweep uses
the heuristic policy because thousands of matched games are required. The
framework records this explicitly and does not present the result as an
equilibrium value.

## Targeted online-MCCFR validation

The broad heuristic counterfactual sweep is intentionally cheap enough to test
all cards, all 153 pairs, and all 120 Subject–Link–Name triples. It now feeds a
second, selective stage.

Targets are nominated when their paired heuristic effect is large, receives a
yellow/orange/red causal level, or its paired interval excludes zero. Only the
highest-priority candidates are then rerun with **online MCCFR**.

For each selected card, pair, or triple, the online stage evaluates the exact
factorial intervention family required for that contrast. It reuses a subset of
the broad experiment's deck contexts, focal seats, and game seeds.

To avoid condition leakage, the non-focal player receives the same uniform deck
hypothesis prior over *all* factorial variants of the focal deck in every
condition. It therefore knows which intervention family is under study, but is
never told which variant is active. The focal player's belief over the opponent
still uses the generic legal-card-pool prior.

Validation labels are:

- **confirmed** — online 95% interval excludes zero in the same direction;
- **reversed** — online 95% interval excludes zero in the opposite direction;
- **direction agrees** — same sign, but online evidence is not yet conclusive;
- **inconclusive** — no stable directional agreement.

Run locally after the broad report:

```bash
python tools/targeted_online_counterfactual.py \
  --broad artifacts/counterfactual-balance.json \
  --contexts 2 \
  --games-per-context 2 \
  --online-iterations 4 \
  --online-depth 2
```

## Telemetry and Balance Lab

Simulations record card playability, immediate board swing, pass behavior, completed Legends, conditional outcomes, and decision statistics. The health analyzer adds Wilson 95% intervals, minimum-evidence thresholds, within-type z-scores, and diagnostic flags.

GitHub Pages publishes:

- printable cards;
- printable rulebook;
- a full Balance Lab generated from fresh simulation and solver runs.

The Balance Lab includes:

- every card with a five-level balance grade: red, orange, yellow, green, or dark green;
- paired per-card causal Δ win probability with 95% intervals;
- pairwise factorial interaction estimates and Subject–Link–Name triple interactions;
- targeted online-MCCFR validation for suspicious card/pair/triple effects, with confirmation status;
- draws, plays, dead-turn rate, pass-deadness, board/control swing, conditional win rates, confidence intervals, static marginal strength, and diagnostic flags per card;
- all 120 possible Subject–Link–Name Legends, including combinations not observed in the current simulation sample;
- static Strength-space diagnostics;
- action, pass, Battle, and decision telemetry;
- heuristic/random and MCCFR/heuristic matchup summaries;
- MCCFR iterations, information-set count, depth, policy coverage/fallback counts;
- the formal Kuhn-poker verification result, including exact-value error and exploitability;
- downloadable raw JSON artifacts for every report.

Card grades are diagnostic rather than prescriptive: **dark green** requires both no warning signals and strong evidence; **green** means currently healthy with thinner evidence; **yellow** is a watch signal; **orange** indicates one high-confidence or multiple watch issues; **red** indicates multiple high-confidence issues.

## Balance pipeline

The automated stack is now:

1. static Subject–Link–Name combinatorial analysis;
2. deterministic full-match engine;
3. heuristic self-play;
4. extended telemetry;
5. confidence-aware health analysis and five-level per-card grading;
6. **depth-limited external-sampling MCCFR**;
7. exact-reference MCCFR verification on Kuhn poker using the shared solver core;
8. MCCFR-policy evaluation against the heuristic baseline;
9. online MCCFR re-solving with observation-history-aware hidden-state beliefs;
10. deck-uncertainty priors with weighted hypothesis conditioning;
11. paired counterfactual card replacement and factorial interaction analysis;
12. targeted online-MCCFR validation of suspicious causal effects;
13. full Balance Lab aggregation and Pages publication.

Planned next layers:

14. action-likelihood learning for richer posterior deck/archetype inference;
15. double-oracle deck/meta search;
16. sampled Shapley attribution across deck contexts.

Static outliers, conditional win rates, heuristic values, and shallow MCCFR policies are diagnostics, not automatic balance verdicts.
