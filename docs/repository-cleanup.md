# Repository cleanup

The repository has been cleaned around the current workstream model:

```text
physical game -> print presentation
physical game -> runtime engine -> AI / research
```

## Current sources of truth

- `cards/cards.json` - canonical machine-readable card pool.
- `rules/rulebook.md` - player-facing physical rules.
- `cards/playtest-decks.json` and `decks/*.json` - physical/research deck content.
- `web/physical-cards.js` / `web/physical-cards.css` - shared physical-card renderer.
- `web/card-symbols.js` - physical-card symbol vocabulary.
- `web/art/cards/<card-id>.png` - canonical production card illustrations.
- `cards/art-sources/` - retained authoring originals, never deployed.

## Removed or retired

- Public/design V2 card labs and style-lab pages.
- V2-named physical renderer/style/symbol files.
- The old `cards/v2/` documentation layer.
- Old artwork manifests, candidate trees, preview outputs, unused frame assets, and one-off art migration scripts.
- Superseded first-80 / approved-mechanics design records.
- Obsolete illustrated-rulebook migration code and unused teaching-plate assets.
- Duplicate public-navigation markup in favor of one build-time navigation fragment.
- Historical design snapshots that no longer describe the current physical game.

Historical engineering and evidence reports remain under `reports/` and are explicitly non-authoritative.

## Deliberately retained

Internal runtime identifiers containing `v2` are not public version surfaces. They remain while the executable engine integration is unfinished, because renaming them now would create churn without changing behavior.

The engine/webgame may lag the physical game. That lag is tracked separately and does not prevent printing or developing the physical game.

Testing policy lives in `TESTING.md`: durable integrity and behavior tests remain; transient card, prose, deck, and visual design decisions are not permanent product requirements.
