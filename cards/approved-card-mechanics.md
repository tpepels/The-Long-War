# Approved card mechanics

This file is a compact reference for the currently approved first-80 card designs.

**Source of truth:** `cards/cards.json`  
**Approved cards:** 56

## Vocabulary

- **Formation** = a Force plus any Bond and/or Name in the same position.
- **Named Formation / is Named** = exactly **Force + Bond + Name**.
- **Has a Bond / has a Name** means that card is present; it does not imply the formation is Named.
- **Prepared Bond / Prepared Name** = present in a battlefield position with no Force.
- **Open Bond** = a Bond attached to a Force while that formation has no Name.
- **Maneuver** is the core movement action. **Move** means movement caused by card text.

## Editorial rules

- Card mechanics are printed in full; roles and classifications do not carry hidden rules.
- Prefer short, literal instructions such as **count**, **ignore**, **move**, **discard**, **draw**, and **win**.
- Bond names should normally read grammatically as `Force + Bond + Name`.
- Avoid engine-facing words such as *resolve*, *resolution*, *trigger*, *contribute*, or *combat effect* where literal wording works.

## Batch 1 - Baseline

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 1 | **The Fifty Men** | Force | 2 | 4 | While this Force is in the **Frontline**, it gets +1 **Strength**. |
| 2 | **Seven Black Ships** | Force | 2 | 4 | While this Force is in the **Rear**, it gets +1 **Strength**. |
| 3 | **The White Hands of Elara** | Force | 1 | 2 | **Deploy - Rear only.** While this Force is in the **Rear**, the friendly Force directly in front of it gets +2 **Strength**. |
| 4 | **Stood Fast With** | Bond | 1 | - | This formation gets +2 **Strength**. |
| 5 | **Followed** | Bond | 1 | - | This formation gets +1 **Strength**. If it is **Named**, it gets +3 **Strength** instead. |
| 6 | **Namar** | Name | 1 | +1 | When this formation becomes **Named**, regain 1 **Command**. |
| 7 | **Oren** | Name | 2 | +2 | When this formation becomes **Named**, draw 1 card. |
| 8 | **Avaros, the Bronze King** | Hero | 3 | 5 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. After this Force **Maneuvers**, you may **Maneuver** one adjacent friendly **Named Formation** for 0 Command. **Name -** When this formation becomes **Named**, you may **Maneuver** it once for 0 Command. |

## Batch 2 - Positioning

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 9 | **The Red Shields** | Force | 2 | 4 | **Deploy - Frontline only.** While this Force is in the **Frontline**, if a friendly Force is directly behind it, this Force gets +1 **Strength**. |
| 10 | **The Crow Archers** | Force | 2 | 4 | **Deploy - Rear only.** While this Force is in the **Rear**, if a friendly Force is directly in front of it, this Force gets +2 **Strength**. |
| 11 | **The House of Reed** | Force | 2 | 3 | **Deploy - Rear only.** This Force cannot move, **Maneuver**, or swap positions. If you lose this Front while you have a **Named Formation** in the Frontline, drive off this Force instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force | 2 | 2 | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or one adjacent Front. Count this Force's **Strength** only in the chosen Front. |
| 13 | **Guarded** | Bond | 1 | - | Cards your opponent plays cannot move this formation. |
| 14 | **Marched With** | Bond | 1 | - | When you play this Bond on a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name | 1 | +1 | When an opposing formation in this Front becomes **Named**, your next **Maneuver** this Battle costs 0 Command. If this happens again before you Maneuver, you still get only one free Maneuver. |
| 16 | **Elian** | Name | 1 | +1 | When this formation becomes **Named**, you may swap it with an adjacent friendly formation. |

## Batch 3 - Maneuver

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 17 | **The Dust Riders** | Force | 2 | 2 | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or one adjacent Front. Count this Force's **Strength** only in the chosen Front. After this Force **Maneuvers** into an empty position, you may move an adjacent friendly formation into the position it left. |
| 18 | **The Black Company** | Force | 2 | 4 | **Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. After this formation swaps positions with another formation during a **Maneuver**, you may **Maneuver** that other formation for 0 Command. |
| 19 | **Kept Pace With** | Bond | 1 | - | After an adjacent friendly **Named Formation** Maneuvers away, you may move this formation into the position it left. |
| 20 | **Covered the Withdrawal of** | Bond | 1 | - | After an adjacent friendly formation **Retreats**, you may **Maneuver** this formation for 0 Command. |
| 21 | **Teren** | Name | 2 | +1 | After this formation **Maneuvers**, you may swap two adjacent friendly formations other than this one. |
| 22 | **Mara** | Name | 1 | +1 | When an opposing formation **Maneuvers** into this Front, you may **Maneuver** this formation for 0 Command. |
| 23 | **Blocked the Road for** | Bond | 1 | - | Cards your opponent plays cannot move a formation from an adjacent Front into this Front. |
| 24 | **The Long March** | Story | 2 | - | **Ongoing.** Your first **Maneuver** each turn costs 0 Command if it moves into an empty position instead of swapping. |

## Batch 4 - Combat

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 25 | **The Red Duelists** | Force | 2 | 3 | **Deploy - Frontline only.** When comparing **Strength** in this Front, ignore Strength from Rear formations. |
| 26 | **The Thornbow Hunters** | Force | 2 | 1 | **Deploy - Rear only.** While this Force is in the **Rear**, if a friendly Force is directly in front of it, this Force gets +2 **Strength**. When comparing Strength in this Front, you may ignore one opposing Rear Force's Strength. |
| 27 | **The Iron Boars** | Force | 3 | 3 | **Deploy - Frontline only.** While this Force is in the **Frontline**, it gets +1 **Strength**. If you win this Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 28 | **The First Spear** | Force | 3 | 3 | **Deploy - Frontline only.** While this Force is in the **Frontline**, if a friendly Force is directly behind it, this Force gets +1 **Strength**. When comparing Strength in this Front, you may ignore an opposing Frontline Force's Strength if the Strength printed on that card is lower than the Strength printed on this one. |
| 29 | **Held the Line for** | Bond | 1 | - | Before comparing Strength in this Front, you may discard this Force and all cards attached to it. If you do, choose one opposing formation here and ignore its Strength. |
| 30 | **Seized the Standard of** | Bond | 1 | - | If this formation wins its Front and an opposing Frontline Named Formation **Retreats**, return that formation's Bond to its owner's hand after it Retreats. |
| 31 | **Asha, the Shield-Bearer** | Name | 1 | +1 | If an opponent's card would make another friendly formation's Strength not count in this Front, you may make this formation's Strength not count instead. The other formation counts normally. |
| 32 | **The Ground Was Held** | Stratagem | 2 | - | **During this Battle**, if a Front is tied and only one player has a Named Formation in its Frontline, that player wins the Front. If both or neither do, it stays tied. |

## Batch 5 - Persistence & Retreat

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 33 | **Stayed Behind For** | Bond | 1 | - | If this Force is driven off, leave this Bond in its position instead of discarding it. If this formation has a Name, return that Name to its owner's hand. The next friendly Force played in this position takes this Bond. |
| 34 | **Swore Again To** | Bond | 1 | - | If this Force is driven off, return this Bond to your hand instead of discarding it. |
| 35 | **Edrin** | Name | 1 | +1 | If this formation is driven off, return this Name to your hand instead of discarding it. |
| 36 | **Sela** | Name | 1 | +1 | After this formation **Retreats** to the Rear, you may move it one Front left or right if that Rear position is empty. |
| 37 | **The Old Guard** | Force | 2 | 2 | **Deploy - Rear only.** If this formation is **Named**, a Force you play in the Frontline of this Front costs 1 less Command (minimum 1). |
| 38 | **Meren** | Name | 2 | +1 | At the start of each Battle, you may move this formation one Front left or right, staying in the same rank, if that position is empty. |
| 39 | **Endured With** | Bond | 1 | - | When this formation **Retreats**, regain 1 Command. |
| 40 | **Tala** | Name | 1 | +1 | Before comparing Strength in this Front, if this formation is in the Frontline and its Rear position is empty, you may **Retreat** it. |

## Batch mechanic coverage

- **Baseline:** positional Force identities, basic Bonds, completion rewards, first Hero.
- **Positioning:** deployment restrictions, Stronghold protection, Skirmisher lateral fighting, movement protection, completion movement.
- **Maneuver:** chained movement, swaps, reactive movement, vacated-position movement, conditional free Maneuvers.
- **Combat:** Rear suppression, Frontline-only comparisons, breakthrough, sacrifice, interception, tie control.
- **Persistence & Retreat:** inherited Bonds, salvage, Name survival, Retreat repositioning, rebuilding, voluntary Retreat.
- **Command:** catch-up discounts, completion discounts, optional investment, refunds, hand-to-Command conversion, recovery, and Battle-wide spending.
- **Heroes:** dual-use Force/Name choices across movement, combat, Retreat, Command, rebuilding, card recovery, and Story support.


## Batch 6 - Command

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 41 | **Rallied Behind** | Bond | 1 | - | If you have less Command than your opponent, this Bond costs 0 Command. |
| 42 | **Sorin** | Name | 1 | +1 | If you play this Name on a Force that already has a Bond, it costs 0 Command. |
| 43 | **Bought Time For** | Bond | 1 | - | When you play this Bond, you may pay 1 extra Command. If you do, draw 2 cards. |
| 44 | **Trusted** | Bond | 1 | - | At Battle end, if this formation wins its Front, regain 1 Command. |
| 45 | **The Baggage Was Abandoned** | Story | 1 | - | When you play this Story, you may discard 1 other card. If you do, regain 2 Command. |
| 46 | **The Lines Held** | Stratagem | 2 | - | At Battle end, when you recover Command, count one fewer Front lost. |
| 47 | **Iven** | Name | 2 | +1 | While you have less Command than your opponent, the first card you play each turn costs 1 less Command (minimum 1). |
| 48 | **All Banners Forward** | Stratagem | 5 | - | **During this Battle**, your **Maneuvers** cost 0 Command, and your formations may **Maneuver** even if they are not Named. |



## Batch 7 - Heroes

| # | Card | Type | Cost | Force Strength | Name Strength | Approved mechanic |
|---:|---|---|---:|---:|---:|---|
| 49 | **Kael, the Roadless** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force -** This formation may **Maneuver** even if it is not Named. After it Maneuvers into an empty position, you may move it one more Front left or right if that position is empty. **Name -** When an opposing formation Maneuvers into an adjacent Front, you may Maneuver this formation for 0 Command. |
| 50 | **Rovan, the Gatebreaker** | Hero | 3 | 5 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** When comparing Strength in this Front, you may ignore the opposing Rear Force's Strength. **Name -** If this formation wins its Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 51 | **Alda, Keeper of the Ford** | Hero | 2 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** If your Frontline Named Formation here would Retreat, you may drive off Alda instead. The Frontline formation stays. **Name -** If this formation is driven off, return Alda to your hand instead of discarding her. |
| 52 | **Tovan, the Quartermaster** | Hero | 3 | 2 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** At Battle end, if you lose this Front, it does not reduce your Command recovery. **Name -** While this formation is Named, the first card you play in this Front each turn costs 1 less Command (minimum 1). |
| 53 | **Nara, Builder of Walls** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** A Force you play in the Frontline of this Front costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return one Bond from your discard pile to your hand. |
| 54 | **Neris, the Ferryman** | Hero | 3 | 4 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** After your Frontline formation here Retreats, you may move it one Front left or right if that Rear position is empty. **Name -** After this formation Retreats, you may move it one Front left or right if that Rear position is empty. |
| 55 | **Veyra, Keeper of Oaths** | Hero | 3 | 4 | +1 | **Hero.** Play as a **Force** or **Name**. **Force -** When you play Veyra, you may move a Bond or Name from an adjacent position with no Force into Veyra's position, if that slot is empty. **Name -** When you play Veyra on a Force with no Bond, you may move a Bond from an adjacent formation with no Name onto this formation. |
| 56 | **Yara, the Chronicler** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** The first Story you play each Battle costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return one Story from your discard pile to your hand. |

