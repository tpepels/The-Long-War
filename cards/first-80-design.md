# First 80 - card design

This file records approved card-design batches for the first 80-card set.

It is a design source, not yet canonical engine data. Move an approved card into `cards/cards.json` only when the canonical engine can represent its full rules text without display/engine divergence.

Costs and Strength values are provisional unless explicitly locked later.

## Batch 1 - Baseline

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text | Design role |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | **The Fifty Men** | Force - Human, Warband - Swordsman | While this Force is in the **Frontline**, it gets +1 **Strength**. |
| 2 | **Seven Black Ships** | Force - Ship, Fleet - Ship | While this Force is in the **Rear**, it gets +1 **Strength**. |
| 3 | **The White Hands of Elara** | Force - Human, Healer | **Deploy - Rear only.** While this Force is in the **Rear**, the friendly Force directly in front of it gets +2 **Strength**. |
| 4 | **Stood Fast With** | Bond | This formation gets +2 **Strength**. |
| 5 | **Followed** | Bond | This formation gets +1 **Strength**. If it is **Named**, it gets +3 **Strength** instead. |
| 6 | **Namar** | Name - Human, King - Unique | When this formation becomes **Named**, regain 1 **Command**. |
| 7 | **Oren** | Name - Human, Warrior - Unique | When this formation becomes **Named**, draw 1 card. |
| 8 | **Avaros, the Bronze King** | Hero - Human, King - Unique | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. After this Force **Maneuvers**, you may **Maneuver** one adjacent friendly **Named Formation** for 0 Command. **Name -** When this formation becomes **Named**, you may **Maneuver** it once for 0 Command. |

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
- Avoid engine-facing words on card faces such as **resolve/resolution**, **contribute**, **trigger**, **accumulate**, and **combat effect** when a literal instruction such as **count**, **ignore**, **move**, or **discard** says the same thing.
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
| 9 | **The Red Shields** | Force - Human, Guard - Spearman | **Deploy - Frontline only.** While this Force is in the **Frontline**, if a friendly Force is directly behind it, this Force gets +1 **Strength**. |
| 10 | **The Crow Archers** | Force - Human, Company - Archer | **Deploy - Rear only.** While this Force is in the **Rear**, if a friendly Force is directly in front of it, this Force gets +2 **Strength**. |
| 11 | **The House of Reed** | Force - Place, Stronghold | **Deploy - Rear only.** This Force cannot move, **Maneuver**, or swap positions. If you lose this Front while you have a **Named Formation** in the Frontline, drive off this Force instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force - Human, Riders - Skirmisher | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or one adjacent Front. Count this Force's **Strength** only in the chosen Front. |
| 13 | **Guarded** | Bond | Cards your opponent plays cannot move this formation. |
| 14 | **Marched With** | Bond | When you play this Bond on a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name - Human, Seer - Unique | When an opposing formation in this Front becomes **Named**, your next **Maneuver** this Battle costs 0 Command. If this happens again before you Maneuver, you still get only one free Maneuver. |
| 16 | **Elian** | Name - Human, Wanderer - Unique | When this formation becomes **Named**, you may swap it with an adjacent friendly formation. |

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
| 17 | **The Dust Riders** | Force - Human, Riders - Skirmisher | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or one adjacent Front. Count this Force's **Strength** only in the chosen Front. After this Force **Maneuvers** into an empty position, you may move an adjacent friendly formation into the position it left. |
| 18 | **The Black Company** | Force - Human, Company - Swordsman | **Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. After this formation swaps positions with another formation during a **Maneuver**, you may **Maneuver** that other formation for 0 Command. |
| 19 | **Kept Pace With** | Bond | After an adjacent friendly **Named Formation** Maneuvers away, you may move this formation into the position it left. |
| 20 | **Covered the Withdrawal of** | Bond | After an adjacent friendly formation **Retreats**, you may **Maneuver** this formation for 0 Command. |
| 21 | **Teren** | Name - Human, Captain - Unique | After this formation **Maneuvers**, you may swap two adjacent friendly formations other than this one. |
| 22 | **Mara** | Name - Human, Scout - Unique | When an opposing formation **Maneuvers** into this Front, you may **Maneuver** this formation for 0 Command. |
| 23 | **Blocked the Road for** | Bond | Cards your opponent plays cannot move a formation from an adjacent Front into this Front. |
| 24 | **The Long March** | Story - Saga - Ongoing | **Ongoing.** Your first **Maneuver** each turn costs 0 Command if it moves into an empty position instead of swapping. |

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
| 25 | **The Red Duelists** | Force - Human, Duelists | **Deploy - Frontline only.** When comparing **Strength** in this Front, ignore Strength from Rear formations. |
| 26 | **The Thornbow Hunters** | Force - Human, Hunters - Archer | **Deploy - Rear only.** While this Force is in the **Rear**, if a friendly Force is directly in front of it, this Force gets +2 **Strength**. When comparing Strength in this Front, you may ignore one opposing Rear Force's Strength. |
| 27 | **The Iron Boars** | Force - Human, Raiders - Swordsman | **Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. If you win this Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 28 | **The First Spear** | Force - Human, Guard - Spearman | **Deploy - Frontline only.** While this Force is in the **Frontline**, if a friendly Force is directly behind it, this Force gets +1 **Strength**. When comparing Strength in this Front, you may ignore an opposing Frontline Force's Strength if the Strength printed on that card is lower than the Strength printed on this one. |
| 29 | **Held the Line for** | Bond | Before comparing Strength in this Front, you may discard this Force and all cards attached to it. If you do, choose one opposing formation here and ignore its Strength. |
| 30 | **Seized the Standard of** | Bond | If this formation wins its Front and an opposing Frontline Named Formation **Retreats**, return that formation's Bond to its owner's hand after it Retreats. |
| 31 | **Asha, the Shield-Bearer** | Name - Human, Shield-Bearer - Unique | If an opponent's card would make another friendly formation's Strength not count in this Front, you may make this formation's Strength not count instead. The other formation counts normally. |
| 32 | **The Ground Was Held** | Stratagem | **During this Battle**, if a Front is tied and only one player has a Named Formation in its Frontline, that player wins the Front. If both or neither do, it stays tied. |

### Mechanics under test

- **Frontline-only resolution** - Rear formations in that Front do not contribute Strength during resolution.
- **Skirmish / suppression** - stop a specific enemy formation contributing without damaging it.
- **Breakthrough** - convert a favorable battlefield shape into a harsher Retreat result.
- **First strike** - neutralize a weaker opposing Force before comparison.
- **Sacrifice** - give up your own formation to neutralize an enemy formation for the resolution.
- **Capture** - winning combat can disrupt the identity/structure of a retreating formation.
- **Interception** - redirect an enemy combat effect onto another friendly formation.
- **Tie control** - battlefield presence can matter when raw Strength is equal.


## Batch 5 - Persistence & Retreat

Status: draft for review.

This batch tests what survives a loss, how Retreat can change position, and how persistent formations help rebuild the next Battle. Card text remains literal and self-contained.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 33 | **Stayed Behind For** | Bond | If this Force is driven off, leave this Bond in its position instead of discarding it. If this formation has a Name, return that Name to its owner's hand. The next friendly Force played in this position takes this Bond. |
| 34 | **Swore Again To** | Bond | If this Force is driven off, return this Bond to your hand instead of discarding it. |
| 35 | **Edrin** | Name - Human, Survivor - Unique | If this formation is driven off, return this Name to your hand instead of discarding it. |
| 36 | **Sela** | Name - Human, Wanderer - Unique | After this formation **Retreats** to the Rear, you may move it one Front left or right if that Rear position is empty. |
| 37 | **The Old Guard** | Force - Human, Veterans | **Deploy - Rear only.** If this formation is **Named**, a Force you play in the Frontline of this Front costs 1 less Command (minimum 1). |
| 38 | **Meren** | Name - Human, Captain - Unique | At the start of each Battle, you may move this formation one Front left or right, staying in the same rank, if that position is empty. |
| 39 | **Endured With** | Bond | When this formation **Retreats**, regain 1 Command. |
| 40 | **Tala** | Name - Human, Captain - Unique | Before comparing Strength in this Front, if this formation is in the Frontline and its Rear position is empty, you may **Retreat** it. |

### Mechanics under test

- **Inherited Bond** - a Bond can stay in a battlefield position and attach to the next friendly Force played there.
- **Bond salvage** - a Bond can return to hand when its Force is driven off.
- **Name survival** - a Name can return to hand when its formation is driven off.
- **Retreat repositioning** - a retreating formation can shift sideways after reaching the Rear.
- **Rebuilding** - a persistent Rear formation can make the next Frontline Force cheaper.
- **Persistent preparation** - a Named Formation can reposition at the start of a later Battle.
- **Loss compensation** - Retreat can return a small amount of Command.
- **Voluntary Retreat** - one Name can leave the Frontline before Strength is compared, but only if its Rear position is empty.


## Canonical card vocabulary

Use these terms consistently in rules and card text:

- **Force / Bond / Name** - the card types.
- **Formation** - a Force plus any Bond and/or Name in the same position.
- **Has a Bond** - a Bond is present. This does not imply a Name is present.
- **Has a Name** - a Name is present. This does not imply a Bond is present.
- **Named Formation / is Named** - exactly **Force + Bond + Name**.
- **Prepared Bond / Prepared Name** - the card is in a position without a Force. It is not a formation yet.
- **Open Bond** - a Bond attached to a Force when that formation has no Name.
- Never use **Named** to mean merely “has a Name.”
- Never say a **Force is Named**. Say **the formation is Named**.
