# Simple Strength, combo value and lost-Front snowball audit

**Status:** physical-print loss rule approved and implemented: **one chosen Exhausted Force per lost Front**. The raw-Strength and combo discussion is still a design audit, not measured win rates. The native/Webgame does not implement the complete physical rules.

## Force Command tariff (current physical cards)

All **33 physical Forces** now pay a fixed 1 Command for the core function
of persistent Strength, occupying a rank and participating in combat. Their
base is `1 + ceil(printed Strength / 2)`; a documented **0–1 Command
ability premium** distinguishes a minor odd-Strength perk from a more
substantial ability, including worthwhile even-Strength class effects.
The individual decisions are in [force-pricing.json](force-pricing.json).
This is **price balancing only**: Force Strength and printed abilities,
Bonds, Names, Heroes and all other card types remain unchanged.

| Printed Strength | Base Force cost | Typical price with meaningful ability |
| ---: | ---: | ---: |
| 2 | 2 | 3 |
| 3 | 3 | 4 (for a strong ability) |
| 4 | 3 | 4 |
| 5 | 4 | 5 |
| 6 | 4 | 5 |

The current **Raw Strength Control** has four copies each of the following
simple Forces:

| Force | Current Command | Strength | Source of ability value |
| --- | ---: | ---: | --- |
| Thirty Spears | 2 | 3 | No special ability; unused half-point discount |
| The Fifty Men | 4 | 5 | No special ability |
| A Hundred Shields | 5 | 6 | Guard classification screens Rear from Middle |
| The Aradai | 3 | 3 | Raider classification permits basic Attack |

The **16** Forces provide 68 printed Strength for **56 Command** in all
(four copies of each); this is a whole-deck number, **not** the cost of
deploying every Force in one Battle. Their average is 4.25 printed
Strength per Force-play Action but only about **1.21 Strength per Force
Command**, compared with 68 Strength for 32 Command before repricing.

**Action efficiency still matters.** Three Thirty Spears provide
9 persistent Strength for 6 Command and three Actions across three
positions, while A Hundred Shields gives 6 Strength for 5 Command and
one Action/position. A Fifty Men (5S, 4C) with Followed (+1S and +1S
while Named, 1C) and a +1 Name (1C) produces **8 persistent Strength
in one position for 6 Command and three card plays**. A Hundred
Shields plus Thirty Spears produce **9 Strength in two positions for
7 Command and two Actions**. The extra Action invested in a Named
stack now saves Command, while its superior position density helps on
a full board.

The new tariff deliberately changes the economics, **not** the
two-Action turn limit. At 20 starting Command, four 5C Forces could
spend the entire reserve even before Bonds or Tactics. Early Command
recovery is 12/9 but falls to 3 then 1; heavier Force prices may
therefore make late deployment difficult or amplify a Command
disadvantage. Check this before adding any other systemic bonuses.

### What to measure next

Compare the Raw Strength Control against **all six combo/supplementary
decks** with mirrored openings and starting player. Record paid
Command and Actions per deployed persistent Strength, early legal
play counts, stranded Forces in hand, rank saturation, Named
completions, temporary/positional effects that flipped Fronts,
Command after every recovery, and late-Battle recovery opportunities.
Use actual physical game results; these static prices do not prove
win rates.

**Do not simultaneously add Attack/Defence statistics, a blanket
Named Strength bonus, faster Bond attachment, or blanket recovery.
Those are separate design experiments.** If simple bodies still
dominate, first inspect whether specialist decisions reliably win
Fronts and whether the new costs create unplayable hands.

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
