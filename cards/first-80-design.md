# First 80 - card design

This file records approved card-design batches for the first 80-card set.

It is a design source, not yet canonical engine data. Move an approved card into `cards/cards.json` only when the canonical engine can represent its full rules text without display/engine divergence.

Costs and Strength values are provisional unless explicitly locked later.

## Batch 1 - Baseline

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text | Design role |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | **The Fifty Men** | Force - Human, Warband - Swordsman | While in the **Frontline**, this Force gets +1 **Strength**. |
| 2 | **Seven Black Ships** | Force - Ship, Fleet - Ship | While in the **Rear**, this Force gets +1 **Strength**. |
| 3 | **The White Hands of Elara** | Force - Human, Healer | **Deploy - Rear only.** While in the Rear, the Force directly in front of this one gets +2 **Strength**. |
| 4 | **Stood Fast With** | Bond | This formation gets +2 **Strength**. |
| 5 | **Followed** | Bond | This formation gets +1 **Strength**. If it is **Named**, it gets +3 **Strength** instead. |
| 6 | **Namar** | Name - Human, King - Unique | When this formation becomes **Named**, regain 1 **Command**. |
| 7 | **Oren** | Name - Human, Warrior - Unique | When this formation becomes **Named**, draw 1 card. |
| 8 | **Avaros, the Bronze King** | Hero - Human, King - Unique | **Hero.** Play as a **Force** or **Name**. **Force - Deploy - Frontline only.** While in the Frontline, Avaros gets +1 **Strength**. After Avaros **Maneuvers**, you may **Maneuver** an adjacent **Named Formation** you control for 0 Command. **Name -** When this formation becomes **Named**, you may **Maneuver** it for 0 Command. |

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
| 9 | **The Red Shields** | Force - Human, Guard - Spearman | **Deploy - Frontline only.** While in the Frontline, if you have a Force directly behind this one, this Force gets +1 **Strength**. |
| 10 | **The Crow Archers** | Force - Human, Company - Archer | **Deploy - Rear only.** While in the Rear, if you have a Force directly in front of this one, this Force gets +2 **Strength**. |
| 11 | **The House of Reed** | Force - Place, Stronghold | **Deploy - Rear only.** This Force cannot change position. If you lose this Front while you have a **Named Formation** in the Frontline, drive off this Force instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force - Human, Riders - Skirmisher | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or an adjacent Front. Count this Force's **Strength** only there. |
| 13 | **Guarded** | Bond | Your opponent's cards cannot move this formation. |
| 14 | **Marched With** | Bond | When you play this Bond on a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name - Human, Seer - Unique | When an opposing formation in this Front becomes **Named**, your next **Maneuver** this Battle costs 0 Command. If this happens again before you use that free Maneuver, you do not gain another. |
| 16 | **Elian** | Name - Human, Wanderer - Unique | When this formation becomes **Named**, you may swap it with an adjacent formation you control. |

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
| 17 | **The Dust Riders** | Force - Human, Riders - Skirmisher | This formation may **Maneuver** even if it is not Named. At Battle end, choose this Front or an adjacent Front. Count this Force's **Strength** only there. After this Force **Maneuvers** into an empty position, you may move an adjacent friendly formation into the position it left. |
| 18 | **The Black Company** | Force - Human, Company - Swordsman | **Deploy - Frontline only.** While in the **Frontline**, this Force gets +1 **Strength**. After this formation swaps positions with another formation during a **Maneuver**, you may **Maneuver** that other formation for 0 Command. |
| 19 | **Kept Pace With** | Bond | After an adjacent **Named Formation** you control Maneuvers away, you may move this formation into the position it left. |
| 20 | **Covered the Withdrawal of** | Bond | After an adjacent formation you control **Retreats**, you may **Maneuver** this formation for 0 Command. |
| 21 | **Teren** | Name - Human, Captain - Unique | After this formation **Maneuvers**, you may swap two adjacent formations you control other than this one. |
| 22 | **Mara** | Name - Human, Scout - Unique | When an opposing formation **Maneuvers** into this Front, you may **Maneuver** this formation for 0 Command. |
| 23 | **Blocked the Road for** | Bond | Cards your opponent plays cannot move a formation from an adjacent Front into this Front. |
| 24 | **The Long March** | Story - Saga - Ongoing | **Saga - Ongoing.** The first time each Battle one of your formations **Maneuvers** into an empty position, regain 1 Command. |

### Batch 3 notes

- Movement effects use **move** when they are card-effect movement and **Maneuver** only when they invoke the core Maneuver action.
- The Dust Riders print the complete Skirmisher mechanic; the label itself carries no hidden rule.
- The Black Company prints its positional Swordsman effect; the label itself carries no hidden rule.
- **The Long March** is intentionally the most experimental card in the batch and tests whether recurring movement economy creates useful battlefield activity without making position trivial.


## Batch 4 - Combat

Status: approved for the first-80 design pool.

This batch deliberately expands what can happen when a Front resolves without introducing hit points, wounds, damage tracking, or a separate attack phase. Every combat mechanic is printed in full on the card; labels such as Duelist or Raider do not carry hidden rules.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 25 | **The Red Duelists** | Force - Human, Duelists | **Deploy - Frontline only.** When comparing **Strength** in this Front, ignore Strength from Rear formations. |
| 26 | **The Thornbow Hunters** | Force - Human, Hunters - Archer | **Deploy - Rear only.** While in the Rear, if you have a Force directly in front of this one, this Force gets +2 **Strength**. When comparing Strength in this Front, you may ignore one opposing Rear Force's Strength. |
| 27 | **The Iron Boars** | Force - Human, Raiders - Swordsman | **Deploy - Frontline only.** While in the **Frontline**, this Force gets +1 **Strength**. If you win this Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 28 | **The First Spear** | Force - Human, Guard - Spearman | **Deploy - Frontline only.** While in the Frontline, if you have a Force directly behind this one, this Force gets +1 **Strength**. When comparing Strength in this Front, you may ignore an opposing Frontline Force's Strength if the Strength printed on that card is lower than the Strength printed on this one. |
| 29 | **Held the Line for** | Bond | Before comparing Strength here, you may discard this Force and all cards attached to it. If you do, choose one opposing formation here and ignore its Strength. |
| 30 | **Seized the Standard of** | Bond | If this formation wins its Front and an opposing Frontline Named Formation **Retreats**, return that formation's Bond to its owner's hand after it Retreats. |
| 31 | **Asha, the Shield-Bearer** | Name - Human, Shield-Bearer - Unique | If an opponent's card would ignore another formation's Strength in this Front, you may have it ignore this formation's Strength instead. |
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

Status: approved for the first-80 design pool.

This batch tests what survives a loss, how Retreat can change position, and how persistent formations help rebuild the next Battle. Card text remains literal and self-contained.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 33 | **Stayed Behind For** | Bond | If this Force is driven off, leave this Bond in its position. Return its Name, if any, to its owner's hand. The next Force you play there takes this Bond. |
| 34 | **Swore Again To** | Bond | If this Force is driven off, return this Bond to your hand instead of discarding it. |
| 35 | **Edrin** | Name - Human, Survivor - Unique | If this formation is driven off, return this Name to your hand instead of discarding it. |
| 36 | **Sela** | Name - Human, Wanderer - Unique | After this formation **Retreats**, you may move it one Front left or right to an empty Rear position. |
| 37 | **The Old Guard** | Force - Human, Veterans | **Deploy - Rear only.** If this formation is **Named**, a Force you play in the Frontline of this Front costs 1 less Command (minimum 1). |
| 38 | **Meren** | Name - Human, Captain - Unique | At the start of each Battle, you may move this formation one Front left or right to an empty position in the same rank. |
| 39 | **Endured With** | Bond | When this formation **Retreats**, regain 1 Command. |
| 40 | **Tala** | Name - Human, Captain - Unique | Before comparing Strength here, if this formation is in the Frontline and its Rear is empty, you may **Retreat** it. |

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


## Batch 6 - Command

Status: approved for the first-80 design pool.

This batch tests Command as a decision resource without directly damaging the opponent's Command. The cards focus on discounts, extra spending, refunds, conversion, recovery, catch-up, and one expensive Battle-wide commitment.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 41 | **Rallied Behind** | Bond | 1 | - | If you have less Command than your opponent, this Bond costs 0 Command. |
| 42 | **Sorin** | Name - Human, Captain - Unique | 2 | +1 | If you play Sorin on a Force that already has a Bond, Sorin costs 1 Command. |
| 43 | **Bought Time For** | Bond | 1 | - | When you play this Bond, you may pay 1 extra Command to draw 2 cards. |
| 44 | **Trusted** | Bond | 1 | - | When this formation becomes **Named**, regain 1 Command. |
| 45 | **The Baggage Was Abandoned** | Story - Warning | 1 | - | **Warning.** When you play this, you may discard 1 other card to regain 2 Command. |
| 46 | **The Lines Held** | Stratagem | 2 | - | At Battle end, one Front you lost does not reduce your Command recovery. |
| 47 | **Iven** | Name - Human, Steward - Unique | 2 | +1 | While you have less Command than your opponent, the first card you play in this Front each turn costs 1 less Command (minimum 1). |
| 48 | **All Banners Forward** | Stratagem - Unique | 5 | - | **During this Battle**, your **Maneuvers** cost 0 Command, and your formations may **Maneuver** even if they are not Named. |

### Mechanics under test

- **Catch-up discount** - a card becomes cheaper while you have less Command.
- **Completion discount** - finishing a Force + Bond + Name can be cheaper.
- **Extra investment** - voluntarily pay more Command for a stronger effect.
- **Success refund** - regain Command if the formation wins its Front.
- **Hand-to-Command conversion** - discard a card to regain Command.
- **Recovery improvement** - reduce the Command penalty from lost Fronts.
- **Persistent catch-up** - a Named Formation can improve efficiency while behind on Command.
- **Large investment** - spend substantial Command now for a Battle-wide change in action economy.


## Batch 7 - Heroes

Status: approved for the first-80 design pool.

Each Hero can be played as a Force or as a Name. Both modes are printed in full. The design goal is that neither mode is automatically correct.

| # | Card | Cost | Force Strength | Name Strength | Rules text |
| --- | --- | ---: | ---: | ---: | --- |
| 49 | **Kael, the Roadless** | 3 | 3 | +1 | **Force -** This formation may **Maneuver** even if it is not Named. After it Maneuvers into an empty position, you may move it one more Front left or right if that position is empty. **Name -** When an opposing formation Maneuvers into an adjacent Front, you may Maneuver this formation for 0 Command. |
| 50 | **Rovan, the Gatebreaker** | 3 | 5 | +1 | **Force - Deploy - Frontline only.** When comparing Strength in this Front, you may ignore the opposing Rear Force's Strength. **Name -** If this formation wins its Front and your opponent has no Rear Force here, drive off their Frontline Named Formation instead of Retreating it. |
| 51 | **Alda, Keeper of the Ford** | 2 | 3 | +1 | **Force - Deploy - Rear only.** If your Frontline Named Formation here would Retreat, you may drive off Alda instead. The Frontline formation stays. **Name -** If this formation is driven off, return Alda to your hand instead of discarding her. |
| 52 | **Tovan, the Quartermaster** | 3 | 2 | +1 | **Force - Deploy - Rear only.** At Battle end, if you lose this Front, it does not reduce your Command recovery. **Name -** While this formation is Named, the first card you play in this Front each turn costs 1 less Command (minimum 1). |
| 53 | **Nara, Builder of Walls** | 3 | 3 | +1 | **Force - Deploy - Rear only.** A Force you play in the Frontline of this Front costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return one Bond from your discard pile to your hand. |
| 54 | **Neris, the Ferryman** | 3 | 4 | +1 | **Force - Deploy - Rear only.** After your Frontline formation here Retreats, you may move it one Front left or right if that Rear position is empty. **Name -** After this formation Retreats, you may move it one Front left or right if that Rear position is empty. |
| 55 | **Veyra, Keeper of Oaths** | 3 | 4 | +1 | **Force -** When you play Veyra, you may move a Bond or Name from an adjacent position with no Force into Veyra's position, if that slot is empty. **Name -** When you play Veyra on a Force with no Bond, you may move a Bond from an adjacent formation with no Name onto this formation. |
| 56 | **Yara, the Chronicler** | 3 | 3 | +1 | **Force - Deploy - Rear only.** The first Story you play each Battle costs 1 less Command (minimum 1). **Name -** When this formation becomes Named, return one Story from your discard pile to your hand. |

### Hero mechanics under test

- proactive movement vs reactive movement;
- immediate combat suppression vs persistent breakthrough;
- protecting another formation vs preserving the Hero;
- Battle-end Command protection vs repeated local efficiency;
- rebuilding a Front vs recovering a Bond;
- moving retreating allies vs moving the Hero's own formation;
- taking prepared cards vs transferring an open Bond;
- making Stories cheaper vs recovering a Story.


## Narrative-card identity

The engine may keep `story` as the umbrella family, but player-facing cards use their specific narrative form: **Legend, Omen, Myth, Prophecy, Warning, Saga, Conspiracy**, and future forms where useful.

- Command is the shared mechanical identity of narrative cards: stories about the war increase a player's Command over the army.
- Most successful narrative conditions regain **1 Command**.
- **2 Command** is reserved for more demanding or uncertain conditions.
- Each narrative card also has a smaller secondary effect that expresses what kind of narrative it is.
- Narrative cards are public. There is no face-down or Veiled narrative system.
- A narrative card that refers to a chosen Front or formation is physically placed beside it so the remembered state is visible.
- Do not use generic **Story** as the player-facing card type when a more specific form applies.


## Batch 8 - Narratives

Status: approved for the first-80 design pool.

Command gain is the common identity of this batch. The secondary effect expresses the specific narrative form.

| # | Card | Form | Cost | Rules text |
| --- | --- | --- | ---: | --- |
| 57 | **The Wall Did Not Break** | Legend | 1 | **Ongoing.** Choose a Front and place this beside it. At Battle end, if you did not lose that Front, regain 1 Command. If you won it, you may also return one Bond from your discard pile to your hand. Then discard this Legend. |
| 58 | **They Returned With Names** | Legend | 1 | **Ongoing.** When one of your formations becomes Named, regain 1 Command. You may Maneuver that formation for 0 Command. Then discard this Legend. |
| 59 | **The Crows Came Down** | Omen | 1 | **Ongoing.** When one of your Named Formations Retreats, regain 1 Command. You may move it one Front left or right if that Rear position is empty. Then discard this Omen. |
| 60 | **They Were Gathering There** | Warning | 1 | **Ongoing.** When an opposing formation becomes Named, regain 1 Command. You may Maneuver one friendly Named Formation for 0 Command. Then discard this Warning. |
| 61 | **Before Sunset, the Ford Would Be Ours** | Prophecy | 2 | **Ongoing.** Choose a Front and place this beside it. At Battle end, if you win that Front, regain 2 Command and draw 1 card. Then discard this Prophecy. |
| 62 | **They Lived to Tell It** | Saga | 1 | **Ongoing.** Place this beside one of your Named Formations. At Battle end, if that formation is still on the battlefield, regain 1 Command and draw 1 card. Then discard this Saga. |
| 63 | **No Road Was Too Long** | Myth | 2 | **Ongoing.** The first time each Battle one of your formations Maneuvers into an empty position, regain 1 Command. You may move an adjacent friendly formation into the position it left. |
| 64 | **The Muster Was False** | Conspiracy | 1 | **Ongoing.** When your opponent has a Force in both the Frontline and Rear of the same Front, regain 1 Command. You may Maneuver one friendly Named Formation for 0 Command. Then discard this Conspiracy. |

### Narrative mechanics under test

- **Legend - hold ground:** Command from surviving or winning a chosen Front; stronger success can recover a Bond.
- **Legend - identity:** Command from completing a Named Formation; secondary free Maneuver.
- **Omen - Retreat:** Command from a visible loss event; secondary repositioning.
- **Warning - enemy commitment:** Command from an opposing formation becoming Named; secondary reaction Maneuver.
- **Prophecy - declared objective:** larger Command reward for winning a visibly chosen Front.
- **Saga - survival:** Command from keeping a chosen Named Formation alive through the Battle.
- **Myth - recurring belief:** once-per-Battle Command from behaving according to the Myth, plus movement.
- **Conspiracy - overcommitment:** Command from the opponent filling both ranks of a Front, plus repositioning.


## Stratagem identity

Stratagems are public tactical plans for the current Battle.

- Play a Stratagem face-up in your separate Stratagem area.
- Normally only one Stratagem may be played from hand by each player per Battle.
- A Stratagem applies only during the Battle in which it is played and is discarded at Battle end.
- Stratagems change deployment, movement, Front comparison, Retreat, or other tactical rules. They do not normally generate Command; that is the shared identity of narrative cards.
- Immediate Stratagem effects still occupy the player's Stratagem allowance for that Battle.


## Batch 9 - Stratagems

Status: approved for the first-80 design pool.

This batch treats a Stratagem as the plan for the Battle: a temporary commitment that changes the geometry or stakes of several decisions, rather than a small tactical bonus.

| # | Card | Cost | Rules text |
| --- | --- | ---: | --- |
| 65 | **No Step Back** | 2 | Choose a Front. **During this Battle**, when a player loses that Front, their Frontline Named Formation is driven off instead of Retreating. |
| 66 | **The Center Must Hold** | 3 | Choose two adjacent Fronts. At Battle end, add each player's Strength across both Fronts. Higher combined Strength wins both; equal totals tie both. |
| 67 | **The Flank Was Refused** | 2 | Choose Front 1 or Front 4. **During this Battle**, ignore your Strength there. Each of your formations in the adjacent Front gets +1 Strength. |
| 68 | **The Line Wheeled** | 2 | Choose left or right. Move any number of your formations one Front that way, same rank, if their destination position was empty before this Stratagem was played. |
| 69 | **The Trap Closed** | 3 | **During this Battle**, if you win Fronts 1, 2, and 3, drive off the opposing Frontline Named Formation in Front 2 instead of Retreating it. Do the same in Front 3 if you win Fronts 2, 3, and 4. |
| 70 | **They Let Them Through** | 2 | At Battle end, before comparing Strength, you may swap your Frontline and Rear formations in one Front. Bonds and Names move with their Forces. |
| 71 | **All Reserves Forward** | 2 | Move any number of Rear formations into empty Frontline positions in their own Fronts. The first costs 0 Command; each additional move costs 1 Command. |
| 72 | **The Battle Turned East** | 3 | Choose left or right. **During this Battle**, each of your Named Formations may Maneuver once for 0 Command if it moves in that direction. |

### Stratagem mechanics under test

- **No retreat:** make one Front lethal for both players.
- **Combined center:** collapse two adjacent Fronts into one high-stakes Strength contest.
- **Refused flank:** deliberately concede Strength on an edge to reinforce the neighboring Front.
- **Wheel the line:** shift multiple formations laterally in one operation.
- **Encirclement:** turn control of three neighboring Fronts into a harsher result in the middle.
- **Feigned retreat:** reverse Frontline and Rear immediately before Strength is compared.
- **Commit reserves:** push several Rear formations forward at once, with escalating Command cost.
- **Directional offensive:** give every Named Formation one free Maneuver, but only toward the chosen side.


## Build-around identity

The final first-80 batch rewards unusual but already visible army structures. These cards do not introduce a new resource, phase, counter, or hidden state.

- Build-around cards may reward **open Bonds**, **prepared Bonds/Names**, empty Fronts, occupying all four Fronts, narratives, Heroes, or succession.
- Their conditions should be visible directly on the battlefield.
- Build-around effects should create alternative ways to assemble and move an army rather than simply adding large Strength bonuses.
- Synergy is intentional: several cards may combine into a small package, but each should still be understandable on its own.


## Batch 10 - Build-around

Status: approved for the first-80 design pool.

| # | Card | Type | Cost | Strength | Rules text |
| --- | --- | --- | ---: | ---: | --- |
| 73 | **The Unnamed Host** | Force - Human, Warband | 2 | 3 | While this formation has a Bond and no Name, it may **Maneuver** even if it is not Named. Its first **Maneuver** each Battle costs 0 Command. |
| 74 | **The Late Banner** | Force - Human, Company | 2 | 3 | When you play this Force into a position with a prepared Bond or Name, it may **Maneuver** once for 0 Command even if it is not Named. |
| 75 | **Arel** | Name - Human, General - Unique | 1 | +1 | While one of your Fronts has no Force, this formation's first **Maneuver** each Battle costs 0 Command. |
| 76 | **Torren** | Name - Human, Marshal - Unique | 2 | +1 | While you have a Force in all four Fronts, after this formation **Maneuvers**, you may **Maneuver** one other Named Formation you control for 0 Command. |
| 77 | **The Banner Singers** | Force - Human, Retinue | 1 | 2 | **Deploy - Rear only.** While in the Rear, after you regain Command from a **Narrative**, you may **Maneuver** one Named Formation you control for 0 Command. |
| 78 | **Marched Beneath the Banner of** | Bond | 1 | - | While this formation is adjacent to a formation containing one of your Heroes, it may **Maneuver** even if it is not Named. Its first **Maneuver** each Battle costs 0 Command. |
| 79 | **Carried the Oath of** | Bond | 1 | - | While this Bond is open, after this Force moves or **Maneuvers**, you may move the Bond to an adjacent Force you control with no Bond. |
| 80 | **Eira** | Name - Human, Heir - Unique | 2 | +1 | If this formation is driven off, you may move Eira to an adjacent Force you control that has a Bond and no Name instead of discarding her. |

### Build-around mechanics under test

- **Open Bond army:** an unnamed bonded formation can Maneuver efficiently.
- **Prepared position:** playing a Force onto a prepared Bond or Name produces immediate movement.
- **Concentrated army:** deliberately leave a Front empty to make one Named Formation highly mobile.
- **Wide army:** occupying all four Fronts enables chained Maneuver.
- **Narrative army:** Command gained from narratives can immediately become battlefield movement.
- **Hero retinue:** an adjacent Hero lets an incomplete formation move like an organized retinue.
- **Travelling Bond:** an open Bond can move between Forces after movement.
- **Succession:** a Name can survive a formation being driven off by completing a neighboring bonded Force.
