# card value model

This is a **diagnostic heuristic**, not a formula that dictates card design. It is meant to expose dominated cards, narrow cards with an inadequate floor, and implausibly high ceilings.

## Force baseline

| Command | Approximate target Force value | Baseline example |
|---:|---:|---|
| 1 | 3 | Thirty Spears - 3 Strength |
| 2 | 5 | The Salt-Road Reavers / The Black Pursuers - 5 Strength |
| 3 | 6 | A Hundred Shields - 6 Strength |

For a Force:

`expected value ~= printed Strength + sum(ability impact × applicability × persistence) - Action tax`

## Starting ability values

| Effect | Starting value |
|---|---:|
| +1 persistent Strength | 1.00 |
| SUPPORT +1 | 0.75 |
| RESERVE +1 | 0.50 |
| PRESS +1 | 0.40-0.60 |
| regain 1 Command from a live Supply raid | 0.45-0.70 |
| STEAL 1 COMMAND from a live Supply raid | 1.20-1.40 |
| save / deny 1 Command | 0.70 |
| MOVE 1 | 0.75-1.00 |
| MOBILE | 1.00-1.25 |
| TIRELESS | 0.40-0.60 |
| remove Exhaustion | 1.25 |
| net +1 card | 1.25 |
| draw/discard filtering | 0.40 |
| inspect hidden information | 0.30 |
| suppress a meaningful Bond/Name for a Battle | about 1.00 |

A repeatable ACTION normally pays an **Action tax of about 1.0-1.5 value**, because it consumes half of a standard turn. Any printed Command payment is additional.

## Applicability multipliers

| Condition | Multiplier |
|---|---:|
| specific row | 0.75 |
| Bonded | 0.65 |
| Named | 0.50 |
| Exhausted | 0.45 |
| specific opposing state / classification | 0.35-0.50 |

Conditions should normally create upside, not rescue a card with an unusably low floor. Because most cards already cost only 1-2 Command, narrow cards are usually healthier when their baseline improves or their effect broadens rather than when their Command cost is reduced.

## Zero-Command cards

A 0-Command card is not free. Playing it still consumes one card from hand and one Action - normally half of a standard turn. In this pool, 0-Command self-support is carried by **Orders**, and every 0-Command Order has a real eligibility condition. The space is for selection, recovery, positioning, or setup - never unconditional permanent Strength, Command profit, or unrestricted card selection.

`Send a Runner` is intentionally stronger filtering than `Fresh Orders`: it sees two cards rather than one, so it requires a **Scout specifically in the Rear row**. `Take Stock` is stronger again because it selects one of the top three and keeps it; it therefore costs **1 Command** and requires a Steward or Stronghold.

For telemetry, record condition-active rate, use rate, Action spent, Command spent/saved, cards gained/lost, whether the effect changed a Front result, and voluntary re-inclusion. Those observed rates should eventually replace the applicability estimates above.
