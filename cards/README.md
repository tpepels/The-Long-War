# Physical game — one-page D6 edition

**There is only one paper rulebook:** [rules/rulebook.md](../rules/rulebook.md).
The published [PDF](../web/rulebook.template.html) is verified as **exactly one A4 page**; [rules/player-rulebook.md](../rules/player-rulebook.md) is the same text for compatibility with existing print tools.

The current printable cards are in [paper-d6.json](paper-d6.json): 44 Force/Hero identities, their Force statistics, costs, roles, six D6 faces, and four simple results (Attack, Defend, Save, Nothing or a brief printed Special). Use the three [24-card paper decks](paper-d6-decks.json).

The only army-wide Battle Plans are **Assault, Hold, Volley, Raid**. Their behavior is printed on the [Battle Plan cards](../web/tokens.html). No separate counters, Tactical Read, Pressure, Pin, Opportunities, rank bonuses or status markers exist. There are no hidden advanced paper rules.

The older [cards.json](cards.json), [print-overrides.json](print-overrides.json), old audits, and runtime deck definitions are retained strictly for the **unchanged digital engine** and historical metadata. The paper-only builder [tools/paper_d6_cards.py](../tools/paper_d6_cards.py) reuses art and rank restrictions. Engine and AI are not synchronized to this paper edition.
