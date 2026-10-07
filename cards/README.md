# Cards and physical design

`cards/cards.json` is the sole machine-readable card pool. Player rules live in `rules/rulebook.md`; shipped runtime/research decks are catalogued by `decks/index.json`.

- `mechanics.md` - formation vocabulary and card grammar.
- `visual-spec.md` / `symbols.md` - physical card layout and symbols.
- `catalogue.md` - human-readable card reference; reconcile it with JSON when editing cards.
- `playtest-matrix.md` / `effect-audit.md` - authored coverage and readability reviews.
- `value-model.md` / `valuation-audit.md` - provisional design diagnostics, not measured balance evidence.
- `playtest-decks.json` / `playtest-decks.md` - four exploratory 48-card physical decklists; distinct from shipped research profiles.
- `art-sources/` - uncropped illustration originals for future artwork edits.

Canonical per-card PNGs live in `web/art/cards/`. Pages generates optimized WebP derivatives in `dist/art/cards-print/`; it never rewrites the PNGs. Neither the physical game nor print presentation requires runtime parity to be usable.
