# Cards and physical design

`cards/cards.json` is the sole machine-readable card pool. Player rules live in `rules/rulebook.md`; shipped runtime/research decks are catalogued by `decks/index.json`.

- `mechanics.md` - formation vocabulary and card grammar.
- `visual-spec.md` / `symbols.md` - physical card layout and symbols.
- `catalogue.md` - human-readable card reference; reconcile it with JSON when editing cards.
- `playtest-matrix.md` / `effect-audit.md` - authored coverage and readability reviews.
- `value-model.md` / `valuation-audit.md` - provisional design diagnostics, not measured balance evidence.
- `playtest-decks.json` / `playtest-decks.md` - four Strength-first 48-card combo decklists with exact two-package availability baselines; distinct from shipped research profiles.
- `mechanic-coverage-decks.json` / `mechanic-coverage-decks.md` - three separate 48-card diagnostic decks for Riders, Seers, hidden plans, preparation and Front exchange. These are not primary competitive decks.
- `art-sources/` - uncropped illustration originals for future artwork edits.

Canonical per-card PNGs live in `web/art/cards/`. Pages generates optimized WebP derivatives in `dist/art/cards-print/`; it never rewrites the PNGs. Neither the physical game nor print presentation requires runtime parity to be usable.

**Physical-print-only redesigns:** `print-overrides.json` is applied by `tools/print_cards.py` to produce the printable card catalogue and playtest deck sheets without modifying the native/Webgame rule data. PLAY effects may be buried; ongoing Force/Bond abilities must remain readable in the fixed 10.5 mm exposed strip. `cards.json` retains unchanged executable content during this print-only stage.

**Print rulebook reconciliation (8 October 2026):** the approved physical rules and explanations are in [`rules/rulebook.md`](../rules/rulebook.md), with card-specific printed wording in [`print-overrides.json`](print-overrides.json). Every Stratagem is associated with a visible active Front; all Narratives last for their Battle, up to four per player. Do not infer these print mechanics from the native/Webgame card catalogue.

**Physical cost rebalance (8 October 2026):** [131-card cost review and play-like hand checks](physical-cost-review.md). The currently retained cost-only corrections, row restrictions, and revised printed card effects are applied in `print-overrides.json`; the native deck and card data are untouched.
