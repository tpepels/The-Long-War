# Simple Strength, combo value and lost-Front snowball audit

**Status:** design analysis and **proposed** rules experiments. The current
131-card physical rules and Exhaustion procedure are **unchanged** in this
commit. The native/Webgame does not implement the complete physical rules,
so there are no simulated or measured physical win rates.

## Does playing only the biggest straightforward Forces win?

The [Raw Strength Control](mechanic-coverage-decks.md#raw-strength-control)
uses the only four Force identities in its list, four copies each:

| Force | Printed cost | Printed Strength | Printed special ability |
| --- | ---: | ---: | --- |
| Thirty Spears | 1 | 3 | None |
| The Fifty Men | 2 | 5 | None |
| A Hundred Shields | 3 | 6 | None |
| The Aradai | 2 | 3 | None; Raider classification still grants a basic Attack |

Those **16** Force cards sum to **68 Strength for 32 Command**, giving an
arithmetic average of **4.25 printed Strength per Force play/Action** and
**2.125 Strength per Command** across the Force subset. These totals are
**not** expected Battle Strength: only deployed units count, each player
has twelve battlefield positions after Front expansion, and draws,
Command, active Fronts, restrictions and opponents limit deployment.

**A simple opening can be efficient:** three Thirty Spears, if drawn and
legally placed, produce 9 persistent Strength for 3 Command, 3 Actions,
and 3 occupied positions. A Hundred Shields offers 6 persistent Strength
for 3 Command and only 1 Action/position. A Fifty Men offers 5 for 2.

**A Named combination improves density instead:** The Fifty Men (5,
cost 2) + Followed (+1, cost 1) + a +1 Name (cost 1) triggers Followed's
additional +1 while Named: **8 persistent Strength in one position for
4 Command and 3 card-play Actions**. A Hundred Shields plus Thirty
Spears offer 9 Strength for 4 Command and 2 Actions, **but occupy two
positions**. Early empty slots may favor plain bodies; late saturated
Fronts may favor attachments, protection and precise denial.

The strongest plain-Force decks might dominate if early Battles are
mostly decided before Named combinations assemble, or if repeated +1
effects and information/movement tools fail to change Front results.
Conversely, a big unit without Guarded, recovery or tactical
protection may suffer −2 Shaken, −1 Exhausted and attachment/condition
pressure. **Neither outcome is proven.**

### Acceptance test (physical, mirrored)

Compare the Raw Strength Control against **each of the six combo decks**
with same opening card deals as far as practical, mirrored starting player,
and a record of cards seen/drawn, Commands and Actions spent, each Front's
before/after Strength, and winners of individual Fronts. Track:

1. Strength added **per played Action**, per Command, and per occupied slot
   for both sides. Distinguish permanent from Battle-only Strength.
2. Percent of Battles where each deck's declared enabler/payoff package
   was not merely in hand but *legally and usefully activated*.
3. Board saturation, unplayable late Force draws, used Attacks, harmful
   markers, recovery and Stratagem opportunities that never triggered.
4. Win/Collapse rate over mirrored games, with confidence intervals,
   not impressions from 2–3 games.

If raw Strength repeatedly dominates, first strengthen **decisions and
reliable payoffs** in the losing deck, or improve counterplay. Do not just
inflate all costs or add another keyword without knowing the cause.

## Why losing Fronts now risks snowballing

After a lost Front, the current rule Exhausts **every unprotected Force in
that Front** for the following Battle. Exhausted means **−1 Strength
and restricted Maneuver**. A Front lost with three unprotected Forces
therefore starts the next Battle **3 Strength behind its former total**.
The opponent need not spend a card or Action to create that gap, and the
loser also loses **1 Command per Front** before Collapse/recovery.
With two full lost Fronts this can mean six weakened Forces next Battle,
even if the winning opponent's board persists unchanged.

This is positive feedback: the greater the defeat, the harder it may be
to contest the same Front again. Between-Battle recovery refills Command,
especially early, but does not restore that Strength disadvantage.

## Candidate interventions (not yet canonical)

| Variant | Procedure | Main tradeoff |
| --- | --- | --- |
| **A — one casualty per lost Front (recommended)** | For each lost Front, losing player chooses one *unguarded* friendly Force there to become Exhausted; if none are unguarded, choose a Guarded one, whose Guarded is consumed instead | Keeps a scar, but limits the new penalty to at most −1 Strength per lost Front; requires one small choice |
| **B — no automatic Exhaustion for Front loss** | Only Attacks/card effects Exhaust; losing a Front still costs its Command | Strongest anti-snowball simplification, but loses a persistent scar from defeat |
| **C — one free Rally per player next Battle** | Before the first turn, remove one existing Exhaustion without Command or Action | Gives meaningful recovery, but adds a new phase, and may erase small pressure entirely |
| **D — extra Command to the loser** | Give comeback Command for each lost Front next Battle | Less effective while recovery already returns players to the 20 Command cap; increases economy rules |

**Proposed trial order:** A versus current all-Forces Exhaustion, then B
if repeated defeats remain decisive. Keep the Command loss, collapse
timing, Attack-created Exhaustion, Guarded prevention, and temporary
condition cleanup unchanged during that comparison. Evaluate at one/two/
three Forces per lost Front and Battles I–IV; separately track whether
Shaken/Depleted combinations amplify the disadvantage.

This audit deliberately does **not** change the rulebook to Variant A.
Changing the system now would invalidate the current deck comparison
baseline before the match data is collected.

## Do the decks contain combinations instead of vague play-styles?

The core decks' packages are written as *specific* enabler/payoff pairs:
King/Captain + leadership Stratagem, Archer + Guard/screen + volley,
House of Reed/Field Train + prepared layers and Named rewards, and
Exhaustion/Depleted + Command transfer or attached-card theft.

That is better than naming only "control", "scouting" or "mobility", but
a card being in both category sets is not a combo by itself. Score an
interaction **meaningful** only when it changes a legal choice or Front
result that the two parts could not accomplish separately. The new
Last Watch and Broken Oaths are supplementary decks for rarer defensive
and raid effects; their numerous singletons make the tests exploratory,
not consistency benchmarks.
