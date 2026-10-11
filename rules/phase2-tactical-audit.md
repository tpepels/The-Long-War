# Phase 2 tactical audit — paper D6 edition

*11 October 2026 · pre-playtest design analysis · paper-only. Not an AI or engine balance result.*

## What Phase 1 actually supports

- **Battle Plans:** Assault moves after combat; Hold can withdraw and widen protection; Volley opens rank targets only for Archers; Raid moves and opens deep targets for Raiders/Riders/Skirmishers. **There is no explicit plan-vs-plan counter**. With no relevant roles, Volley and Raid are frequently weaker than Assault or Hold.
- **Position:** each of Frontline, Middle and Rear initially counts **one** for Front control, regardless of rank. A Guard's Protect, an Archer's targeting and a mobile Force's Raid reach are mostly determined by printed text or the Plan, *not* by where the Force stands. Rear often has no reason to differ from Middle.
- **Combos:** a Guard's rolled Protect can keep an Archer alive; an Archer can target an opposing Healer under Volley; a Raider can bypass a Frontline under Raid. These are real synergies but only when the appropriate die face and plan coincide.
- **Movement:** unconditional Assault advance can happen after an unsuccessful combat, while successfully defending under Hold (or killing support under Volley) opens no comparable advance. Full Fronts frequently leave no empty square for movement.
- **Constraints:** 44 Force/Hero identities (8 Guards, 3 Archers, 15 mobile Raiders/Riders/Skirmishers, 4 Healers/Stewards); many have legal-row restrictions. Preserve all existing Force, Command costs, faces, combat outcomes, permanent casualties and majority scoring until Phase 3.

## Complete matchup audit (all sixteen)

Rows are **your Plan**; columns are your opponent's. “Counter” is a directional tactical advantage **if you have an appropriate rolled Strike or Protect**, not an automatic battle victory. Strong predictions matter, but dice, rows and card composition still matter.

| Yours \\ Theirs | Assault | Hold | Volley | Raid |
| --- | --- | --- | --- | --- |
| **Assault** | Mirror: both seek forward positions after combat | **Countered by Hold**: reactive defence vs your frontal attack | **Counters Volley**: break a shooting formation before its support prevails | Neutral: Assault pushes forward; Raid pressures flanks |
| **Hold** | **Counters Assault**: protected ranks can absorb direct pressure | Mirror: protection and defence movement | Neutral: Hold screens survivors; Volley threatens back-rank specialists | **Countered by Raid**: mobile bypass risks exposing the defended rear |
| **Volley** | **Countered by Assault**: exposed Archers face a frontal push | Neutral: ranged targeting tests deep protection | Mirror: both armies seek specialist targets | **Counters Raid**: Archers punish the mobile squad's commitment |
| **Raid** | Neutral: mobile redeployment vs frontal advance | **Counters Hold**: bypass the strong Frontline to reach support | **Countered by Volley**: exposed mobile units face ranged focus | Mirror: lateral moves and deep attacks on both sides |

**Two neutral pairs** (Assault/Raid and Hold/Volley) and **four directional counter pairs** are deliberate: a four-plan system cannot make every unordered pairing a balanced, asymmetric rock-paper-scissors win without making some plans systematically favoured. Mirror games never grant a counter benefit. The cycle is **Hold > Assault > Volley > Raid > Hold**. The opponent cannot change plans after seeing yours.

## Proposed single shared counter rule: Tactical Read

When your revealed Plan counters the opponent's, you may use **one Tactical Read in each occupied Front** after dice are rolled. Select **one** of your eligible rolled results in that Front:

- **Read Strike:** one *ordinary*, unqualified Strike may target any occupied enemy rank and **ignores one Protect** assigned to it. It does not pierce Evade or Rescue, grant Force, or change a fixed-target Special. If declared as Pressure instead, it cannot also pierce Protect and gives no coordination bonus.
- **Read Protect:** one Protect cancels **one additional damaging Strike against one of its normally eligible friendly targets**. Its original printed capacity and reach remain in force; the Read adds capacity only. It cannot cancel Pressure, Evade or Rescue.

Choose during the usual target/protection declaration, not in a separate timing phase. **No Read is available if you rolled neither an eligible ordinary Strike nor Protect.** Do not create a marker or reroll. A successful counter is powerful but remains contingent on the actual die and army composition.

This one rule is preferable to inventing four different special-case attacks or protection schemes for the four Plans. It also keeps the strong-counter advantage separate from ordinary rank/role interactions: the chosen army-wide Plan predicts an opponent's Plan, while individual Forces determine *how* to exploit that prediction.

## Rank × role audit and constrained changes

| Role / position | Before Phase 2 | Phase 2 positional interaction | Explicit non-effect |
| --- | --- | --- | --- |
| **Guard — Frontline** | Printed Protect may restrict recipients | On a rolled Protect, the Guard may protect **any Force in its own Front**, without changing cancellation capacity | No passive protection, extra die face or new attack |
| **Archer — Middle/Rear** | Volley opens all ranks at any location | Only an Archer in **Middle or Rear** gets Volley's open-rank targeting | Printed fixed-rank Special still works in any legal row |
| **Raider/Rider/Skirmisher — Frontline/Middle** | Raid opens Middle/Rear from any position | Only a mobile Force in **Frontline or Middle** gets Raid's open-rank targeting | A Rear mobile Force may still make the regular Raid lateral movement |
| **Healer/Steward — Rear** | Printed Rescue often says “foremost” | A rolled Rescue may save **any friendly Force in its own Front** without adding targets | Printed adjacent-Front Special reach remains unchanged; Middle-row Healers retain their printed limits |
| **Other roles / ranks** | Printed effect only | Remain defined by their card and Plan; other placement may matter for screening and target eligibility | No surprise automatic stat bonuses |

A printed **fixed-target Special** overrides a role's regular plan targeting; a printed **adjacent-Front Special** remains the only permission for cross-Front support or attack. No new rank markers or Force modifiers.

## Limited post-combat opportunities

Each player may make at most **one forward rank-step move per Front after casualties**; this includes a printed Special advance or a plan/opportunity advance. It must enter an **empty rank after casualties on that player's side**, obey placement restrictions, and use an unpinned surviving Force that has not already moved during this Battle.

A post-combat **Opportunity** is earned in that Front if at least one of your damaging Strikes **permanently defeated** an enemy Force there, **or** one of your Protect/Evade cancelled an incoming damaging Strike there, **or** your Rescue prevented a defeat there. A saved enemy is not a casualty. Ordinary Pressure, the mere presence of a Guard, a failed damaging Strike and a plan counter by themselves do **not** earn an Opportunity.

- **Assault** retains an unconditional post-combat forward step, but gets **no second move** from an Opportunity.
- **Hold / Volley / Raid** may make the one forward step only if they earned an Opportunity, or if an eligible card's printed Special explicitly orders it; that Special uses the same one-step allowance.
- Forward movement is optional, only after casualties, and cannot enter an inactive Front, leap over occupied ranks, swap, or cross the battle line.

This gives defence and specialist attacks a modest path to improved positioning without changing headcount scoring or adding resources. If every rank is occupied, the Opportunity is simply unusable.

## Failure conditions to check in Phase 3 playtests

1. Tactical Reads are too effective: even a single ignored Protect may produce excessive permanent casualties.
2. The **two neutral pairs** lead to dull mirrors or default Assault selection.
3. Guards or Healers are indispensable in every deck because of new rank reach.
4. Most Fronts remain fully occupied, making advances irrelevant despite success.
5. Read Strike plus fixed-rank Specials causes ambiguity; printed Specials always retain their printed targeting.
6. An automatic one-step advance changes position, **not** majority control directly. Cheap-body flooding may still dominate.

No matchups or probability outcomes were simulated in the engine. This is a qualitative **16/16 matchup audit and testable paper-only proposal**, not a claim of statistical balance.
