# Physical playtest evidence (131-card print pool)

The printable card set is **not** the current native/Webgame card set. Do not
derive physical card win rates from existing Webgame matches. Collect gameplay
from the physical rules or first implement that ruleset in a dedicated runtime.

## Record JSONL events

Write one JSON object per line in a local `playtests.jsonl` file. Do not commit
real player-identifiable data. The following are **schema examples, not match results**:

```jsonl
{"kind":"opportunity","game_id":"sample-01","player":"A","battle":2,"turn":3,"card_id":"the-crows-came-down","playable":true,"useful":false}
{"kind":"play","card_id":"the-crows-came-down","effect_triggered":true,"command_spent":2,"actions_spent":1,"formations_moved":0,"markers_changed":1,"fronts_flipped":0}
{"kind":"turn","battle":4,"active_positions":12,"occupied_positions":12,"stranded_forces":1}
{"kind":"result","game_id":"sample-01","deck_a":"Maneuver & Relief","deck_b":"Hold & Counter","winner":"A"}
```

- **opportunity:** one record per card title, player and normal turn when the
  card was observed in hand. `playable` means at least one legal play existed
  within that turn. `useful` means at least one play was judged meaningfully
  better than passing the Action or cycling; log the judgment consistently.
  Do not report an unobserved opportunity.
- **play:** record each play, including cards with no effect. `effect_triggered`
  indicates whether at least one conditional effect actually did something,
  rather than only whether the card entered play. `actions_spent` includes
  the play Action; count later ACTION uses in separate `play` observations
  only if using that convention consistently, or sum them with the original
  event. This is a *manual observation* metric, not rules adjudication.
  `fronts_flipped` records Front outcomes known to have changed because of
  the card; leave 0 when uncertain. Numeric effect fields default to 0.
- **turn:** each player's normal turn; `active_positions` on one player's
  side is 6, 9, or 12. Count occupied Force slots and friendly Forces in hand
  unable to enter due to occupancy. Record both players' turns separately.
- **result:** once per completed game, label the two decks and winner `A`,
  `B` or `draw`. Use distinct `game_id` per match. Mirrored pairings
  should swap decks and starting positions; capture match IDs consistently.

## Generate the report

```bash
python tools/physical_playtest_metrics.py --self-test
python tools/physical_playtest_metrics.py playtests.jsonl
python tools/physical_playtest_metrics.py playtests.jsonl --format json > playtests-summary.json
```

The report shows per-card playable/useful opportunity rates, conditional effect
trigger rates, average Command/Action costs and effect counts; by-deck game
scores; matchup counts; and late-battle full-occupancy/stranded-Force rates.

Diagnostic flags require a minimum sample (10 card opportunities or plays,
10 late turns, 30 games per deck). They are **investigation prompts, not
balance proofs**. In particular, manual `useful` judgments and inferred
`fronts_flipped` are subjective; scored game outcomes depend on deck
selection, player experience and opening-hand luck.

## Recommended controlled sequence

1. Compare **Every Banner Turned Toward Them** with **The Center Must Hold**
   in identical board states; record whether the extra Front matters.
2. Run Battle II and IV test hands for **The Field Train**, **The Stores Were
   Taken**, and **Re-form the Line**. Record stranded Forces and actual
   sacrifices, including the Strength lost and future deployment enabled.
3. Test Riders in Rear versus Middle/Frontline, especially with **The Long
   March**, and counterattacks with **The Archers Were Ready**. Record each
   legal target and Attack marker.
4. Compare the four published 48-card decks with mirrored deals, both starting
   players, and more than one opponent archetype. Record full game results,
   not just opening-hand Command affordability.

Do not tune numerical card costs based on the analyzer's synthetic self-test.
No automated game-balance evidence exists until real matches or a physical
rules-compatible simulation are supplied.
