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
- `src/longwar/agents/` — random and heuristic automated players.
- `src/longwar/telemetry.py` — game, card, pass, and Legend telemetry.
- `src/longwar/balance.py` — static balance diagnostics.
- `src/longwar/simulate.py` — repeated game simulation.
- `web/` — static source for the printable GitHub Pages site.
- `tools/` — CLI entry points.
- `.github/workflows/` — CI, balance diagnostics, and Pages deployment.

The printed cards, the engine, and the balance tooling all consume the same card database. Human-facing card text is not parsed by the engine; the `rules` object is executable card semantics.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python tools/balance_report.py
python tools/simulate.py --games 1000 --agent-a heuristic --agent-b heuristic
python tools/build_pages.py
```

Then open `dist/index.html`.

## Implemented engine rules

The engine currently implements:

- 30-card deck validation and Unique/copy limits;
- seeded shuffling, opening hands, and optional two-card mulligans;
- six Subject positions: Left/Center/Right × Front/Rear;
- Subject → Link → Name construction;
- placement restrictions and position-dependent Strength;
- all effects of the first 18-card set;
- Plot targeting and Legend break/removal rules;
- passing and hand economy;
- three-Front scoring and pass-first tiebreaks;
- best-of-three Battles;
- the losing player choosing who starts the next Battle;
- reproducible automated simulations.

The state transition is deterministic after setup randomness. `legal_actions(state)` enumerates every action the active player may take; `apply(state, action)` rejects anything else.

## Heuristic agent

The heuristic player performs one-ply lookahead across every legal action. Its evaluation uses:

- Front control and Strength margins;
- Victory-marker advantage;
- public hand-size advantage;
- completed Legends;
- own-hand completion potential for open Links;
- the value of conserving cards through passing.

The agent does **not** inspect hidden opponent card identities. It sees only public battlefield information and public hand sizes, plus its own hand. A small exploration rate prevents self-play from collapsing into one deterministic line.

This agent is a stepping stone: it produces strategically meaningful trajectories for balance telemetry before MCCFR is introduced.

## Telemetry

Every simulation now records:

- actions by type;
- cards drawn and played;
- play rate per draw;
- turns a card is playable/unplayable while held;
- cards held or dead when a player passes;
- immediate net Front-margin swing per played card;
- immediate Front-control swing;
- win rate conditional on drawing or playing each card;
- every completed Subject–Link–Name combination;
- Strength at Legend completion;
- win rate conditional on completing a Legend;
- pass timing, hand size, controlled Fronts, and subsequent Battle result;
- actions and total Strength per Battle;
- heuristic candidate counts and score gaps.

Conditional win rates are observational diagnostics, not causal estimates. MCCFR and counterfactual replacement experiments will provide stronger value estimates later.

## GitHub Pages

The Pages workflow builds the site from `web/`, `rules/rulebook.md`, and `cards/cards.json`. The cards page is formatted for A4 printing at 100% scale with poker-size cards (63 × 88 mm), nine cards per sheet.

## Balance pipeline

The automated balance stack now has three layers:

1. **Static combinatorial analysis** — evaluates every Subject–Link–Name combination using explicit Strength semantics.
2. **Heuristic rules-engine self-play** — generates strategically directed full matches.
3. **Extended telemetry** — measures card usability, immediate board swing, pass behavior, and Legend-combination outcomes.

Planned next layers:

4. Monte Carlo CFR for play strategy;
5. double-oracle search for deck/meta strategy;
6. marginal/Shapley interaction analysis for card and combo value.

Static outliers, heuristic values, and conditional win rates are diagnostics, not balance verdicts.
