# Card redesign V2

This directory is a **design proposal**, not the canonical engine card pool.

It deliberately ignores the current decks and does not replace `cards/cards.json` yet.

Files:

- `mechanics.md` - the new mechanical and physical card grammar.
- `catalogue.md` - readable catalogue of all 95 redesigned cards.
- `cards.json` - machine-readable version of the same 95-card proposal.

The browser preview is published as `web/cards-v2.html` and, on GitHub Pages, as `cards-v2.html`.

## Design direction

- Battlefield rows are **Front / Middle / Rear**.
- Force + Bond + Name is still a **Named Formation**.
- Formation cards persist between Battles.
- Classifications have no inherent rules; other cards refer to them.
- New **Tactic** cards resolve immediately.
- Stratagems are hidden and triggered.
- Narratives are visible and may create class-wide effects.
- Recurring/continuing state must remain visible in the exposed stack strip.
- Temporary state and once-per-Battle use are represented by physical markers.
- Hard row restrictions on Forces are intentionally uncommon.