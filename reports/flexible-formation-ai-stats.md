# Flexible-formation AI pacing statistics

This snapshot measures the requested structural rules experiment before any hand-size change:

1. Subject, Bond, and Name may occupy a formation in any order.
2. Bond/Name components without a Subject are prepared and inactive where text depends on a Subject.
3. A later Subject activates the prepared formation.
4. Removing a Subject removes its Bond and Name with it.
5. Between Battles, players keep their hand, shuffle all other owned cards together, and draw back up to 10.

The evidence comes from **Expanded Pool Playtest Gate run 35777648138** on ruleset fingerprint `3fef19ae1beb7606`: **20,000 heuristic matches and 51,131 Battles** across Reference and all archetype/seat combinations. Draw remains once per player per Battle in this experiment.

## Before versus after

| Metric | Previous rules | Flexible formations + recycle | Change |
| --- | ---: | ---: | ---: |
| Battles per match | 2.55 | 2.56 | +0.3% |
| Cards played per match | 25.88 | 35.15 | +35.8% |
| Cards played per Battle | 10.16 | 13.75 | +35.3% |
| Cards played per player per Battle | 5.08 | 6.87 | +35.3% |
| Normal turn actions per player per Battle | 6.24 | 8.01 | +28.3% |
| Complete Subject–Bond–Name formations per Battle | 0.85 | 1.00 | +18.1% |
| Draw opportunity used | 45.2% | 42.2% | -3.0 pp |
| Hand size when passing | 3.87 | 3.83 | -0.04 |
| Dead-card share at Pass | 26.2% | 6.5% | -75.3% |
| Card-in-hand turns unplayable | 22.1% | 2.2% | -89.9% |
| First passer Battle win rate | 35.4% | 35.9% | +0.5 pp |
| Legal candidates per heuristic decision | 11.58 | 24.57 | +112.2% |

The structural goal was achieved: Bonds and Names are almost never mechanically stranded merely because a Subject has not yet appeared. The trade-off is a much larger action space and substantially more cards committed per Battle.

## Match and Battle pacing

| Metric | Result |
| --- | ---: |
| Battles per match | 2.56 |
| 2-Battle matches | 8,869 (44.3%) |
| 3-Battle matches | 11,131 (55.7%) |
| Action events per match | 43.98 |
| Cards played per match | 35.15 |
| Action events per Battle | 16.59 |
| Normal turn actions per player per Battle | 8.01 |
| Cards played per Battle | 13.75 |
| Cards played per player per Battle | 6.87 |
| Complete Subject–Bond–Name formations per Battle | 1.00 |

## Card mix per Battle

| Card type | Mean per Battle | Share of card plays |
| --- | ---: | ---: |
| Subjects | 6.97 | 50.7% |
| Bonds | 2.61 | 19.0% |
| Names | 1.73 | 12.6% |
| Stories | 0.54 | 3.9% |
| Veiled Stories | 1.33 | 9.7% |
| Stratagems | 0.58 | 4.2% |

Names are now played about twice as often as under the previous ordering rule (1.73 versus 0.85 per Battle), and Bonds rise from 1.75 to 2.61. Complete formations increase more modestly because players also distribute prepared components across several positions.

## Draw, passing, and hand pressure

| Metric | Result |
| --- | ---: |
| Draw actions per Battle | 0.84 |
| Draw opportunity used | 42.2% |
| Stratagem opportunity used | 28.9% |
| Hand size when passing | 3.83 |
| Dead cards when passing | 0.25 |
| Dead-card share of cards held at Pass | 6.5% |
| Card-in-hand turns that were unplayable | 2.2% |
| Drawn cards eventually played | 83.8% |
| First passer wins the Battle | 35.9% |
| Mean legal candidates per heuristic decision | 24.57 |

The first-passer result barely moved, so the earlier 35% result was not primarily caused by downstream-card deadness. That makes Pass timing a separate design question rather than something the formation-order change automatically fixes.

Draw usage also remains situational. Because Draw costs a normal action and is used only about 42% of player-Battles, the present rule is **not** statistically equivalent to simply starting every Battle with one additional card.

## Implication for hand-size testing

The next hand-size experiment should not assume that 11 cards is automatically preferable. Flexible construction already increased cards played per Battle by about 35% and doubled the number of legal alternatives seen by the heuristic. Increasing guaranteed hand size could amplify both effects.

A useful next experiment is therefore to remove the once-per-Battle Draw and compare fixed Battle hand targets around the current effective resource level, rather than simply replacing 10 + optional Draw with an 11-card hand. Candidate targets should be compared on:

- cards and actions per Battle;
- dead/unplayable-card rate;
- complete formation rate;
- Pass timing;
- legal-choice count;
- first-player and deck balance.

AI self-play still cannot measure reading time, comprehension, memory burden, or whether a larger choice set feels interesting rather than exhausting. Those remain human-playtest questions.
