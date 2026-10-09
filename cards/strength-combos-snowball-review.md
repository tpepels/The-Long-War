# Simple Strength, combo value and lost-Front snowball audit

**Status:** physical-print loss rule approved and implemented: **one chosen Exhausted Force per lost Front**. The raw-Strength and combo discussion is still a design audit, not measured win rates. The native/Webgame does not implement the complete physical rules.

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

## The updated loss rule reduces the attrition feedback loop

**Current, approved rule:** after losing a Front and paying the normal 1 Command (with Collapse checked before recovery), the losing player chooses **one Force** in that lost Front, if any, to become Exhausted for the next Battle. Exhaustion gives **−1 Strength** and restricts ordinary Maneuvers. If the chosen Force has Guarded, that Guarded prevents the Exhaustion and is consumed; the loser does not choose a substitute. A Front with no surviving Force causes no loss-based Exhaustion. Old afflictions/Boons clear before the unprevented new token is applied.

The old rule Exhausted **every unprotected Force** in the lost Front. Three surviving unprotected Forces could therefore produce **−3 next-Battle Strength**, and two lost Fronts could weaken six separate Forces. The new rule limits the same loss to **at most −1 per Front**, rather than −1 per surviving Force. Card- and Attack-inflicted Exhaustion still operates normally.

This change reduces a positive feedback loop without changing printed Force Strength, the −1 Command penalty, Command recovery, or the one-Battle lifetime of loss-based Exhaustion. A player who continually loses still faces real danger; **no measured comeback or win rates exist** to show how large the improvement will be.

### Historical comparison and remaining watchpoints

| Situation | Historical all-Forces rule | Current one-chosen-Force rule |
| --- | --- | --- |
| Lost Front with 3 unguarded Forces | 3 exhausted; −3 next-Battle Strength | 1 exhausted; −1 next-Battle Strength |
| Lost Front with 1 unguarded Force | 1 exhausted; −1 | 1 exhausted; −1 |
| Lost Front with 1 Guarded + 2 unguarded | Both unguarded Exhausted; −2 | Losing player may choose Guarded to prevent all loss-based Exhaustion |
| Lost Front with no surviving Force | None | None |
| Command loss | −1 before Collapse | Unchanged |

Use matched hands and the same board state to compare repeated Front losses and opportunities to recover. Track selection choices and Guarded prevention separately from other sources of Exhaustion. If one lost Front still repeats too reliably, investigate the persistent board disparity and direct temporary combat penalties before adding an automatic consolation bonus.

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
