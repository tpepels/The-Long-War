# Card cohesion, mechanical spread and combo audit — historical baseline

> **Archived baseline.** This audit preceded the print-only cost and effect rebalance; several of its card criticisms were fixed afterward. For the CURRENT 131 printable cards and their prices, use [physical-cost-review.md](physical-cost-review.md). Numbers and card statuses below describe the older executable pool, not the active printable layer.

> **Scope — 8 October 2026:** Static design audit of `cards/cards.json` at the current 131-card canonical pool. This report changes **no cards, rules, or engine behavior**. It does not claim measured win rates or completed AI playtests. Where the rulebook and native runtime diverge, intended tabletop combinations are marked as such.

## Verdict

The pool offers real positional strategy but its possibilities are unevenly distributed. The best cards create reusable spatial puzzles, attach or steal formation components, impose real choices, or alter a Front's structure. The weakest cards are mechanically duplicated, functionally outclassed, rely on unlikely targets, or have a payoff less than their expenditure. The pool does **not** need more cards or equal support counts; it needs clearer, reliable, *different* decisions on existing cards.

### Measured composition

- **131** cards: 33 Forces, 24 Bonds, 20 Names, 11 Heroes, 14 Tactics, 11 Stratagems, 12 Narratives, 6 Orders.
- **146** executable effect entries across **66** distinct low-level operation identifiers. These are engine primitives, **not** 66 distinct player decisions; **37** operations are used once.
- **20** cards lack printed effects (**12 Forces**, **8 Bonds**). Simplicity is useful, but identical baseline bodies should be consciously retained rather than treated as a source of variety.
- Mechanic families overlap across cards: roughly 22 have spatial operations, 20 formation/raid operations, 31 tactical pressure/protection operations, 13 Command/tempo operations, and 22 card-flow/information operations. These counts use an authored operation grouping and are not exclusive or formal balance ratings.
- **34** identities have `combat_redesign_proposal` material that is **not** active printed/executable card text. Zero current printed cards explicitly use the words Attack, Shaken, Depleted, Guarded, Inspired or Empowered.

## Material-changing combo lines worth preserving

1. **Open a breach, then exploit it.** The Line Was Baited (0C, Skirmisher required) pushes an opposing Frontline Force toward its Rear if a slot is empty. An exposed Middle/Rear then becomes susceptible to a Raider Attack under the tabletop Attack rules; Seven Black Ships also exploits an unoccupied opposing Frontline to return attachments. Position and Action order matter. **The native Attack part is not yet implemented.**
2. **Screen the Rear; threaten the Front.** A Middle Guard screens a Rear Force from Archer basic Attacks. The Serekh or Supported By taxes opposing targeted Tactics while The Wall Did Not Break permits Command-free Maneuvers for Named Guards. Screening is part of the tabletop combat system and currently lacks full native implementation; tax stacking needs tests.
3. **Prepare, transfer, complete.** The Field Train / The House of Reed / Supplied By move prepared Bond/Name layers onto the Frontline. Oren, Torren, Tovan and Nara can accelerate completion, retrieve a spent Bond or reduce cost. Limited Front occupancy (three friendly ranks) creates genuine setup constraints. Several tools duplicate the same `attach_prepared` payoff, so each needs a different decision or price.
4. **Mobile Riders and positional reactions.** Grey Riders, Dust Riders, The Long March and Neris facilitate repeated movement; The Battle Turned East rewards a Rider moving. Repositioning costs Actions even if Maneuver Command is discounted, which keeps a decision cost. The flanking Rider Attack is a tabletop design goal, not yet a verified native behavior.
5. **Scouting and hidden traps.** Teren sets a Stratagem without an extra Action, The Scouts Found the Gap reveals and taxes one, while Seers now offer top-three card selection through They Knew the Ground. This creates bluff/counterplay potential, although look-only cards offer little if no hidden Stratagem exists.
6. **Battlefield transformation.** No Road Was Too Long exchanges entire adjacent Front columns; The King Had Given the Order swaps two attached Bonds. These are distinctive “magic-like” effects because they change formation structure and can reverse plans without merely adding Strength. Both have once-per-Battle executable limits missing from printed wording.

## Serious issues

### Gameplay/runtime parity (blocker to measured balance)

The native runtime declares `MAX_CARDS = 128`, stores card codes in signed 8-bit state fields, and raises when `len(engine.cards) > MAX_CARDS`. The canonical pool has **131 cards**. This must be repaired properly through the native card-index representation before whole-pool native tests or AI balancing can be trusted; increasing only the constant is unsafe. Separately, the current `cards/combat-reference.md` warns that Attacks, Boons and afflictions are not yet fully implemented in the native runtime. The 34 combat proposals must not be confused with live abilities.

### Mechanical duplication and weak floors

- **Four exactly matching gameplay groups** (by type, cost, printed Strength, class set and executable effects): The Fifty Men / The Damar; The Red Duelists / The Ilyri; The First Spear / The King's Spears; and seven 1C/+1 Strength blank Bonds.
- **Other likely inferior options:** The Old Guard (2C/3 Guard) against 2C/4 Guards; The Crow Archers (2C/3 Human Archer) against The Thornbow Hunters (same cost and Strength, also Scout, plus vision); Mara against Lysa the Listener (same hand peek but Lysa also Seer); Watched the Skies For (1C/0 Strength with no text) against 1C/+1 blank Bonds. A card being cheaper than another or belonging to a different class is **not** by itself proof of domination.
- **The Lines Held** costs 3 Command and can prevent at most 2 lost-Front Command reductions. On Command alone it cannot pay back its cost, let alone its Action. It needs a compelling second purpose or revised payoff.
- **Fresh Orders** costs 0 Command but spends a card and an Action just to draw one random card (conditional on King/Captain). It replaces itself rather than improving board state or hand size; evaluate whether thinning alone is worth it.
- **The Wolf Skirmishers** (internal id `the-ash-bowmen`) has an Archer-dependent PLAY effect but its **Build & Chain** exploratory deck contains no Archer carrier. The ability cannot trigger in that deck.

### Trigger reliability and decision costs

- The Wall Did Not Break costs 2 Command plus an Action and still needs Named Guards/Strongholds for normal Maneuvers; free Command may be weak if players cannot profitably spend enough Maneuver Actions.
- The Banner Singers requires a Named Middle Force and opposing Tactics targeting another friendly formation; Supported By requires Bonded Middle placement and an occupied Rear. Both are coherent but risk low use rates.
- The Crows Came Down costs 2 Command to play and 1 Command per activation for repeated Exhaustion; assess multi-Battle payoff versus one-shot Tactics.
- The Raiders Came Home Loaded discounts only sufficiently expensive eligible Tactics; the Narrative itself consumes 1 Command and an Action.
- Information-only cards need a second payoff when no opposing face-down Stratagem exists, or a clearly accepted deliberate risk.

### Card-text correctness

Four Narratives implement `limit: once_per_battle` for ACTION abilities but do **not** print that limitation: **The Crows Came Down**, **No Road Was Too Long**, **No One Would Be First to Leave**, and **The King Had Given the Order**. The printed face must be brought into agreement with the executable rule; do not make an ability unlimited solely to match an omission.

## Priority-ranked revision plan

1. **Fix game truth before balancing:** native identity cap / signed codes; implement and verify Attacks, afflictions, screening and Boons; resolve the four unprinted ACTION limits.
2. **Repair clearly poor choices:** The Lines Held, Watched the Skies For, Fresh Orders, and the Archer prerequisite on The Wolf Skirmishers or its deck.
3. **Replace duplicate bodies and Bonds with sidegrades, not buffs.** Keep a few clean benchmarks, but vary Strength, cost, row positioning, deployment, movement or interaction on the rest. Avoid simply making all plain cards stronger.
4. **Strengthen actual battlefield stakes:** prioritize changing occupancy, who can Attack whom, screening, reinforcement timing, attaching or losing Bonds/Names, and temporary condition interactions over more class-only +1 Strength effects.
5. **Differentiate archetype signatures:** Ships should transport or raid, Seers should alter information/timing, Stewards should move prepared assets, Guards should screen or cover positions, and Raiders/Skirmishers should exploit distinct openings. Resist adding generic class synergy numbers.
6. **Test combo formation rates and counterplay:** does a card have at least one legal attractive use in ordinary early and late Battle states? Does its effect change a real decision rather than marginal Strength? Can the opponent respond? Is the two-Action turn limit meaningful?
7. **Watch physical complexity:** no additional player-facing keywords until they replace more text than they add; a buried Force/Bond must not require lifting the stack.

## Targeted test scenarios

These test decision structure first, not win rates. Start with the printed rules and move to native simulation **after** the implementation parity blockers are resolved.

| Setup | Meaningful choice and counterplay | What would constitute evidence |
|---|---|---|
| **Break an enemy Front.** Friendly Skirmisher and Raider face an opposing Frontline Force; its Middle row is empty. | Play The Line Was Baited to push the defender into Middle, then use the Raider basic Attack against the newly exposed formation. Opponent can occupy its Middle row or contest the Skirmisher. | Legal two-Action sequence changes Attack eligibility rather than merely giving +Strength; works without card-specific exceptions |
| **Guard screening puzzle.** Opposing Middle Guard protects a Rear Force; friendly Skirmisher and Archer can Attack in the same Front. | Shake or Deplete the Guard so screening fails, then Attack the exposed Rear. Opponent may prioritize defending Guard or moving Rear. | At least two viable target/Action orderings with counterplay, consistent temporary markers |
| **Complete a formation from reserve.** Frontline Force with Bond, Middle Field Train, prepared Name behind it. | Attach the Name through the Train, creating a Named Formation for later Maneuvers. Counterplay can pressure the Frontline or prevent preparation. | Actions/card placement produce a real timing advantage over playing the Name directly |
| **Outflank or withdraw.** Grey Riders, a friendly Rider source and at least one adjacent active Front with opposing forces. | Rider movement can threaten a different Frontline; The Battle Turned East rewards committing to one move. | Players trade Actions, Command and rank exposure to alter a flank, not merely farm a numerical buff |
| **Change the whole geography.** Two adjacent active Fronts have materially different friendly Force/Bond/Name layouts. | No Road Was Too Long swaps complete friendly Front columns. Opponent can pre-position to make either destination dangerous. | More than one Front outcome or subsequent maneuver changes; no illegal rank occupancy |
| **Hidden-plan duel.** Teren can set a Stratagem, opposed by a Scout and The Scouts Found the Gap. | Free Stratagem timing versus the Scout's decision to reveal and tax the plan. | Information meaningfully changes when to play/withhold Tactics or which Front to contest |
| **Defensive tax stack.** Named Banner Singers in Middle with another friendly target; Held the Line for and an enemy Tactic. | Verify which targeted Tactics pay which surcharges and whether 1C/2C Tactics remain legal. | Stacking is transparent, does not unintentionally deny all counterplay, and is worth its setup |
| **Economic nonbo.** The Lines Held, Command about to be lost on Front resolution. | Compare playing the 3C Stratagem against holding it and absorbing up to two 1C Front penalties. | A legal state where paying to play improves survival or long-run Command; otherwise rework |

For each scenario record legal Actions, Command and Action deltas, board positions before/after, counterplay, whether a Named/Bonded gate delayed the combo, and whether the effect remained relevant by Battle III or later.

## Audit rubric (all 131 identities)

Statuses below are **qualitative**, not measured win rates: **Signature** is a distinct battlefield/tempo decision or combo anchor; **Keep** is useful identity or deliberate uncomplicated glue; **Glue** is a plain reference body/layer; **Test** has a narrow payoff or questionable cost; **Rework** is redundant, outclassed, inapplicable or economically unsound. The note describes why the status was assigned; it does not add executable behavior.


### Forces

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| The Fifty Men | **Rework** | Same 2C/4 Strength Human as The Damar, while equivalent Guard Forces gain screening |
| Seven Black Ships | **Signature** | Breaks attachments behind an empty opposing Frontline |
| The White Hands of Elara | **Keep** | Negative-marker recovery |
| The Red Shields | **Keep** | Front-row self-protection has a meaningful positional tax |
| The Crow Archers | **Rework** | 2C/3 Human Archer is weaker than same-cost Thornbow Hunters with Scout and Rear ability |
| The House of Reed | **Signature** | Moves prepared layers onto the Frontline |
| The Grey Riders | **Signature** | Unbonded and Exhausted movement flexibility |
| The Dust Riders | **Signature** | Combines Rider and Skirmisher Attacks after activation |
| The Black Pursuers | **Test** | High total spending and an Exhausted target with an attached component |
| The Red Duelists | **Rework** | Same 2C/3 Strength Human Skirmisher as The Ilyri; compare Dust Riders |
| The Thornbow Hunters | **Test** | Largely upgrades Crow Archers with a free Scout class and passive vision |
| The Iron Boars | **Keep** | Uncomplicated 3C Raider body with intrinsic Attack |
| The First Spear | **Keep** | One clear 2C/4 Strength Guard reference body |
| The Old Guard | **Rework** | 2C/3 Guard loses a full Strength to otherwise equivalent 2C/4 Guards |
| The Salt-Road Reavers | **Keep** | steal command |
| The Late Banner | **Keep** | slot discount |
| The Banner Singers | **Test** | Needs Force + Bond + Name and Middle placement for a conditional Tactic tax |
| Thirty Spears | **Keep** | Good minimal 1C/3 Strength Force benchmark |
| A Hundred Shields | **Keep** | Simple big Guard body at meaningful cost |
| The Vardai | **Keep** | Relocates itself at an additional Command + Action cost |
| The Aradai | **Test** | Cheap 2C Raider has no printed payoff; compare Ship/Raider and other Raider alternatives |
| The Ilyri | **Rework** | Same 2C/3 Strength Human Skirmisher as The Red Duelists; compare Dust Riders |
| The Damar | **Rework** | Duplicate of The Fifty Men, and weaker than 2C/4 Guard options |
| The Serekh | **Keep** | Frontline protects the friendly Middle row |
| The Relief Column | **Keep** | Middle-row protected-movement support |
| The Field Train | **Signature** | Middle-rank logistics using a prepared component |
| The Signal Company | **Signature** | Allows an Unnamed Frontline to Maneuver |
| The Wolf Skirmishers | **Rework** | The Wolf Skirmishers need a friendly Archer, absent from their Build & Chain test deck |
| The Lantern Scouts | **Keep** | Accessible 1C Scout with backline information |
| The River Raiders | **Keep** | Attachment raid |
| The King's Spears | **Rework** | Mechanically identical to The First Spear (same cost, Strength, classes) |
| The Salt-Road Fleet | **Test** | PLAY transport needs occupied friendly source and legal empty destination |
| The Watchtowers of Eren | **Keep** | Rear passive information role, though information payoffs require testing |

### Bonds

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| Followed | **Keep** | Bond Strength bonus |
| Guarded | **Keep** | Negative-marker recovery |
| Stood Fast With | **Keep** | Keep as explicit reference 1C/+1 Strength Bond |
| Marched With | **Keep** | Positional displacement |
| Kept Pace With | **Keep** | Hand filtering |
| Covered the Withdrawal of | **Keep** | tireless |
| Blocked the Road for | **Rework** | Generic 1C/+1 Bond repeated seven times; flavor promises a road effect |
| Held the Line for | **Keep** | Tactic protection tax |
| Seized the Standard of | **Rework** | Generic 1C/+1 Bond repeated seven times; title suggests a raid |
| Stayed Behind For | **Keep** | Prepared-card logistics |
| Swore Again To | **Rework** | Generic 1C/+1 Bond repeated seven times; name suggests an oath payoff |
| Endured With | **Rework** | Generic 1C/+1 Bond repeated seven times; name suggests resistance |
| Rallied Behind | **Keep** | Command restoration |
| Bought Time For | **Keep** | optional extra payment draw |
| Trusted | **Keep** | tireless |
| Marched Beneath the Banner of | **Keep** | Bond Strength bonus |
| Carried the Oath of | **Rework** | Generic 1C/+1 Bond repeated seven times; name suggests an oath payoff |
| Had Been Ordered Forward | **Rework** | Generic 1C/+1 Bond repeated seven times; name suggests deployment |
| Watched the Skies For | **Rework** | 1C/0 Strength Bond with no text is below 1C/1 Strength blank Bonds |
| Kept the Gate For | **Keep** | tireless |
| Shared the Spoils With | **Keep** | steal command |
| Carried Messages For | **Keep** | Hand filtering |
| Supported By | **Test** | Bonded Middle-to-Rear Tactic tax depends on three aligned ranks and enemy targeting Rear |
| Supplied By | **Keep** | Prepared-card logistics |

### Names

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| Namar | **Keep** | Command restoration + next slot discount |
| Iria | **Keep** | Deck ordering |
| Oren | **Signature** | Creates/attaches a Bond and filters cards |
| Elian | **Keep** | Positional displacement |
| Teren | **Signature** | Sets a Stratagem without another Action |
| Mara | **Rework** | Same hand-peek-on-Named as Lysa, but Lysa also carries Seer |
| Asha, the Shield-Bearer | **Keep** | Negative-marker recovery + redirect tactic |
| Edrin | **Keep** | Command restoration + prevent negative marker |
| Sela | **Keep** | Positional displacement + tireless |
| Meren | **Keep** | recover |
| Tala | **Signature** | Debuffs and suppresses a Bond in a single Formation |
| Sorin | **Keep** | draw put top |
| Iven | **Keep** | Command restoration + global discount |
| Arel | **Signature** | Classification buff plus vertical swap |
| Torren | **Signature** | Turns a Name completion into an extra Bond deployment |
| Eira | **Keep** | draw |
| Corin of the High Wall | **Keep** | add strength marker + local class aura |
| Lysa the Listener | **Keep** | look hand |
| Brannoc | **Keep** | Attachment raid + prepared pay or return |
| Maelin | **Keep** | Exhaustion recovery + Tactic protection tax |

### Heros

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| Avaros, the Bronze King | **Keep** | Strength allocation + Command restoration + choose class strength |
| Kael, the Roadless | **Keep** | Positional displacement + Hidden-Stratagem information |
| Rovan, the Gatebreaker | **Signature** | Prepared disruption, suppression and taxation |
| Alda, Keeper of the Ford | **Keep** | Tactic protection tax + Negative-marker recovery + redirect tactic |
| Tovan, the Quartermaster | **Keep** | Hand filtering + Command restoration + global discount split |
| Nara, Builder of Walls | **Signature** | Moves prepared cards or recovers a Bond |
| Neris, the Ferryman | **Signature** | Force/Name alternatives for formation movement |
| Veyra, Keeper of Oaths | **Keep** | Negative-marker recovery + grant name suppression immunity + Tactic protection tax |
| Yara, the Chronicler | **Signature** | Card selection and discarded Narrative recursion |
| Serai, Queen of Crows | **Keep** | self strength + class strength markers + add strength marker |
| Doros, the Last Spear | **Keep** | self strength + Command restoration + prevent tactic strength reduction; positional or class gate |

### Tactics

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| The Baggage Was Abandoned | **Test** | 2C Rear Exhaustion loses meaning if target is already Exhausted |
| They Returned With Names | **Keep** | suppress name |
| They Were Gathering There | **Keep** | Exhaustion pressure; positional or class gate |
| The Muster Was False | **Keep** | return prepared |
| They Had Gone Too Far | **Signature** | Forces an opposing formation Rearward |
| All Banners Forward | **Keep** | suppress action |
| The Line Wheeled | **Keep** | suppress bond |
| They Let Them Through | **Keep** | suppress limited |
| All Reserves Forward | **Keep** | Attachment raid |
| The Line Had Begun to Move | **Keep** | tax |
| A Volley Before Dawn | **Keep** | add strength marker; positional or class gate |
| The Scouts Found the Gap | **Signature** | Exposes and taxes a hidden Stratagem |
| The Stores Were Taken | **Keep** | prepared pay or return; positional or class gate |
| The Line Was Baited | **Signature** | Skirmisher-gated free Rearward displacement |

### Stratagems

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| The Ground Was Held | **Signature** | Named-vs-Unnamed tie reversal |
| The Lines Held | **Rework** | 3 Command paid to prevent at most 2 Command of Front losses |
| No Step Back | **Keep** | hidden cancel tactic |
| The Center Must Hold | **Keep** | hidden buff targets; positional or class gate |
| The Flank Was Refused | **Test** | Can only reveal in outer Fronts, which do not exist in Battle I |
| The Trap Closed | **Signature** | Temporary-marker combo, needs a reliable producer |
| The Battle Turned East | **Keep** | hidden buff moved source; positional or class gate |
| There Was No Road Back | **Keep** | hidden draw discard |
| Every Banner Turned Toward Them | **Keep** | Leadership Strength boost; positional or class gate |
| The Archers Were Ready | **Test** | +2 Strength may not counter a Tactic that moves or suppresses its target |
| The Scouts Had Warned Them | **Test** | Hidden reaction requires opponent to set a Stratagem near Scout/Seer; low trigger rate |

### Narratives

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| The Long March | **Signature** | Rider movement without Command costs |
| The Wall Did Not Break | **Test** | 2C + Action before discounts pay back; ability still requires Named Maneuvers |
| The Crows Came Down | **Test** | 2C Narrative + 1C per use + Action; assess payoff versus instant Archer Tactics |
| Before Sunset, the Ford Would Be Ours | **Test** | Does nothing when opponent has no hidden Stratagem; Ships merely duplicate Scout eligibility |
| They Lived to Tell It | **Test** | Needs a negative marker and an Action after playing the Narrative; repeatability must pay off |
| No Road Was Too Long | **Test** | Action is limited to once per Battle in engine, not printed; verify balance of 4C |
| The Battle Had Chosen Them | **Keep** | status strength aura |
| No One Would Be First to Leave | **Test** | Recovery costs 2C to play and 1C per use, with Action; per-battle limit is not printed |
| The King Had Given the Order | **Test** | Powerful unusual effect, but 1/BATTLE execution limit is not printed |
| Every Bow Was Strung | **Keep** | Archer Strength support |
| They Knew the Ground | **Keep** | pick top to hand bottom rest; positional or class gate |
| The Raiders Came Home Loaded | **Test** | 1C Narrative + Action saves 1C only on eligible >1C Tactics; check payback rate |

### Orders

| Card | Review | Mechanical contribution or concern |
|---|---|---|
| Fresh Orders | **Rework** | 0C + 1 Action to spend one card and draw one: little immediate hand or board improvement |
| Catch Your Breath | **Keep** | Exhaustion recovery |
| Re-form the Line | **Keep** | Formation swap |
| Bind the Wound | **Keep** | Negative-marker recovery; positional or class gate |
| Send a Runner | **Keep** | Hand filtering; positional or class gate |
| Take Stock | **Keep** | pick top to hand bottom rest; positional or class gate |

## Definition of done for the next card pass

For each changed card, keep its authored identity and art; update `text`, `effects`, `rule_blocks`, `design_rules`, and any exposed physical strip together. Avoid changing basic Attacks or Guard screening by accident. Require one deterministic example where the effect is legal/useful and one counterexample where it should not fire. Recompute deck pairings and the reference matrix from canonical cards; retain all 131 identities. Do not use mutable card-text expectations as broad CI blockers during active design.

