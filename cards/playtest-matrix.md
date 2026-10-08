# Playtest and archetype matrix

**Current canonical pool:** 131 cards, 14 classifications, 146 printed effects. Counts are recalculated from `cards/cards.json` on 8 October 2026, after retiring Builder, Heir, Spearman and Veteran.

This is an **advisory design audit**, not a balance verdict or a merge/deployment test. Card classifications are carried in `classes`; printed effects and executable `design_rules` determine what cards actually do. The retired `references` metadata is not used.

## Authored design themes

The following counts are distinct cards carrying each `design_tags` label, not measured effectiveness or automatically compiled mechanics. In particular, historical labels such as `reserve` do **not** establish that a keyword remains in the current rules.

| Design tag | Cards |
|---|---| 
| Named Payoff | 33 |
| Marker State | 32 |
| Classification Synergy | 26 |
| Command | 25 |
| Baseline | 20 |
| Formation Building | 20 |
| Hostile Interaction | 19 |
| Exhaustion | 18 |
| Positional Support | 18 |
| Action Engine | 17 |
| Card Flow | 17 |
| Movement | 17 |
| Simple | 16 |
| Strength | 16 |
| Information | 13 |
| Command Recovery | 11 |
| Hidden Plan | 11 |
| Persistent State | 11 |
| Protection | 10 |
| Army Support | 9 |
| Prepared Cards | 9 |
| Suppression | 9 |
| Single Ability Name | 8 |
| Raids | 7 |
| Tax | 7 |
| Zero Command | 5 |
| Flank Defense | 4 |
| Healing | 4 |
| Positional Interaction | 4 |
| Archer | 3 |
| Play Effect | 3 |
| Battlefield | 2 |
| Exposure | 2 |
| Logistics | 2 |
| Magic | 2 |
| Attachment | 1 |
| Flanking | 1 |
| Forced Movement | 1 |
| Formation Disruption | 1 |
| Geography | 1 |
| Middle Only | 1 |
| Oaths | 1 |
| Prepared | 1 |
| Reaction | 1 |
| Recovery | 1 |
| Reserve | 1 |
| Scouting | 1 |

## Printed effect timings

These count effect records in `effects` and all Hero `modes`, rather than counting one card once per timing.

| Timing | Effects |
|---|---| 
| Play | 39 |
| Becomes Named | 31 |
| Action | 27 |
| Continuous | 12 |
| Hidden | 11 |
| Bonded | 9 |
| While Named | 4 |
| Trigger | 4 |
| Front | 3 |
| Rear | 2 |
| Middle | 2 |
| Mobile | 1 |
| Tireless | 1 |

## Printed memory requirements

These count `memory` annotations on printed effects; a card may have multiple effects or require more than one memory indicator.

| Representation | Effects |
|---|---| 
| Used Marker | 21 |
| Effect Marker | 11 |
| Face Up Source | 11 |
| Face Down Source | 11 |
| Suppression Marker | 6 |
| Front Marker | 6 |

## Classification support

**Carriers** are distinct canonical cards with the classification. **Positive references** are distinct cards explicitly mentioning the classification in their *effect text* without treating that classification as the opposing target. **Hostile references** are explicit effects that target an opposing classification. A card may reference more than one class. These are **opportunities**, not a count of playable synergies or a measure of balance. A Hero is counted once even though it has two modes. General “choose one classification” text is not counted toward any specific class. Basic Attacks and Guard screening are shown separately.

| Classification | Layer | Carriers | Positive references | Hostile references | Intrinsic role |
|---|---|---|---|---|---| 
| **Human** | Kind | 60 | 4 | 0 | — |
| **Ship** | Kind | 2 | 1 | 0 | — |
| **Stronghold** | Kind | 2 | 3 | 0 | — |
| **Guard** | Role | 9 | 2 | 1 | Screening |
| **Raider** | Role | 8 | 4 | 0 | Basic Attack |
| **Scout** | Role | 7 | 8 | 0 | — |
| **Rider** | Role | 6 | 3 | 0 | Basic Attack |
| **Skirmisher** | Role | 6 | 4 | 0 | Basic Attack |
| **Steward** | Role | 5 | 2 | 0 | — |
| **Archer** | Role | 4 | 8 | 0 | Basic Attack |
| **Healer** | Role | 3 | 3 | 0 | — |
| **Seer** | Role | 3 | 2 | 0 | — |
| **Captain** | Rank | 9 | 6 | 1 | — |
| **King** | Rank | 4 | 4 | 1 | — |

### Interpreting the counts

- **Ship:** 2 carriers (Seven Black Ships; The Salt-Road Fleet); 1 reference (Before Sunset, the Ford Would Be Ours). Both carriers are also Raiders. The one reference competes with the Scout option and provides no uniquely naval effect. The exploratory decks do not put this Ship-specific reference and a Ship carrier into the same deck.
- **Seer:** 3 carriers (Iria; Yara, the Chronicler; Lysa the Listener); 2 references. Both shared Scout-or-Seer effects inspect opposing Stratagems. These cards have their own useful text, but the Seer classification has little unique deck-building identity.
- **Steward:** 5 carriers; 2 references (Catch Your Breath; Take Stock). Several Steward cards already have strong logistical identities through their *own* effects; the weakness is external synergy, not necessarily their strength.
- **Healer:** 3 carriers; 3 references (They Lived to Tell It; Catch Your Breath; Bind the Wound). This support is concentrated on removing Exhaustion or other adverse markers, and multiple effects compete for a narrow set of situations.
- **Stronghold:** 2 carriers; 3 apparent references. The Wall Did Not Break concerns Exhaustion *from flanking*, which is not produced by a rule or card currently found in the canonical pool, making its support suspect. The Flank Was Refused works only in an outer Front.
- **Archer:** 4 carriers and 8 references, including benefits printed on Archer cards themselves. The Crows Came Down, A Volley Before Dawn, and The Wolf Skirmishers all use effectively the same “friendly Archer present → Exhaust an opposing Force” effect. Depth is less than the raw total suggests.
- **Guard:** 9 carriers with the built-in screening rule. Of its 3 references, 1 is hostile (The Line Was Baited) and 1 protects against the possibly nonexistent flanking-Exhaustion event.
- **King/Captain:** respectable counts, but most effects treat King and Captain as alternatives; one shared Tactic, All Banners Forward, is hostile. Count this as broad leadership synergy, not exclusive King differentiation.
- **Rider, Skirmisher, Raider:** their basic Attacks grant a clear role even when references are fewer. Scout and Human serve broader support and baseline roles. Do not force symmetry among classes.

## Urgent mechanical dead-end: flanking Exhaustion

The current rulebook states that *flanking does not automatically inflict Exhaustion*. No canonical card currently creates Exhaustion **because a Force was flanked**; Rider basic Attacks inflict Shaken, not Exhaustion. The following protection text therefore appears to have no triggering event:

1. **The Banner Singers:** While Named and in Middle, flanking cannot Exhaust the friendly Force directly ahead.
2. **Held the Line for:** While Bonded, flanking cannot Exhaust its Force.
3. **Supported By:** While Bonded and in Middle, flanking cannot Exhaust the friendly Force directly ahead.
4. **The Wall Did Not Break:** Guards and Strongholds cannot become Exhausted from flanking this Battle.

These must be reconciled with the current flanking and Attack rules before judging Guard/Stronghold protection strength. Prefer **replacing the four ineffective abilities with useful existing positional/protection effects**, not introducing an extra universal flanking penalty merely to make these cards work.

## Recommended design queue

1. **Repair the four flanking-Exhaustion protections first.** This affects four cards and removes a misleading promise from their printed text.
2. **Give Ship a distinct reason to exist.** Review the two Ship/Raider Forces and rework a low-impact or repetitive effect to interact meaningfully with Ships (movement, attachments, or adjacent Fronts). Prefer repurposing an existing card over creating an isolated Ship-only support card.
3. **Differentiate Seer from Scout.** `They Knew the Ground` and `The Scouts Had Warned Them` currently overlap as Stratagem-information support. Rework one toward a distinct information/timing payoff while preserving Scout utility.
4. **Reduce Archer effect duplication.** Keep the basic Archer Attack and at least one Archer-enabled Exhaustion effect; repurpose the weaker of `The Crows Came Down`, `A Volley Before Dawn`, and `The Wolf Skirmishers` for a different positional consequence.
5. **Separate Healer effects by decision and target.** Compare `They Lived to Tell It` with `Bind the Wound`, and test `Catch Your Breath`; keep the persistent Narrative vs one-shot Order distinction only if it creates genuine decisions.
6. **Evaluate `The Line Was Baited` after the removal of Spearman.** It now needs an opposing Guard and a friendly Skirmisher in the same Front. Test whether that is too narrow for a Tactic; a positional target may be healthier if its gameplay frequency is low.
7. **Improve support distribution before adding cards.** `Before Sunset, the Ford Would Be Ours` is included in the Maneuver & Relief deck with Scouts but no Ships; Ship carriers are in Build & Chain and Pressure & Intelligence. Fix evaluation coverage so Ship-specific synergy can actually be observed.
8. **Retain viable sparse classifications for now.** Steward cards have substantial standalone effects; do not automatically add buffs or remove the class based only on its two support references. Human is deliberately broad; Rider, Raider, Skirmisher and Guard have intrinsic combat utility.

**Scope:** This report does not alter canonical card effects or add keywords/abilities. Changes to card text should be made in a deliberate card-design pass, with matching executable mechanics and printed text, and validated for usefulness and balance.

## Playtest evidence to collect

For each proposed replacement, track the source card drawn/played/dead-in-hand, whether the class condition could actually be met, whether the effect influenced movement, Attack, or a Front outcome, and whether the same outcome was available from a cheaper card. In particular, verify flanking-condition activation, Ship support activation, Seer-vs-Scout differentiation, and Archer effect duplication before adding more card designs.
