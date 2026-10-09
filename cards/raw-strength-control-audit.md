# Raw Strength versus combos — physical balancing control

**Status:** design audit and reproducible test specification, **not** empirical win-rate evidence. Uses the printed 131-card pool and its physical-only effect overlay, not the executable/Webgame engine.

## What a deck of the strongest simple Forces actually buys

The 48-card [Raw Strength Control](mechanic-coverage-decks.md#raw-strength-control) uses **only four Force identities with no printed special text**, at four copies apiece:

| Force | Copies | Printed Strength | Command each | Sum Strength |
| --- | ---: | ---: | ---: | ---: |
| Thirty Spears | 4 | 3 | 1 | 12 |
| The Fifty Men | 4 | 5 | 2 | 20 |
| A Hundred Shields | 4 | 6 | 3 | 24 |
| The Aradai | 4 | 3 | 2 | 12 |
| **Total Force cards** | **16** | | **32** | **68** |

The Aradai has **Raider** classification and a corresponding basic Attack; lack of printed effect text does not mean it lacks a mechanic. This is a simple-*Force*-only control deck, not a deck without Bonds, Names, Tactics or Stratagems. The complete 48-card list costs **71 Command in aggregate**, not 71 Command to deploy at once.

Comparison with the **sum of printed Force Strength over the entire deck** (not a Battle total):

| Main deck | Force copies | Sum printed Force Strength |
| --- | ---: | ---: |
| Banner & Blood | 16 | 64 |
| Crown of Crows | 16 | 50 |
| Oathforge | 16 | 53 |
| Blood & Spoils | 17 | 67 |
| Raw Strength Control | 16 | **68** |

A simple Force played to an empty position has *immediate, persistent Strength for one Action*. A Bond or Name needs a Force to improve a Front and usually consumes another Action and Command. Because the battlefield is persistent, a high-Strength Force is likely to pay off across multiple Battles; all-Force pressure is therefore a **plausible strong strategy**, especially while there are open positions. The game caps each player's board at 12 Force positions. Simple large Forces lose comparative value when all positions are occupied, when negative conditions reduce their Strength, or when an opponent completes a Named Formation with repeatable support, protected ranks and hidden Strength shifts.

**We cannot conclude that simple Forces win most games without playtesting.** Their pre-printed totals exclude the cost of Actions, availability per hand, active Front schedule, opponent responses, placement legality, protection, exhaustion, opponent Command collapse, and attached Strength. It would be misleading to compare 68 and 50 as though these were simultaneous competing Front totals.

## Proper A/B test

1. Play each of the four core combo decks against the same Raw Strength Control in **mirrored** openings, switching first player, initial card order and seats.
2. Record **Battle-by-Battle Force Strength actually deployed**, total persistent Strength per Front, Command spent and remaining, Actions spent preparing attachments, and whether Front positions fill before combos matter.
3. For every successful Named combo, record **incremental realized Strength** (including one-time Battle bonuses), attacks/conditions prevented, Bonds/Names returned to hand, Command gained/stolen, and **Front winners changed**.
4. Count meaningful hands with too many Bonds/Names but no unbonded playable Force versus hands where a high-Strength vanilla Force is always the best Action.
5. Repeat with shorter legal decks (34 and 48 cards), adjusting lists to respect card copy and Force minimums; do **not** assume shorter decks behave like longer ones.

**Balance criterion, not a predetermined outcome:** there should be games where a simple-Force deployment is correct, but the strongest repeated combinations should outperform raw Force placement **when their enabling state is achieved**. If the control wins broadly despite well-played legal combos, first consider (a) the combined Action/Command burden of assembling Named, (b) useful but delayed effects of support Forces, and (c) whether +2 temporary Strength is insufficient compared with a permanently occupying 5-Strength body. Avoid automatically nerfing all vanilla Forces without this evidence.

## Existing deck identities are combination hypotheses

The four core decks have explicit **enabler/payoff packages**, not merely a movement/scouting/defence play-style label:

- **Banner & Blood:** Captain/King + leadership Bond + named or hidden Front boost
- **Crown of Crows:** Bonded Archers + protection of supporting ranks + Counterattack/Exhaustion
- **Oathforge:** prepared layers + House of Reed / Field Train + guarded or +2 Named completion
- **Blood & Spoils:** Exhaustion or depleted opening + Command transfer + attached layer theft

These are **testable combinations** but they are not all inherently *deep* combos. Some are an efficient body followed by an unconditional +1 bonus. The key open test is whether play regularly offers a real choice among *which* chain to complete, *when* to commit it, and *how* an opponent can disrupt it, rather than an automatic sequence of bigger Strength numbers.
