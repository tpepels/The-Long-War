# Playtest and archetype matrix

**Current canonical pool:** 131 cards, 14 classifications, 146 printed effects. Reviewed against `cards/cards.json` on 8 October 2026, with a nine-card replacement pass after retiring Builder, Heir, Spearman and Veteran.

This is an **advisory design audit**, not a balance verdict or a merge/deployment test. Card classifications are carried in `classes`; printed effects and executable `design_rules` determine what cards actually do. The retired `references` metadata is not used.

## Authored design themes

The following counts are distinct cards carrying each `design_tags` label, not measured effectiveness or automatically compiled mechanics. In particular, historical labels such as `reserve` do **not** establish that a keyword remains in the current rules.

| Design tag | Cards |
|---|---| 
| Marker State | 33 |
| Named Payoff | 33 |
| Classification Synergy | 25 |
| Command | 25 |
| Baseline | 20 |
| Formation Building | 20 |
| Positional Support | 20 |
| Movement | 19 |
| Card Flow | 18 |
| Hostile Interaction | 18 |
| Action Engine | 17 |
| Exhaustion | 17 |
| Strength | 17 |
| Simple | 16 |
| Information | 13 |
| Protection | 13 |
| Command Recovery | 11 |
| Hidden Plan | 11 |
| Persistent State | 11 |
| Tax | 10 |
| Army Support | 9 |
| Suppression | 9 |
| Prepared Cards | 8 |
| Single Ability Name | 8 |
| Raids | 6 |
| Zero Command | 6 |
| Positional Interaction | 5 |
| Healing | 4 |
| Play Effect | 4 |
| Archer | 3 |
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
| Effect Marker | 12 |
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
| **Guard** | Role | 9 | 2 | 0 | Screening |
| **Raider** | Role | 8 | 4 | 0 | Basic Attack |
| **Scout** | Role | 7 | 7 | 0 | — |
| **Rider** | Role | 6 | 3 | 0 | Basic Attack |
| **Skirmisher** | Role | 6 | 4 | 0 | Basic Attack |
| **Steward** | Role | 5 | 2 | 0 | — |
| **Archer** | Role | 4 | 8 | 0 | Basic Attack |
| **Healer** | Role | 3 | 2 | 0 | — |
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

## Replacement pass: completed

The following nine existing cards have updated effects in the current canonical pool. All use *existing executable effect primitives*; card count remains 131, and basic Attacks and Guard screening do not change.

| Card | What replaced the old effect |
|---|---|
| The Banner Singers | Named Middle-row command protection against opposing Tactics targeting other friendly formations in the Front |
| Held the Line for | Bonded protection: opposing Tactics targeting its formation cost 1 more Command |
| Supported By | Bonded Middle-row protection for the friendly Rear formation directly behind |
| The Wall Did Not Break | Guards and Strongholds Maneuver for 0 Command this Battle |
| The Salt-Road Fleet | Transports another friendly formation toward Rear on play; Strength 4→3 to offset the broader utility |
| They Knew the Ground | Once-per-Battle top-three card selection, conditional on controlling a Seer |
| A Volley Before Dawn | Archer-enabled -2 Strength marker this Battle, instead of another Exhaustion |
| They Lived to Tell It | Once-per-Battle removal of one negative marker from any friendly formation, without a Healer restriction |
| The Line Was Baited | Costs 0 Command; a friendly Skirmisher enables displacement of any opposing Force in the same Front toward Rear |

**Why:** four flanking-Exhaustion protections had no producer under the current rules; the two Archer instant Exhaustion copies competed; narrow Seer/Healer/Skirmisher effects had poor usability. These replacements emphasize tempo, actual board positions, and different card-family costs.

**Playtest caveats:** Keep an eye on whether -2 Strength from A Volley is too strong at 2 Command; whether persistent Tactic taxes stack too much; whether free Guard Maneuvers create excessive repositioning; and whether the 0-Command The Line Was Baited has adequate counterplay. These require observation, not automatic balance gates.

## Further design opportunities

- **Ship:** Now has a movement-oriented carrier in The Salt-Road Fleet; its existing remote information Narrative is unchanged. Maneuver & Relief now includes one Salt-Road Fleet to create a Ship/support pairing.
- **Seer:** Has a distinct top-deck selection Narrative alongside Scouts' hidden-information cards.
- **Archer:** The Crows Came Down (repeatable Exhaustion) and The Wolf Skirmishers (one-time Force play) still share an effect. Assess whether different timing/costs justify keeping both before further edits.
- **Healer/Steward:** Catch Your Breath and Bind the Wound retain their distinct sources, targets, and Command costs. They Lived to Tell It is now a broadly usable Narrative instead of a third Healer-only recovery.
- **Guard/Stronghold:** Protective effects now have actual Tactic or movement interactions. Test The Wall Did Not Break with Named Guards/Strongholds.
- **Leadership:** King/Captain overlap remains intentional at present.

## Playtest evidence to collect

For each proposed replacement, track the source card drawn/played/dead-in-hand, whether the class condition could actually be met, whether the effect influenced movement, Attack, or a Front outcome, and whether the same outcome was available from a cheaper card. In particular, verify flanking-condition activation, Ship support activation, Seer-vs-Scout differentiation, and Archer effect duplication before adding more card designs.
