# Proposed card redesign — battlefield cohesion

**Status:** **proposal only**, for review. No changes to canonical cards, deck lists, rules, or runtime. Grounded in `cards/cohesion-mechanics-audit.md` on 8 October 2026.

## Objective

Keep **131 card identities**, existing artwork and classification vocabulary. Replace mechanically identical, dominated, or too-passive cards with **positional and formation-building choices**. Reward setups that (a) alter which forces can Attack; (b) make opening and defending a Frontline matter; (c) reposition complete formations; (d) protect, steal or attach the Force/Bond/Name layers; (e) create useful information and counterplay. Do not try to give each class an equal number of references.

No new player-facing keywords or blanket buffs. Extra code to support an expressive effect is acceptable **only** when it creates an interaction reusable across cards. Respect the no-lifting physical rule and the hard occupancy restrictions.

## Decision

- Keep **The Fifty Men** as the generic 2-Command/4-Strength Human, and **The Red Duelists** as the simple 2-Command/3-Strength Skirmisher.
- Change **16 existing cards** (6 Forces, 7 Bonds, 1 Name, 1 Stratagem, 1 Order), while retaining their identities. [CHECK: table below is canonical candidate list.]
- Resolve **four incorrectly unprinted once-per-Battle limits** before any physical reprint.
- No edits to the four intrinsic basic Attack types or Guard's existing screening rule; The Crow Archers' proposed extra target is **card-specific**.
- Treat all numerical values as **starting costs for playtesting**, not validated balance.

## Candidate replacement cards

Use these as proposed physical card faces. A text line is a **whole replacement ability**, not an additional effect. Wording must be brought into the repository's normal timing/strip style before implementation.

| Existing card | Proposed stats | Replacement card text | Why it changes play | Implementation dependency |
|---|---|---|---|---|
| **The Fifty Men** | 2 Command · 4 Strength | No special rules. | The clean Human baseline stays as a useful comparison and low-cognitive-load recruit. | — |
| **The Red Duelists** | 2 Command · 3 Strength | No special rules. | A basic Skirmisher with an intrinsic Attack; keep it straightforward. | — |
| **The Damar** | 2 Command · 3 Strength (4 → 3) | PLAY — You may move one other friendly formation in this Front one row toward its Frontline, if that position is empty and legal. | A reinforcement Force that can fill a critical open Frontline rather than a second vanilla 2/4 Human. | New friendly directional movement target |
| **The Crow Archers** | 2 Command · 3 Strength (unchanged) | ATTACK — This Force's basic Archer Attack may also target an opposing Middle Force when the opposing Frontline is empty. | Opens another target option instead of competing with the Thornbow Hunters' vision. | Attack system integration |
| **The Ilyri** | 2 Command · 2 Strength (3 → 2) | PLAY — You may move this formation one position into an adjacent active empty position, if legal. | Mobile infiltrator that trades Strength for immediate deployment flexibility; retains its Skirmisher Attack. | Existing self-move primitive on PLAY |
| **The Old Guard** | 2 Command · 3 Strength (unchanged) | MIDDLE — While this Force is in the Middle row, it screens the friendly Rear Force from basic Archer Attacks even while Shaken. Depletion still disables its screening. | Reliable veteran defense with a weakness opponents can exploit, instead of a strictly smaller Guard body. | Attack/screening extension |
| **The King's Spears** | 2 Command · 3 Strength (4 → 3) | PLAY — If this Force is played in the Middle row, you may swap its formation with the friendly Frontline formation in this Front, if both placements are legal. | A reserve Guard can relieve the Frontline immediately; cost of Strength pays for tempo. | PLAY row-specific friendly swap |
| **The Wolf Skirmishers** | 3 Command · 4 Strength (3 → 4) | PLAY — Choose an opposing Frontline Force in this Front. Move it one row toward its Rear if the destination is empty and legal. | Breaks a line itself instead of depending on an Archer not present in Build & Chain. Strong in the correct board state; no help if enemy Middle is occupied. | Existing opposing rearward move, with Frontline target |
| **Blocked the Road for** | 1 Command · +0 Strength (+1 → 0) | BONDED — Opposing card effects cannot move this formation. | Positional insurance against forced movement rather than another generic +1 Bond. | New movement-protection check |
| **Seized the Standard of** | 1 Command · +0 Strength (+1 → 0) | PLAY — Choose an opposing Bonded Formation in this Front. Return its Bond to its owner's hand. | A one-shot capture that disrupts formation completeness; opponents can play around it by separating their valuables. | Existing return-component effect with same-Front target |
| **Swore Again To** | 1 Command · +0 Strength (+1 → 0) | PLAY — If this Bond completes a Named Formation, you may immediately Maneuver that formation once without using another Action or spending Command. | A deliberate sequencing combo for prepared Force+Name stacks instead of a universally better Strength Bond. | New free-Maneuver completion effect |
| **Endured With** | 1 Command · +0 Strength (+1 → 0) | PLAY — If this position contains a Force, give that Force Guarded. | Immediate protection against the next affliction, counterable by stripping Guarded or disrupting the Bond. | Guarded Boon / native Attack-condition parity |
| **Carried the Oath of** | 1 Command · +0 Strength (+1 → 0) | BONDED — The Name attached to this formation cannot have its text suppressed. | Protects a crucial Named payoff; a situational answer rather than extra Strength. | Existing name-text suppression immunity |
| **Had Been Ordered Forward** | 1 Command · +0 Strength (+1 → 0) | BONDED — This formation may Maneuver without being Named. | An early mobility choice for any Force; complements rather than replaces the Dust Riders' innate identity. | Existing maneuver_unnamed primitive |
| **Watched the Skies For** | 1 Command · +0 Strength (unchanged) | PLAY — Draw 1 card, then put 1 card from your hand on top of your deck. | Always has a useful on-play option and allows planning the next draw, without more Stratagem-peeking redundancy. | Existing draw_put_top primitive |
| **Mara** | 1 Command · +1 Strength (unchanged) | BECOMES NAMED — Look at your opponent's hand. You may then move this formation one position into an adjacent active empty position, if legal. | Scout reconnaissance leads to repositioning; Lysa retains the simpler Scout/Seer hand-information niche. | Existing look_hand and self_move as a sequential completion effect |
| **The Lines Held** | 2 Command (3 → 2) | HIDDEN — Reveal before Strength is compared in this Front. If your Frontline is empty, you may move one of your Middle formations into it, if legal. That formation gets +2 Strength this Battle. | A visible battlefield consequence and lasting positional recovery, rather than paying 3 Command to avoid at most 2 Command of loss. | New hidden timing/compound movement + Strength |
| **Fresh Orders** | 0 Command (unchanged) | PLAY — Choose one of your Captains or Kings. Move another friendly formation in its Front one position to an adjacent active empty position, if legal. | Converts leadership into real positioning rather than spending an Action to replace one hand card with another. | Order targeting a leadership-gated friendly move |

### Important balance / usability notes

- **The Damar:** The 3-Strength floor is intentional; the free Frontline reinforcement is the reward. If this is only useful in rare empty-lane cases, expand the destination options instead of simply increasing Strength.
- **The Crow Archers:** Their extra Attack is *not* a free second Attack. They still take an Action, still Attack only once per Battle, and still obey screening and Depleted rules. This is a distinct sidegrade to The Thornbow Hunters.
- **The Ilyri:** Its free PLAY movement is one square, not a Maneuver; it may move vertically or sideways into a legal empty active position, but cannot swap occupied positions. It trades one Strength for tempo.
- **The King's Spears:** PLAY swap occurs only after its deployment into an empty Middle slot. Never violate a printed row restriction when swapping.
- **The Wolf Skirmishers:** The attacking source is itself a Skirmisher; **no Archer prerequisite**. The front displacement opens a Raider line and may be countered by occupying the destination. Recheck whether 3 Command/4 Strength is excessive if this displacement is frequent.
- **Blocked the Road for / Carried the Oath of:** Protected effects should remain understandable in the exposed Bond strip. Both have relevant opponent counters: suppress the Bond's text or choose other targets.
- **Swore Again To:** The free Maneuver is granted *only* when playing this Bond **immediately completes** Force+Bond+Name. Preparing the Bond early does not reserve a free move. Enforce normal adjacency, activation and row legality.
- **Endured With:** Guarded is a *single temporary Boon* preventing the next affliction, not unlimited immunity and not protection from card-driven movement or attachment removal. If played prepared, it has no immediate Force to affect and supplies no deferred trigger.
- **The Lines Held:** The Stratagem is defensive, but its action changes the material of the battlefield, not just the Command ledger. The opponent can occupy its Middle/Front interactions or use a Scout to challenge the hidden plan. The +2 Strength is a proposed payoff, not a universal new rule.
- **Fresh Orders:** An Order still consumes a card and an Action even at 0 Command. The leader must already be present, and only one other friendly formation is moved. It is not free deployment of a new card.

## Four text/engine corrections (independent of redesign)

Do **not** rebalance these four abilities yet. All four already have `limit: once_per_battle` in executable `design_rules` but omit that limit on their printed ACTION text:

| Card | Required printed timing |
|---|---|
| The Crows Came Down | `ACTION · 1/BATTLE` |
| No Road Was Too Long | `ACTION · 1/BATTLE` |
| No One Would Be First to Leave | `ACTION · 1/BATTLE` |
| The King Had Given the Order | `ACTION · 1/BATTLE` |

Update `text`, `effects[].limit`, `rule_blocks`, catalogue and renderer-facing representations together. Correct the printed limitations without making the executable ability unlimited.

## Deck-archetype and combo coverage

**Breach / infiltration:** The Wolf Skirmishers or The Line Was Baited moves a defender away; Raider basic Attack can Deplete an exposed Middle/Rear Force. An Archer (including the proposed Crow Archers) chooses a support target, while **Blocked the Road for** defends the line against hostile displacement. This must be playable with 2 Actions across one or more turns, and the defender can answer by filling Middle.

**Frontline rotation / relief:** **The Damar**, **The King's Spears**, **The Old Guard**, and the revised **Fresh Orders** offer different ways to keep a Frontline alive. Opposing player can exploit empty ranks, suppression or an alternative Front. Neither +1 Strength nor an automatic win should be the default result.

**Formation-building burst:** **Swore Again To** completes a Named Formation and grants an immediate Maneuver; The Field Train, Nara and Torren handle prepared layers. **Carried the Oath of** protects the Name's ongoing text. Opponent can remove an attachment or suppress a Bond before a planned sequence.

**Mobile reconnaissance:** **Mara** sees the hand then repositions, **The Ilyri** shifts on deployment, **Watched the Skies For** improves the next draw. **The Lines Held** turns hidden information into a positional countermove rather than another +Strength-only trap.

**Attrition / resilience:** The Old Guard keeps screening while Shaken, **Endured With** grants one Guarded prevention, and Healers still remove negative states. They should not neutralize Depleted or every Attack.

Each exploratory 48-card deck should exercise at least two complete proposed synergies **without** cards whose required class is absent. Add no card identities: exchange existing card slots and keep legal counts by family.

## Suggested implementation slices

**Slice A — exact correctness / no gameplay redesign**
1. Fix the 4 printed ACTION limits.
2. Address native signed-int8 / 128-identity constraint correctly across state, zones, hashing, serialization and tests; do not merely increase `MAX_CARDS`.
3. Complete implementation and reference tests for the four intrinsic Attacks, Guard screening, Shaken/Depleted and Guarded before attempting to interpret balance.
4. Fix orphan deck interactions, including the current Wolf Skirmishers Archer prerequisite, when updating that card/deck.

**Slice B — low-engine-risk sidegrades**
- Ilyri PLAY movement, Watched the Skies For card draw/reorder, Seized the Standard of attachment return, Had Been Ordered Forward unnamed mobility, and Mara scouting + relocation (requires sequencing validation).
- All are recognizable current effect operations; targeting/ordering and legal state transitions still require tests.

**Slice C — signature battlefield effects**
- Damar Frontline reinforcement; Crow Archers modified basic Attack; Old Guard screening resilience; King's Spears deployment swap; Wolf Skirmishers frontline displacement; Fresh Orders leadership movement; Swore Again To completion Maneuver; The Lines Held hidden reinforcement.
- Build minimal reusable low-level targeting/trigger rules; avoid one-off hidden state flags for each card.

**Slice D — physical cards and balance**
- Bond replacements Blocked the Road for, Endured With, Carried the Oath of after Guarded/suppression/movement protection behavior is verified.
- Verify all exposed Bond text is readable without lifting. Update the catalogue and playtest matrix; regenerate deck fixtures and inspect print fit.
- Playtest and then tune costs/Strength, not the other way round.

## Per-card acceptance standard

For every modified card:

1. **Useful floor:** demonstrate one ordinary board position where the card still offers a plausible Action even if its special condition is unavailable; if a Bond intentionally trades all Strength for a rare effect, label that as a tech choice.
2. **Combo:** document a concrete interaction with another existing card or intrinsic Attack that changes legal targets, occupation, attachment structure or hidden decisions.
3. **Counterplay:** specify at least one achievable response by the opponent; do not require an obscure unique card as the only answer.
4. **Implementability:** ensure printed prose, rule blocks, executable specs, native behavior and webgame descriptions mean the same thing. Unsupported mechanics cannot be silently approximated.
5. **Costs:** measure cards played, Command, Actions, expected board swing, and condition-active/use rates for Battles I/II/III+.
6. **Physical usability:** effect fits the visible Force/Bond/Name strips, marker bookkeeping is explicit, no hidden trigger memory.
7. **Pool invariant:** 131 identities, current role counts and class vocabulary unchanged, all four exploratory decks legal.
8. **Development freedom:** avoid brittle golden text/screenshot expectations that prevent normal card iteration; keep strict checks for schema, legality and runtime correctness.

## Approval boundaries

This is a **design proposal**, not approval to edit the canonical cards. Do not merge proposed changes into `cards/cards.json` until their actual playtest rules and runtime parity are understood. Once accepted, implement in small changesets and report which cards are playable in native webgame versus physical-only.
