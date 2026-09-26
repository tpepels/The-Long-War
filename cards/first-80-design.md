# First 80 - card design

This file records approved card-design batches for the first 80-card set.

It is a design source, not yet canonical engine data. Move an approved card into `cards/cards.json` only when the canonical engine can represent its full rules text without display/engine divergence.

Costs and Strength values are provisional unless explicitly locked later.

## Batch 1 - Baseline

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text | Design role |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | **The Fifty Men** | Force - Human, Warband - Swordsman | 2 | 4 | - | Baseline Frontline Force. |
| 2 | **Seven Black Ships** | Force - Ship, Fleet - Ship | 2 | 4 | - | Baseline Rear Force. |
| 3 | **The White Hands of Elara** | Force - Human, Healer | 1 | 2 | **Deploy - Rear only.** | Baseline support Force. |
| 4 | **Stood Fast With** | Bond | 1 | - | **This formation gets +2 Strength.** | Pure baseline Bond. |
| 5 | **Followed** | Bond | 1 | - | **This formation gets +1 Strength. While it is Named, it gets +2 more.** | Teaches the value of completing a Named Formation. |
| 6 | **Namar** | Name - Human, King - Unique | 1 | +1 | **When this formation becomes Named, regain 1 Command.** | Simple completion payoff. |
| 7 | **Oren** | Name - Human, Warrior - Unique | 2 | +2 | **When this formation becomes Named, draw 1 card.** | Simple completion payoff with card flow. |
| 8 | **Avaros, the Bronze King** | Hero - Human, King - Unique | 3 | Force: 5 | **Force:** Swordsman. **Deploy - Frontline only.** After Avaros Maneuvers, you may Maneuver one adjacent friendly Named Formation without paying Command. **Name:** When this formation becomes Named, you may Maneuver it once without paying Command. | Maneuver-focused Hero; both modes change board position rather than adding Strength arithmetic. |

### Batch 1 notes

- **The Fifty Men** and **Seven Black Ships** establish the basic positional baseline. Their positional effects are printed explicitly on the cards.
- **The White Hands of Elara** is intentionally simple. Its final cost may need tuning because Healer converts Rear presence into effective Front strength.
- **Stood Fast With** is intentionally plain. The set needs uncomplicated Bonds that establish the baseline value of a Bond.
- **Followed** is conceptually approved; the +1 / +2 numbers remain balance targets rather than locked values.
- **Namar** is allowed to be unusually Command-efficient as a distinctive completion reward, but this should not become a common pattern.
- **Oren** is conceptually approved; its persistent value plus card replacement should be tested carefully.
- **Avaros** should remain about Maneuver and battlefield command, not generic Strength bonuses. His exact wording may be tightened once card-triggered Maneuver is represented in the engine.

## Design guardrails established so far

- Prefer cards that interact with existing core rules instead of introducing new subsystems.
- Avoid arithmetic-heavy designs whose main identity is stacking Strength modifiers.
- Most cards should do one clear thing.
- Role and classification names never substitute for rules text. If a card has a mechanic, the complete mechanic is printed on that card.
- Bond titles should normally form a grammatical phrase between the Force and a future Name: `Force + Bond + Name`.
- Prefer short, literal card text over new vocabulary or compressed rules language. A player should normally understand an effect from the card without checking the rulebook.
- Prefer player-facing phrases such as **when comparing Strength** over abstract rules terms such as **when this Front is resolved**.
- No new universal counters, wounds, exhaustion, Renown, veteran state, movement points, resources, phases, or hidden memory state.
- Use canonical timing language consistently: **when you play**, **when this formation becomes Named**, **while**, **after this formation Maneuvers**, **when this formation Retreats**, **when this formation is driven off**, **at Battle end**.
- **Maneuver** means the core named movement action; **move** is reserved for card-effect movement that does not automatically inherit Maneuver rules.
- Direct opponent Command destruction should be rare or absent from the first set.
- Temporary effects must state their duration.
- Stories are public; each player may have at most **2 ongoing Stories**.


## Batch 2 - Positioning

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 9 | **The Red Shields** | Force - Human, Guard - Spearman | 2 | 4 | **Deploy - Frontline only.** While this Force is in the **Frontline**, if a friendly Force is directly behind it, this Force gets +1 **Strength**. |
| 10 | **The Crow Archers** | Force - Human, Company - Archer | 2 | 4 | **Deploy - Rear only.** While this Force is in the **Rear**, if a friendly Force is directly in front of it, this Force gets +2 **Strength**. |
| 11 | **The House of Reed** | Force - Place, Stronghold | 2 | 3 | **Deploy - Rear only.** This Force cannot move, Maneuver, or swap positions. If you lose this Front while you have a Named Formation in the Frontline, drive off this Force instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force - Human, Riders - Skirmisher | 2 | 2 | This Force may **Maneuver** even while not Named. When Fronts are resolved, choose this Front or one adjacent Front. The Grey Riders contribute their Strength to the chosen Front instead of their own. |
| 13 | **Guarded** | Bond | 1 | - | Opponent card effects cannot move this formation. |
| 14 | **Marched With** | Bond | 1 | - | When you play this Bond onto a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name - Human, Seer - Unique | 1 | +1 | Whenever an opposing formation in this Front becomes Named, your next Maneuver this Battle costs 0 Command. Additional triggers do not accumulate. |
| 16 | **Elian** | Name - Human, Wanderer - Unique | 1 | +1 | When this formation becomes Named, you may swap it with an adjacent friendly formation. |

### Batch 2 card-text principle

Stronghold and Skirmisher are useful labels, but their mechanics are printed in full on every card that uses them. The player never needs a role lookup table to know what a card does.

### Batch 2 notes

- **The Three Brothers of Avar** were not included in this approved batch; the Skirmisher slot adds more positional vocabulary.
- Stronghold is intentionally low-Strength. Its value is defensive structure, not winning through raw arithmetic.
- Skirmisher creates lateral pressure without attacks, damage, wounds, or a separate combat step.
- Iria changes Maneuver cost rather than moving automatically. Her discount lasts only for the current Battle and does not accumulate.


## Batch 3 - Maneuver

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 17 | **The Dust Riders** | Force - Human, Riders - Skirmisher | 2 | 2 | This Force may **Maneuver** even while not Named. When Fronts are resolved, choose this Front or one adjacent Front. The Dust Riders contribute their Strength to the chosen Front instead of their own. After this Force **Maneuvers** into an empty position, you may move an adjacent friendly formation into the position it left. |
| 18 | **The Black Company** | Force - Human, Company - Swordsman | 2 | 4 | **Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. After this formation swaps positions during a **Maneuver**, you may **Maneuver** the formation it swapped with for 0 Command. |
| 19 | **Kept Pace With** | Bond | 1 | - | After an adjacent friendly **Named Formation** Maneuvers away, you may move this formation into the position it left. |
| 20 | **Covered the Withdrawal of** | Bond | 1 | - | When an adjacent friendly formation **Retreats**, after that Retreat resolves you may **Maneuver** this formation for 0 Command. |
| 21 | **Teren** | Name - Human, Captain - Unique | 2 | +1 | After this formation **Maneuvers**, you may swap two adjacent friendly formations other than this one. |
| 22 | **Mara** | Name - Human, Scout - Unique | 1 | +1 | When an opposing formation **Maneuvers** into this Front, you may **Maneuver** this formation for 0 Command. |
| 23 | **Blocked the Road for** | Bond | 1 | - | Opponent card effects cannot move formations into this Front from an adjacent Front. |
| 24 | **The Long March** | Story - Saga - Ongoing | 2 | - | **Ongoing.** The first **Maneuver** you make each turn costs 0 Command if it moves a formation into an empty position rather than swapping. |

### Batch 3 notes

- Movement effects use **move** when they are card-effect movement and **Maneuver** only when they invoke the core Maneuver action.
- The Dust Riders print the complete Skirmisher mechanic; the label itself carries no hidden rule.
- The Black Company prints its positional Swordsman effect; the label itself carries no hidden rule.
- **The Long March** is intentionally the most experimental card in the batch and tests whether recurring movement economy creates useful battlefield activity without making position trivial.


## Batch 4 - Combat

Status: draft for review.

This batch deliberately expands what can happen when a Front resolves without introducing hit points, wounds, damage tracking, or a separate attack phase. Every combat mechanic is printed in full on the card; labels such as Duelist or Raider do not carry hidden rules.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 25 | **The Red Duelists** | Force - Human, Duelists | 2 | 3 | **Deploy - Frontline only.** When comparing Strength in this Front, ignore Rear formations. |
| 26 | **The Thornbow Hunters** | Force - Human, Hunters - Archer | 2 | 1 | **Deploy - Rear only.** While in the Rear with a friendly Force directly ahead, this Force gets +2 Strength. When resolving this Front, you may choose an opposing Rear Force. It does not contribute Strength this resolution. |
| 27 | **The Iron Boars** | Force - Human, Raiders - Swordsman | 3 | 3 | **Deploy - Frontline only.** While in the Frontline, this Force gets +1 Strength. If you win this Front while the opponent has no Force in the Rear, drive off their Frontline Named Formation instead of Retreating it. |
| 28 | **The First Spear** | Force - Human, Guard - Spearman | 3 | 3 | **Deploy - Frontline only.** While in the Frontline with a friendly Force directly behind it, this Force gets +1 Strength. Before Strength is compared, you may choose an opposing Frontline Force with lower printed Strength. It does not contribute this resolution. |
| 29 | **Held the Line for** | Bond | 1 | - | Before Strength is compared, you may discard this Force and all attached cards. If you do, choose one opposing formation here. It does not contribute Strength this resolution. |
| 30 | **Seized the Standard of** | Bond | 1 | - | When this formation wins its Front and an opposing Frontline Named Formation Retreats, after the Retreat return that formation's Bond to its owner's hand. |
| 31 | **Asha, the Shield-Bearer** | Name - Human, Shield-Bearer - Unique | 1 | +1 | When an opponent's combat effect would make another friendly formation in this Front not contribute Strength, you may have this formation not contribute instead. The other formation contributes normally. |
| 32 | **The Ground Was Held** | Stratagem | 2 | - | **During this Battle**, when a Front is tied, if exactly one player has a Named Formation in the Frontline there, that player wins the Front. Otherwise the Front remains tied. |

### Mechanics under test

- **Frontline-only resolution** - Rear formations in that Front do not contribute Strength during resolution.
- **Skirmish / suppression** - stop a specific enemy formation contributing without damaging it.
- **Breakthrough** - convert a favorable battlefield shape into a harsher Retreat result.
- **First strike** - neutralize a weaker opposing Force before comparison.
- **Sacrifice** - give up your own formation to neutralize an enemy formation for the resolution.
- **Capture** - winning combat can disrupt the identity/structure of a retreating formation.
- **Interception** - redirect an enemy combat effect onto another friendly formation.
- **Tie control** - battlefield presence can matter when raw Strength is equal.
