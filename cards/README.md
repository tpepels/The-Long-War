# Physical cards — D6 Force-only paper experiment

**Active physical rules:** [player-rulebook.md](../rules/player-rulebook.md) (short guide) and [rulebook.md](../rules/rulebook.md) (complete D6 reference). These are *paper-only* and deliberately differ from the runtime.

- [paper-d6.json](paper-d6.json) — all **44 Force / Hero identities**, their one Force statistic, role, printed Command cost, six die-face mappings and four combat outcomes.
- [paper-d6-decks.json](paper-d6-decks.json) — three **24-card** decks for first tabletop tests.
- [paper_d6_cards.py](../tools/paper_d6_cards.py) — projects existing card identities/artwork into the **experimental printable dataset**, without changing executable cards.json.
- [check_paper_d6.py](../tools/check_paper_d6.py) — schema, membership and paper-only isolation checks.
- [playmat.html](../web/playmat.html) and [tokens.html](../web/tokens.html) — battlefield reference and reusable hidden Battle Plan cards.

**All old Bonds, Names, Tactics, Orders, Stratagems, Narratives, printed special abilities, conditions and Opening Orders are suspended in this prototype.** The printable cards display only the D6 behaviour. Every Force can participate once per Battle without a normal Attack action. Players roll independently, one D6 per occupied Front.

## Legacy material retained

`cards.json` remains canonical **for the separate engine/Webgame only**. `print-overrides.json`, `playtest-decks.json`, `playtest-decks.md`, `mechanic-coverage-decks.json`, former cost reviews and old audits document the previous 131-card Bond/Name physical experiment and **are not the current physical rules**. The D6 assembler reads these older sources solely to reuse art metadata, IDs, validated row restrictions and experimental card prices.

Original PNG art remains in `web/art/cards`; `tools/build_pages.py` now publishes the 44-card D6 catalogue, three 24-card decks and revised physical rulebook. The executable `dist/data/cards.json` remains the unchanged 131-card runtime export and is not a source for paper gameplay.

This prototype has not yet been physically playtested or balanced. Do not report historical engine results as D6 evidence.
