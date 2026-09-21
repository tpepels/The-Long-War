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
- `src/longwar/agents/` — automated players.
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
python tools/simulate.py --games 1000
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
- reproducible random-agent simulations.

The state transition is deterministic after setup randomness. `legal_actions(state)` enumerates every action the active player may take; `apply(state, action)` rejects anything else.

## GitHub Pages

The Pages workflow builds the site from `web/`, `rules/rulebook.md`, and `cards/cards.json`. The cards page is formatted for A4 printing at 100% scale with poker-size cards (63 × 88 mm), nine cards per sheet.

## Balance pipeline

The automated balance stack now has two layers:

1. **Static combinatorial analysis** — evaluates every Subject–Link–Name combination using explicit Strength semantics.
2. **Rules-engine simulation** — runs complete seeded matches using automated agents and reports seat/first-player results and game length.

Planned next layers:

3. heuristic agents with state-value features;
4. Monte Carlo CFR for play strategy;
5. double-oracle search for deck/meta strategy;
6. marginal/Shapley interaction analysis for card and combo value.

Static outliers and random-agent win rates are diagnostics, not balance verdicts.
