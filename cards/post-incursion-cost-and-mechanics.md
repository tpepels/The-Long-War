# Post-Incursion cost and mechanics audit — physical game

**9 October 2026.** Scope: the **131 printed cards** assembled from
`cards/cards.json` and `cards/print-overrides.json`. The separate native
engine/AI do **not** implement this current paper game; do not cite their
wins, attacks or match duration as evidence for these printed changes.

## Decision

The Force tariff is now **strict**:

> **Force Command = 1 + ceil(Strength / 2) + ability premium (0 or 1).**

The Strength is the printed **Force** Strength, not total strength after Bonds,
Names, conditions or temporary bonuses. The +1 ability premium is appropriate
when a Force performs a genuinely valuable extra task (not merely its
classification's ordinary basic Attack). No discount or special Force cost
may go below the baseline. Every **odd-Strength** Force receives a small,
clearly understandable on-card ability; more powerful odd-Strength abilities
pay a premium. Simple baseline/Guard Forces remain important: every Force
need not have elaborate text or extra counters.

### Full Force price enumeration

| Command | Number of Force identities | Interpretation |
| ---: | ---: | --- |
| 3 | 17 | Cheapest Forces; 2- or 3-Strength, with necessary role premiums |
| 4 | 13 | 3–5 Strength and/or stronger abilities |
| 5 | 3 | Expensive 5–6 Strength or powerful class role |
| **Total** | **33** | **118 Command** to purchase one copy of every distinct Force |

- **23 odd-Strength Forces** now have explicit printed compensation.
- **18 Forces** pay +1 for a meaningful extra ability or expensive
  classification (including Guard at even Strength).
- **0 Forces** have a below-tariff credit.
- Printed body prices range from **3C to 5C**. The expensive persistent
  Force commitment remains the centre of the Command economy.
- Other card types retain their existing printed prices and card counts.

The definitive machine-readable per-Force rationale is
[`force-pricing.json`](force-pricing.json), verified by
`tools/check_force_pricing.py`,
`tools/check_final_balance.py`, and
`tools/check_post_incursion_economy.py`.

### The concrete corrections

| Card | Before | Now | Why |
| --- | --- | --- | --- |
| **The Damar** | 3 Strength / **3C**, immediate Move plus possible free Attack | 3 Strength / **4C**; no change to ability | A combined Move and newly enabled Attack deserves a premium above the odd-Strength rounding allowance |
| **Thirty Spears** | 3 Strength / **2C**, no effect | 3 Strength / **3C**; give another friendly formation here +1 temporary Strength on PLAY | Removes the one below-formula exception; compensates odd Strength on the card |
| **The Fifty Men** | 5 Strength / 4C, no effect | Same 5/4C; conditional +1 temporary Strength if another friendly Human is here | At 5/4C, odd Strength shouldn't be worse than an equally priced even body merely by rounding |
| **The Aradai** | 3 Strength / 3C, Raider only | Same 3/3C; temporary −1 Strength to opposing Frontline when deployed to your Frontline | Makes a modest opening in the Incursion contest without granting a free Attack |
| **A Volley Before Dawn** | 2C for temporary −2 on a Force with an Archer in its Front | 2C for **Shaken** on such a Force | Archer basic Attacks now Shake Rear; the Tactic's distinction is reaching **any opposing row** with an Archer enabler |
| **Shared the Spoils With** | 1C, zero Strength, rare Exhaustion-based Command transfer | 1C, zero Strength, move a Raider/Skirmisher when a foe here is Shaken | A tactical opening instead of compounding the loser's persistent Command deficit |
| **Brannoc** | Named completion removes an attachment from an Exhausted enemy | Named completion removes from a **Shaken** enemy; 2C Name and its repeatable paid ACTION unchanged | Uses the now-accessible attack condition without smuggling in a new once-per-Battle limit |

These changes **replace** effects; they do not add abilities on top of
older text. No new markers, Attack allowances, mission phases, row labels,
or player-rulebook exceptions were introduced.

## Other-card mechanism review

| Family | Count | Economic and mechanical finding | Remaining watch |
| --- | ---: | --- | --- |
| Force | 33 | Formula checked individually; differentiated line, Guard, Archer, Raider, Rider, Skirmisher, Scout, command and support jobs | Do free-Attack combinations create more than their +1 Command premium's worth of tempo? |
| Bond | 24 | All cost **1C**; positive Strength and non-Strength tactical Bonds compete for an Action. Replaced one persistent Command drain with a movement decision. | **Seized the Standard Of** can still be unusually efficient at returning an enemy's permanent Bond for 1C |
| Name | 20 | Prices 1–4C; Named completion, recurring ACTION, and classification transfer remain distinct. Brannoc updated. Edrin's marker prevention is already **once per Battle**, not unlimited. | Price/value of permanent discount engines (Namar, Iven, Oren) and effects that require prepared targets |
| Hero | 11 | Separate Force/Name prices and one-Hero-per-mode-from-hand allowances retained; no blanket increase to their Name modes | Strong King/Steward effects versus the still-valuable low-cost alternative Name choice |
| Tactic | 14 | All target the opponent; costs 0–2C. Archer's new Shake exposed an old −2 Tactic as insufficiently distinct; fixed. | Generic attachment returns may overwhelm investment in building Named Formations |
| Stratagem | 11 | Still one from hand per Battle, with a single simultaneous reveal window. Counterattacks consume unused Attack allowance. | Very high late-Battle swings, especially **The Trap Closed**, **The Archers Were Ready** and tie plans |
| Narrative | 12 | Battle-duration effects and existing four-card cap remain. No new event chain. | **The Long March** and **The Raiders Came Home Loaded** can amplify mobility/discounts across multiple Forces |
| Order | 6 | Five cost 0C, one costs 1C; each still consumes a normal play Action. Orders remain friendly utility rather than a free third Action. | Low-Command late Battles may favour repeated 0C Orders over investing in new Forces |

### Interaction checks after Archer/Incursion

1. **Attack → Shake → Raid.** Shaken subtracts 2 Strength, so a 4-Strength
   Raider may now outmatch a formerly 5-Strength Frontline defender.
   Its Incursion still consumes its **one normal Attack** and only targets
   opposing Middle or Rear. At equal Strength, the defender holds.
2. **Archer → Shaken → guard opening.** Shaking a Middle Guard disables
   screening; a basic Archer only targets Rear (unless a card says otherwise).
   A Volley Before Dawn supplies an Archer-enabled way to hit Middle
   without pretending to be a free Archer Attack.
3. **Shaken attachments.** Black Pursuers, Brannoc and The Trap Closed now
   have viable, distinct Shaken/negative-marker payoff routes, but require
   different class, Action or completion commitments. Avoid automatically
   returning multiple attachments in a single resolution.
4. **Exhaustion remains purposeful.** The Baggage Was Abandoned, They Were
   Gathering There and The Crows Came Down still create Exhaustion.
   Healing and lost-Front recovery therefore retain targets. Not every
   card should be converted to Shaken.
5. **Maneuver / free Attack.** Grey Riders, Vardai and Damar grant specific
   combinations. A normal Maneuver does **not** grant an Attack; no card
   refreshes an already used Attack. An unused free Attack is still a
   single Attack, not a chain.
6. **Persistent attrition.** Under the subsequent Opening Orders
   revision, each lost Front costs Command equal to its final
   **Strength difference**, while still Exhausting only one chosen
   Force for the next Battle (Guarded may prevent Exhaustion). This
   changes Command economics substantially and requires new playtests.
7. **Card types stay comprehensible.** New opportunities live primarily
   in short PLAY/ACTION/CONTINUOUS card text, not extra procedures in the
   short rulebook. No new role badges are printed; every Force has a
   *design* role in `tactical-force-roles.json`.

### Targeted affordability risks

- A powerful **4C** Damar competes with a **4C** Grey Riders but differs:
  Damar grants a one-time Move to an ally and an Attack *only if the target
  becomes legal*; Grey Riders grants its own flexible Maneuver permissions
  and can spend its normal unused Attack after Maneuver.
- Odd-Strength **3C** Aradai and Thirty Spears must not strictly dominate
  one another: Aradai affects the opposing Frontline and can Raid; Spears
  provide an unconditional-class allied +1 if an ally exists.
- Odd-Strength **4C** Fifty Men do not replace Red Shields at the same cost:
  Fifty gets transient deployment Strength; Red Shields has Guard
  screening and an ongoing Frontline Tactic tax.
- Changing 2C Thirty Spears to 3C adds **3C** to the 48-card *Last Watch*
  deck (three copies), alongside **2C** for two Damar. The Last Watch's
  total printed Command rises **91–95 to 96–100**, but these totals are
  entire-deck sums, not the Command available each turn.
- The 48-card Raw Strength Control adds **4C** (four Spears) and now has
  short printed effects on three of its four Force identities. It is a
  **low-complexity Force control**, no longer an ability-free experiment.

## Required evidence before more repricing

Run matched real-paper drills from
[`physical-rule-playtest-scenarios.md`](physical-rule-playtest-scenarios.md).
Record individual *legal* Attack and Maneuver opportunities and the
best alternative use of the Action. Capture Command after each Battle,
Front reversals triggered by Shaken/Incursion, blocked raids on ties,
attachment losses, and whether a player losing early Fronts can recover.

**Limit:** all 131 printed identities, current prices, type interactions
and these regression cases have been audited *statically*. No paper-rules
compatible AI win-rate study has been completed, and static consistency
cannot prove that all cards are equally attractive or that comeback
rates are healthy.

## Subsequent battlefield-agency revision

The later [Non-Force battlefield review](nonforce-battlefield-review.md)
extends this price-focused snapshot with a role evaluation of every
Bond, Name, Hero, Tactic, Stratagem, Narrative and Order. Eighteen
effects were revised for immediate repositioning, Attack
opportunities and actionable information. Existing prices, the
131-card ceiling, core player rules and no-routine-casualties
principle were preserved. This earlier audit's statements about
individual old effects are historical, not the current card text.
