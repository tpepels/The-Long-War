# Approved card mechanics

This file is a compact reference for the currently approved first-80 card designs.

**Source of truth:** `cards/cards.json`  
**Approved cards:** 80

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
| 1 | **The Fifty Men** | Force | 2 | 4 | While in the **Frontline**, this Force gets +1 **Strength**. |
| 2 | **Seven Black Ships** | Force | 2 | 4 | While in the **Rear**, this Force gets +1 **Strength**. |
| 3 | **The White Hands of Elara** | Force | 1 | 2 | **Deploy - Rear only.** While in the Rear, the Force directly in front of this one gets +2 **Strength**. |
| 4 | **Stood Fast With** | Bond | 1 | - | This formation gets +2 **Strength**. |
| 5 | **Followed** | Bond | 1 | - | This formation gets +1 **Strength**. If it is **Named**, it gets +3 **Strength** instead. |
| 6 | **Namar** | Name | 1 | +1 | When this formation becomes **Named**, regain 1 **Command**. |
| 7 | **Oren** | Name | 2 | +2 | When this formation becomes **Named**, draw 1 card. |
| 8 | **Avaros, the Bronze King** | Hero | 3 | 5 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** While in the Frontline, Avaros gets +1 **Strength**. After Avaros **Maneuvers**, you may **Maneuver** an adjacent **Named Formation** you control for 0 Command. **Name -** When this formation becomes **Named**, you may **Maneuver** it for 0 Command. |

## Batch 2 - Positioning

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 9 | **The Red Shields** | Force | 2 | 4 | **Deploy - Frontline only.** While in the Frontline, if you have a Force directly behind this one, this Force gets +1 **Strength**. |
| 10 | **The Crow Archers** | Force | 2 | 4 | **Deploy - Rear only.** While in the Rear, if you have a Force directly in front of this one, this Force gets +2 **Strength**. |
| 11 | **The House of Reed** | Force | 2 | 3 | **Deploy - Rear only.** This Force cannot change position. If you lose this Front while you have a **Named Formation** in the Frontline, drive off this Force instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force | 2 | 2 | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or an adjacent Front. Count this Force's **Strength** only there. |
| 13 | **Guarded** | Bond | 1 | - | Your opponent's cards cannot move this formation. |
| 14 | **Marched With** | Bond | 1 | - | When you play this Bond on a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name | 1 | +1 | When an opposing formation in this Front becomes **Named**, your next **Maneuver** this Battle costs 0 Command. If this happens again before you use that free Maneuver, you do not gain another. |
| 16 | **Elian** | Name | 1 | +1 | When this formation becomes **Named**, you may swap it with an adjacent formation you control. |

## Batch 3 - Maneuver

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 17 | **The Dust Riders** | Force | 2 | 2 | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or an adjacent Front. Count this Force's **Strength** only there. After this Force **Maneuvers** into an empty position, you may move an adjacent friendly formation into the position it left. |
| 18 | **The Black Company** | Force | 2 | 4 | **Deploy - Frontline only.** While in the **Frontline**, this Force gets +1 **Strength**. After this formation swaps positions with another formation during a **Maneuver**, you may **Maneuver** that other formation for 0 Command. |
| 19 | **Kept Pace With** | Bond | 1 | - | After an adjacent **Named Formation** you control Maneuvers away, you may move this formation into the position it left. |
| 20 | **Covered the Withdrawal of** | Bond | 1 | - | After an adjacent formation you control **Retreats**, you may **Maneuver** this formation for 0 Command. |
| 21 | **Teren** | Name | 2 | +1 | After this formation **Maneuvers**, you may swap two adjacent formations you control other than this one. |
| 22 | **Mara** | Name | 1 | +1 | When an opposing formation **Maneuvers** into this Front, you may **Maneuver** this formation for 0 Command. |
| 23 | **Blocked the Road for** | Bond | 1 | - | Cards your opponent plays cannot move a formation from an adjacent Front into this Front. |
| 24 | **The Long March** | Story | 2 | - | **Saga - Ongoing.** The first time each Battle one of your formations **Maneuvers** into an empty position, regain 1 Command. |

## Batch 4 - Combat

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 25 | **The Red Duelists** | Force | 2 | 3 | **Deploy - Frontline only.** When comparing **Strength** in this Front, ignore Strength from Rear formations. |
| 26 | **The Thornbow Hunters** | Force | 2 | 1 | **Deploy - Rear only.** While in the Rear, if you have a Force directly in front of this one, this Force gets +2 **Strength**. When comparing Strength in this Front, you may ignore one opposing Rear Force's Strength. |
| 27 | **The Iron Boars** | Force | 3 | 3 | **Deploy - Frontline only.** While in the **Frontline**, this Force gets +1 **Strength**. If you win this Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 28 | **The First Spear** | Force | 3 | 3 | **Deploy - Frontline only.** While in the Frontline, if you have a Force directly behind this one, this Force gets +1 **Strength**. When comparing Strength in this Front, you may ignore an opposing Frontline Force's Strength if the Strength printed on that card is lower than the Strength printed on this one. |
| 29 | **Held the Line for** | Bond | 1 | - | Before comparing Strength here, you may discard this Force and all cards attached to it. If you do, choose one opposing formation here and ignore its Strength. |
| 30 | **Seized the Standard of** | Bond | 1 | - | If this formation wins its Front and an opposing Frontline Named Formation **Retreats**, return that formation's Bond to its owner's hand after it Retreats. |
| 31 | **Asha, the Shield-Bearer** | Name | 1 | +1 | If an opponent's card would ignore another formation's Strength in this Front, you may have it ignore this formation's Strength instead. |
| 32 | **The Ground Was Held** | Stratagem | 2 | - | **During this Battle**, if a Front is tied and only one player has a Named Formation in its Frontline, that player wins the Front. If both or neither do, it stays tied. |

## Batch 5 - Persistence & Retreat

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 33 | **Stayed Behind For** | Bond | 1 | - | If this Force is driven off, leave this Bond in its position. Return its Name, if any, to its owner's hand. The next Force you play there takes this Bond. |
| 34 | **Swore Again To** | Bond | 1 | - | If this Force is driven off, return this Bond to your hand instead of discarding it. |
| 35 | **Edrin** | Name | 1 | +1 | If this formation is driven off, return this Name to your hand instead of discarding it. |
| 36 | **Sela** | Name | 1 | +1 | After this formation **Retreats**, you may move it one Front left or right to an empty Rear position. |
| 37 | **The Old Guard** | Force | 2 | 2 | **Deploy - Rear only.** If this formation is **Named**, a Force you play in the Frontline of this Front costs 1 less Command (minimum 1). |
| 38 | **Meren** | Name | 2 | +1 | At the start of each Battle, you may move this formation one Front left or right to an empty position in the same rank. |
| 39 | **Endured With** | Bond | 1 | - | When this formation **Retreats**, regain 1 Command. |
| 40 | **Tala** | Name | 1 | +1 | Before comparing Strength here, if this formation is in the Frontline and its Rear is empty, you may **Retreat** it. |

## Batch mechanic coverage

- **Baseline:** positional Force identities, basic Bonds, completion rewards, first Hero.
- **Positioning:** deployment restrictions, Stronghold protection, Skirmisher lateral fighting, movement protection, completion movement.
- **Maneuver:** chained movement, swaps, reactive movement, vacated-position movement, conditional free Maneuvers.
- **Combat:** Rear suppression, Frontline-only comparisons, breakthrough, sacrifice, interception, tie control.
- **Persistence & Retreat:** inherited Bonds, salvage, Name survival, Retreat repositioning, rebuilding, voluntary Retreat.
- **Command:** catch-up discounts, completion discounts, optional investment, refunds, hand-to-Command conversion, recovery, and Battle-wide spending.
- **Heroes:** dual-use Force/Name choices across movement, combat, Retreat, Command, rebuilding, card recovery, and Story support.
- **Narratives:** Legends, Omens, Warnings, Prophecies, Sagas, Myths, and Conspiracies turn battlefield events into Command plus a secondary effect.
- **Stratagems:** one-Battle plans that can reshape Front geometry, Retreat, deployment, and movement.
- **Build-around:** unusual visible board states such as open Bonds, prepared cards, wide or concentrated lines, narratives, Heroes, and succession.


## Batch 6 - Command

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 41 | **Rallied Behind** | Bond | 1 | - | If you have less Command than your opponent, this Bond costs 0 Command. |
| 42 | **Sorin** | Name | 2 | +1 | If you play Sorin on a Force that already has a Bond, Sorin costs 1 Command. |
| 43 | **Bought Time For** | Bond | 1 | - | When you play this Bond, you may pay 1 extra Command to draw 2 cards. |
| 44 | **Trusted** | Bond | 1 | - | When this formation becomes **Named**, regain 1 Command. |
| 45 | **The Baggage Was Abandoned** | Story | 1 | - | **Warning.** When you play this, you may discard 1 other card to regain 2 Command. |
| 46 | **The Lines Held** | Stratagem | 2 | - | At Battle end, one Front you lost does not reduce your Command recovery. |
| 47 | **Iven** | Name | 2 | +1 | While you have less Command than your opponent, the first card you play in this Front each turn costs 1 less Command (minimum 1). |
| 48 | **All Banners Forward** | Stratagem | 5 | - | **During this Battle**, your **Maneuvers** cost 0 Command, and your formations may **Maneuver** even if they are not Named. |



## Batch 7 - Heroes

| # | Card | Type | Cost | Force Strength | Name Strength | Approved mechanic |
|---:|---|---|---:|---:|---:|---|
| 49 | **Kael, the Roadless** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force -** This formation may **Maneuver** even if it is not Named. After it Maneuvers into an empty position, you may move it one more Front left or right to an empty position in the same rank. **Name -** When an opposing formation Maneuvers into an adjacent Front, you may Maneuver this formation for 0 Command. |
| 50 | **Rovan, the Gatebreaker** | Hero | 3 | 5 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** When comparing Strength here, you may ignore the opposing Rear Force's Strength. **Name -** If this formation wins its Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 51 | **Alda, Keeper of the Ford** | Hero | 2 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** If your Frontline Named Formation here would Retreat, you may drive off Alda instead; that formation stays. **Name -** If this formation is driven off, return Alda to your hand. |
| 52 | **Tovan, the Quartermaster** | Hero | 3 | 2 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** At Battle end, if you lose this Front, it does not reduce your Command recovery. **Name -** While this formation is Named, the first card you play in this Front each Battle costs 1 less Command (minimum 1). |
| 53 | **Nara, Builder of Walls** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** A Force you play in the Frontline of this Front costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return a Bond from your discard pile to your hand. |
| 54 | **Neris, the Ferryman** | Hero | 3 | 4 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** After your Frontline formation here Retreats, you may move it one Front left or right to an empty Rear position. **Name -** After this formation Retreats, you may move it one Front left or right to an empty Rear position. |
| 55 | **Veyra, Keeper of Oaths** | Hero | 3 | 4 | +1 | **Hero.** Play as a **Force** or **Name**. **Force -** When you play Veyra, you may move a prepared Bond or Name from an adjacent position into Veyra's position, if that slot is empty. **Name -** When you play Veyra on a Force with no Bond, you may move an open Bond from an adjacent formation onto this one. |
| 56 | **Yara, the Chronicler** | Hero | 3 | 3 | +1 | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Rear only.** The first **Narrative** you play each Battle costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return a Narrative from your discard pile to your hand. |



## Batch 8 - Narratives

| # | Card | Form | Cost | Approved mechanic |
|---:|---|---|---:|---|
| 57 | **The Wall Did Not Break** | Legend | 1 | **Legend - Ongoing.** Choose a Front when you play this and place it beside that Front. At Battle end, if you did not lose that Front, regain 1 Command. If you won it, you may also return a Bond from your discard pile to your hand. Then discard this Legend. |
| 58 | **They Returned With Names** | Legend | 1 | **Legend - Ongoing.** When one of your formations becomes Named, regain 1 Command. You may Maneuver it for 0 Command. Then discard this Legend. |
| 59 | **The Crows Came Down** | Omen | 1 | **Omen - Ongoing.** When one of your Named Formations Retreats, regain 1 Command. You may then move it one Front left or right to an empty Rear position. Discard this Omen. |
| 60 | **They Were Gathering There** | Warning | 1 | **Warning - Ongoing.** When an opposing formation becomes Named, regain 1 Command. You may Maneuver one Named Formation you control for 0 Command. Then discard this Warning. |
| 61 | **Before Sunset, the Ford Would Be Ours** | Prophecy | 2 | **Prophecy - Ongoing.** Choose a Front when you play this and place it beside that Front. At Battle end, if you win that Front, regain 2 Command and draw 1 card. Then discard this Prophecy. |
| 62 | **They Lived to Tell It** | Saga | 1 | **Saga - Ongoing.** Place this beside one of your Named Formations when you play it. At Battle end, if that formation is still on the battlefield, regain 1 Command and draw 1 card. Then discard this Saga. |
| 63 | **No Road Was Too Long** | Myth | 2 | **Myth - Ongoing.** The first time each Battle one of your formations Maneuvers into an empty position, regain 1 Command. You may then move an adjacent formation you control into the position it left. |
| 64 | **The Muster Was False** | Conspiracy | 1 | **Conspiracy - Ongoing.** As soon as your opponent has a Force in both ranks of one Front, regain 1 Command. You may Maneuver one Named Formation you control for 0 Command. Then discard this Conspiracy. |



## Batch 9 - Stratagems

| # | Card | Cost | Approved mechanic |
|---:|---|---:|---|
| 65 | **No Step Back** | 2 | Choose a Front when you play this and place it beside that Front. **During this Battle**, a Frontline Named Formation that loses that Front is driven off instead of Retreating. |
| 66 | **The Center Must Hold** | 3 | Choose two adjacent Fronts when you play this. At Battle end, total each player's Strength across those Fronts. Higher total wins both; equal totals tie both. |
| 67 | **The Flank Was Refused** | 2 | Choose Front 1 or Front 4 when you play this. **During this Battle**, your formations there count no Strength. Each of your formations in the adjacent Front gets +1 Strength. |
| 68 | **The Line Wheeled** | 2 | Choose left or right when you play this. Move any number of your formations one Front that way, staying in the same rank, but only into positions that were empty when you played this card. |
| 69 | **The Trap Closed** | 3 | **During this Battle**, if you win Fronts 1, 2, and 3, drive off the opposing Frontline Named Formation in Front 2 instead of Retreating it. Do the same in Front 3 if you win Fronts 2, 3, and 4. |
| 70 | **They Let Them Through** | 2 | At Battle end, before comparing Strength, you may swap your Frontline and Rear formations in one Front. Bonds and Names move with their Forces. |
| 71 | **All Reserves Forward** | 2 | When you play this, you may move any number of your Rear formations to the empty Frontline position in their own Front. Moving the first costs no extra Command; pay 1 Command for each additional formation. |
| 72 | **The Battle Turned East** | 3 | Choose left or right when you play this. **During this Battle**, your Named Formations may **Maneuver** in that direction for 0 Command. |



## Batch 10 - Build-around

| # | Card | Type | Cost | Strength | Approved mechanic |
|---:|---|---|---:|---:|---|
| 73 | **The Unnamed Host** | Force | 2 | 3 | While this formation has a Bond and no Name, it may **Maneuver** even if it is not Named. Its first **Maneuver** each Battle costs 0 Command. |
| 74 | **The Late Banner** | Force | 2 | 3 | When you play this Force into a position with a prepared Bond or Name, it may **Maneuver** once for 0 Command even if it is not Named. |
| 75 | **Arel** | Name | 1 | +1 | While one of your Fronts has no Force, this formation's first **Maneuver** each Battle costs 0 Command. |
| 76 | **Torren** | Name | 2 | +1 | While you have a Force in all four Fronts, after this formation **Maneuvers**, you may **Maneuver** one other Named Formation you control for 0 Command. |
| 77 | **The Banner Singers** | Force | 1 | 2 | **Deploy - Rear only.** While in the Rear, after you regain Command from a **Narrative**, you may **Maneuver** one Named Formation you control for 0 Command. |
| 78 | **Marched Beneath the Banner of** | Bond | 1 | - | While this formation is adjacent to a formation containing one of your Heroes, it may **Maneuver** even if it is not Named. Its first **Maneuver** each Battle costs 0 Command. |
| 79 | **Carried the Oath of** | Bond | 1 | - | While this Bond is open, after this Force moves or **Maneuvers**, you may move the Bond to an adjacent Force you control with no Bond. |
| 80 | **Eira** | Name | 2 | +1 | If this formation is driven off, you may move Eira to an adjacent Force you control that has a Bond and no Name instead of discarding her. |

