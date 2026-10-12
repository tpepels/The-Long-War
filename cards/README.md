# The Long War — physical D6 edition

The [one-page rules](../rules/rulebook.md) describe the entire game. The [44-card identity matrix](paper-d6-identity-matrix.md) records why each Force's new Special exists, what allies enable it, and how opponents may counter it. The digital engine and AI remain a separate, older ruleset.

## Two decks per player

- A **24-card Force deck** with unit and Hero cards. Use the [44 printable identities](paper-d6.json) to construct it, or print either of the three [24-card starter decks](paper-d6-decks.json). Every Force has a Command cost, permitted battlefield positions and four D6 outcomes. All 44 have a different Special; 20 ordinary Attacks and 17 Defends also differ by role and formation. **No dice face produces a blank result:** the former `F` slot now prints a card-specific Defend, Save or Draw action (sometimes with movement or Command recovery), while keeping its original face assignments.
- A separate **12-card Order deck**, with three copies each of Assault, Hold, Volley and Raid. Use [cards/paper-d6-orders.json](paper-d6-orders.json), or [print both players' Order decks](../web/orders.html).

The four Orders reuse original illustrations from retired cards: **All Banners Forward** (Assault), **No Step Back** (Hold), **A Volley Before Dawn** (Volley) and **The Line Wheeled** (Raid). Their image IDs are assigned in [the canonical Order data](paper-d6-orders.json), not inferred from titles. The website build publishes optimized illustrations on the printable card faces.

Shuffle the decks separately. Begin with ten Forces, three Orders and twenty Command.

During deployment, draw Forces and take ordinary actions (Play, Move, or Pass). Before each Battle, secretly choose one Order from your hand, reveal simultaneously, and apply that Order army-wide. Discard the played Order and draw a new Order after combat. The original **reusable Battle Plan menu and printed Command reference card are no longer part of this edition**.

**Command is a resource, not a card.** Its cost, loss, recovery and victory conditions are in the short rulebook.

The [battlefield mat](../web/playmat.html) provides four Fronts with three ranks per player. There are no Pressure, Pin, Tactical Read, Opportunity or status-marker systems.

The older [cards.json](cards.json), historical print overrides and executable game remain unchanged; only the experimental paper D6 edition uses these new Order rules.
