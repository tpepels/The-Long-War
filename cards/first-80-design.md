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
| 4 | **Held Fast** | Bond | 1 | - | **This formation gets +2 Strength.** | Pure baseline Bond. |
| 5 | **Followed** | Bond | 1 | - | **This formation gets +1 Strength. While it is Named, it gets +2 more.** | Teaches the value of completing a Named Formation. |
| 6 | **Namar** | Name - Human, King - Unique | 1 | +1 | **When this formation becomes Named, regain 1 Command.** | Simple completion payoff. |
| 7 | **Oren** | Name - Human, Warrior - Unique | 2 | +2 | **When this formation becomes Named, draw 1 card.** | Simple completion payoff with card flow. |
| 8 | **Avaros, the Bronze King** | Hero - Human, King - Unique | 3 | Force: 5 | **Force:** Swordsman. **Deploy - Frontline only.** After Avaros Maneuvers, you may Maneuver one adjacent friendly Named Formation without paying Command. **Name:** When this formation becomes Named, you may Maneuver it once without paying Command. | Maneuver-focused Hero; both modes change board position rather than adding Strength arithmetic. |

### Batch 1 notes

- **The Fifty Men** and **Seven Black Ships** establish the basic positional baseline through their roles rather than extra rules text.
- **The White Hands of Elara** is intentionally simple. Its final cost may need tuning because Healer converts Rear presence into effective Front strength.
- **Held Fast** is intentionally plain. The set needs uncomplicated Bonds that establish the baseline value of a Bond.
- **Followed** is conceptually approved; the +1 / +2 numbers remain balance targets rather than locked values.
- **Namar** is allowed to be unusually Command-efficient as a distinctive completion reward, but this should not become a common pattern.
- **Oren** is conceptually approved; its persistent value plus card replacement should be tested carefully.
- **Avaros** should remain about Maneuver and battlefield command, not generic Strength bonuses. His exact wording may be tightened once card-triggered Maneuver is represented in the engine.

## Design guardrails established so far

- Prefer cards that interact with existing core rules instead of introducing new subsystems.
- Avoid arithmetic-heavy designs whose main identity is stacking Strength modifiers.
- Most cards should do one clear thing.
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
| 9 | **The Red Shields** | Force - Human, Guard - Spearman | 2 | 4 | **Deploy - Frontline only.** |
| 10 | **The Crow Archers** | Force - Human, Company - Archer | 2 | 4 | **Deploy - Rear only.** |
| 11 | **The House of Reed** | Force - Place, Stronghold | 2 | 3 | **Stronghold. Deploy - Rear only.** Cannot move, Maneuver, or swap positions. If you lose this Front while you have a Named Formation in the Frontline, drive off this Stronghold instead of Retreating that formation. |
| 12 | **The Grey Riders** | Force - Human, Riders - Skirmisher | 2 | 2 | **Skirmisher.** May Maneuver even while not Named. When Fronts are resolved, choose this Front or one adjacent Front. The Grey Riders contribute their Strength to the chosen Front instead of their own. |
| 13 | **Guarded** | Bond | 1 | - | Opponent card effects cannot move this formation. |
| 14 | **Marched With** | Bond | 1 | - | When you play this Bond onto a Force, you may move that formation to an adjacent empty position. |
| 15 | **Iria** | Name - Human, Seer - Unique | 1 | +1 | Whenever an opposing formation in this Front becomes Named, your next Maneuver this Battle costs 0 Command. Additional triggers do not accumulate. |
| 16 | **Elian** | Name - Human, Wanderer - Unique | 1 | +1 | When this formation becomes Named, you may swap it with an adjacent friendly formation. |

### Batch 2 role definitions

**Stronghold**
- Deploy - Rear only.
- Cannot move, Maneuver, or swap positions.
- If its controller loses the Front while a Named Formation is in the Frontline, drive off the Stronghold instead of Retreating that formation.

**Skirmisher**
- May Maneuver even while not Named.
- At Front resolution, may contribute its Strength to its own Front or one adjacent Front, not both.

### Batch 2 notes

- **The Three Brothers of Avar** were not included in this approved batch; the Skirmisher slot adds more positional vocabulary.
- Stronghold is intentionally low-Strength. Its value is defensive structure, not winning through raw arithmetic.
- Skirmisher creates lateral pressure without attacks, damage, wounds, or a separate combat step.
- Iria changes Maneuver cost rather than moving automatically. Her discount lasts only for the current Battle and does not accumulate.
