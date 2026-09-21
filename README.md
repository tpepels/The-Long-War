# The Long War

A head-to-head card game about building legends across a physical battlefield.

The core grammar is:

**Subject → Link → Name**

Example: **The Fifty Men → Followed → Namar**

## Repository roles

- `cards/cards.json` — canonical card database.
- `rules/rulebook.md` — canonical printable rules.
- `src/longwar/` — game and balance code.
- `web/` — static source for the printable GitHub Pages site.
- `tools/` — build and analysis entry points.
- `.github/workflows/` — CI, balance diagnostics, and Pages deployment.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python tools/balance_report.py
python tools/build_pages.py
```

Then open `dist/index.html`.

## GitHub Pages

The Pages workflow builds the site from `web/`, `rules/rulebook.md`, and `cards/cards.json`. The cards page is formatted for A4 printing at 100% scale with poker-size cards (63 × 88 mm), nine cards per sheet.

## Balance pipeline

The first automated layer validates card data and measures static Legend strength and interaction outliers. The planned solver stack is:

1. deterministic rules engine;
2. random and heuristic agents;
3. Monte Carlo CFR for play strategy;
4. double-oracle search for deck/meta strategy;
5. marginal/Shapley interaction analysis for card and combo value.

The algorithms and the print site consume the same canonical card data.
