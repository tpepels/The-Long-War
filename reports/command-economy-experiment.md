# Command economy experiment

Tested gameplay revision: `2b4aebcdafaca83991417f5369179fcff89d3e7c`

Workflow: **Command Economy Experiment** run `35854387681`

Scope: **4,000 heuristic mirror matches / 10,277 Battles**, 1,000 matches each with the Reference, Avaros, Mara and Sera Name-rich decks.

The branch remains experimental. `main` was not changed.

## Prototype rules

The core rules added by this experiment are deliberately small:

- each player starts the match with **20 Command**;
- unused Command carries between Battles;
- at the start of each later Battle, gain **10 Command**, to a maximum of **20**;
- take exactly **one operation per turn**;
- **Play** a card: pay the Command cost printed on the card;
- **Cycle**: pay 1 Command, discard one card, draw one card;
- **Pass**: cost 0;
- there is no generic Draw operation.

All other added complexity is card text.

## Printed cost model

Every card receives a computed internal power value and then a printed Command cost:

- value below 2.5 -> **1 Command**
- value below 5.5 -> **2 Command**
- otherwise -> **3 Command**

The cost calculation uses Strength, effect value, reliability/conditions, restrictions and flexibility. `tools/compute_command_costs.py` checks that the stored card costs still match the model.

Current pool:

| Cost | Cards |
| ---: | ---: |
| 1 | 15 |
| 2 | 31 |
| 3 | 2 |

By type:

| Type | Mean cost | Distribution |
| --- | ---: | --- |
| Subject | 2.00 | 2x1, 10x2, 2x3 |
| Bond | 1.56 | 4x1, 5x2 |
| Name | 1.14 | 6x1, 1x2 |
| Story | 1.70 | 3x1, 7x2 |
| Stratagem | 2.00 | 8x2 |

A typical Subject + Bond + Name formation therefore costs roughly **4.7 Command** before discounts/refunds.

## Redesigned Names

The seven existing Names now carry the utility ideas rather than primarily adding raw Strength.

- **Namar — economy:** when the formation first has a Subject, Bond and Name, regain 1 Command.
- **Iria — movement:** when played onto a Subject, may move that formation to an adjacent empty position.
- **Oren — filtering:** when the formation first has all three components, the next Cycle this Battle costs 0.
- **Teyra — information:** on three-component formation, reveal the opposing Veiled Story in that Front.
- **Maela — protection:** while the formation has all three components, its Subject cannot be chosen by an opponent's immediate Story.
- **Vara — recovery:** on three-component formation, return the most recently discarded Bond to hand.
- **Elian — adjacency/economy:** while the formation has all three components, cards played into adjacent Fronts cost 1 less Command, minimum 1.

This leaves the core rules small while putting tactical complexity onto individual cards.

## Aggregate result

| Metric | Command prototype |
| --- | ---: |
| Battles/match | 2.569 |
| Cards/Battle | 12.05 |
| Complete formations/Battle | 1.37 |
| Names/Battle | 2.21 |
| Cycles/Battle | 1.52 |
| Legal choices/decision | 32.10 |
| First-passer Battle WR | 20.7% |
| First-player match WR | 45.9% |
| Command at Pass | 7.55 |
| Passes at 0 Command | 9.6% |
| Battle-I loser wins match | 27.4% |
| Command spent/player/Battle | 10.77 |
| Command refunded/player/Battle | 0.10 |
| Command remaining/player at Battle end | 7.55 |
| Battle-I winner minus loser Command | **-2.29** |
| Command entering next Battle/player | 17.09 |

## Per-archetype result

| Profile | Complete/Battle | Cards/Battle | Names/Battle | Cycles/Battle | Choices | First-pass WR | First-player WR | Battle-I winner minus loser Command | Battle-I loser wins match |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Reference | 1.23 | 11.90 | 2.35 | 1.46 | 33.61 | 18.8% | 44.0% | -2.67 | 28.6% |
| Avaros | 1.53 | 12.05 | 2.29 | 1.52 | 32.59 | 21.2% | 44.0% | -1.94 | 26.5% |
| Mara | 1.31 | 12.22 | 1.96 | 1.62 | 30.49 | 24.0% | 46.5% | -2.26 | 27.5% |
| Sera | 1.41 | 12.04 | 2.24 | 1.46 | 31.73 | 18.9% | 48.9% | -2.30 | 27.1% |

The same qualitative behavior appears in all four profiles.

## Comparison with the previous 30/10 candidate

The previous higher-sample Name-rich 30-card / 10-card / recycle candidate with selective completion-draw produced approximately:

| Metric | Previous 30/10 | Command prototype |
| --- | ---: | ---: |
| Complete formations/Battle | 1.50 | 1.37 |
| Names/Battle | 2.74 | 2.21 |
| Cards/Battle | 14.72 | 12.05 |
| Legal choices/decision | 24.82 | 32.10 |
| First-passer Battle WR | 58.5% | 20.7% |
| First-player match WR | 47.2% | 45.9% |

This comparison is deliberately a whole-package comparison: the Command prototype also replaces the old completion-draw test abilities with the seven actual Name identities.

## Interpretation

### Carry-over creates attrition rather than snowballing

This is the strongest positive result.

The winner of Battle I ends that Battle with **2.29 less Command than the loser on average**. The difference is negative in every deck profile.

If later Battles were independent 50/50 contests, a player who lost Battle I would have to win both remaining Battles and would win the match 25% of the time. The observed rate is **27.4%**.

That does not prove an ideal comeback mechanism, but it provides no evidence of a Command snowball. The direction is instead consistent with the intended attrition effect: securing a Battle tends to cost resources that the opponent can preserve.

### Command is meaningful but not normally exhausted

Players spend **10.77 Command per player per Battle** and pass with **7.55** remaining. Only **9.6%** of Passes happen at zero Command.

Later Battles begin with an average **17.09 Command** after carry-over and replenishment.

The resource therefore constrains choices without usually forcing the Battle to end through exhaustion.

### Cycle is used substantially

The agent Cycles **1.52 times per Battle**.

This shows that paid discard/draw is functioning as a real hand-correction mechanism, not dead rules text.

It also explains a large part of the lower card-play count: turns are being spent improving the hand rather than deploying cards.

### Formation completion fell, but not dramatically

Complete formations fell from roughly **1.50 to 1.37 per Battle** while cards played fell from **14.72 to 12.05**.

The cost curve itself does not appear prohibitively expensive: the average Subject costs 2.0, Bond 1.56 and Name 1.14.

The reduction is therefore better understood as a consequence of the new strategic economy: Cycle consumes turns and players preserve Command for later Battles.

### First Pass changed meaning

The first passer wins only **20.7%** of Battles, consistently across archetypes.

Under persistent Command this should not be interpreted the same way as the old first-passer statistic. Passing first is now frequently an intentional concession that preserves resources for a later Battle. The Battle-I loser match result supports that reading.

This metric still deserves human playtesting because the system should not make conceding a Battle too automatic or obvious.

### Decision space increased

Mean legal choices increased from about **24.8 to 32.1**.

Most of this comes from Cycle: every distinct card in hand is a possible card to discard. The core rules remain simple, but the tactical option count is higher.

This is the main complexity cost of the prototype and should be watched in human play.

### Card-level Command generation is currently modest

Only **0.10 Command/player/Battle** is refunded on average.

So the current economic card effects are not driving or destabilizing the resource system. If anything, Command refunds/discounts remain a relatively light layer on top of the base economy.

## Current assessment

The prototype successfully demonstrates the parts that were uncertain:

- persistent Command is mechanically viable;
- 20 / +10 / cap 20 does not normally exhaust players;
- carrying resources creates measurable cross-Battle attrition;
- the Battle winner tends to spend more than the loser;
- paid Cycle is used and solves hand access without a generic Draw rule;
- the seven Name utility identities can live on cards without expanding the universal operation list;
- systematic 1/2/3 printed costs are viable.

It also identifies two costs:

- fewer cards and slightly fewer completed formations are played per Battle;
- Cycle increases the decision space substantially.

There is not yet evidence that the printed card-cost curve itself needs changing. The next useful evidence should come from human play with the Command prototype, especially whether 20 Command feels consequential without feeling like accounting, whether ~1–2 Cycles per Battle feels natural, and whether strategic early concessions feel satisfying rather than automatic.
